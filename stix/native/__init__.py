"""The VM-less native runtime — grows later (STAGE 4+).

When enough of ``recovered/`` is proven, this package composes those SAME
pure functions with the VM gone: native game state (decoded from the $4B00
model in ``bridge/``), the boot constants, and the fixed-step frame driver —
the shipped ``play_native``.  One implementation, many adapters: the native
loop calls the exact functions the hooks call, never a second copy.

Empty until the recovered surface is broad enough to run a tick without
falling back to the oracle for gameplay-owned state.
"""
