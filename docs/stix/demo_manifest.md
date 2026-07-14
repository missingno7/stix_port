# Stix — demo manifest

The corpus is a measured artifact: track what it covers AND what it doesn't
(blind spots are open risks — pitfall #22). Recorded with
`python scripts/play.py --record-demo --demo-name NAME` (cold-start, whole
session from power-on).

| Demo | Frames | Source | Covers | Recorded over |
|---|---|---|---|---|
| demos/demo_run1_20260714_202142 | 6301 | human-played | cold boot → RUN/STOP trainer (NNNNN) → full game → game-over | oracle (pure ASM at record time) |
| demos/demo_stix_20260714_222316 | 527 | human-played | snapshot-anchored; joystick play, border-only movement (WZAD keyboard attempt — see controls.md gotcha) | oracle |
| demos/demo_stix_20260714_222635 | 4336 | human-played | snapshot-anchored; reached **level 2**. Same 48 JSR targets as level 1 — no new code, confirms the engine is compact/shared across levels | oracle |
| demos/demo_stix_20260714_224856 | 1911 | human-played | snapshot-anchored; **keyboard controls exercised** (both draw speeds, $4B07 and $4B08 both nonzero) — closes the keyboard blind spot below | oracle |

All four replay bit-identically (`scripts/grind.py check`). The full-demo
grind against `demo_run1` (the longest, most complete corpus member): **39
ORACLE_PASSING, 1538 calls, 0 unexpected divergences** over all 6301 frames
(one true self-modifying-code divergence at $00F1, expected — see
symbol_ledger.md). Against `demo_stix_20260714_224856` specifically: **35
ORACLE_PASSING, 1389 calls, 0 divergences**, and the lift census hit 100%
liftable (48/48) for the first time — see run_status.md session 7.

## Corpus blind spots (open risks)

- ~~Keyboard controls ($6CF8) unexercised~~ — CLOSED by
  `demo_stix_20260714_224856` (both draw-speed keys pressed).
- Only the NNNNN trainer answers; the Y-paths patch the game body ($6213
  et al.) and are completely unexercised.
- 5 playthroughs, all reaching similar early-game state; unclear which
  hazards/RNG branches beyond level 2 exist. The REFUSED (brk/bad_opcode/
  jmp_ind — 16 of 69) + LIFTED-not-fired routines include code these runs
  never entered; more/longer demos will exercise and either verify or
  refuse them.
- No demo yet isolates a specific transition (death→respawn, level-end) for
  targeted verification, nor a Y-answer trainer run.
