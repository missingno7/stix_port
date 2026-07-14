"""Replacement hooks: thin VM adapters over the pure recovered rules.

A hook does exactly four things (template §"Layering"): read state from
original memory/registers, call a clean recovered function that knows nothing
about the CPU, write the result back, and reproduce the routine's EXACT exit
mechanics (registers, flags, and the RTS).  No game logic accumulates here —
it lives in ``recovered/``, and the native runtime composes the same
functions with the VM gone.

Each hook is grounded against the oracle: install ``registry`` and run the
differential verifier over the demo (see ``tests/test_recovered_stix.py``).
"""
from __future__ import annotations

from c64_re.hooks import HookRegistry

from .bridge.state_fields import CIA1_PRA, CIA1_PRB, SID_V1_FREQ_HI, SID_V1_FREQ_LO, state
from .recovered.audio import voice1_frequency
from .recovered.input_decode import decode_joystick
from .recovered.sprites import sprite_to_grid

registry = HookRegistry()


def _rts(cpu) -> None:
    lo = cpu.pull()
    hi = cpu.pull()
    cpu.s.pc = ((lo | (hi << 8)) + 1) & 0xFFFF


@registry.replace(0x6A0B, "sid_voice1_freq")
def _sid_voice1_freq(cpu) -> None:
    st = state(cpu)
    lo, hi = voice1_frequency(st.sound_freq_source)
    st.sound_freq_lo = lo
    cpu.mem.wb(SID_V1_FREQ_HI, hi)
    cpu.mem.wb(SID_V1_FREQ_LO, lo)
    cpu.s.a = cpu._nz(lo)   # exit A = $4B18 (LDA $4B18); N/Z from it
    cpu.s.c = 0             # the trailing ROL $4B18 leaves carry clear
    _rts(cpu)


@registry.replace(0x763A, "poke_cia1_pra")
def _poke_cia1_pra(cpu) -> None:
    cpu.mem.wb(CIA1_PRA, cpu.s.a)   # STA $DC00 — A/X/Y/flags unchanged
    _rts(cpu)


@registry.replace(0x72A0, "sprite_to_grid")
def _sprite_to_grid(cpu) -> None:
    x = cpu.s.x
    msb_mask = 0x80 if x == 2 else 0x40
    carry = 1 if (cpu.mem.rb(0xD010) & msb_mask) else 0
    xl = cpu.mem.rb(0xD00C + x)
    yl = cpu.mem.rb(0xD00D + x)
    gx, gy = sprite_to_grid((carry << 8) | xl, yl)
    st = state(cpu)
    st.sprite_grid_x = gx
    st.sprite_grid_y = gy
    # exit A and flags reproduce the final `SEC; SBC #$30` on the sprite's Y
    cpu.s.a = yl
    cpu.s.c = 1
    cpu._sbc(0x30)
    _rts(cpu)


@registry.replace(0x739E, "read_joystick")
def _read_joystick(cpu) -> None:
    st = state(cpu)
    entry_x = cpu.s.x
    port = cpu.mem.rb(CIA1_PRB)
    joy = decode_joystick(port)
    st.joy_up = 1 if joy.up else 0
    st.joy_down = 1 if joy.down else 0
    st.joy_left = 1 if joy.left else 0
    st.joy_right = 1 if joy.right else 0
    st.joy_fire = 1 if joy.fire else 0
    st.fire_release = 0
    st.aux_input = 0
    # exact CPU exit state along $739E's three control-flow paths
    if joy.fire:                                    # fire held: RTS at $73E0
        cpu.s.a = (port >> 5) & 0xFF
        cpu.s.x, cpu.s.c, cpu.s.n, cpu.s.z = 1, 0, 0, 0
    else:                                           # $73E1: fire-release path
        enable = st.fire_release_enable
        if enable == 0:
            any_dir = joy.up or joy.down or joy.left or joy.right
            cpu.s.a = 0
            cpu.s.x = 1 if any_dir else entry_x
            cpu.s.c, cpu.s.n, cpu.s.z = 1, 0, 1
        else:
            st.fire_release = 1
            cpu.s.a = enable
            cpu.s.x, cpu.s.c, cpu.s.n, cpu.s.z = 1, 1, 0, 0
    _rts(cpu)
