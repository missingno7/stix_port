"""Record (and, once a native tick exists, verify) Stix game-tick demos.

The tick demo is the mode-independent equivalence proof (c64_re.tick_demo):
per game tick it stores the consumed input + a digest of gameplay-owned
state, so it replays IDENTICALLY in pure-ASM, hybrid, and VM-less native
modes.  The native `play_native` is "done" when it reproduces a tick demo's
digest at every tick over the whole demo corpus.

    python scripts/tickdemo.py record --demo artifacts/demos/demo_run1_...
    python scripts/tickdemo.py verify --tickdemo artifacts/ticks/run1.tickdemo   # (needs the native tick)

`record` drives the ASM oracle through an input demo and captures the tick
timeline to artifacts/ticks/<name>.tickdemo (gitignored — it embeds a 64K
RAM seed = game state).  `verify` replays that timeline on the VM-less
native core (stix.native) and asserts the digest matches every tick.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

from c64_re.input_demo import InputDemoPlayback  # noqa: E402
from c64_re.runtime import run_frames  # noqa: E402
from c64_re.tick_demo import TickDemo  # noqa: E402
import stix.tick as tickmod  # noqa: E402
from stix.input_waits import is_input_wait  # noqa: E402

TICKS = PORT_ROOT / "artifacts" / "ticks"


def _advance_fn(demo: InputDemoPlayback, rt, frame_limit=None):
    def advance() -> bool:
        b = rt.machine.vic.frame
        if demo.finished(b) or (frame_limit is not None and b >= frame_limit):
            return False
        demo.apply_to_runtime(b, rt, single=is_input_wait(rt))
        run_frames(rt, 1)
        return True
    return advance


def record_from_demo(demo_path: str, *, frame_limit=None, max_ticks=100_000) -> TickDemo:
    demo = InputDemoPlayback.load(demo_path)
    rt = demo.make_runtime()
    return tickmod.record(rt, _advance_fn(demo, rt, frame_limit), max_ticks=max_ticks)


def cmd_record(args) -> int:
    td = record_from_demo(args.demo, frame_limit=args.frames or None)
    name = args.name or Path(args.demo).name.replace("demo_", "").rstrip("/")
    TICKS.mkdir(parents=True, exist_ok=True)
    out = TICKS / f"{name}.tickdemo"
    td.save(out)
    evo = len(set(td.digests))
    print(f"recorded {td.n_ticks} ticks ({evo} distinct digests, "
          f"key record {len(td.keys[0]) if td.keys else 0}B) -> {out}")
    if td.n_ticks == 0:
        print("WARNING: 0 ticks — check the seam PCs in stix/tick.py")
        return 1
    return 0


def cmd_verify(args) -> int:
    td = TickDemo.load(args.tickdemo)
    try:
        from stix.native import make_state, inject, tick  # noqa: F401
    except ImportError as exc:
        print(f"native tick not available yet ({exc}); nothing to verify against.")
        print(f"tick demo has {td.n_ticks} ticks ready as the equivalence target.")
        return 1
    from c64_re.tick_demo import verify_ticks
    state = make_state(td.seed)
    matched, divergence = verify_ticks(td, state, inject=inject, tick=tick,
                                       digest=tickmod.digest)
    if divergence is None:
        print(f"NATIVE == ORACLE: all {td.n_ticks} ticks matched byte-for-byte.")
        return 0
    print(f"diverged after {matched}/{td.n_ticks} ticks: {divergence}")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["record", "verify"])
    ap.add_argument("--demo", default="")
    ap.add_argument("--tickdemo", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--frames", type=int, default=0, help="limit (0 = whole demo)")
    args = ap.parse_args()
    if args.phase == "record":
        if not args.demo:
            ap.error("record needs --demo")
        return cmd_record(args)
    if not args.tickdemo:
        ap.error("verify needs --tickdemo")
    return cmd_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
