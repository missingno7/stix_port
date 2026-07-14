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
from .recovered.bitmap import bitmap_byte_addr, plot_pixel, test_pixel
from .recovered.input_decode import decode_joystick
from .recovered.sprites import sprite_to_grid

# Game data tables the bitmap routines index (addresses are game layout).
BITMAP_ROW_TABLE = 0x6F1B   # $6F1B: 16-bit cell-row base addresses (per y>>2)
PIXEL_MASK_TABLE = 0x75D1   # $75D1: column bit-mask per (x & 3)

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


# ---- hires bitmap pixel primitives ($709F / $70D9 / $697F) --------------------
def _bitmap_addr(cpu) -> tuple[int, int, int, int, int]:
    """Replicate $709F's address computation for pixel (X_reg, Y_reg): stash
    the args at $4B1C/$4B1D, set the bitmap byte pointer $14/$15, and return
    (byte_addr, row=y&7, col_pair=x&3, carry, overflow).  ``carry``/``overflow``
    are the exit C/V of the two-byte ``ADC`` (row-base + x term) — the routine
    leaves them and the caller sees them (pitfall: flags are part of the
    contract, not just the address)."""
    ram = cpu.mem.ram
    x, y = cpu.s.x, cpu.s.y
    ram[0x4B1C] = x
    ram[0x4B1D] = y
    row_table = ram[BITMAP_ROW_TABLE:BITMAP_ROW_TABLE + 256]
    addr, row, col_pair = bitmap_byte_addr(x, y, row_table)
    ram[0x14] = addr & 0xFF
    ram[0x15] = (addr >> 8) & 0xFF
    # the two ADCs: low = rlo + (x<<1 & 0xF8); high = rhi + (x>>7) + carry_lo
    lo = (x << 1) & 0xF8
    hi = (x >> 7) & 1
    idx = (y >> 2) & 0xFE
    rlo, rhi = row_table[idx], row_table[idx + 1]
    carry_lo = 1 if (rlo + lo) > 0xFF else 0
    s1 = rhi + hi + carry_lo
    carry = 1 if s1 > 0xFF else 0
    overflow = 1 if (~(rhi ^ hi) & (rhi ^ s1) & 0x80) else 0
    return addr, row, col_pair, carry, overflow


@registry.replace(0x709F, "bitmap_pixel_addr")
def _bitmap_pixel_addr(cpu) -> None:
    addr, row, col_pair, carry, overflow = _bitmap_addr(cpu)
    byte = cpu.mem.rb((addr + row) & 0xFFFF)   # LDA ($14),Y
    cpu.s.x = col_pair
    cpu.s.y = row
    cpu.s.a = cpu._nz(byte)
    cpu.s.c = carry                            # C/V survive from the address ADC
    cpu.s.v = overflow
    _rts(cpu)


@registry.replace(0x70D9, "bitmap_plot")
def _bitmap_plot(cpu) -> None:
    # the original is `JSR $709F` then plot; reproduce the JSR's stack scratch
    # (the return address it pushes and $709F's RTS pops — pitfall #7) so the
    # freed stack bytes match the oracle byte-for-byte.
    ret = 0x70DB  # address of the JSR $709F instruction's last byte
    cpu.push((ret >> 8) & 0xFF)
    cpu.push(ret & 0xFF)
    cpu.pull()
    cpu.pull()
    addr, row, col_pair, carry, overflow = _bitmap_addr(cpu)
    at = (addr + row) & 0xFFFF
    mask = cpu.mem.rb(PIXEL_MASK_TABLE + col_pair)
    plotted = plot_pixel(cpu.mem.rb(at), mask)   # ORA $75D1,X
    cpu.mem.wb(at, plotted)                       # STA ($14),Y
    cpu.s.x = col_pair
    cpu.s.y = row
    cpu.s.a = cpu._nz(plotted)
    cpu.s.c = carry
    cpu.s.v = overflow
    _rts(cpu)


@registry.replace(0x697F, "bitmap_test")
def _bitmap_test(cpu) -> None:
    ram = cpu.mem.ram
    ram[0x46] = ram[0x46] | 0x80                 # LDA $46 / ORA #$80 / STA $46
    ptr = ram[0x45] | (ram[0x46] << 8)
    byte = cpu.mem.rb((ptr + cpu.s.y) & 0xFFFF)  # LDA ($45),Y
    mask = cpu.mem.rb(PIXEL_MASK_TABLE + cpu.s.x)
    cpu.s.a = cpu._nz(test_pixel(byte, mask))    # AND $75D1,X
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
