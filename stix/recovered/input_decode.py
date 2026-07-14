"""Joystick input decode — recovered from $739E.

Evidence: $739E reads CIA1 port B ($DC01, joystick port 1) and tests bits
0-4, which are active-low (0 = pressed): up, down, left, right, fire.  The
original clears the five direction/fire flags in the $4B00 state page, then
sets each to 1 when its bit reads low.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..islands import oracle_link


@dataclass(frozen=True)
class JoyInput:
    up: bool
    down: bool
    left: bool
    right: bool
    fire: bool


@oracle_link(
    boundary="$739E",
    contract="CIA1 port B (joystick 1, active-low bits 0-4) -> direction/fire",
    status="RECOVERED",
)
def decode_joystick(port_b: int) -> JoyInput:
    """Decode a raw CIA1 port-B read into pressed booleans (active low)."""
    return JoyInput(
        up=not (port_b & 0x01),
        down=not (port_b & 0x02),
        left=not (port_b & 0x04),
        right=not (port_b & 0x08),
        fire=not (port_b & 0x10),
    )


# Keyboard fallback controls ($6CF8): scanned only when the joystick gave no
# input this tick.  Each entry maps a C64 keyboard-matrix key to the state-page
# flag it sets (offset from $4B00).  Derived from $6CF8's $DC00 column selects
# ($FD = col 1, $FE = col 0) + $DC01 row masks.
#
# STATUS: OBSERVED, not RECOVERED — the demo was played on the joystick, so
# $6CF8 always takes its "joystick active, skip keyboard" path and this mapping
# is UNEXERCISED.  Verifying it needs a keyboard-played demo (see
# docs/stix/demo_manifest.md corpus blind spots).
KEYBOARD_CONTROLS = {
    "W": 0x02,  # up
    "Z": 0x03,  # down
    "A": 0x04,  # left
    "S": 0x05,  # right
    "CRSR_UD": 0x08,  # fire
    "CRSR_LR": 0x07,  # (fire-release line)
    "F5": 0x0B,       # (aux)
}


@oracle_link(
    boundary="$6CF8",
    contract="keyboard fallback: if no joystick input this tick, map keys -> flags",
    status="OBSERVED",
)
def keyboard_controls(joystick_active: bool, pressed: frozenset) -> dict:
    """Flag updates from the keyboard when the joystick is idle.

    Returns ``{offset: 1}`` for each mapped key currently pressed (plus a
    reset of the fire-release flag $4B07), or ``{}`` when the joystick already
    supplied input this tick.  OBSERVED only — see KEYBOARD_CONTROLS.
    """
    if joystick_active:
        return {}
    out = {0x07: 0}  # $6CF8 clears $4B07 before scanning
    for key, off in KEYBOARD_CONTROLS.items():
        if key in pressed:
            out[off] = 1
    return out
