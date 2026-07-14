# START_HERE — you are the porting agent

You are an AI agent who has been given this repository and a C64 game to port.
This file is the boot sequence; everything else is reachable from here.
([`AGENTS.md`](AGENTS.md) is the one-page operating card distilled from this —
if you only cache one file, cache that one.)

This repo is `stix_port`, the first C64 port — and it doubles as the future
`template_c64_port`: the method docs live here for now and will be extracted
later, exactly as `template_dos_port` was extracted from `pre2_port`. The
method below is the *target*; framework machinery that does not exist yet in
`c64_re` is marked "(planned — see `c64_re/README.md` §Deliberately not built
yet)" at first mention.

The human's role is deliberately small: they put the game files (`.d64` disk
images) in `assets/`, and when you ask, they record demos, provide
saves/screenshots/snapshots, and playtest. They do **not** reverse-engineer,
read ASM, or drive this workflow — you do. Requests to the human must be
concrete (exact command + what to do in-game + where the artifact lands); the
request patterns are in [`AGENTS.md`](AGENTS.md) §"Requesting things from the
human".

## What you are building

A verified, native source port of the game, recovered one proven routine at a
time from the original program running in this repo's VM. The original binary
is the oracle — the single source of truth. You never guess behaviour; you
trace what the original did and match it, byte-exact, at every step.
Definition of done: the native port replays the whole demo corpus with the VM
disabled in the hot path, and the VM-as-oracle suite confirms frame-and-state
equivalence. ([`docs/lifecycle.md`](docs/lifecycle.md) tells the whole arc.)

## Boot sequence

1. **Read, in order:** [`docs/lifecycle.md`](docs/lifecycle.md) →
   [`docs/ai_porting_charter.md`](docs/ai_porting_charter.md) (the method —
   read all of it, twice for §6) → [`docs/pitfalls.md`](docs/pitfalls.md)
   (the mistakes already made for you) →
   [`docs/porting_new_game.md`](docs/porting_new_game.md) (the checklist you
   will now follow). The per-task rituals and accountability REPORT blocks
   live in the DOS template for now
   (`D:\Games\DOS\dos_recosystem\template_dos_port\prompts\`) and apply
   unchanged. Status claims follow the ladder (never present OBSERVED work as
   VERIFIED).
2. **Check for a port in flight.** `git log` + `docs/<game>/run_status.md` +
   `docs/<game>/blockers.md` are the resume state. In this repo, **Stix is in
   flight** — resume from [`docs/stix/run_status.md`](docs/stix/run_status.md);
   never restart bring-up on a repo that has islands.
3. **Set up the workspace** (fresh port only). The game's `.d64` images go in
   `assets/` (gitignored — original game files are never committed; if it's
   empty, ask the human). Create your adapter package **in this repository, at
   the root** — e.g. `mygame/` — by copying the shape of the live example,
   [`stix/`](stix/__init__.py). Your tests go in `tests/` and **must skip when
   `assets/` is missing** (CI has no game files — copy the pattern from
   [`tests/test_boot.py`](tests/test_boot.py)). Register your package in
   `c64_re/tools/lint.py` and run `c64_re/tools/audit_layers.py
   mygame/recovered` with the suite (both tools are real: `lint.py` keeps the
   core stdlib-only and checks the registered adapter packages' rules;
   `audit_layers.py` proves pure layers never import the VM).
   **Import note:** `c64_re` is a **sibling directory** (`../c64_re`), not a
   submodule yet, and that directory is the framework's repo root — the
   actual package is `../c64_re/c64_re/`. Every entry point puts the sibling
   repo root on `sys.path` itself: copy the `PORT_ROOT`/`sys.path` header from
   [`scripts/play.py`](scripts/play.py) or [`scripts/boot.py`](scripts/boot.py)
   for any further scripts; the tests do the same insertion (see
   `tests/test_boot.py` — there is no pyproject `pythonpath` shim here yet).
   Run `python -m pytest tests -q` in `../c64_re` once — the framework suite
   needs no game assets and confirms the framework works on this machine.
4. **Start the ledgers** in `docs/<game>/`: `run_status.md` (current phase +
   findings — its summary is also the human's progress report, keep it
   readable), `symbol_ledger.md` (addresses → evidence), `blockers.md` (see
   the loop protocol), `demo_manifest.md` (the corpus and its blind spots),
   plus the generated island manifest (`python
   c64_re/tools/gen_island_manifest.py <packages> -o
   docs/<game>/recovered_islands.md` — generated, never hand-edited). The live copies are in
   [`docs/stix/`](docs/stix/run_status.md); the annotated templates are in the
   DOS template's `examples/ledgers/`.
5. **Follow [`docs/porting_new_game.md`](docs/porting_new_game.md)** step by
   step: load & run → see output → find frame boundaries → stand up the frame
   verifier → build the input-wait registry → record the first demo → start
   the lifting loop.
6. **Keep the human in the loop.** `python scripts/play.py --start` is the
   live window (F9 pause, F10 screenshot, F11 demo-record toggle, F12
   snapshot; arrows + Right-Ctrl = joystick),
   and `python scripts/boot.py` renders headless PNG evidence into
   `artifacts/` — use them to show progress and gather the human's feedback on
   how the game *runs*; the oracle judges whether the code is *correct*.
   Those are different jobs, and both matter.

## Mechanical tools first

Never hand-derive what a tool can measure, generate, or prove. The standing
order: **probe → profile → lift → verify**, and only read ASM where the tools
stop. The question→tool table is in [`AGENTS.md`](AGENTS.md); the three that
save the most time:

- **The hotspot profiler** (planned — see `c64_re/README.md` §Deliberately
  not built yet) before any manual tracing — it finds the wait loops (tight
  backward edges) and the real cost centres. Until it lands, the CPU's trace
  and cycle telemetry (`c64_re/cpu.py`) do the job by hand: the usual C64
  waits are `$D012` raster polls, CIA1 matrix scans of `$DC00/$DC01`, and
  KERNAL GETIN buffer drains.
- **The automatic lifter** before any hand translation — census which
  entries are mechanically liftable and emit literal Python hooks with
  `python c64_re/tools/liftgen.py IMAGE [--frames N] [--entries $A,..]
  [--scan-jsr LO:HI] [--emit DIR]`, then install and prove them against the
  ASM oracle in-situ with `python c64_re/tools/liftverify.py IMAGE
  --entries $A,.. [--verify-frames M] [--manifest PATH]` (IMAGE may be
  .d64/.prg/.c64snap). You refactor a *verified* artifact
  into clean recovered code; you do not decompile from scratch
  ([`docs/porting_new_game.md`](docs/porting_new_game.md) step 7).
- **Demo replay** (`c64_re.input_demo`) before any claim — a change is
  proven by the corpus replaying identically, not by your reading of the
  diff (the Stix gate: [`tests/test_demo_stix.py`](tests/test_demo_stix.py) —
  a scripted gameplay demo replays bit-identically). The deterministic
  full-state digest suite backs it up (the Stix pattern:
  [`tests/test_boot.py`](tests/test_boot.py) hashes RAM + color RAM + VIC
  registers + CPU state across scripted runs).

## Phase map

| Phase | You produce | Exit condition |
|---|---|---|
| Bring-up ([`porting_new_game.md`](docs/porting_new_game.md) steps 0–6) | adapter, boot snapshot, rendered frame, frame verifier, input-wait registry, first promoted demo | no-op candidate passes frame verify; the demo replays identically under every driver |
| Lifting loop (step 7, charter Phase 1) | `lifted/` + proof ledger; `recovered/` + `@oracle_link` (`c64_re.islands`); goldens | every slice verified vs the ASM oracle; demo suite green at every commit |
| Subsystems (lifecycle stages 3–4, charter Phases 2–4) | state mirror; collapsed hook chains; native tick driver | a subsystem reproduces frame/state from a snapshot **without stepping the VM** |
| The flip (stage 5, charter Phases 5–6) | boot constants; native runner; verification switch; the tick-demo adapter (`c64_re.tick_demo` — seams, ownership mask, sidebands, tick fn) | full demo corpus passes native-vs-VM tick-by-tick; zero interpreted instructions in the hot path |
| Enhancements (stage 6 — only now) | the enhanced presentation layer (see the DOS template's `docs/post_endgame.md` — endgame-gated) | parity gate: enhanced-at-neutral ≡ faithful, pixel- and state-exact |

## The loop protocol (how work proceeds, slice by slice)

Proven over months of autonomous recovery on the DOS source ports (their
unattended relaunch harness, `overnight_loop.sh`, lives in the DOS template
and belongs to the lifting phase — deploy only once the game is fully
runnable and the demo corpus spans gameplay):

1. **One slice per iteration** — one routine, one field naming, one raw-offset
   drain; the smallest coherent unit. Not a subsystem.
2. **Never commit red.** Every commit passes the test suite + the demo gates.
   One slice = one focused commit.
3. **Blocked ⇒ revert + log.** If a slice can't be finished byte-exact, or the
   fix would require guessing: revert all its changes immediately, write the
   evidence into `docs/<game>/blockers.md`, and take the next target. A logged
   blocker is progress; a workaround is debt. If a divergence resists ~2
   focused trace attempts, it usually needs a lower layer recovered first.
4. **Never weaken an oracle or test to make a change pass.** Fix the code to
   match the original, or revert.
5. **Fail loud, never fake.** An unrecovered path raises a `HybridGap`
   (`from c64_re.gaps import HybridGap`); it never silently falls back to ASM or to a
   plausible guess. The framework already lives by this rule: unimplemented
   KERNAL is JAM-filled and fails loud with the exact address.
6. **Check for existing mechanisms before building.** The framework and your
   own adapter likely already have the tool (`c64_re/README.md` +
   `c64_re/docs/hardware_support.md` are the map) — and for problems the
   framework does NOT solve in code, check the DOS template's
   `docs/cookbook.md` FIRST: it maps symptoms (busy-wait crawl,
   runtime-patched code, resident audio driver, slow probes, cold-start
   endgame…) to proven worked examples in the DOS source repos. The C64
   translation of a technique is usually mechanical; re-deriving it from
   scratch wastes days the previous ports already paid for.
7. **Update the ledgers as you go** — `run_status.md` for state, the island
   manifest for progress, the symbol ledger for evidence. The next agent (or
   the next session of you) resumes from git + these files alone.

## On failure — the routing table

| Symptom | Do this |
|---|---|
| A hook diverges from the oracle | The differential hook oracle (`c64_re.verification`, `install_live_verifier`) is the tool: set `C64_RE_TRACE_HOOK=$XXXX`, rerun, and read the dumped ASM-oracle instruction trace — what the original actually did. After ~2 focused attempts: revert + log the blocker. |
| A demo freezes or deadlocks on replay | You missed a boundary-less input-wait loop — charter §6. On the C64 these are `$D012` raster polls, raw CIA1 `$DC00/$DC01` matrix scans (Stix's title loop polls `$DC01` raw), and KERNAL GETIN drains. Find the canonical head, register it in the adapter's `input_waits.py` (shared by ALL drivers); the fix is in the driver, not the demo. |
| The VM fails loud (JAM in the shim ROM / unstable illegal opcode / unmapped I/O) | The framework is asking to grow — the JAM fill prints the exact KERNAL address. Extend `c64_re/` under [`../c64_re/AGENTS.md`](../c64_re/AGENTS.md): implement the *observed* behaviour only, document the contract, add a focused test. |
| Nothing advances; all time is spent in the IRQ handler | An IRQ storm from an unacknowledged source. The Stix bring-up hit exactly this with CIA1: the interrupt must be acknowledged (reading `$DC0D` clears the ICR) or it refires forever. Check acknowledgement before suspecting the game. |
| Headless runs crawl | PyPy is the speed path (`c64_re/README.md`); deterministic fast-forward machinery is DOS-cookbook territory for now ("Timing and speed"). |
| You can't drive the game past the menus / can't reach a state | Ask the human for a recorded demo with the exact command (`python scripts/play.py --record-demo NAME` — `c64_re.input_demo`). Or script it through the machine API — `machine.key_down/key_up/set_joy1/set_joy2` (the Stix trainer menu is answered this way via KERNAL GETIN in `stix/`). |
| A rebuilt buffer won't match | It's history-dependent state — pitfall #11 (DOS lineage). Replay the real sequence from a known init or recover the exact invariant; mark it *blocked* rather than guessing a stateless model. |
| A divergence appears minutes into a demo | Suffix repro — resume right before the failure, never from the start. Snapshots exist (`c64_re.snapshot` — `write_snapshot`/`load_snapshot`, bit-identical resume); demo suffixes are `c64_re.input_demo`'s `write_suffix` (re-anchor the tail on a snapshot). Reproduce from the nearest deterministic state, not from boot. |
| The native runner hits a gap or crashes | It must have written a resumable snapshot (`c64_re.snapshot.write_snapshot` — a `.c64snap`) + printed the repro command — build that in from the runner's first day. `scripts/boot.py` already prints the disassembly around PC on a crash; the crash *is* the next work item. |
| Verification passes but the game *feels* wrong to the human | Trust both signals: the oracle proves state; the human hears pacing/audio. The heartbeat is PAL 50 Hz (312 lines × 63 cycles) — check the pacing model and the frame clock before doubting the oracle. |

## The framework is a living organism

Your game WILL exercise CPU opcodes, KERNAL services, and chip behaviour the
previous games didn't. Extending `c64_re/` is part of the job — under its
rules ([`../c64_re/AGENTS.md`](../c64_re/AGENTS.md)): stdlib-only core,
game-agnostic, add only what your program *proves* it needs, document the
observed contract, add a focused test, keep it deterministic by default. When
the VM fails loud on a JAM-filled KERNAL address or an unmodeled chip
feature, that is the framework asking to grow — implement the observed
behaviour, never a datasheet's generality. If you build a mechanism the
*next* game would reuse (a new chip model, a new verifier capability),
promote it into `c64_re/` with an origin note; if it knows your game's
addresses or formats, it stays in your adapter.

## Hard boundaries (violating these voids the work)

- `c64_re/` never learns your game — no game addresses, filenames, or formats
  (enforced by `python c64_re/tools/lint.py`). The one
  exception: *authentic KERNAL/hardware addresses* (jump table entries,
  vector bodies, `$EA31`, `$FD30`) are hardware truth, not game knowledge,
  and belong in `c64_re/kernal.py`.
- Your adapter's pure layers (`recovered/`) never import the VM
  (enforced by `python c64_re/tools/audit_layers.py` — apply from day one).
- One shared definition of "a boundary" and "a wait loop" across all drivers
  (charter §6 — the trap that silently voids demo proofs).
- Full-memory diffs by default; narrowing is a temporary, deliberate lever.
  (The Stix digest already hashes all of RAM + color RAM + VIC + CPU.)
- **No enhanced-presentation work until the faithful native game is complete
  and stable** (lifecycle Stage 6). The only exception class is an
  audio-style disruption fix — small, separable, justified in the ledger.

## Progress is measured, not vibed

- Native % over a demo replay — `c64_re.coverage.CoverageCollector` on the
  CPU's existing cycle/coverage telemetry (feed `record_hook_verified` from
  the verifier's `VerifyOutcome.oracle_instructions`); your adapter supplies
  only the address→island classifier. The unmeasurable is reported OUTSIDE
  the percentage, never guessed into it.
- The generated island manifest (count × confidence ladder) —
  `python c64_re/tools/gen_island_manifest.py <packages> -o
  docs/<game>/recovered_islands.md`.
- Demo-corpus coverage and pass rate.
- The glue-hook count (falling is good).

When in doubt: trace it, snapshot it, prove it. The oracle is right there.
