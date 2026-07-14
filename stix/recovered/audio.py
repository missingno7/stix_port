"""SID sound — recovered from $6A0B.

Evidence: $6A0B takes a game byte ($4B28), splits it into a high nibble and
a bit-reversed low nibble, and writes them to SID voice-1 frequency HI/LO
($D403/$D402).  The high nibble becomes FREQ HI; the bit-reversed low nibble
becomes FREQ LO (and is stashed in $4B18).  This is the low-level "set voice
1 pitch from a game value" primitive; the value's musical meaning is not yet
established (kept as an address-level fact).
"""
from __future__ import annotations

from ..islands import oracle_link


@oracle_link(
    boundary="$6A0B",
    contract="game freq byte -> SID voice-1 (FREQ LO = bit-reversed low nibble, FREQ HI = high nibble)",
    status="RECOVERED",
)
def voice1_frequency(value: int) -> tuple[int, int]:
    """Return ``(freq_lo, freq_hi)`` for SID voice 1 from a game byte.

    ``freq_hi`` is the value's high nibble; ``freq_lo`` is its low nibble
    with the four bits reversed (bit0->3, bit1->2, bit2->1, bit3->0), exactly
    as $6A0B's ``LSR``/``ROL`` loop builds it.
    """
    value &= 0xFF
    lo = ((value & 1) << 3) | ((value >> 1 & 1) << 2) | ((value >> 2 & 1) << 1) | (value >> 3 & 1)
    hi = value >> 4
    return lo, hi
