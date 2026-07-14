# Task: recover one routine (the core loop)

One routine, one verification, per slice. Nothing else.

1. **Pick by evidence**: a profiler hotspot or a frame-verify divergence — not
   an address that "looks interesting". State why this routine, with numbers.
2. **Observe**: trace it in the VM from a snapshot fixture
   (`c64_re.snapshot` — `write_snapshot`/`load_snapshot`, or `capture()` for
   in-memory fixtures). Record: entry state, exit PC, stack effect,
   A/X/Y/P/SP written,
   memory touched, VIC/SID/CIA register side effects. Save the snapshot; it
   is the golden's seed.
3. **Classify + choose the boundary**: the smallest coherent unit with a
   clean continuation. Avoid broad parents that hide unverified children.
4. **Implement**: a pure recovered rule (VM-free, unit-testable, in
   `recovered/`) behind a thin `@registry.replace(pc, name)` hook
   (`c64_re/hooks.py`) with exact return mechanics (RTS/RTI, stack shape).
   Flag semantics must be 6502-exact (N/Z/C/V, decimal mode) — mirror
   `c64_re/cpu.py`, never re-derive. Tag the rule with
   `@oracle_link(boundary, contract, status="RECOVERED", merge_target=...)`
   (`c64_re.islands`).
5. **Verify**: strict JSR-return mode first, then add the
   `HookStop(continuations=(...))` metadata (`c64_re.verification`,
   `install_live_verifier`). Full-memory diff. Then confirm the routine
   actually fires in a demo replay with zero divergence — a hook no demo
   exercises is NOT verified (pitfall #6). Only now raise the status to
   ASM_MATCHED / VERIFIED accordingly.
6. **Document**: symbol ledger entry, island manifest regenerated
   (`python c64_re/tools/gen_island_manifest.py <packages> -o
   docs/recovered_islands.md`), run_status updated.

Hard rules: address-level names until evidence converges (pitfall #1); no
logic accumulating in the hook body (pitfall #3); if it diverges and resists
two focused trace attempts (`C64_RE_TRACE_HOOK=$XXXX`), revert
fully, log the blocker, and take the next target (pitfall #20). Finish with
the REPORT block.
