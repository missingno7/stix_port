"""Typed views over VM memory: the ONE place Stix's raw offsets live.

The bridge quarantines the game's memory layout — ``c64_re.state_view``
descriptors mapping named fields (``player_grid_x``, ``joy_fire``) onto the
original byte layout of the $4B00 state page.  Hooks and the native runtime
read state through these views; ``recovered/`` receives plain values and
never sees an offset.

Rules (template §"Layering"):
- Layout knowledge only — no gameplay decisions here.
- A different read WIDTH is a different field descriptor, never a width
  parameter at the call site (pitfall #2).
"""
from .state_fields import GAME_STATE_BASE, GameState, state  # noqa: F401
