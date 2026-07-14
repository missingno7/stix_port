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
# ($7F -> trainer, $EF -> start).  $23BE is the trainer's own Y/N poll
# (found 2026-07-14, session 7 — see INPUT_WAIT_ROUTINES): JSR $FFE4 (GETIN) /
# CMP #$4E (N) / BEQ done / CMP #$59 (Y) / BNE $23BE.  The in-game (post-title)
# input poll is not yet located.
INPUT_WAIT_HEADS: dict[int, str] = {
    **{pc: "title poll ($DC01)" for pc in range(0x2306, 0x2311)},
    0x23BE: "trainer Y/N poll (GETIN)",
}

# Routine ENTRY points (JSR targets) whose body contains an input-wait head
# above — i.e. the routine's own RTS is gated on a keypress arriving via the
# IRQ-driven keyboard buffer.  These are fundamentally unsuited to the
# automatic lift + differential hook oracle: a verified call runs with
# interrupts inhibited for its whole duration (c64_re.verification's
# documented contract), so SCNKEY never refills the buffer and the oracle
# spins until timeout (observed: HookDivergence "oracle never returned...").
# grind.py excludes these from its census/lift/verify census the same way it
# excludes the bootstrap and KERNAL regions — recover them by hand instead.
INPUT_WAIT_ROUTINES: dict[int, str] = {
    0x23A5: "trainer_ask — GETIN poll at $23BE, see INPUT_WAIT_HEADS",
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
