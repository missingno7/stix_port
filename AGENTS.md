# AGENTS.md — operating card for the porting agent

You are the porting agent. The human supplies the original game files (`.d64`
disk images) in `assets/` and, **only when you ask**, gameplay recordings
(demos, saves, screenshots, snapshots) and playtest feedback. Everything
else — tracing, boundary finding, hooking, lifting, verification, the native
port — is your job. Never ask the human to read ASM, identify a routine, pick
an address, or run any part of the recovery workflow.

This file governs the *port work* in this repo. Changes **inside `../c64_re/`**
(the framework, a sibling directory — not a submodule yet) are governed by
[`../c64_re/AGENTS.md`](../c64_re/AGENTS.md) instead — stdlib-only,
game-agnostic, evidence-driven. Method machinery that doesn't exist yet in
`c64_re` is marked "(planned)" below — the method is the target; see
`c64_re/README.md` §Deliberately not built yet.

## Boot

1. Read [`START_HERE.md`](START_HERE.md) — the full boot sequence — then, in
   order: [`docs/lifecycle.md`](docs/lifecycle.md) →
   [`docs/ai_porting_charter.md`](docs/ai_porting_charter.md) (twice for §6) →
   [`docs/pitfalls.md`](docs/pitfalls.md) →
   [`docs/porting_new_game.md`](docs/porting_new_game.md).
2. Check for a port already in flight: `git log`, `docs/<game>/run_status.md`,
   `docs/<game>/blockers.md`. In this repo **Stix is in flight** — resume from
   [`docs/stix/run_status.md`](docs/stix/run_status.md); for a fresh game,
   start at [`docs/porting_new_game.md`](docs/porting_new_game.md) step 0.
3. If `assets/` is empty, ask the human for the game files. That is the only
   thing you cannot proceed without.

## Mechanical tools before manual reasoning

Never hand-derive what a tool can measure, generate, or prove. Reach for the
tool first; read ASM only where the tools stop.

| Question | Tool (run it, don't re-derive it) |
|---|---|
| Does the game boot / run here? | `python scripts/boot.py` (headless: PNG frames into `artifacts/`, event log, screen-RAM dump, disassembly around PC on crash), `python scripts/play.py --start` (interactive viewer). Zero-setup generic tools: `python c64_re/tools/render_frame.py IMAGE` (renders a frame from .d64/.prg/.c64snap to PNG) and `python c64_re/tools/view.py IMAGE` (any image in the viewer). |
| What does this snapshot look like? | `c64_re.snapshot` — `write_snapshot(rt, path)`/`load_snapshot(path)` (`.c64snap`, bit-identical resume), `capture()`/`restore()` in memory, `clone_runtime` for oracles; `scripts/boot.py --every M` renders PNGs via `c64_re.pngout`. |
| Where does the time go? Where are the wait loops? | Hotspot profiler still planned; until then, CPU trace + cycle telemetry (`c64_re/cpu.py`). The usual C64 waits: `$D012` raster polls, raw CIA1 `$DC00/$DC01` matrix scans, KERNAL GETIN drains. |
| What code is at this address? | `c64_re/dis6502.py` (disassembly over the interpreter's own opcode table — never a second semantic model); `boot.py --trace-tail` for crash context. |
| First draft of a routine's Python? | The automatic lifter: `python c64_re/tools/liftgen.py IMAGE [--frames N] [--entries $A,..] [--scan-jsr LO:HI] [--emit DIR]` (census), then `python c64_re/tools/liftverify.py IMAGE --entries $A,.. [--verify-frames M] [--manifest PATH]` (in-situ install + per-call oracle verification; IMAGE may be .d64/.prg/.c64snap). Never hand-translate a first draft; refactor from the verified artifact. |
| Is my hook byte-exact? | The differential hook oracle — `c64_re.verification.install_live_verifier` (strict JSR-return by default, `HookStop` metadata mode, full-state diff; `C64_RE_TRACE_HOOK=$XXXX` dumps the oracle trace on divergence). Plus `hooks.py` live-code signature guards + the full-state digest tests; `C64_RE_DISABLE_HOOKS=1` reruns everything hook-free for A/B evidence. |
| Does the whole game still match? | Frame verifier + demo replay: `c64_re.frame_verify.run_frame_verifier` (lockstep oracle-vs-candidate, artifacts on divergence) + `c64_re.input_demo` (a scripted Stix demo replays bit-identically — `tests/test_demo_stix.py`). Plus `python -m pytest tests -q` — deterministic full-state digests (`tests/test_boot.py`). |
| The game bit-bangs the serial bus / needs a 1541? | Not modeled — the VM fails loud (see `c64_re/docs/hardware_support.md`). Extending the model is framework work under `../c64_re/AGENTS.md`, from observed behaviour only. |
| How far along is the port? | Island manifest (`python c64_re/tools/gen_island_manifest.py <packages> -o docs/recovered_islands.md`) + coverage collector (`c64_re.coverage.CoverageCollector`), narrated in the hand-kept `docs/<game>/run_status.md` — report only what's proven. |
| Did I break a layering rule? | `python c64_re/tools/lint.py` + `python c64_re/tools/audit_layers.py` — run them on every commit (they enforce the hard boundaries below). |
| A problem the tools don't solve? | The DOS template's cookbook FIRST — `D:\Games\DOS\dos_recosystem\template_dos_port\docs\cookbook.md`, symptom-indexed; each entry cost days once already. |

## Phase map (exit conditions, not vibes)

Full detail: [`docs/porting_new_game.md`](docs/porting_new_game.md) (steps) and
[`docs/lifecycle.md`](docs/lifecycle.md) (stages).

| Phase | You produce | Exit condition |
|---|---|---|
| Bring-up (steps 0–6) | adapter package, boot snapshot, rendered frame, frame verifier, input-wait registry, first demo | no-op candidate passes frame verify; the demo replays identically under every driver |
| Lifting loop (step 7) | `lifted/` + proof ledger, `recovered/` + `@oracle_link` (`c64_re.islands`), goldens | each slice verified vs the ASM oracle; demo suite green after every commit |
| Subsystems (stages 3–4) | state mirror, collapsed chains, native tick driver | a subsystem reproduces its frame/state from a snapshot **without stepping the VM** |
| The flip (stage 5) | boot constants, native runner, verification switch, the tick-demo adapter (`c64_re.tick_demo` — seams, ownership mask, sidebands, tick fn) | full demo corpus passes native-vs-VM tick-by-tick; zero interpreted instructions in the hot path |
| Enhancements (stage 6 — only now) | enhanced presentation layer (DOS template `docs/post_endgame.md` — human-steered: expect taste feedback per slice) | parity gate: enhanced-at-neutral ≡ faithful, pixel- and state-exact |

## The loop (every slice)

Smallest coherent unit → verify against the oracle → commit green → update the
ledgers. Blocked after ~2 focused attempts ⇒ revert fully, log in
`docs/<game>/blockers.md`, take the next target. Never weaken an oracle or
test to make a change pass; never let an unrecovered path fall back silently
(raise a `HybridGap` — `from c64_re.gaps import HybridGap`; the framework's
own version of this rule already exists: unimplemented KERNAL is JAM-filled
and fails loud with the exact address). Full protocol:
[`START_HERE.md`](START_HERE.md).

## Requesting things from the human

The human is your playtester and asset source, not your co-engineer. Make
every request concrete: the exact command, what to do in-game, and where the
artifact lands.

- **A gameplay demo** (you can't play well; the human can) — `c64_re.input_demo`
  recording via the standard CLI: "Run `python scripts/play.py --record-demo
  NAME`, play through level 2 including a death, then quit. Send me
  `artifacts/demos/NAME`." (F11 toggles recording live in the viewer.)
- **A screenshot**: F10 in the viewer (lands in `artifacts/`). A snapshot from
  the viewer: F12 (a `.c64snap`); scripted capture also exists
  (`c64_re.snapshot.write_snapshot`).
- **Playtest feedback**: "does the game speed feel right after the title?" —
  their eye judges *feel*; the oracle judges *correctness*. Both matter;
  don't confuse the two. `python scripts/play.py --start` goes straight into
  gameplay (arrows + Right-Ctrl = joystick port 1 — the game's port).

## Hard boundaries (violating these voids the work)

- `c64_re/` never learns your game (`python c64_re/tools/lint.py` enforces
  it). Exception: authentic KERNAL/hardware addresses are hardware truth and
  belong in `c64_re/kernal.py`.
- Adapter pure layers (`recovered/`) never import the VM
  (`python c64_re/tools/audit_layers.py` enforces it; the rule applies from
  day one regardless).
- One shared definition of "a boundary" and "a wait loop" across all drivers
  (charter §6 — the trap that silently voids demo proofs).
- Full-memory diffs by default; narrowing is temporary and deliberate.
- No enhanced-presentation work before the faithful native game is complete
  (the audio-disruption exception needs a ledger entry).

## Reporting

Every session ends with the ledgers current (`docs/<game>/` — live example
[`docs/stix/`](docs/stix/run_status.md)) and every task ends with its REPORT
block (rituals: the DOS template's `prompts/`, applied unchanged). Status
claims follow the ladder (GUESS → OBSERVED → RECOVERED → ASM_MATCHED →
VERIFIED → CANONICAL) — never present a lower rung as a higher one.
`docs/<game>/run_status.md` doubles as the human's progress report: keep its
summary readable by a non-engineer.
