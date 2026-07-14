"""Per-hook continuation metadata for the differential verifier.

Every recovered routine in ``hooks.py`` so far is a plain JSR-entered
subroutine, so the verifier's default strict mode (run the original to the
return address on the stack) needs no metadata — ``HOOK_STOPS`` is empty.
Add a :class:`c64_re.verification.HookStop` here only for a boundary that is
NOT a simple subroutine (JMP-entered, fall-through, or a shared tail).
"""
from __future__ import annotations

from c64_re.verification import HookStop

HOOK_STOPS: dict[int, HookStop] = {}
