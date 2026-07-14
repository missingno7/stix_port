"""The VM-less native runtime — the shipped ``play_native`` (STAGE 4+).

When enough of ``recovered/`` is proven, this package composes those SAME
pure functions with the VM gone: native game state, the boot constants, and
the fixed-step tick driver.  One implementation, many adapters: the native
loop calls the exact functions the hooks call, never a second copy.

**Design constraints, discovered from the oracle (session 8):**

- Stix runs its whole game step inside a CIA-timer IRQ (handler ``$66B8``);
  the tick body is ``$66C5``..``$66F5`` (see ``stix.tick``).  The native
  tick reproduces that body's call sequence: input decode → hazard AI +
  moves → collision, three times.  The full-game equivalence target is
  ``artifacts/ticks/run1.tickdemo`` (4882 ticks, every digest distinct).

- **Gameplay state spans RAM *and* VIC.**  The ``$4B00`` page holds most of
  it, but the sprite positions the tick moves and collides against are
  written *directly* to VIC registers ``$D000``-``$D010`` (movers
  ``$72CC``/``$72EA``/``$72F3``) with no RAM shadow.  So a native state
  carries BOTH a RAM image and the VIC sprite-register array, seeded from a
  full-machine snapshot — the RAM-only tick-demo seed alone is insufficient
  (that seed is the input+digest timeline; the native *state* seed is a
  ``c64_re.snapshot``).

- **RNG.**  The hazard AI reads SID ``$D41B`` (OSC3 noise) for randomness.
  The LFSR is deterministic (``c64_re.sid``) but lives outside RAM, so the
  native state carries the LFSR and advances it identically, or takes the
  per-tick values as tick-demo sidebands.  TBD when the AI is recovered.

This module raises ``HybridGap`` for anything not yet recovered — a native
tick that silently faked a move would pass a weakened digest and hide the
gap.  ``scripts/tickdemo.py verify`` reports the first diverging tick, which
is the recovery worklist.

Not runnable yet: the moves (``$7183``/``$6AAC``/``$6C41`` and the BIT-skip
AI children) are still ORACLE_PASSING lifted artifacts, not recovered pure
rules.  ``make_state``/``inject``/``tick`` land here as each is recovered.
"""
from __future__ import annotations

# from .tick import make_state, inject, tick  # noqa: F401  (once recovered)
