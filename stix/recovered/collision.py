"""Player-vs-hazard collision — recovered from $73EC.

Evidence: $73EC derives the player's grid position from sprite 0
(``player_x = (sprite0_x9 >> 1) + 5``, ``player_y = sprite0_y + 8``) and
tests it against the three hazard sprites (6, 7, 3).  The caller
(``JSR $73EC / BNE``) reads the Z flag: **Z=1 means a hazard occupies the
player's cell** (a hit).  When the collision-disable countdown ($4B4A) is
non-zero the routine decrements it and reports no hit (invulnerability
frames).

This is the semantic (native) form: it computes the same player position and
collision result the ASM does.  The routine's exact CPU exit flags are not
reproduced here (that is the lifted artifact's job for the hybrid runtime);
the contract this honours is the observable one — player position and the
hit boolean — verified against the demo in tests/test_recovered_stix.py.
"""
from __future__ import annotations

from collections.abc import Sequence

from ..islands import oracle_link


@oracle_link(
    boundary="$73EC",
    contract="sprite 0 (x9,y) -> player grid pos ((x9>>1)+5, y+8)",
    status="RECOVERED",
)
def player_grid_pos(sprite0_x9: int, sprite0_y: int) -> tuple[int, int]:
    """The player's grid cell from sprite 0's position."""
    return ((sprite0_x9 >> 1) + 5) & 0xFF, (sprite0_y + 8) & 0xFF


@oracle_link(
    boundary="$73EC",
    contract="player cell vs hazard sprites -> hit (any hazard shares the cell)",
    status="RECOVERED",
)
def hazard_collision(player_x: int, player_y: int,
                     hazards: Sequence[tuple[int, int]]) -> bool:
    """True when any hazard sprite occupies the player's grid cell.

    ``hazards`` is the (x9, y) of each hazard sprite in check order (6, 7, 3);
    a hazard collides when ``(x9 >> 1) == player_x`` and ``y == player_y``.
    """
    for hx, hy in hazards:
        if ((hx >> 1) & 0xFF) == player_x and (hy & 0xFF) == player_y:
            return True
    return False
