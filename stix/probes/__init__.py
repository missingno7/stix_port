"""Throwaway observation / diagnostic scripts (not part of the shipped port).

Probes read the oracle to gather evidence — disassembly, memory-access
traces, address censuses.  They may import the VM freely (they are not the
pure layer).  Keep them small and disposable; promote nothing from here into
``recovered/`` without re-deriving it cleanly.
"""
