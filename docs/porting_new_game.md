# Porting a new C64 game — the bring-up checklist

This is the concrete path from "an original disk image" to "the oracle-driven
recovery loop is running". The full method is in the DOS charter
(`template_dos_port/docs/ai_porting_charter.md` — platform-neutral); this
guide is the ordered to-do list with the `c64_re` touchpoints named.
[`pitfalls.md`](pitfalls.md) is the list of mistakes already made for you.

**Where this port sits:** Stix has completed steps 0–2 (load & run, see
output, wire input) — it boots from the original cracked D64 through
decruncher → trainer menu → gameplay → game over, deterministically. Current
phase, findings, and evidence-ordered next targets:
[`stix/run_status.md`](stix/run_status.md).

A few pieces below lean on machinery `c64_re` deliberately hasn't built yet
(see the "Deliberately not built yet" list in `c64_re/README.md`). Those
carry a "(planned)" marker — the method is the method; the tools land in
dependency order as the port needs them.

## Know your game's style first

The DOS-lineage source projects span the spectrum, and the recovery emphasis
differs; the same split exists on the C64:

- **Code-heavy procedural games**: behaviour lives in handler zoos, dispatch
  tables, runtime-patched routines (self-modifying code is *idiomatic* on the
  6502 — pitfall #15), IRQ-chained choreography. Expect to invest in handler
  classification, shared-primitive detection, routine-family grouping, and
  staticizing patched code — the goal is recovering the implicit
  actor/choreography model hiding inside the spaghetti, not rewriting each
  handler forever.
- **Data-driven games** (script/bytecode-interpreter engines, table-driven
  level machinery): behaviour lives in data the engine interprets. Expect to
  invest in loaders, format decoders, and verifying the interpreter's opcodes
  one by one — round-trip decode tests carry more of the proof there.

Most games mix both. Classify early (a few hours of tracing tells you), and
let it steer where the first islands go. No C64 port has been carried far
enough yet to serve as the worked example of either style; the DOS repos
(Overkill for code-heavy, the charter's data-driven notes) remain the
references.

## How the numbering systems line up

Three DOS-lineage docs count differently; they describe one process, and this
guide keeps the same step numbers:

| This guide (steps) | `lifecycle.md` (stages) | `ai_porting_charter.md` (phases) |
|---|---|---|
| 0–6 (bring-up: adapter, boot, output, boundaries, verifier, input waits, first demo) | Stage 0 | charter §9 (bootstrapping checklist) |
| 7 (the lifting loop) | Stages 1–2 | Phase 1 |
| 8 (coverage telemetry) | ongoing | §10 (metrics) |
| Endgame steps 1–5 | Stages 3–5 | Phases 2–6 |
| Endgame step 6 (enhanced layer) | Stage 6 | after Phase 6 |

(Both referenced docs live in `template_dos_port/docs/`.)

## 0. Set up the adapter

Copy the shape of this repo (`stix/` + `scripts/` + `docs/<game>/` + `tests/`)
into your own porting repo (`mygame_port/mygame/`). From day one, enforce the
boundaries: `c64_re` never learns your game's addresses, filenames, or
formats; your `recovered/` layer never imports `c64_re`. The automated lint
that enforces this is `python c64_re/tools/lint.py` (core stays stdlib-only;
adapter-package rules) plus `python c64_re/tools/audit_layers.py` (pure layers
never import the VM) — wire both into your adapter's suite from day one.

## 1. Load & run

```python
from c64_re.runtime import create_runtime, run_frames
rt = create_runtime("assets/MYGAME.d64")
print(f"entry ${rt.program.entry:04X}")
run_frames(rt, 300)
print(hex(rt.cpu.pc), rt.cpu.instruction_count)
```

The runtime parses the D64 directory, finds the boot PRG, reads the BASIC
stub's `SYS`, and jumps in — no BASIC ROM involved.

- **Crunched PRGs**: the decruncher is *bootstrap, not gameplay*. Let it run
  in the VM (Stix's runs out of the stack page, $0100), then snapshot past it
  (`c64_re.snapshot.write_snapshot(rt, path)` to a `.c64snap`;
  `load_snapshot(path)` resumes bit-identically, and `liftgen`/`liftverify`
  accept `.c64snap` images directly) and work from the decrunched image.
- **Fastloaders / multi-load games**: a game that bit-bangs the IEC bus
  bypasses the KERNAL LOAD trap and fails loud at the CIA2/IEC seam. That is
  correct behaviour — recover the loader as game-specific HLE serving the same
  bytes from the D64, never a silent skip (anticipated pitfall F).
- **When the interpreter fails loud** — an unstable illegal opcode, or a
  JAM-filled shim-KERNAL address — decode the exact instruction or service,
  implement only the required behaviour for the observed use, and add a
  focused test. Don't generalize beyond what the program proves it needs.
  Watch for games reading ROM *as data* (Stix copies the $FD30 vector table
  and the chargen): shim-ROM data reads are part of the contract (anticipated
  pitfall B).
- Add a snapshot point after init/first playable state: run the scripted
  deterministic boot once (`stix.boot()` + `stix.start_game()` is the worked
  shape), then `write_snapshot(rt, path)` — the `.c64snap` is the anchor.

## 2. See output, wire input

- See the screen: copy this repo's [`scripts/boot.py`](../scripts/boot.py) —
  it boots headless, renders PNG frames via `c64_re.pngout.save_frame_png`
  (the VIC model covers all screen modes and sprites), dumps screen RAM as
  text, and on a crash prints the disassembly around PC. The crash *is* the
  next work item.
- Watch it live: copy [`scripts/play.py`](../scripts/play.py) — a
  `c64_re.player.GameFrontend` subclass (arrows + Right-Ctrl = joystick,
  letter keys = the C64 matrix; F9 pause, F10 screenshot, F11 demo-record
  toggle, F12 snapshot). That IS your port's runner and the human owner's
  window from day one. The standardized `GameFrontend` CLI comes with it:
  `--headless`, `--frames`, `--snapshot`/`--save-snapshot`,
  `--record-demo`/`--play-demo`/`--demo-continue`, `--no-replacements`
  (oracle mode), `--verify-hooks`/`--trace-hooks`,
  `--joy-port`/`--scale`/`--fps`.
- Deliver input and confirm the game *sees* it. C64 games rarely use GETIN for
  gameplay: most poll the CIA1 matrix ($DC00/$DC01) or the joystick lines
  directly. Find where: Stix reads $DC01 raw for keys, polls joystick port 1
  for play, and uses KERNAL GETIN only in its trainer menu — three different
  seams in one game. Verify against rendered frames, not assumptions.

## 3. Find the frame boundaries

Identify, in the original code: the raster IRQ (or IRQ chain — trace the
$D012/$D019 writes), any $D012 poll loops, and the frame-counter boundary or
present/flip ($D018/$DD00 writes) the main loop handshakes on. The
hotspot-profiling tool (tight backward edges = wait loops) is planned; until
then, sample executed PCs over a few frames and read the loops with
`c64_re.dis6502`. These addresses become your frame-verify boundary hooks.
Beware multi-stage raster chains: the boundary you want is the *frame's*
handshake, not an arbitrary stage's (anticipated pitfall C).

## 4. Stand up the frame verifier

Adapter `frame_verify.py`: boundaries + a `sample_builder` (rendered frame +
screen/bitmap/color RAM first). Confirm a no-op candidate (no hooks) matches
the oracle frame-for-frame before trusting anything else. The lockstep frame
oracle is `c64_re.frame_verify` (`run_frame_verifier`/`FrameVerifyConfig`;
default boundary = the VIC frame advance, optional `boundary_pcs`; on
divergence it dumps `ref.png`/`cand.png`/`diff.png` + `report.txt`/`.json`);
the boundary identification (step 3) and the sample-builder design are yours.

## 5. Build the input-wait registry (before any demo)

Find the boundary-less poll loops (title/menu/"press fire") and register their
canonical head addresses in the adapter's `input_waits.py`, consumed by every
driver. Stix's title poll at $2306 is the first ledger entry of this kind;
its gameplay poll is still to be found. Recording demos before this step
produces proofs that freeze or lie (the DOS lineage's
`demos_and_snapshots.md` carries the full argument).

## 6. Record the first demo

Drive menus into gameplay; confirm the demo replays identically under every
driver (interactive, headless, frame verifier). `c64_re.input_demo` —
frame-keyed input recording/replay (`InputDemoRecorder`/`InputDemoPlayback`;
snapshot-anchored or cold-start) — exists precisely so a human can
hand the agent a played demo. This demo is your first regression asset: record
into `artifacts/` (scratch), then **promote** it to `artifacts/test_oracles/`
with a `docs/<game>/demo_manifest.md` entry.

You can usually script this first demo yourself (a few keys/joystick pushes
through the menus into gameplay — Stix's scripted trainer-menu drive is the
worked shape, and `tests/test_boot.py` proves a scripted run is
byte-deterministic). For demos that need real *play* — clearing a level,
reaching a boss, dying in a specific way — **ask the human**: give them the
exact command (`python scripts/play.py --record-demo NAME`), what to do
in-game, and where the artifact lands. The human records;
you promote it into the corpus and it becomes a proof. (Corpus breadth matters
more than skill — deaths, game-overs and full playthroughs are the proof
spine's spine; pitfall #22.)

## 7. Start the lifting loop

Start with the hot, well-bounded **leaf** routines — decrunchers and decoders,
char/sprite blitters, screen builders, color-RAM fills. They have clean
verifiable boundaries, they make the interpreted VM dramatically faster, and
each one makes the system more observable (both DOS ports started exactly
here). Then move inward to the densest gameplay routines the profiler shows.

For each slice: trace → snapshot fixture → thin hook over a pure recovered
rule (`@registry.replace(pc, name)` in `c64_re.hooks`, with a live-code
signature guard — SMC is idiomatic on this CPU, pitfall #15) → verify against
the ASM oracle (the differential verifier — `c64_re.verification`,
`install_live_verifier`; a hook that passes it climbs to ASM_MATCHED on the
status ladder) → document. One routine, one verification, per slice.

**Optional accelerator — don't hand-translate the first draft.** The
automatic lifter (6502 static decode → literal, verified Python hooks) is
`c64_re/lift/`. Census what's liftable with
`python c64_re/tools/liftgen.py IMAGE [--frames N] [--entries $A,..]
[--scan-jsr LO:HI] [--emit DIR] [--manifest PATH]`, then install and prove
in-situ with `python c64_re/tools/liftverify.py IMAGE --entries $A,..
[--verify-frames M] [--manifest PATH]` (per-call oracle verification; the
manifest tracks the REFUSED/LIFTED/ORACLE_PASSING/INSTALLED ladder; IMAGE may
be a .d64, .prg, or .c64snap). The DOS lineage's shape carries over: a passing lift is
a correct replacement island *for free*, living in its own `mygame/lifted/`
tier with its own proof ledger; it counts as recovered **only after** you
refactor it into clean Python with the same oracle keeping it honest.

Tag every recovered function with `@oracle_link(boundary, contract, status,
merge_target)` (`c64_re.islands`), and generate your island manifest from the
code (`python c64_re/tools/gen_island_manifest.py <packages> -o
docs/recovered_islands.md`) with a drift test.
The ledger — not vibes — is what tells you how far the port is.

## 8. Stand up coverage telemetry

The DOS lineage made the collector a framework engine (`coverage.py`
implementing CPU telemetry hook points; the adapter supplies only the
address→island classifier). c64_re's version is `c64_re.coverage`
(`CoverageCollector` — feed `record_hook_verified` from the verifier's
`VerifyOutcome.oracle_instructions`; unmeasured calls stay loudly outside
the percentage). The headline
metric transfers verbatim, so define it now and report 0 honestly: **native %
= hook-covered ASM-equivalent instructions / all measured work**, accumulated
over a full demo replay, reported overall and per island, with unmeasured work
reported *outside* the percentage. Stix's run_status.md already reports
"Native %: 0" in exactly these terms.

## Then: the phased roadmap

Phase 1 lift rules → Phase 2 collapse understood chains → Phase 3 decode all
game data natively → Phase 4 earn the native world model → Phase 5 native
backends → Phase 6 flip the engine, keep the VM as oracle. Details and exit
criteria per phase: the DOS charter §7 (platform-neutral).

## The endgame — what "flip the engine" concretely takes

These are the pieces the completed DOS port (Prehistorik 2) needed to go from
"hybrid plays" to "a standalone native game ships"; every C64 instance of this
machinery is still to be built, but the list is the map:

1. **Boot constants.** Extract the post-bootstrap initialized state (the
   tables the program builds after decrunching, before the first frame) into
   native data, so the native game cold-boots from the data files alone — no
   PRG, no D64, no snapshot at runtime.
2. **A native state + tick driver.** A byte-backed game state (the state
   mirror) plus a fixed-step frame driver at the original PAL 50Hz cadence,
   with explicit pacing. Do **not** port the raster-wait/busy-wait machinery;
   preserve the heartbeat, not the spin. **From day one, the native runner
   writes a resumable snapshot + prints the exact repro command on every
   gap/crash** (state image + a short state summary). The VM runners get this
   from the framework; the VM-less runner implements the same — it is the
   endgame's biggest debug accelerator.
3. **Per-subsystem equivalence contracts.** Gameplay byte-exact; rendering
   pixel-exact but mechanism-flexible; audio event-exact (the SID register
   stream) but mixer-flexible; input semantic-exact. Write these down for your
   game before flipping, or you will argue every divergence twice.
4. **The tick-equivalence harness** (`c64_re.tick_demo` —
   `record_ticks`/`verify_ticks`, `masked_digest`, binary `.tick` files).
   Replay a
   recorded demo through the ASM oracle and the native core tick by tick and
   compare the game-state RAM image byte-exact. This — over a demo corpus that
   reaches death, respawn, level-end, and game-over — is the proof the flip
   changed nothing. Your adapter supplies the tick seams, the consumed-input
   capture points, the ownership mask, any sidebands (instruction-count- or
   raster-phase-derived state must be *recorded and injected* — the native
   port has neither), and the tick function with its transition outcomes.
5. **A verification switch.** ON: the oracle runs beside the native game and
   diffs at boundaries. OFF: no VM starts. The shipped build contains no VM,
   no PRG, no fallback.
6. **Only now, the enhanced layer.** Higher resolutions, interpolation,
   scaling and friends are Stage 6 — built on top of the *complete* faithful
   game, never during recovery (pitfall #24). The audio-style exception
   (small, separable, fixes something that disrupts the recovery workflow
   itself) needs explicit justification in your run_status ledger.

**Audio deserves its own plan.** Recover it in layers, with the SID register
model + the original ASM driver as the *oracle path*, never the final
architecture: music/SFX data decode → a typed data model → the player routine
(usually one call per frame from the IRQ chain) → verify: same state + events
+ timing → same per-frame SID register stream against the oracle's — then
detach the native game from the ASM audio path entirely. Only after that does
a mixer/synthesis backend choice even arise.

## What is game-specific (yours to write)

Boot constants and PRG identity/signatures; loader policy (KERNAL vs
fastloader HLE); asset codecs; game-state RAM layout + zero-page descriptors
(with widths and phases — pitfall #2, anticipated pitfall E); hook
registrations + continuation metadata; frame boundaries + sample builder;
input-wait registry; island/coverage classification; the recovered logic
itself. The framework gives you the machine, the proof engines, and the
method — the knowledge of *your* game is earned from *your* oracle.
