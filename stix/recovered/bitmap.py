"""Hires/multicolor bitmap pixel primitives — recovered from $709F/$70D9/$697F.

Evidence: the game draws into a bitmap addressed through zero-page pointer
$14/$15.  $709F converts a pixel (x,y) into the byte address of the cell
plus the row-within-cell (y&7) and the pixel-column selector (x&3), using a
per-cell-row base-address table ($6F1B).  $70D9 sets a pixel (OR a mask from
the $75D1 table into the byte); $697F tests a pixel (AND the mask).

The two lookup tables ($6F1B row bases, $75D1 column masks) are game data —
passed in here as arguments so this logic stays pure and testable; recovering
the tables' *contents* is a separate (data) task.
"""
from __future__ import annotations

from collections.abc import Sequence

from ..islands import oracle_link


@oracle_link(
    boundary="$709F",
    contract="pixel (x,y) -> (byte_addr, row_in_cell=y&7, col_pair=x&3) via row-base table",
    status="RECOVERED",
)
def bitmap_byte_addr(x: int, y: int, row_base_table: Sequence[int]) -> tuple[int, int, int]:
    """Byte address in the bitmap for pixel (x, y), plus the row-in-cell and
    the pixel-column selector.

    ``row_base_table`` is the $6F1B table: a flat little-endian array of
    16-bit cell-row base addresses, indexed by ``(y >> 2) & 0xFE``.
    """
    x_contrib = ((x << 1) & 0xF8) | ((x >> 7 & 1) << 8)   # $14/$15 x term
    idx = (y >> 2) & 0xFE
    base = row_base_table[idx] | (row_base_table[idx + 1] << 8)
    addr = (base + x_contrib) & 0xFFFF
    return addr, y & 7, x & 3


@oracle_link(
    boundary="$70D9",
    contract="set a bitmap pixel: byte | column_mask",
    status="RECOVERED",
)
def plot_pixel(byte: int, column_mask: int) -> int:
    """Return the bitmap byte with the pixel at ``column_mask`` set."""
    return (byte | column_mask) & 0xFF


@oracle_link(
    boundary="$697F",
    contract="test a bitmap pixel: byte & column_mask (nonzero = set)",
    status="RECOVERED",
)
def test_pixel(byte: int, column_mask: int) -> int:
    """Return ``byte & column_mask`` — nonzero when the pixel is set."""
    return byte & column_mask
