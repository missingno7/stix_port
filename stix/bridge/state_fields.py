"""The $4B00 game-state page as a typed view (see docs/stix/symbol_ledger.md).

Every field's name is earned from what a routine provably does with it (the
routine that reads/writes it is cited).  Offsets are relative to
``GAME_STATE_BASE`` ($4B00); this module is the only place they appear.
"""
from __future__ import annotations

from c64_re.state_view import StructView, U8, coerce_backend

GAME_STATE_BASE = 0x4B00

# Hardware register addresses the recovered routines target (facts, not game
# layout — but kept next to the hooks that use them for readability).
SID_V1_FREQ_LO = 0xD402
SID_V1_FREQ_HI = 0xD403
CIA1_PRA = 0xDC00        # joystick 2 / keyboard column drive
CIA1_PRB = 0xDC01        # joystick 1 / keyboard row read


class GameState(StructView):
    """Named fields of the $4B00 state page (offsets from $4B00)."""

    player_grid_x = U8(0x00)          # $4B00 — written by $73EC from sprite 0
    player_grid_y = U8(0x01)          # $4B01
    joy_up = U8(0x02)                 # $4B02 — set by $739E
    joy_down = U8(0x03)               # $4B03
    joy_left = U8(0x04)               # $4B04
    joy_right = U8(0x05)              # $4B05
    fire_release = U8(0x07)           # $4B07 — $739E fire-release path
    joy_fire = U8(0x08)               # $4B08
    fire_release_enable = U8(0x09)    # $4B09 — gates the fire-release flag
    aux_input = U8(0x0B)              # $4B0B — cleared by $739E (unnamed use)
    sound_freq_lo = U8(0x18)          # $4B18 — $6A0B scratch (= SID V1 FREQ LO)
    sound_freq_source = U8(0x28)      # $4B28 — $6A0B source byte
    sprite_grid_x = U8(0x3C)          # $4B3C — written by $72A0
    sprite_grid_y = U8(0x3D)          # $4B3D
    collision_disable = U8(0x4A)      # $4B4A — $73EC skip/countdown

    def __init__(self, source):
        super().__init__(coerce_backend(source, GAME_STATE_BASE), 0)


def state(cpu) -> GameState:
    """A :class:`GameState` view over a CPU's RAM (the $4B00 page is RAM)."""
    return GameState(cpu.mem.ram)
