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
| $739E | read_joystick_port1 | OBSERVED | clears $4B02-05,08,07,0B; reads $DC01, LSR×5 → UP$4B02/DOWN$4B03/LEFT$4B04/RIGHT$4B05/FIRE$4B08 (active-low). SPACE aliases to FIRE: prior routine leaves $DC00=$7F (col7), SPACE=(col7,row4)=fire bit4. See docs/stix/controls.md |
| $6CF8 | read_keyboard_controls | OBSERVED | runs only when $739E set nothing; W$4B02/Z$4B03/A$4B04/S$4B05 (col1), CRSR-UD$4B08/CRSR-LR$4B07/F5$4B0B (col0); ends LDA#$7F JSR $763A (select col7 for SPACE=fire next tick) |
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

The tick's own sequence (linear at $66C5): read_joystick $739E →
keyboard_controls $6CF8 → $7183 (hazard move: sprites 6/7 via $D41B random,
reads player pos) → $7479 → collision $73EC (set $4B2B) → $6AAC (move) →
collision → $6C41 (move sprite 3: $D006/7) → collision.

Correction (2026-07-14): the routines below were mislabelled "SMC" — they
are NOT self-modifying. They use the 6502 **BIT-skip idiom** ($2C = BIT abs
swallows the next 2 bytes, $24 = BIT zp swallows 1) so a branch "un-skips" a
constant load; the same bytes decode two ways by entry point. The lifter now
allows overlapping instruction decodes, so all of these are ORACLE_PASSING
(verified byte-exact + strict cycles over real level-1 and level-2 play,
`tests/test_lift_stix.py::test_bit_skip_overlap_routines_pass_oracle`):

Tick children understood (roles, now ORACLE_PASSING lifted):
- $6CF8 = keyboard controls (WASD $4B02-05 + CRSR/F5 $4B07/08/0B via matrix;
  skipped when joystick active — see docs/stix/controls.md). OBSERVED.
- $7183 (96 insns) = hazard AI move for sprites 6/7 (writes $D02D/$D02E,
  reads $D41B random + player pos $4B00/01); dispatches to the BIT-skip
  movers $72C2/$72F4/$7316/$7338/$735A (each lifts, overlaps=1..3).
- $6C41 (39 insns) = move hazard sprite 3 ($D006/$D007/$D010 MSB).
- $7479 (41 insns, BIT-skip), $6AAC (217 insns, BIT-skip) = movers, lifted.
- $653C (27 insns, BIT-skip $2C at $655B) = periodic BCD score/bonus
  accumulator: INC $4B20; every 256th call adds 20 (or 2 when $4B06==2, via
  the BIT-skip) to the 24-bit BCD counter $4B2E-30; fires during drawing.

Census over the executed code region jumped from ~54% to **91.2% liftable**
(52/57 JSR targets; 11 use the BIT-skip idiom). Remaining refusals: 4 brk +
1 bad_opcode (data bytes misread as call targets).

Big ORACLE_PASSING routines not yet disassembled: $6703 (228 insns, $67xx
draw region), $6237 (239 insns). Any true runtime-patched code would need
runtime_code
analysis; the $D41B-random hazard AI is the core game behaviour.

## Runtime state model — the $4B00 game-state page (earned field names)

| Address | Width | Name | Evidence |
|---|---|---|---|
| $4B00/$4B01 | u8,u8 | player_grid_x, player_grid_y | written by $73EC from sprite 0 |
| $4B02/$4B03/$4B04/$4B05 | u8 | in_up/down/left/right | $739E joy bits 0-3 / $6CF8 keys W,Z,A,S |
| $4B08 | u8 | in_draw1 (fire) | $739E joy bit 4 / SPACE (col7 alias) / CRSR-UD; the primary draw button, gates draw path $6B57 |
| $4B07 | u8 | in_draw2 | $6CF8 CRSR-LR only; second draw speed, gates $6BB3 path (Qix fast/slow) |
| $4B0B | u8 | in_abort (F5) | $6CF8 F5 only; read at $6077 → JMP $6223 |
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
