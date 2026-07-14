# Stix — symbol ledger (address → evidence)

Status ladder (template_dos_port canon): `GUESS → OBSERVED → RECOVERED →
ASM_MATCHED → VERIFIED → CANONICAL`. A name climbs only on evidence.
Nothing is RECOVERED yet — bring-up produced OBSERVED facts only.

## Code

| Address | Name | Status | Evidence |
|---|---|---|---|
| $080B | packed-PRG entry (BASIC `SYS 2059`) | OBSERVED | boot trace |
| $0100-$015x | decrunch_stackpage_loop | OBSERVED | PC profile, boot frames 0-200 |
| $0C40 | init_$0C40 (colors, clrscr, font copy, vectors) | OBSERVED | trace: $D020/$D021 writes, `JSR $E536`, copies char ROM $D800→$0800 |
| $0C88 | vector_restore_loop (ROM $FD30 → $0314-$0333) | OBSERVED | write log; forced the $FD30 table into the shim ROM |
| $0C90 | nmi_patch (vector low byte → $FEC1, RESTORE neutralized) | OBSERVED | write log |
| $0CE5/$0CEA | install_init_irq_$0D7D | OBSERVED | write log ($0314/15 ← $0D7D) |
| $0D10/$0D15 | restore_default_irq_$EA31 | OBSERVED | write log |
| $0D7D | irq_init_phase_$0D7D | GUESS | vector write only; body untraced |
| $2306-$230F | title_poll_loop (`LDA $DC01`; $7F→trainer, $EF→start fade) | OBSERVED | disassembly + input experiments |
| $2324 | title_fade_step_$2324 (X = phase) | OBSERVED | callers $2303/$2313/$2354 |
| $2352 | trainer_menu_$2352 (clrscr, 5 questions, patch game body) | OBSERVED | disassembly $2352-$2396 |
| $23A5 | trainer_ask_$23A5 (copy line, GETIN until 'Y'/'N'; SMC at $23AD) | OBSERVED | disassembly |
| $618A, $6DE7, $6E26 | gameplay code region | GUESS | PC samples during play; no boundaries traced |

## Data / state

| Address | Width | Name | Status | Evidence |
|---|---|---|---|---|
| $02/$03 | u16 | title_start_countdown (-$18/step; start at exactly $21A0) | OBSERVED | disassembly $22F6-$2322 |
| $2200+ | bytes | trainer_question_lines (screen codes, row-sized) | OBSERVED | $23A5 reads $2200,X |
| $6213, $74B2, $66D7, $66F1, $67E0, $68B7, $6B22 | u8 | trainer patch targets (lives/energy/hazard checks?) | GUESS | trainer writes them; meaning unconfirmed |
| sprite 0 | — | player crosshair, joystick port 1 | OBSERVED | movement experiment (y 190→131 on UP) |
| $D011=$3B, $D018=$1F | — | gameplay video mode (hires bitmap; decode $D018 pending) | OBSERVED | VIC regs during play |

## Naming candidates (not yet earned)

- "lives/energy/hazard checks" for the trainer patch targets — needs a Y-run
  A/B against an N-run.
- "main loop" for $61xx-$6Exx — needs boundary tracing before any name.
