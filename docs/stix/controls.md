# Stix — controls (decoded from the oracle)

Evidence: input routines `$739E` (joystick) and `$6CF8` (keyboard),
disassembled + confirmed against `demo_run1` (1807 draw-plot events at
`$6B6D`, with SPACE as the only fire input — no joystick mask ever carried
the fire bit). Status: OBSERVED, reversible to ASM.

## What can be pressed

| Action | Joystick port 1 | Keyboard | Writes flag |
|---|---|---|---|
| Up | up | `W` | `$4B02` |
| Down | down | `Z` | `$4B03` |
| Left | left | `A` | `$4B04` |
| Right | right | `S` | `$4B05` |
| Draw / fire (speed 1) | fire | `SPACE`, or cursor ↑/↓ | `$4B08` |
| Draw (speed 2) | — | cursor ←/→ | `$4B07` |
| Abort/pause | — | `F5` (→ `$6223`) | `$4B0B` |

Movement is a **W/Z/A/S diamond** (right is `S`, not `D`). On a border you
can only travel along it with no fire held; hold **fire + a direction** to
draw a line into the open area, then reconnect to a border/your own line to
claim the enclosed region (Qix mechanic).

## SPACE-as-fire (shared matrix line)

Both input routines end by leaving keyboard **column 7 selected**
(`LDA #$7F : STA $DC00`, `$6CF8` via `JSR $763A`). SPACE is at matrix
(col 7, row 4); joystick-port-1 fire is `$DC01` bit 4 — the *same* line.
So a held SPACE pulls the fire bit low and `$739E` reads it as fire. This
is deliberate (a common C64 idiom) and the emulator models it exactly
(`machine._matrix_pulls` + `joy1` share `$DC01`), which is why SPACE draws
replay bit-identically.

## Two draw speeds (classic Qix)

`$4B08` (fire path, `$6B57`→draw at `$6B6D`) and `$4B07` (`$6BB3` path) are
the fast/slow draw pair. The joystick's single fire button reaches only
`$4B08`; both cursor-key pairs reach both on a real keyboard. The viewer
maps host arrows to the joystick and does **not** currently expose the C64
cursor keys, so only draw-speed-1 is reachable in the viewer today.

## Playing in the viewer

Two schemes; pick one, don't mix (see the gotcha below):

- **Joystick (recommended, one draw speed):** arrow keys = move,
  **SPACE or Right-Ctrl** = draw. This is what `demo_run1` used.
- **Keyboard (both draw speeds):** `W/Z/A/S` = move, **PageUp** = draw-speed-1
  (C64 CRSR↑↓ → `$4B08`), **PageDown** = draw-speed-2 (C64 CRSR←→ → `$4B07`),
  `F5` = abort. The cursor keys are now mapped in the viewer keymap
  (`player._build_keymap`) on PageUp/PageDown — host keys chosen not to
  collide with any host key the game reads.

**Gotcha — why you can't mix them:** `$6CF8` (keyboard) runs only when
`$739E` (joystick) set nothing that tick (`ORA $4B02..$4B08 / BNE skip`).
So the keyboard-only controls (draw-speed-2 `$4B07`, abort `F5`) are read
**only while the joystick is completely idle**. Move with the joystick and
they're ignored; move with `W/Z/A/S` and they work. Likewise, holding SPACE
during keyboard play aliases to fire in `$739E`, which makes `$6CF8` skip —
so SPACE breaks `W/Z/A/S` movement. Keyboard players draw with PageUp/PageDown,
not SPACE.
