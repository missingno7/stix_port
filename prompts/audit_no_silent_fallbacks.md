# Task: audit for silent fallbacks

Silent fallback creates fake confidence — a run that "works" while quietly
guessing. Sweep the adapter (and any framework code touched recently) for the
danger patterns and make each one loud, modeled, or explicitly documented.

Search for:
1. **Quiet ASM fallback**: any path where native/hybrid code, on missing
   recovery, falls back to the original instead of raising a `HybridGap`
   (`from c64_re.gaps import HybridGap`).
2. **Default-instead-of-model**: an unsupported VIC mode treated as another
   mode; an unknown KERNAL trap returning "success"; an unmodeled I/O
   register read used for logic. (The core's known limits are documented in
   `c64_re/AGENTS.md` "Known model limits"; anything new needs the same
   honesty.) The JAM-filled shim ROM and fail-loud unmapped I/O are the
   enforcement mechanism — check that nothing recent papered over one.
3. **Tolerated mismatches**: a verifier/checkpoint that logs a diff without
   failing; a comparison narrowed to "the bytes that matter"; a test relaxed
   to pass (grep for recently-changed tolerances, skips, and `except` blocks
   swallowing verifier exceptions).
4. **Signature-less patched-code hooks**: hooks at addresses the game patches
   at runtime without the live-code signature guards in `c64_re/hooks.py` —
   crack intros and stack-page decrunchers (Stix's lives in `$0100`) make
   self-modifying code the C64 default, not the exception.
5. **Boundary drift**: a driver with its own frame/wait definition instead of
   the shared input-wait registry (Stix: the raw `$DC01` title poll).

For each finding, classify: *intentionally unsupported* (make it raise with
context) / *not yet modeled* (raise + ledger entry) / *modeled but
approximate* (document exactly where it diverges and what verifies it) /
*adapter responsibility* (move it there). Fix small ones inline; file blockers
for the rest. Every change re-runs the full gates.

Finish with the REPORT block, listing every location examined — an audit that
only reports its hits can't be re-checked.
