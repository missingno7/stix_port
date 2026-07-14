"""stix — the game adapter package for the Stix recovery port.

Game-specific knowledge lives HERE, never in c64_re (the framework stays
game-agnostic; that boundary is the method's one hard rule).  The package
follows the proven pre2_port layer layout:

    runtime.py       boot / navigation / hook install
    hooks.py         @registry.replace thin VM adapters over recovered rules
    verification.py  per-hook continuation metadata (HookStop) for the verifier
    input_waits.py   the input-poll loops the game parks in (shared by drivers)
    bridge/          typed views over VM memory — the ONE place offsets live
    recovered/       pure recovered game logic (never imports the VM); @oracle_link
    native/          [grows later] the VM-less runtime — the shipped play_native
    probes/          throwaway observation / diagnostic scripts

The recovery evidence (memory map, routine semantics) is in
docs/stix/symbol_ledger.md; the lift census / grind results in
artifacts/grind/.  This module re-exports the runtime entry points so
`import stix; stix.boot(...)` keeps working.
"""
from __future__ import annotations

from .runtime import (  # noqa: F401
    DISK_FILE,
    TITLE_LOOP,
    boot,
    install_recovered_hooks,
    start_game,
)

__all__ = ["DISK_FILE", "TITLE_LOOP", "boot", "start_game", "install_recovered_hooks"]
