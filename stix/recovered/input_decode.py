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
