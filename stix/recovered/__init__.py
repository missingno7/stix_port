"""Pure recovered Stix logic. THE LAYERING RULE IS ABSOLUTE HERE.

Nothing in this package may import the VM (``c64_re.cpu`` / ``memory`` /
``machine`` / ``runtime``), touch a CPU/memory object, or know that a VM
exists — that is what makes the logic portable to the native (VM-less)
runtime unchanged (one leaf, many adapters).  Enforced mechanically:
``python c64_re/tools/audit_layers.py stix/recovered`` runs with the test
suite (pitfall #17 — VM imports creep in during refactors otherwise).

Only ``c64_re.islands`` (pure metadata) may be imported, for the
``@oracle_link`` tags the island manifest is generated from.

Names are earned from evidence (hardware register contracts, traced
reads/writes — see docs/stix/symbol_ledger.md), never invented; status
climbs GUESS → OBSERVED → RECOVERED → ASM_MATCHED → VERIFIED → CANONICAL
only on proof.  These functions are the clean form of routines that are
already ORACLE_PASSING lifted artifacts (byte-exact over the full demo).
"""
