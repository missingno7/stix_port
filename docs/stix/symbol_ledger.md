# Stix — symbol ledger (address → evidence)

Status ladder (template_dos_port canon): `GUESS → OBSERVED → RECOVERED →
ASM_MATCHED → VERIFIED → CANONICAL`. A name climbs only on evidence.
Nothing is RECOVERED yet — but 31 routines are ORACLE_PASSING lifted
artifacts (byte-exact over the full demo), and the disassembly below is
UNDERSTOOD (semantics earned from hardware contracts + traced reads/writes,
reversible to the ASM). These are the refactoring queue toward pure source.

## Gameplay routines (understood from ORACLE_PASSING disassembly)

Names earned from HARDWARE FACTS (register targets), not screen-watching:

| Address | Name | Status | Evidence |
|---|---|---|---|
| $739E | read_joystick_port1 | OBSERVED | clears $4B02-08, reads $DC01 (joy1), LSRs 5 bits → dir/fire flags; fire-release path checks $4B09→$4B07 |
| $73EC | player_vs_hazard_collision | OBSERVED | reads sprite0 pos ($D000/1/+MSB) → player grid $4B00/$4B01; compares vs sprites 6,7,3 ($D00C-F,$D006/7); $4B4A disables (DEC + ret 1) |
| $72A0 | sprite_to_grid(x_reg=sprite sel) | OBSERVED | reads $D00C+x/$D00D+x + MSB $D010 → grid $4B3C/$4B3D = (sx9>>1)-$0B, sy-$30 |
| $6A0B | sid_voice1_freq_from_$4B28 | OBSERVED | bit-reverses low nibble of $4B28→$4B18, hi nibble; writes SID $D402/$D403 (voice-1 freq) |
| $709F | bitmap_pixel_addr(x=X,y=Y) | OBSERVED | X,Y→byte addr $14/$15 via row table $6F1B, returns col-pair X=x&3, row Y=y&7, A=byte |
| $70D9 | plot_pixel | OBSERVED | JSR $709F; ORA mask $75D1,X; STA ($14),Y — sets a hires/MC bitmap pixel |
| $697F | test_pixel | OBSERVED | LDA ($45),Y AND $75D1,X — reads a bitmap pixel; sets $46 bit7 |
| $763A | poke_cia1_pra | OBSERVED | STA $DC00 (joystick/keyboard column select) |
| $6703, $6237 | large gameplay routines (228, 239 insns) | OBSERVED | ORACLE_PASSING; not yet disassembled in full |

## Game tick structure (from the caller graph, ~68 ticks / 120 frames)

The main per-tick routine lives around $66xx and sequences the subsystems
(each caller fires ~once per tick unless noted); this is the call order the
native tick driver (`stix/native/`) will reproduce:

| Caller | Calls | Role |
|---|---|---|
| $66C5 | read_joystick $739E | input phase |
| $66D1, $66DE, $66EB | collision $73EC ×3 | hazard collision (3 hazards) |
| $680D | sid_voice1_freq $6A0B | audio |
| $719F, $7203 | sprite_to_grid $72A0 | sprite→grid (2 sprites) |
| $6955 (×210!), $68A5, $67D2 | bitmap_test $697F | draw: read-pixel inner loops |
| $6B05, $6BD0 | bitmap_pixel_addr $709F | draw: address setup |
| $6B80 | bitmap_plot $70D9 | draw: set-pixel |
| $6D87 | poke_cia1_pra $763A | (CIA port select) |

Big ORACLE_PASSING routines not yet disassembled: $6703 (228 insns, $67xx
draw region), $6237 (239 insns). $66xx is the top of the tick — the next
target for understanding the whole-frame flow.

## Runtime state model — the $4B00 game-state page (earned field names)

| Address | Width | Name | Evidence |
|---|---|---|---|
| $4B00/$4B01 | u8,u8 | player_grid_x, player_grid_y | written by $73EC from sprite 0 |
| $4B02/$4B03/$4B04/$4B05 | u8 | joy_up/down/left/right | set by $739E from $DC01 bits 0-3 |
| $4B08 | u8 | joy_fire | set by $739E from $DC01 bit 4 |
| $4B07/$4B09 | u8 | fire-release flag / its enable | $739E fire-not-pressed path |
| $4B3C/$4B3D | u8,u8 | sprite_grid_x, sprite_grid_y | written by $72A0 |
| $4B28 | u8 | sound_freq_source | read by $6A0B → SID voice-1 freq |
| $4B18 | u8 | sound_freq_lo scratch | $6A0B; also = SID $D402 |
| $4B4A | u8 | collision_disable countdown | $73EC BNE/DEC |
| $14/$15, $45/$46 | ptr | bitmap byte pointers | $709F/$697F |
| $6F1B.. | table | bitmap row-address table (Y//8→base) | $709F index |
| $75D1.. | table | bitmap pixel bit-mask (x&3→mask) | $70D9/$697F |

## Original symbol ledger below


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
