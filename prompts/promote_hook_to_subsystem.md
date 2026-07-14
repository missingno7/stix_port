# Task: promote hooks into a subsystem (coastline shortening)

Requires: `c64_re.islands` (`@oracle_link`, `collect_islands`) and
`c64_re.verification` — both exist.

Collapse a set of proven neighbouring islands into one larger native unit.

Preconditions — do not start unless all hold:
- every island involved is VERIFIED (not just RECOVERED), tagged, and demo-
  exercised;
- the original call graph *proves* they belong to one original
  routine/controller (traces, not aesthetics — the collapse rule);
- the glue between them is classified `glue` in the hook taxonomy.

1. **Map the target**: name the subsystem after the evidence
   (`frame renderer`, not `RenderingEngine2`). Its islands' `merge_target`
   fields should already point at it.
2. **Compose, don't rewrite**: the subsystem calls the SAME recovered leaf
   functions the hooks used (one leaf, many adapters — pitfall #4). Where a
   recovered island returned to ASM only to reach another recovered callee,
   call it directly.
3. **Keep children verifier-visible** where they remain hooked: route
   through the dispatcher's JSR-like call helper
   (`c64_re.hooks.call_installed_hook_like_jsr` — it routes the child through
   the verifier; lifted hooks already compose this way — `emit.py` routes JSR
   through `emulate_call`). The dedicated static hook-oracle audit tool is
   still planned — enforce the routing rule by review until it lands.
4. **Prove it standalone**: given state captured from a snapshot, the
   subsystem reproduces the oracle's output byte-exact *without stepping the
   VM* — as a committed test. Then demo-replay: zero new divergences with the
   collapsed chain live.
5. **Retire scaffolding in the same change**: remove the now-internal glue
   hooks, update the taxonomy and frontier manifest, regenerate the island
   manifest. Falling hook count is the point.

If the composed subsystem diverges where the individual islands passed, the
glue you collapsed had behaviour you didn't understand — revert, trace the
glue, recover it as its own island first. Finish with the REPORT block.
