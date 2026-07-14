"""The recovery grind: lift + differentially verify Stix routines against a
recorded full-game demo (the oracle).

Phases (each resumable; state in artifacts/grind/):
  check    replay the demo twice, confirm bit-identical final state
  census   replay once, collect the JSR targets the playthrough actually
           calls + an executed-PC coverage bitmap  -> census.json
  lift     scan every called target; LIFTED vs structured REFUSED  -> manifest
  verify   install the lifted hooks, replay (windowed), route every call
           through the differential oracle (strict cycle model); routines
           with calls and zero divergences become ORACLE_PASSING
  report   print the manifest summary + coverage

Usage:
  python scripts/grind.py all    --demo artifacts/demos/demo_run1_...   [--verify-frames N]
  python scripts/grind.py census --demo ...
  python scripts/grind.py lift
  python scripts/grind.py verify --demo ... [--verify-frames N] [--entries $A,$B]
  python scripts/grind.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

from c64_re.hooks import HookRegistry  # noqa: E402
from c64_re.input_demo import InputDemoPlayback  # noqa: E402
from c64_re.lift.cfg import refuse_unsafe_callers, scan_function  # noqa: E402
from c64_re.lift.emit import lift_and_compile  # noqa: E402
from c64_re.lift.manifest import LiftManifest, LiftRecord  # noqa: E402
from c64_re.runtime import run_frames  # noqa: E402
from c64_re.verification import install_live_verifier  # noqa: E402
import stix  # noqa: E402

GRIND = PORT_ROOT / "artifacts" / "grind"
CENSUS = GRIND / "census.json"
MANIFEST = GRIND / "lift_manifest.json"


def state_digest(rt) -> str:
    h = hashlib.sha256()
    h.update(rt.mem.ram)
    h.update(rt.mem.color_ram)
    h.update(bytes(rt.machine.vic.regs))
    h.update(str((rt.cpu.s.as_dict(), rt.cpu.cycle_count,
                  rt.machine.vic.frame)).encode())
    return h.hexdigest()


def load_demo(path: str) -> InputDemoPlayback:
    return InputDemoPlayback.load(path)


def replay(demo: InputDemoPlayback, rt, *, max_frames: int | None = None,
           on_frame=None, progress_every: int = 500) -> int:
    """Drive ``rt`` through the demo.  Returns the frame reached."""
    demo.reset()
    end = demo.end_boundary
    limit = end if max_frames is None else min(end or max_frames, max_frames)
    t0 = time.time()
    while True:
        b = rt.machine.vic.frame
        demo.apply_to_runtime(b, rt, single=_is_input_wait(rt))
        if (limit is not None and b >= limit) or demo.finished(b):
            return b
        run_frames(rt, 1)
        if on_frame is not None:
            on_frame(rt, b)
        if progress_every and b and b % progress_every == 0:
            print(f"  frame {b}/{limit}  ({b/(time.time()-t0):.0f} fps)", flush=True)


def _is_input_wait(rt) -> bool:
    from stix.input_waits import is_input_wait
    return is_input_wait(rt)


# ---- check -------------------------------------------------------------------------
def cmd_check(args) -> int:
    demo = load_demo(args.demo)
    digs = []
    for i in range(2):
        rt = demo.make_runtime()
        reached = replay(demo, rt)
        digs.append(state_digest(rt))
        print(f"  run {i + 1}: reached frame {reached}")
    ok = digs[0] == digs[1]
    print(f"demo determinism: {'BIT-IDENTICAL' if ok else 'DIVERGED'}")
    return 0 if ok else 1


# ---- census ------------------------------------------------------------------------
def cmd_census(args) -> int:
    demo = load_demo(args.demo)
    rt = demo.make_runtime()
    called: set[int] = set()
    cov = bytearray(0x10000)

    def tracer(cpu, pc, op):
        cov[pc] = 1
        if op == 0x20:  # JSR: record the callee entry
            called.add(cpu.mem.rb((pc + 1) & 0xFFFF) | (cpu.mem.rb((pc + 2) & 0xFFFF) << 8))

    rt.cpu.trace_fn = tracer
    t0 = time.time()
    reached = replay(demo, rt)
    rt.cpu.trace_fn = None
    exercised = sum(cov)
    print(f"census: replayed {reached} frames in {time.time() - t0:.0f}s, "
          f"{len(called)} distinct JSR targets, {exercised} bytes of code touched")
    GRIND.mkdir(parents=True, exist_ok=True)
    CENSUS.write_text(json.dumps({
        "demo": str(Path(args.demo).name),
        "frames": reached,
        "called_targets": sorted(called),
        "exercised_bytes": exercised,
    }, indent=2), encoding="utf-8")
    print(f"  -> {CENSUS}")
    return 0


# ---- lift --------------------------------------------------------------------------
def cmd_lift(args) -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    targets = census["called_targets"]
    demo = load_demo(args.demo) if args.demo else None
    # a fresh cold runtime gives the code image as it stands after decrunch;
    # the demo runtime is the honest source (self-modified code included).
    rt = demo.make_runtime() if demo else None
    if rt is not None:
        replay(demo, rt, max_frames=args.image_frame)
    else:
        rt = stix.boot(PORT_ROOT / "assets")
        stix.start_game(rt)
        run_frames(rt, 60)
    manifest = LiftManifest.load(MANIFEST)
    scans = {entry: scan_function(rt.mem.rb, entry, max_instructions=args.max_instructions)
             for entry in targets}
    # Tier-2: a function that JSRs to a nonlocal_return target is ALSO unsafe
    # to lift standalone (its own emitted emulate_call for that JSR hangs) —
    # see c64_re.lift.cfg's module docstring.  Caught here, before verify
    # ever installs a hook for it.
    scans.update(refuse_unsafe_callers(scans))
    lifted = refused = 0
    for entry, scan in scans.items():
        if scan:
            lifted += 1
            manifest.update(LiftRecord(entry=entry, name=f"lifted_{entry:04X}",
                                       status="LIFTED", size_bytes=scan.size_bytes,
                                       instructions=len(scan.insns)))
        else:
            refused += 1
            manifest.update(LiftRecord(entry=entry, name=f"refused_{entry:04X}",
                                       status="REFUSED", refusal_reason=scan.reason))
    manifest.save(MANIFEST)
    pct = 100.0 * lifted / max(1, lifted + refused)
    print(f"lift census: {lifted} liftable, {refused} refused ({pct:.1f}%) "
          f"of {len(targets)} exercised routines")
    print(f"  -> {MANIFEST} ({manifest.summary()})")
    return 0


# ---- verify ------------------------------------------------------------------------
def cmd_verify(args) -> int:
    from collections import Counter

    demo = load_demo(args.demo)
    manifest = LiftManifest.load(MANIFEST)
    if args.entries:
        entries = _parse_entries(args.entries)
    else:
        entries = [r.entry for r in manifest.records.values() if r.status in ("LIFTED", "ORACLE_PASSING")]

    # Phase 1: obtain the code image to lift from (a throwaway runtime replayed
    # to image_frame, past decrunch and into gameplay).  The compiled hooks
    # carry their own SMC guard bytes, so they no longer depend on this runtime.
    img = demo.make_runtime()
    replay(demo, img, max_frames=args.image_frame)
    registry = HookRegistry()
    installed = {}
    for entry in sorted(set(entries)):
        try:
            hook, _, scan = lift_and_compile(img.mem.rb, entry, max_instructions=args.max_instructions)
        except Exception as exc:  # noqa: BLE001
            print(f"  ${entry:04X} lift failed at verify time: {exc}")
            continue
        registry.replace(entry, f"lifted_{entry:04X}")(hook)
        installed[f"lifted_{entry:04X}"] = (entry, scan)

    # Phase 2: a FRESH cold runtime with the hooks + verifier, replayed from
    # frame 0.  The hooks only fire once the game reaches each entry (bytes in
    # place); a guard mismatch fails loud and is caught as a divergence.
    rt = demo.make_runtime()
    registry.install(rt.cpu)
    print(f"verify: {len(installed)} lifted hooks installed; "
          f"replaying frames 0..{args.verify_frames}")

    verified: Counter = Counter()
    diverged: Counter = Counter()
    reasons: dict[str, str] = {}
    name_entry = {name: entry for name, (entry, _) in installed.items()}
    cap = args.cap

    def on_result(name, ok, reason):
        entry = name_entry[name]
        if ok:
            verified[name] += 1
            # Once a routine passes `cap` diverse calls with zero divergence it
            # is proven ORACLE_PASSING; route it to passthrough so it keeps
            # running as a hook but is no longer re-diffed (bounds the cost so
            # the WHOLE demo — edge cases, game-over — can be swept).
            if cap and verified[name] == cap and not diverged[name]:
                rt.cpu.hook_verifier_passthrough.add(entry)
        else:
            diverged[name] += 1
            reasons.setdefault(name, reason)
            # A wrong/runtime-patched lifted hook: UNINSTALL it so the original
            # ASM runs for the rest of the sweep (the verifier already rolled
            # the live state back to pre-hook).  Passthrough would keep running
            # the broken hook and could raise on a guard mismatch.
            rt.cpu.replacement_hooks.pop(entry, None)

    install_live_verifier(rt, on_result=on_result, raise_on_divergence=False,
                          strict_cycles=True)
    window = None if args.verify_frames <= 0 else args.verify_frames
    t0 = time.time()
    reached = replay(demo, rt, max_frames=window, progress_every=250)
    print(f"  verified window reached frame {reached} in {time.time() - t0:.0f}s")

    passing = fired = 0
    for name, (entry, scan) in sorted(installed.items(), key=lambda kv: kv[1][0]):
        ok, bad = verified[name], diverged[name]
        if bad:
            status = "DIVERGED"
            print(f"  {name}: {ok} ok, {bad} DIVERGED -- {reasons[name][:120]}")
        elif ok:
            status = "ORACLE_PASSING"
            passing += 1
            fired += 1
        else:
            status = "LIFTED"
        manifest.update(LiftRecord(
            entry=entry, name=name, status=status,
            size_bytes=scan.size_bytes, instructions=len(scan.insns),
            calls_seen=ok + bad, verified_calls=ok, diverged_calls=bad,
            notes=reasons.get(name, ""),
        ))
    manifest.save(MANIFEST)
    total_verified = sum(verified.values())
    print(f"\nverify done: {passing} ORACLE_PASSING, {total_verified} calls "
          f"verified, 0-divergence over {reached} frames")
    print(f"  -> {MANIFEST} ({manifest.summary()})")
    return 0 if not diverged else 2


# ---- report ------------------------------------------------------------------------
def cmd_report(args) -> int:
    manifest = LiftManifest.load(MANIFEST)
    print(f"lift manifest: {manifest.summary()}")
    passing = sorted((r for r in manifest.records.values() if r.status == "ORACLE_PASSING"),
                     key=lambda r: -r.verified_calls)
    print(f"\nORACLE_PASSING routines ({len(passing)}), by verified-call volume:")
    for r in passing[:40]:
        print(f"  ${r.entry:04X}  {r.instructions:3d} insns  {r.size_bytes:4d} B  "
              f"{r.verified_calls} calls verified")
    if CENSUS.exists():
        c = json.loads(CENSUS.read_text(encoding="utf-8"))
        print(f"\ncensus: {len(c['called_targets'])} exercised routines over "
              f"{c['frames']} frames; {c['exercised_bytes']} code bytes touched")
    return 0


def _parse_entries(text: str) -> list[int]:
    out = []
    for tok in text.replace(";", ",").split(","):
        tok = tok.strip().lstrip("$")
        if tok:
            out.append(int(tok, 16) & 0xFFFF)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["all", "check", "census", "lift", "verify", "report"])
    ap.add_argument("--demo", default="")
    ap.add_argument("--verify-frames", type=int, default=0,
                    help="verify window (0 = the whole demo)")
    ap.add_argument("--cap", type=int, default=50,
                    help="stop re-verifying a routine after this many clean calls")
    ap.add_argument("--image-frame", type=int, default=900,
                    help="replay to this frame to obtain the code image to lift from")
    ap.add_argument("--entries", default="")
    ap.add_argument("--max-instructions", type=int, default=768)
    args = ap.parse_args()

    if args.phase in ("all", "check", "census", "verify") and not args.demo:
        ap.error(f"phase {args.phase!r} needs --demo")

    if args.phase == "check":
        return cmd_check(args)
    if args.phase == "census":
        return cmd_census(args)
    if args.phase == "lift":
        return cmd_lift(args)
    if args.phase == "verify":
        return cmd_verify(args)
    if args.phase == "report":
        return cmd_report(args)
    if args.phase == "all":
        rc = cmd_check(args)
        if rc:
            print("determinism check failed; stopping")
            return rc
        cmd_census(args)
        cmd_lift(args)
        cmd_verify(args)
        return cmd_report(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
