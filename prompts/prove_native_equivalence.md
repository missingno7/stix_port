# Task: prove the VM-less native core equals the oracle (the flip's exit gate)

Requires: `c64_re.tick_demo` (`TickDemo`, `record_ticks`/`verify_ticks`,
`masked_digest`, `replay_to`; binary `.tick` files).

The endgame proof: every recorded demo replays on the native core tick for
tick, byte-identical to the VM under the gameplay ownership mask. The engine
is the `c64_re` tick-demo layer; this task is building its adapter and
running the corpus through it.

Preconditions: a native tick function exists; the forward oracle's gameplay/
render ownership boundary is defined; the demo corpus covers death, respawn,
level-end, and game-over (pitfall #22 — a happy-path corpus proves little).

1. **Build the tick-demo adapter**:
   - the seams: main-loop top (seed), the input CONSUMPTION points (observe;
     capture where the tick reads `$DC00/$DC01`, not where the frame starts —
     a raster/CIA IRQ in between falsifies the recording), the end-of-tick
     commit site;
   - the digest: `masked_digest` over the gameplay-owned state —
     the SAME exclusion mask the forward oracle byte-compare uses, one
     definition, imported not copied;
   - sidebands for state the native core cannot reproduce (cycle-count/
     CIA-timer/raster-derived values the gameplay only *reads* —
     record-and-inject). Each sideband gets a one-line justification in the
     symbol ledger.
2. **Record** a tick timeline for each corpus demo, driving the VM with the
   demo's own replay — in the SAME hook mode the demo was recorded in (the
   instruction clock is mode-dependent; a mode mismatch desyncs the drive and
   truncates the recording — check `TickDemo.load(path).n_ticks` against the
   demo's length).
3. **Verify**: seed the native state from the recording, `verify_ticks`.
   A terminal outcome (level-end / game-over / game-complete)
   legitimately ends that recording's compare; note the tick count it proved.
4. **On divergence**: it is a real finding, never noise. First carve the
   repro so every iteration is instant: replay to tick i, then re-anchor the
   demo's suffix on the captured state — the divergence reproduces at the
   suffix's own tick 0 instead of after i ticks. Then diff the digested
   state against the recording and treat it like any hook divergence (two
   focused attempts, then revert + blocker). Common causes: a capture point
   at the wrong consumption site, a missing sideband, render state leaking
   into the digest on ONE side only.
5. **Report the corpus result** in `run_status.md` and the demo manifest:
   per demo — ticks proven, terminal outcome, or the open divergence.

Hard rules: never widen the digest exclusions to make a tick pass (that is
weakening an oracle); a sideband is for genuinely non-reproducible state, not
for state the native tick computes wrongly; zero recorded ticks or a
truncated recording is a seams/mode bug, not a pass. Finish with the REPORT
block; corpus-wide green here is the evidence the flip's exit condition asks
for.
