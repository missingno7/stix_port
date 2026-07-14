# c64_re — AI Porting Charter

**Audience:** an AI agent given the `c64_re` package and a C64 game (a PRG on
a .d64 disk image + its data). This document tells you *exactly* what we are
trying to achieve, the method, the tools `c64_re` already gives you (and which
are still planned — see `c64_re/README.md`), the invariants you must never
break, and the traps that will silently invalidate your work if you ignore
them.

Read this whole file before writing code. This method was piloted and proven
end-to-end on DOS games under `dos_re` (Overkill, then a playable VM-less
source port of Prehistorik 2); **your game is different**, and this is a
different machine. You create a per-game adapter package for it (this repo's
`stix/` is the first). Every concrete address, video configuration, and data
layout is an *example* that lives in the adapter, not in `c64_re`.

---

## 0. North star — what "done" means

A **standalone source port**: the game runs as native code (Python here) that
interprets **zero original 6502 instructions in the hot path**. It still loads
the original data (sprites, charsets, level data, SID sequences) through
native codecs — that is normal and expected. What disappears is *interpreted
code*, not original *data*.

**"Provably equivalent"** does not mean a formal proof (infeasible for a whole
ASM game). It means the strongest practical proof available to us:
deterministic, **frame-and-state-exact** equivalence against the original,
replayed over a demo corpus that exercises the whole game. (Scope note:
"byte-exact" applies to *gameplay state*; rendering is pixel-exact but
mechanism-flexible, audio SID-register-stream-exact but synthesis-flexible,
timing heartbeat-exact but never the waiting machinery — the per-subsystem
contracts are the table in `docs/lifecycle.md` Stage 4.)

Our structural advantage over a normal source port: **we have the exact
original behavior on tap** (the VM) to diff against. The entire method is about
keeping that diff *cheap and total* while we hollow the VM out.

---

## 1. The core idea: turn the VM from the engine into the oracle

Right now the VM does two jobs: it **runs** the game and it **is** the ground
truth. The whole migration is splitting those apart:

- native code progressively takes over **running** the game;
- the VM is demoted to **proving** the native code is correct.

The source of truth shifts over time:
1. early: "does each replacement hook match its original routine at its $XXXX?"
2. later: "does the live game's full frame + decoded state still match the
   original, replayed over recorded input?"

You are always doing one of two things: **lifting** logic out of the VM into
native code, or **strengthening the proof** that the lift was exact.

---

## 2. The two invariants (never break these)

1. **Always runnable.** The game is playable/observable at every commit. There
   is no long-lived "big rewrite" branch. Every change is a thin slice.
2. **Always verified.** Every slice is proven against the VM oracle *before* it
   is trusted. You never replace original behavior with code you have not diffed
   against the original.

If a change cannot be verified, it is not done — it is a hypothesis.

A third law underlies both: **the original executable is the oracle. Never
guess.** If you don't know what a routine does, you trace it in the VM and read
what it actually did; you do not invent plausible behavior.

---

## 3. Architecture: reusable core vs per-game adapter

### 3.1 `c64_re/` — the reusable, game-agnostic core

`c64_re` knows about the 6510, the VIC-II, the CIAs, the SID, the KERNAL seam,
memory banking, D64 media, and the verification machinery. It knows **nothing**
about any specific game's addresses, screen layout, or data formats. Key
modules (the few still-deferred items are listed in `c64_re/README.md`
§Deliberately not built yet):

- **`cpu.py` — `CPU6502` (the 6510).** The interpreter: all documented opcodes
  incl. decimal mode + the stable illegals; unstable ones fail loud. Important
  surface:
  - `step()` runs one instruction (or one hook); `run(n)` runs n.
  - `replacement_hooks: dict[pc -> handler]` — native game-recovery code
    installed at an address, with `hook_names` parallel for reporting.
    `service_hooks` is the separate framework seam (the KERNAL shim bodies) —
    never mix the two.
  - `hook_verifier` — if set, `step()` routes a hooked address through it
    instead of calling the handler directly (this is how verification wraps
    every hook). `hook_verifier_passthrough` exempts addresses.
  - `trace_fn` — per-instruction capture; `dis6502.py` disassembles over the
    interpreter's own opcode table (never a second semantic model).
  - instruction/cycle telemetry — the machine clock (VIC raster, CIA timers,
    the frame counter) is derived from CPU cycles. Coverage telemetry for the
    measured native-% metric (§10) is `coverage.py` (`CoverageCollector`, fed
    from the verifier's `VerifyOutcome.oracle_instructions`).
- **`memory.py` — `Memory`.** PLA banking with RAM-under-ROM, `rb/wb`,
  `block`/`load_block`, and the VIC's independent 14-bit bank view
  (`vic_read`).
- **`machine.py` — `C64Machine`.** Wires VIC-II, both CIAs, SID, the keyboard
  matrix and joysticks (`key_down`/`key_up`, `set_joy1`/`set_joy2`), the IRQ
  line, and the per-cycle `tick`.
- **`kernal.py` — the KERNAL seam.** No Commodore ROM bytes: a clean-room shim
  ROM shaped like the real one (vectors, dispatch stubs, the jump table with
  real `JMP ($03xx)` indirections, the $FD30 vector-table image) with service
  contracts as Python traps at the authentic body addresses — LOAD is served
  from the attached D64. Everything unimplemented is **JAM-filled: it fails
  loud with the exact address and becomes the next work item.** Never soften
  this.
- **`runtime.py` — `Runtime` / `create_runtime`.** Bundles machine + CPU +
  loaded program; `run_frames` / `run_until` drive it. The unit you clone for
  an oracle.
- **`d64.py`.** D64 directory/chain parsing, CBM-DOS name matching, the static
  BASIC-stub `SYS` parser used to boot without any BASIC ROM. Handle crunched
  PRGs as a bootstrap that runs once to materialize the real image, then
  snapshot past it (see §4). Bootstrap = extraction, not gameplay.
- **`snapshot.py`** — freeze/restore full machine state: `capture()`/`restore()`
  in-memory state dicts, `clone_runtime(rt, install_hooks=False)` for oracle
  clones, and `write_snapshot(rt, path)`/`load_snapshot(path)` (`.c64snap`
  files; the media path is stored absolute). Snapshots are how you skip the
  decrunch bootstrap and how you pin a reproducible starting point for
  verification — proven on Stix, where a gameplay snapshot resumes
  bit-identical.
- **Input delivery.** Keys and joysticks go in through the CIA1 matrix
  ($DC00/$DC01 as the game scans it), not by faking KERNAL GETIN — many games
  poll the matrix raw (Stix's title loop polls $DC01 directly). Hold each key
  down for ≥1 full polled frame before releasing, or same-frame make+break
  taps are lost.
- **`input_demo.py`** — `InputDemoRecorder`/`InputDemoPlayback`: a demo
  directory (`input_demo.json` + `snapshot.c64snap`) records VM-visible input
  events keyed to an **emulated boundary counter** (the VIC frame counter);
  replay them deterministically into one or more runtimes
  (`playback.make_runtime()` rebuilds one — resume the snapshot or cold-boot
  from the recorded boot args; `write_suffix` extracts a tail repro;
  snapshot-anchored and cold-start demos both work). This is the substrate of
  the proof corpus. **Read §6 before trusting it.**
- **`verification.py` — the differential hook oracle**. Two modes, ported
  from `dos_re`; install via `install_live_verifier(rt, metadata=...,
  on_result=..., raise_on_divergence=..., strict_cycles=...)` around
  `HookOracle`:
  - **metadata mode:** you declare each hook's valid continuation target(s)
    as `HookStop(continuations=(...))` (RTS, RTI, fixed-PC, computed
    dispatch, …); the verifier clones the runtime, runs the *original* ASM to
    that target, runs your hook, and diffs the full state — registers + flags,
    all 64K RAM, color RAM, VIC, CIAs, SID.
  - **strict JSR-return mode (the default):** no metadata to maintain — the
    verifier runs the original ASM to the JSR return and holds your hook to
    the same full-state diff there.
  - the trace-on-divergence switch (DOS lineage: `OK_TRACE_HOOK`): set
    `C64_RE_TRACE_HOOK=$XXXX` — on a divergence at that hook, the exact
    ASM-oracle instruction trace is dumped. The primary debugging tool — it
    shows precisely what the original did that your hook did not.
  - contracts: interrupts stay latched-but-undelivered inside the verified
    window (`cpu.inhibit_interrupts`) — the per-hook proof covers the routine
    body; interleaving belongs to the frame/tick oracles (`frame_verify.py`,
    `tick_demo.py`). Hand hooks
    tick 0 cycles and the verifier makes up the deficit; lifted hooks tick
    exact cycles, and `strict_cycles=True` turns any deficit into a
    divergence.
- **`frame_verify.py` — the semantic/frame oracle**. `run_frame_verifier` /
  `FrameVerifyConfig` steps two runtimes (reference = original ASM oracle,
  candidate = hooked/native) to **frame boundaries** (default: the VIC frame
  advance; optional `boundary_pcs`), builds a `FrameSample` at each (rendered
  indexed frame + VIC regs, widened via `sample_builder(rt)`), and diffs them
  (`compare_samples`), dumping `ref.png`/`cand.png`/`diff.png` +
  `report.txt`/`.json` artifacts on divergence. Game-independent;
  the adapter supplies boundary addresses, a `sample_builder`,
  `reference_env_hooks`, optional `pump_inputs`, and an `input_wait_detector`
  (see §6).

### 3.2 The per-game adapter — everything game-specific

This is what *you* write/extend for your game. It contains the only code that
knows your game's addresses and formats:

- **Replacement hooks** (`hooks.py` / `replacements.py`): native handlers
  registered to original PCs via `@registry.replace(pc, name)`
  (`c64_re.hooks`; duplicate fail-fast, `C64_RE_DISABLE_HOOKS` env disabling,
  live-code signature guards for self-modifying code).
- **Continuation metadata**: one stop declaration per hooked address
  describing its valid return/continuation (as `HookStop` metadata for
  `c64_re.verification`; strict JSR-return hooks need none).
- **Frame-verify adapter**: your game's frame boundary addresses (raster wait,
  raster-IRQ entry, $D018/$DD00 pointer flip), the VIC memory layout, palette,
  and the `reference_env_hooks` (hardware-wait hooks the *oracle* must keep so
  it does not spin forever — typically the $D012 raster wait and CIA-timer
  waits).
- **Input-wait registry** (`input_waits.py`): detectors for busy-wait input
  loops that produce no frame boundary (see §6 — this is mandatory, not
  optional).
- **Runtime loader** (`runtime.py`): boot from the D64 through the decruncher
  and any trainer/crack menu to a pinned start state.
- **Asset codecs** (`asset_codecs/`): native decoders for the game's packed
  data.
- **Coverage classifier**: maps addresses to "islands" (subsystems) so
  progress telemetry is meaningful (framework side: `c64_re.coverage`).

**Rule:** if a piece of code mentions a concrete address, VIC configuration,
or file format, it belongs in the adapter, never in `c64_re`.

---

## 4. The disciplined lifting loop (do this for every slice)

This is the unit of work. One routine, one verification, per slice.

1. **Run the original** under the VM; reach the state you want to study (load a
   snapshot to skip the decrunch bootstrap).
2. **Trace** to identify exactly ONE routine to lift. Use `trace_fn` or
   `dis6502`.
3. **Snapshot** before/after the routine so you have a reproducible fixture.
4. **Write a narrow native hook** at the routine's $XXXX — a *thin VM adapter*
   (reads/writes VM memory, registers, and chip state) wrapping a **pure
   recovered rule** (the actual game logic, side-effect-free where possible,
   unit-testable).
5. **Declare continuation metadata** for the address, or use strict
   auto-continuation mode.
6. **Verify against the interpreted ASM oracle**: a test in the adapter's test
   suite asserts full machine state + memory blocks equal between your hook and
   the original ASM executed from the same pre-state. The oracle is the
   interpreter executing the real bytes — never a hand-written expectation.
7. **Update** the symbol ledger, runtime-findings notes, and status doc.

When a hook diverges, enable the divergence trace at that address, reproduce,
and read the ASM oracle trace. Fix the hook to match what the original *did*,
not what you think it should do. (DOS lineage, but the bug class is
machine-independent: a hook took an "empty-scan" exit where the original
jumped straight to a shared RET, leaving a register/flag wrong; another
modeled a nested call natively without leaving the call's return-address bytes
on the freed stack, which full-memory verification caught. Expect exactly this
class on the 6502 — freed-stack scratch below SP, flag shape, zero-page temps,
early-out branch selection. The trace tells you which.)

---

## 5. The proof spine (build it ahead of the lifting)

Verification must get **stronger as the VM gets weaker**, because collapsing
code loses per-hook granularity. Evolve it in this order:

1. **Per-hook ASM match**: every hooked address diffed register + flag +
   full-memory + chip-state against the original at its continuation.
2. **Semantic frame verifier**: diff ASM-oracle vs candidate at each frame
   boundary — the rendered frame + VIC-visible memory (screen matrix, bitmap,
   color RAM, sprite data + VIC/SID register state) to start.
3. **Widen the semantic snapshot** until it covers **all observable state**:
   every object field, player, **RNG state**, score/lives, level state,
   timers, and the frame. *If it is not in the snapshot, divergence can hide
   there.* Locating the RNG in memory — on the C64 typically SID OSC3 ($D41B)
   reads or a software LFSR — is usually the first hard sub-task and a
   prerequisite for everything downstream.
4. **Deterministic demo-replay harness**: for each recorded demo, assert
   candidate ≡ oracle for **every frame to the end**. Determinism (fixed input +
   seed ⇒ identical state) becomes a hard requirement; any wall-clock or RNG
   nondeterminism must be modeled out in verify mode.
5. **Demo corpus** covering all levels, enemy types, edge interactions, and
   RNG paths. "Proven equivalent" = every demo passes full-frame/full-state,
   and you track which behaviors/branches the corpus exercises so confidence is
   *measured*, not vibed.

(Item 1 exists — `c64_re/verification.py`, proven in-situ on Stix. Item 2 is
`c64_re/frame_verify.py` (`run_frame_verifier`; widen via `sample_builder`).
Item 4's substrate is `c64_re/input_demo.py` + `frame_verify.py`; Stix already
has the seed: deterministic full-state digest tests in
`stix_port/tests/test_boot.py` and a bit-identical demo replay in
`stix_port/tests/test_demo_stix.py`.)

---

## 6. Determinism and the boundary-clock invariant (the trap that voids proofs)

**This is the most important non-obvious section. Read it twice.**

Demo events are keyed to an **emulated boundary counter** ("the demo clock") —
on this machine, the VIC frame counter, which is itself derived from CPU
cycles, never from wall time. A demo is only a valid proof artifact if it is
**byte-for-byte reproducible across every driver** that replays it. There is
typically more than one driver:

- an interactive play loop (the pygame viewer),
- a headless per-hook verifier,
- the frame verifier.

If these count "a boundary" differently, the same demo replays at different
internal points in each driver, gameplay diverges, and your corpus pass/fail
becomes driver-dependent — i.e. the proof is an illusion. (DOS lineage: in the
reference ports this manifested as **freezes/deadlocks**, not loud errors,
which is worse.)

Two concrete failure modes you *will* hit:

1. **Boundary-less input-wait loops.** Some original code busy-waits on input
   *without* reaching a raster/timer/present boundary (e.g. a "press FIRE to
   start" / "wait for release" poll — Stix's title loop polls $DC01 raw in
   exactly this shape). The demo clock is frozen inside such a loop, so a
   recorded key *release* keyed to a later boundary is never delivered — the
   loop waits forever for input it can't receive. **Every driver must
   recognize these loops** and treat them as a boundary so input is pumped and
   the clock advances. Keep these detectors in **one shared registry** (the
   adapter's `input_waits.py`) consumed by all drivers — duplicating them
   per-driver guarantees they drift. In the frame verifier, detect the loop at
   its **canonical head address** and check it **every step**, so the
   reference and candidate stop at the *identical* instruction; if they stop
   at different sub-positions of the loop they resume differently when input
   is pumped and diverge spuriously.

2. **Driver-specific clocks.** Before standing up the demo-replay corpus,
   **unify the boundary/clock definition** so record-time and replay-time, and
   every driver, agree on exactly what increments the counter. This is a
   prerequisite for step 4 of the proof spine, not a cleanup afterward.

Also model out, in verify mode: real-time pacing (no wall-clock sleeps gating
state), asynchronous IRQ delivery (make raster and CIA-timer interrupts
deterministic — Stix already taught the acknowledge lesson: a CIA1 interrupt
left unacknowledged becomes an IRQ storm, so interrupt-flag semantics must be
exact), and RNG seeding. The oracle must keep the *hardware-wait* hooks
(raster wait, timer wait) so the original ASM doesn't spin on a flag that, on
real hardware, an interrupt or the beam would clear — but those waits must
return deterministically.

---

## 7. Phased roadmap

- **Phase 1 — Lift every game rule out of hook bodies.** Turn each gameplay
  hook into a thin VM adapter over a pure, tested recovered rule (object
  behaviors, collision predicates, movement/clamp, spawn selection,
  contact/overlap, HUD/state). Exit: decisions are native even though the VM
  still owns memory and the loop. Proof: per-hook ASM match + frame verifier.
- **Phase 2 — Collapse understood hook chains.** Where the runtime ping-pongs
  ASM→hookA→glue→hookB→ASM and the glue is understood, fuse into one native
  flow. Accept coarser hook-coverage granularity; the frame/state verifier
  covers it. Exit: gameplay control flow is native, not PC ping-pong.
- **Phase 3 — Decode all game data into native structures.** Jump tables,
  sprite/animation tables, level data, SID sequences, charsets — decode via
  typed decoders into native data the lifted rules consume. Exit: a native data
  layer loadable from the original disk without a running VM. Proof: round-trip
  (decode → re-encode → byte-identical to the original image) + rules behave
  identically on decoded vs VM-read data.
- **Phase 4 — Earn the native world model + systems.** Only now compose the
  accumulated rules into systems over a native world model (the abstraction is
  *earned* by Phases 1–3, not invented up front). Run as a shadow: decode VM
  state, advance natively, semantic-diff every frame. Exit: a native `tick()`
  reproducing the VM frame for the systems it owns.
- **Phase 5 — Native backends.** Wire Video/Input/Audio/Timing/AssetProvider to
  real adapters (frame producer, SID synthesis, keyboard/joystick→action,
  deterministic timing). Exit: native systems produce frames/audio without the
  VM's render/sound hooks. Proof: native frame == VM frame; SID register
  streams match.
- **Phase 6 — Flip the engine, keep the VM as oracle.** Native loop drives; VM
  runs only in test/dev as the proof harness; ASM interpretation leaves the hot
  path. Exit: standalone playable build. Proof: the full demo-corpus equivalence
  suite passes native-vs-VM end-to-end.

Never break "always runnable, always verified" between phases.

---

## 8. Cross-cutting hard parts (call these out early for your game)

- **The music/sound driver** (typically a raster-IRQ-driven SID player: a
  sequencer stepped once per frame from the interrupt). "Exact audio" means
  matching its SID register stream. Often the longest pole; treat as a
  separable chunk.
- **The main frame loop / dispatcher.** Collapsing it to a native loop is the
  riskiest step — leave it for Phase 6.
- **Self-modifying / runtime-patched routines.** Endemic on the C64 (patched
  operands, code copied over itself, code run from unusual places — Stix's
  decruncher runs from the stack page). Static lifting must handle the
  *patched* variants; the verifier must catch them (full-memory diff helps),
  and hooks carry live-code signature guards (`c64_re.hooks`).
- **Determinism.** RNG + timing must be exactly reproducible in verify mode or
  the proof spine collapses (see §6).
- **Rendering.** Pin down the game's actual VIC configuration (mode, bank,
  $D018 layout, sprite usage) early; keep any secondary display states (title
  vs gameplay) isolated so they never block the primary.
- **Crunched PRGs.** The decruncher is dynamic-init materialization, not game
  logic — run it once, snapshot past it, lift from the decrunched image.
  Bootstrap = extraction, not gameplay.

---

## 9. Bootstrapping a NEW game on `c64_re` (concrete checklist)

1. **Load & run.** Get the D64 booting: directory + BASIC-stub `SYS`, the
   decruncher (if any) running to completion; reach the first visible frame.
   Add a snapshot point after init (`c64_re.snapshot.write_snapshot(rt, path)`
   after a deterministic frame-count boot; `load_snapshot(path)` resumes
   bit-identically, and `liftgen`/`liftverify` accept `.c64snap` images
   directly).
2. **See output.** Render the VIC frame to a PNG so you can visually confirm
   state. Wire input through the CIA1 matrix and verify the game's own polling
   (raw $DC01 or KERNAL SCNKEY/GETIN) sees it.
3. **Find the frame boundaries.** Identify the raster wait, the raster-IRQ
   handler, and any $D018/$DD00 pointer flip (many C64 games draw directly
   into VIC memory — there may be no blit at all). These become your
   frame-verify boundary hooks and `reference_env_hooks`.
4. **Stand up the frame verifier** (`c64_re.frame_verify.run_frame_verifier`):
   boundaries + `sample_builder` (rendered frame + VIC-visible memory first).
   Confirm a
   no-op candidate (no hooks) matches the oracle frame-for-frame.
5. **Build the input-wait registry** (`input_waits.py`) — find the boundary-less
   poll loops (title/menu/"press fire") before recording any demo (§6).
6. **Record a first demo** that drives menus into gameplay; confirm it replays
   identically under every driver.
7. **Start Phase 1** on the densest gameplay routines, one slice + one
   verification each, following §4.
8. **Stand up coverage telemetry** so you can report progress (§10;
   `c64_re.coverage.CoverageCollector`).

---

## 10. Progress metrics (replace "hook coverage" as the headline)

- **% of per-frame VM instructions running through native code vs interpreted
  ASM** (coverage telemetry: `c64_re.coverage.CoverageCollector`, fed from the
  verifier's `VerifyOutcome.oracle_instructions`; unmeasured calls stay loudly
  outside the %). This is the headline number.
- **# of gameplay rules lifted to pure recovered functions, with tests.**
- **Semantic-snapshot state coverage** (fraction of observable state decoded +
  diffed).
- **Demo-corpus coverage** (levels/behaviors/RNG paths exercised) and **pass
  rate**.

Report measured numbers only — **an accurate 23% native beats an impressive
lie**.

**Definition of done:** the native loop runs the whole demo corpus with the VM
disabled in the hot path, and the VM-as-oracle suite confirms frame-and-state
exact equivalence for every demo in the corpus.

---

## 11. Rules of engagement (the laws)

1. **The original executable is the oracle. Never guess** a routine's behavior —
   trace it and read what it did.
2. **Verify before you trust.** No lift is "done" until diffed against the ASM
   oracle (per-hook) and/or the frame/state oracle (demos).
3. **Thin slices only.** One routine or one understood chain at a time; the game
   stays runnable at every step.
4. **Pure rule + thin adapter.** Keep recovered game logic side-effect-free and
   unit-tested; isolate VM memory/register/chip I/O in the adapter.
5. **Game specifics never leak into `c64_re`.** Addresses, VIC configurations,
   and formats live only in the adapter.
6. **One shared definition of "a boundary" and "a wait loop."** All drivers must
   agree, or the demo proof is void (§6).
7. **Full-memory + full-state diffs by default.** Narrowing the diff hides bugs
   (freed-stack scratch, flags, off-screen state, chip registers). Narrow only
   as a deliberate, temporary performance lever.
8. **When stuck, get the trace.** The per-hook divergence trace and the
   frame-verify divergence artifacts tell you exactly where reality and your
   model parted. Read them before theorizing.

---

*End of charter. The method here was piloted on Overkill and carried to a
complete VM-less port on Prehistorik 2 — both DOS games under `dos_re`; reuse
the patterns, but re-derive every address and format for your game — and
re-verify everything against your game's original binary, which is your only
oracle.*
