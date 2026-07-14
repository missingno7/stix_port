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

Reliable scheme: **arrow keys = move, SPACE (or Right-Ctrl) = draw.** This
is what `demo_run1` used. Mixing keyboard-letter movement (`W/Z/A/S`) with
SPACE works but the shared-column timing is fiddly; the joystick path is
clean. To also reach draw-speed-2, the viewer keymap would need the C64
cursor keys added (host PageUp/PageDown or similar) — not yet wired.
