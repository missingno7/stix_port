"""Sprite <-> playfield-grid conversion — recovered from $72A0.

Evidence: $72A0 reads a VIC sprite's 9-bit X (low byte $D00C+2n, MSB in
$D010) and Y ($D00D+2n), and converts them to the game's grid coordinates:
``grid_x = (sprite_x9 >> 1) - 0x0B`` and ``grid_y = sprite_y - 0x30``.  The
0x0B/0x30 offsets are the sprite-to-visible-origin correction; the >>1 maps
the 9-bit hi-res sprite X onto the (half-resolution) playfield X.
"""
from __future__ import annotations

from ..islands import oracle_link


@oracle_link(
    boundary="$72A0",
    contract="VIC sprite (x9,y) -> game grid (x,y): ((x9>>1)-0x0B, y-0x30)",
    status="RECOVERED",
)
def sprite_to_grid(sprite_x9: int, sprite_y: int) -> tuple[int, int]:
    """Convert a sprite's 9-bit X and 8-bit Y to game grid coordinates."""
    grid_x = ((sprite_x9 >> 1) - 0x0B) & 0xFF
    grid_y = (sprite_y - 0x30) & 0xFF
    return grid_x, grid_y
