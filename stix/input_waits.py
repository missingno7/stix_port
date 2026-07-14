"""Input-wait registry — the poll loops the game parks in between inputs.

The single shared registry consumed by every driver (viewer, demo replay,
frame verifier): when the game is spinning in one of these loops sampling
input, demo events are delivered one per frame so a same-frame release/press
pair is observed separately (otherwise the game's debounce collapses two
taps into one — the proven dos_re rule).

Detected at the canonical HEAD address, checked every step.
"""
from __future__ import annotations

# PC -> description.  The title/attract loop at $2306 polls $DC01 raw
# ($7F -> trainer, $EF -> start).  The in-game input poll is not yet located.
INPUT_WAIT_HEADS: dict[int, str] = {
    pc: "title poll ($DC01)" for pc in range(0x2306, 0x2311)
}


def is_input_wait(obj) -> bool:
    """True when the game is parked in an input-poll loop.  Accepts a PC int,
    a CPU (``.s.pc``), or a Runtime (``.cpu.s.pc``)."""
    if isinstance(obj, int):
        pc = obj
    elif hasattr(obj, "cpu"):
        pc = obj.cpu.s.pc
    else:
        pc = obj.s.pc
    return pc in INPUT_WAIT_HEADS
