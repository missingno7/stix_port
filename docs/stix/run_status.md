# Stix — run status

## Summary (for the human)

The original Stix disk boots and plays inside our new C64 recovery VM, and
your full-game demo (power-on through game-over) is now the reference
oracle. Against that whole 2-minute playthrough, the automatic lifter has
turned **31 of the game's own routines into Python that was checked against
the original on every call — 1,222 calls, zero differences** — while the
game played through to game-over as a live hybrid. That is the first real
slice of the game provably reproduced. The tool also flagged three routines
it could NOT safely reproduce yet (self-modifying zero-page code and two
loop/wait constructs) — exactly the honest "not done" signal the method is
built to surface. Grind driver: `python scripts/grind.py`.

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
  overflow and the JSR $709F freed-stack scratch). Island manifest:
  `docs/stix/recovered_islands.md` (6 RECOVERED).
- Lift manifest over the full demo: **31 ORACLE_PASSING** (1,475 instr,
  3,353 code bytes proven byte-exact), 3 DIVERGED, 8 LIFTED-not-fired,
  27 REFUSED, of 69 routines (`artifacts/grind/lift_manifest.json`).
- Islands by status: 6 RECOVERED (verified) pure functions; the 31
  ORACLE_PASSING lifted artifacts remain the refactoring queue.
- Demo corpus: 1 — `demo_run1_20260714_202142` (cold-start, 6301 frames,
  power-on → trainer → full game → game-over; replays bit-identically).
- Open blockers: none. Findings to chase: $00F1 (runtime-patched SMC →
  runtime_code machinery), $7166/$70E2 (non-returning loop/wait constructs
  → checkpoint seams, not leaves).

## Recent findings (newest first)

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

1. Grow the demo corpus: more played demos covering paths this one misses
   (other trainer answers, each hazard, edge cases) — each replays into the
   grind and widens verified coverage. Ask the human.
2. Refactor the ORACLE_PASSING lifted artifacts into named pure rules
   (recover_one_routine), biggest/hottest first: $6703 (228 insns), $6237
   (239 insns), $7183 (96 insns). Name via evidence; track with @oracle_link.
3. Chase the DIVERGED findings: wire $00F1 through `runtime_code` (variant
   guarding); classify $7166/$70E2 as checkpoint/wait seams.
4. Frame-boundary identification → frame verifier with a no-op candidate
   (the frame oracle already proved the lifted hybrid pixel-exact for 100
   frames; extend it across the whole demo).
5. Push liftable count up: several REFUSED entries are indirect-jump
   dispatchers — candidates for jump-table recovery, not static lifting.
