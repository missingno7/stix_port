# Stix — demo manifest

The corpus is a measured artifact: track what it covers AND what it doesn't
(blind spots are open risks — pitfall #22). Recorded with
`python scripts/play.py --record-demo --demo-name NAME` (cold-start, whole
session from power-on).

| Demo | Frames | Source | Covers | Recorded over |
|---|---|---|---|---|
| demos/demo_run1_20260714_202142 | 6301 | human-played | cold boot → RUN/STOP trainer (NNNNN) → full game → game-over | oracle (pure ASM at record time) |

Replays bit-identically (`scripts/grind.py check`). Drove the first grind:
69 routines exercised, 31 ORACLE_PASSING (see `artifacts/grind/`).

## Corpus blind spots (open risks)

- **Keyboard controls ($6CF8) unexercised** — the demo was played on the
  joystick, so $6CF8 always takes its "joystick active, skip keyboard" path;
  its WASD + cursor-key mapping (`stix.recovered.input_decode.keyboard_controls`,
  status OBSERVED) can't be verified without a **keyboard-played demo**.
  Ask the human for one recorded with the keyboard (W/A/S/Z + cursor keys).
- Only the NNNNN trainer answers; the Y-paths patch the game body ($6213
  et al.) and are completely unexercised.
- Single playthrough — unclear which hazards/levels/RNG branches it reaches.
  The 27 REFUSED + 8 LIFTED-not-fired routines include code this run never
  entered; more demos will exercise and either verify or refuse them.
- No demo yet isolates a specific transition (death→respawn, level-end) for
  targeted verification.
