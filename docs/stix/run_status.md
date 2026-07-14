# Stix — run status

## Summary (for the human)

The original Stix disk boots and plays inside our new C64 recovery VM, and
your demos (five now, including a full game and a level-2 run) are the
reference oracle. Against the full 2-minute playthrough, the automatic
lifter has turned **39 of the game's own routines into Python that was
checked against the original on every call — 1,538 calls, zero unexpected
differences** — while the game played through to game-over as a live
hybrid. That is the first real slice of the game provably reproduced. The
tool also flags what it can't safely reproduce yet — one true
self-modifying-code spot — the honest "not done" signal the method is
built to surface (two earlier "unsafe" guesses turned out to be a
misdiagnosis, corrected this session — see below). Grind driver:
`python scripts/grind.py`.

## Where we are

- Phase: recovery loop (recover_one_routine) — the `stix/` adapter now
  follows the pre2_port layer layout (recovered/ bridge/ native/ hooks.py
  input_waits.py verification.py probes/).
- Native %: first recovered islands landed. **6 recovered functions**
  (`stix/recovered/`), **7 wired as verified hooks and proven BYTE-EXACT
  against the demo oracle** — I/O + audio + the whole hires-bitmap pixel
  subsystem: `sid_voice1_freq`, `read_joystick`, `sprite_to_grid`,
  `poke_cia1_pra`, `bitmap_pixel_addr`, `bitmap_plot`, `bitmap_test`
  (0 divergences over 1300+ frames, `tests/test_recovered_stix.py`;
  the bitmap ones required reproducing the address ADC's exact carry +
  overflow and the JSR $709F freed-stack scratch). Plus the **collision
  gameplay logic** ($73EC) recovered as pure functions and SHADOW-VERIFIED
  against the ASM (player grid pos + the hit boolean the caller reads via
  the Z flag — 0 mismatches over 993 calls). Island manifest:
  `docs/stix/recovered_islands.md` (8 RECOVERED islands).
- Lift manifest over the full demo: **39 ORACLE_PASSING**, 1 DIVERGED
  (the one true SMC spot, $00F1), 11 LIFTED-not-fired, 18 REFUSED
  (10 brk + 5 bad_opcode + 1 jmp_ind + the 2 non-local-return routines),
  of 69 routines (`artifacts/grind/lift_manifest.json`).
- Islands by status: 8 RECOVERED pure functions (7 hook-verified byte-exact,
  collision shadow-verified); the 39 ORACLE_PASSING lifted artifacts remain
  the refactoring queue.
- Demo corpus: 5 recorded, 4 human-played and analyzed — see
  `docs/stix/demo_manifest.md` (full game, level 2, keyboard controls).
- Open blockers: none. Findings to chase: $00F1 (runtime-patched SMC →
  runtime_code machinery). $7166/$70E2 are RESOLVED this session (see
  below) — they were never checkpoint seams; corrected in the ledger.

## Recent findings (newest first)

- 2026-07-14 (session 7, part 2) — **Lifter learned the non-local-return
  idiom; $7166/$70E2 were misdiagnosed.** Installing every lifted routine
  across a new keyboard-controls demo hung: $6AAC's lifted hook nested a
  JSR into $70E2, which nested a JSR into $7166 — which sometimes does
  `PLA PLA; ...; RTS`, discarding $70E2's return address and cascading two
  levels back to $6AAC. Legal on hardware; fatal to `emulate_call`'s
  single-frame return bookkeeping. Fixed generically in `c64_re/lift/cfg.py`:
  `scan_function` tracks each routine's own PHA/PLA balance and refuses a
  net-negative one as `nonlocal_return`; `refuse_unsafe_callers` refuses its
  direct callers as `calls_nonlocal_return` (stopping at one level — callers
  further up are unaffected once the unsafe pair is left uninstalled).
  Result: full-demo grind went from 31 → **39 ORACLE_PASSING** with the
  crash gone (`test_lift.py::test_scan_refuses_nonlocal_return`,
  `test_refuse_unsafe_callers_flags_direct_caller_only`). $7166 is
  correctly understood now: `test_move_collision_abort`, not a wait loop.
- 2026-07-14 (session 7, part 1) — **Lifter learned the 6502 BIT-skip idiom.** The
  hottest "missing" routines were not self-modifying code (as the ledger
  guessed) but the `$2C`/`$24` BIT-skip trick (a branch lands inside a BIT
  operand, so bytes decode two ways). The lifter previously refused these as
  `mid_insn`; it now allows overlapping instruction decodes. Result: the
  executed-code census jumped ~54% → **91.2% liftable** (52/57), and the top
  10 formerly-refused routines — the hazard-AI movers $72C2/$72F4/$7316/
  $7338/$735A/$7479/$6AAC (217 insns) and the score accumulator $653C
  (28,591 calls in one demo) — all lift and pass the differential oracle
  byte-exact + strict cycles (2,088+ verified calls, 0 divergences across
  level-1 and level-2 play). Locked in by `test_lift_stix.py` and a
  framework regression `test_lift.py::test_bit_skip_overlap_*`. Also decoded
  the keyboard controls ($6CF8) and fixed the viewer controls docs — see
  docs/stix/controls.md (W/Z/A/S move, PageUp/PageDown = the two draw
  speeds; keyboard-only controls are ignored while the joystick moves).
- 2026-07-14 (session 6) — Recovery-proper started: `stix/` restructured to
  the pre2 layer layout. First recovered source — pure functions in
  `stix/recovered/` (input/audio/sprites/bitmap), the $4B00 state model as a
  typed view in `stix/bridge/`, thin verified hooks in `stix/hooks.py`. Four
  hooks pass the differential oracle byte-exact on the real demo (incl. the
  branchy $739E joystick, exact exit-state derived by hand). Pure layer is
  VM-free (audit_layers enforced in the test suite).
- 2026-07-14 (session 4) — First recovery grind against the full-game demo:
  census found 69 exercised routines (2,657 code bytes touched over 6301
  frames); 42 lift statically; a full-demo differential sweep (per-routine
  cap 50, uninstall-on-divergence) proved **31 ORACLE_PASSING, 1,222 calls,
  0 divergence** in 57s. Divergences caught by the oracle: $00F1
  (runtime-patched), $7166/$70E2 (unbounded — don't return to caller).
  Reproduce: `python scripts/grind.py all --demo artifacts/demos/demo_run1_...`.
- 2026-07-14 (session 4) — Full playthrough demo replays BIT-IDENTICALLY
  over all 6301 frames (`scripts/grind.py check`).
- 2026-07-14 (session 3) — c64_re now mirrors dos_re completely (except
  viewer audio / post-endgame widgets): input demos (a scripted Stix
  gameplay demo replays bit-identically — `tests/test_demo_stix.py`), the
  standard play CLI (`--record-demo`/`--play-demo`/`--verify-hooks`/...,
  F10/F11/F12), the frame oracle, tick demos, checkpoints, islands,
  coverage, runtime-code (SMC), state views, and the lint/audit/manifest
  guardrail tools. 101 framework + 7 port tests green. **The human can now
  record cold-start demos:** `python scripts/play.py --record-demo
  --demo-name NAME` (whole session from power-on; recording auto-starts,
  close the window to save).
- 2026-07-14 (session 3) — Frame-oracle proof on the real game: the hybrid
  runtime (3 lifted hooks installed) ran PIXEL-IDENTICAL to the pure-ASM
  oracle at every one of 100 gameplay frame boundaries — and a planted
  $D021 difference was caught at frame 1 with ref/cand/diff PNG artifacts
  (`tests/test_frame_verify_stix.py`).
- 2026-07-14 — Lifter + differential verifier proven in situ: JSR census
  over $0800-$7FFF found 76 candidates, 41 liftable; 16 installed as
  lifted hooks; 6 fired during 150 gameplay frames and passed 781
  oracle-verified calls with 0 divergences under the strict cycle model
  ($73EC ~2.4 calls/frame, $7183 96 insns + 7 call deps, $739E, $70A5,
  $706A, $763A). Locked in by `tests/test_lift_stix.py`.
- 2026-07-14 — Gameplay snapshot (`artifacts/gameplay.c64snap`) resumes
  bit-identical to the live runtime (proved in-line before the census).

- 2026-07-14 — Deterministic under scripted input: full-machine digest
  identical across runs (proved by `tests/test_boot.py`, 3 passed).
- 2026-07-14 — Gameplay reached: bitmap mode $D011=$3B, 7 sprites, joystick
  port 1 moves sprite 0; Stix collision → GAME OVER (frame evidence in
  `artifacts/`).
- 2026-07-14 — Trainer menu driven via KERNAL GETIN (SHIFT opens, 5 × Y/N);
  answers patch the decrunched body ($6213 et al.).
- 2026-07-14 — Three shim-KERNAL contracts the game forced, now in c64_re
  with tests: CIA1 ack in the default IRQ ($DC0D read), the real vector
  table image at ROM $FD30 (game block-copies it), direct-call internals
  ($E536/$E544/$FDA3/...).

## Risks / unknowns

- Trainer 'Y' answers untested (patch semantics = GUESS in the ledger).
- Title "hold fire to start" countdown ($02/$03 → $21A0) observed cycling
  but never driven to completion; start_game() uses the trainer path.
- Shim chargen font differs cosmetically from the real ROM (game copies
  char ROM to $0800 at init); real `roms/chargen` would restore glyphs.
- VIC timing is line-granular, no badline cycle stealing — raster-counting
  code lands on slightly different lines than hardware (deterministically).
  No effect observed on Stix so far.

## Next targets (evidence-ordered)

1. Grow the demo corpus: more played demos covering paths these five miss
   (Y trainer answers, each hazard, death/respawn, game-over from level 2+)
   — each replays into the grind and widens verified coverage. Ask the human.
2. Refactor the ORACLE_PASSING lifted artifacts into named pure rules
   (recover_one_routine), biggest/hottest first: $6703 (228 insns), $6237
   (239 insns), $7183 (96 insns), $6AAC (217 insns). Name via evidence;
   track with @oracle_link. $7166/$70E2 are understood (collision-abort)
   but stay lift-excluded by design — recover them by hand instead.
3. Chase the one remaining DIVERGED finding: wire $00F1 through
   `runtime_code` (variant guarding) — the only true SMC spot found so far.
4. Frame-boundary identification → frame verifier with a no-op candidate
   (the frame oracle already proved the lifted hybrid pixel-exact for 100
   frames; extend it across the whole demo).
5. Push liftable count up: the 5 brk + 1 jmp_ind refusals are likely
   indirect-jump dispatchers — candidates for jump-table recovery, not
   static lifting. 5 bad_opcode refusals are probably data bytes
   misidentified as JSR targets by the census heuristic — check first.
