# Pitfalls — the mistakes the source ports actually made

Every entry below is a real mistake from the DOS-lineage ports (Overkill or
Prehistorik 2, built on `dos_re` — the framework `c64_re` is the sibling of),
with the consequence it caused and the rule that fixed it. These are not
hypothetical warnings; each one cost hours or days. The hardware faces are
translated to their C64 equivalents where they apply; the lessons transfer
whole. Read this before your first hook, and reread the relevant section
whenever a verifier starts disagreeing with you.

Format: **Mistake → Consequence → Rule.** (DOS lineage: OK = Overkill,
P2 = Prehistorik 2.)

## Naming and abstraction

**1. Naming by guess.** [DOS lineage: OK] Hooks were named by assumed gameplay
semantics (`step_death_*` for what turned out to be a scripted boss-event
subsystem, not player death). → The false names reinforced a wrong mental
model for weeks and required a full evidence-trace rename. → *Keep
address-level or structural names until multiple independent evidence paths
agree: `logic_id` before `enemy_type`, `ObjectSlot` before `Enemy`. A kept
address name (`scan_$4537`) is cheaper than an encoded false abstraction.*
(See the status ladder in [`methodology.md`](methodology.md).)

**2. Width-aliased fields treated as one field.** [DOS lineage: P2] The same
bytes read at different widths by the ASM (a velocity word vs an anim-mirror
byte). → Bugs where a "width argument" was threaded through call sites and got
confused. → *A different width is a different semantic: on the 6502 this is
the lo/hi byte pair read sometimes as a 16-bit value and sometimes as a lone
byte (a position hi-byte doubling as a screen-column index). Give each width
its own named descriptor (`facing` vs `facing_lo`), never a width parameter at
the call site.* (dos_re grew `state_view` for this; the c64_re equivalent is
`c64_re.state_view` — `StructView`/`StructArray` with `U8`/`U16`/`S8`/`S16`
field descriptors, and `WidthContractBackend` to enforce declared widths; the
symbol ledger still carries the width note.)

## Hooks and structure

**3. Logic accumulating in hooks.** [DOS lineage: OK] Hooks were added without
declared lifetimes or merge targets until the hook file reached 4106 lines *of
gameplay logic*. → The VM-shaped hook pile became the de facto architecture;
every later refactor had to first extract logic back out of glue. → *Every
hook declares a role and a merge target (`@oracle_link` in
`c64_re.islands`); hooks stay registration + adapter only. "A hook without a lifetime is
suspicious; a hook without a merge target is suspicious." Falling glue-hook
count IS progress.*

**4. The "checker" duplicate.** [DOS lineage: OK] A hook kept a full
ASM-shaped replay as the real implementation and called the pure recovered
function only to assert agreement. → Two copies of one behaviour, drifting on
the next change, with the wrong one able to win silently. → *One recovered
leaf, many adapters. The adapter reads state → calls the leaf → writes back;
the parallel replay is deleted in the same commit that grounds the leaf.*

**5. Parent hooks hiding children.** [DOS lineage: both] A lifted parent
called a child hook's Python function directly, making the child a shared
black box inside the parent's verify transaction. → Hook verification passed
while the child was wrong. → *Route child boundaries through
`call_installed_hook_like_jsr` / the jump-boundary helper in `c64_re.hooks` —
it routes the child through the verifier, so the child keeps its own proof;
the dedicated static audit tool (dos_re's `audit_hook_oracle.py`) is still
planned for c64_re — enforce the routing rule by review until it lands.*

## Verification

**6. Trusting per-hook oracles alone.** [DOS lineage: OK] A contact predicate
was never exercised by its hook's captured oracle (callers passed a stub), so
three different visible bugs all traced to one unverified branch. →
Divergences only surfaced in long demo replays, far from the cause. →
*Per-hook oracles are scaffolding; demo-replay equivalence is the real gate —
and only counts if the routine is actually exercised. For every hook: a
focused oracle, evidence it runs in a real demo, and zero demo-suite
divergence.*

**7. Narrowing the diff.** [DOS lineage: both] Restricting verification to
"the registers that matter" or a memory window. → Freed-stack scratch words,
flag shapes, and off-window writes hid there; bugs surfaced later as
unexplainable frame divergence. → *Full-memory + full-state diffs by default;
on the C64 the hiding places are zero-page scratch, the stack page ($0100 —
Stix's decruncher literally executes there), and the VIC/SID/CIA register
shadows games keep in RAM. Narrow only as a deliberate, temporary performance
lever. Never weaken an oracle or test to make a change pass.*

**8. Refactoring away "dead" flag writes.** [DOS lineage: OK] Flag-setting
helpers that *looked* dead were removed; one video-marker bit-test was
reversed in an "optimization". → Demo divergence; visibly corrupted menu
assets. The hook oracle passed because it never exercised the branch. → *The
boundary contract is law — and on the C64 a single bit in a RAM shadow of
$D015 or a color-RAM nybble is exactly this kind of "looks dead" write. Before
deleting a state write, prove it dead: instrument with a counter and
demo-replay; if the demo suite never reaches it (count = 0), the change is
UNVERIFIABLE — revert it, don't keep it.*

## State capture and rendering fidelity

**9. Ad-hoc mid-frame state reads.** [DOS lineage: P2] A live viewer read
renderer state whenever it liked, mid-frame. → 79% of the frame diverged
during fast camera moves: the mirror mixed the in-progress frame's state with
the completed frame's pixels. → *Capture visual/game state as one snapshot at
the frame boundary (after the $D018/$DD00 flip or the game's frame-counter
increment commits), and render THAT snapshot.*

**10. Boundary capture of transient state.** [DOS lineage: P2] Blink counters
and one-shot particles are mutated (or killed) *during* the draw pass, so the
frame-boundary capture read them post-mutation. → Particles vanished; blink
was one phase behind. → *State consumed by a pass is captured at that pass's
ENTRY; the raster/frame-counter boundary is right only for state that survives
the frame. In IRQ-chained renderers, "the pass" may be one stage of the raster
chain, not the whole frame.*

**11. Rebuilding history-dependent buffers from scratch.** [DOS lineage: P2]
The menu/map pages are stateful (an init fill + per-frame self-copy +
per-column updates); a stateless rebuild "from the source data" was attempted.
→ ~11% pixel match — worse than random guessing among plausible models. → *If
a buffer is history-dependent, either replay the real sequence from a known
init (the game is deterministic) or recover the exact invariant. Never guess a
stateless model for stateful screen/bitmap/color RAM.*

## Timing and determinism

**12. Skipping waits by poking flags.** [DOS lineage: OK] "Fast-forward" set
the timer flag directly to skip the timer wait. → The skipped ISR ticks lost
music/SFX and interrupt-chain state — hundreds of bytes of measurable
divergence. → *Fast-forward means delivering the REAL installed IRQ handler
(the game's raster/CIA IRQ, through the same $0314 or $FFFE path it installed)
at the same instruction boundaries the verifier uses, then letting the wait
exit naturally. No game state is faked; only the delivery point is synthetic.
Stix already taught the shim-KERNAL half of this: the default handler must ack
CIA1 by reading $DC0D, or the machine drowns in an IRQ storm.*

**13. Skipping across IRQ-due boundaries.** [DOS lineage: P2] A wait-loop skip
jumped past points where a timer tick was due. → The tick counter diverged and
demos forked. → *Only collapse provably-identical poll iterations BETWEEN pump
boundaries; re-emit every due IRQ (CIA underflow or raster line) at its
emulated-time point. The step budget is `cpu.step()` invocations, not
`instruction_count` — an IRQ entry is one step.*

**14. Conflating deterministic skip with live pacing.** [DOS lineage: P2] The
deterministic retrace skip was reused in the interactive viewer. → The game
ran faster than real time (the live clock is wall-clock, not instruction
count). → *Two different mechanisms: deterministic fast-forward (advance the
emulated timeline exactly, frame by PAL 50Hz frame) vs live wall-clock parking
(sleep until the real phase matches, keep servicing IRQs). Never swap them.*

## Self-modifying and runtime-patched code

**15. Hooking patched code blind.** [DOS lineage: OK] Some routines' live
bytes are rewritten at runtime (a cold display helper became a hot
object-steering routine after patching). → A hook written against the cold
bytes would have silently run the wrong recovery. → *On the 6502 this pitfall
is PROMOTED: self-modifying code is idiomatic — inline operand patching,
computed branch targets, cheap dispatch — and trainer cracks patch the game
body on top (Stix's trainer answers patch the decrunched body at $6213 et
al.). Every accepted live-byte body is named and signature-guarded
(`self_disable_if_patched` in `c64_re.hooks`); an unknown variant fails loud.
The end state is static: observed bytes → named variant → byte guard →
explicit Python. Never keep "Python-level self-modifying code".*

## Performance

**16. Optimizing the hot leaf.** [DOS lineage: OK] Per-address frequency
profiling pointed at small leaf hooks; effort went into micro-optimizing them.
→ The real cost was interpreted *outer driver loops* crossing the VM/hook
boundary thousands of times — invisible to leaf-frequency counts. → *Profile
control-flow patterns (backward edges, boundary crossings) before optimizing
anything — the hotspot-profiling tool is still planned for c64_re; count
executed PCs by hand until it lands. And never trade byte-exactness for speed:
a faster
wrong replacement is a regression.*

## Layering

**17. Pure layers quietly importing the VM.** [DOS lineage: OK] During
refactors, `cpu`/`mem` imports crept into the recovered-logic layers. → The
"portable" game logic became unmigratable to the native runtime. → *Automated
layer audits run with the test suite from day one: recovered/ never imports
c64_re/cpu/memory/hooks. The audit tools exist — `python c64_re/tools/lint.py`
(core stays stdlib-only; adapter-package rules) and
`python c64_re/tools/audit_layers.py` (pure layers never import the VM) — run
them with the suite from day one.*

**18. Two parallel state models.** [DOS lineage: P2] A semantic frame model
was built as a *parallel* representation next to the machine-level render
state, each maintained separately. → Two truths for palette/camera/HUD state
that drifted apart. → *One canonical capture; the semantic/enhanced model is
DERIVED from it, never maintained beside it.*

## Working style (agent sessions)

**19. Broad speculative changes.** [DOS lineage: OK] Autonomous sessions
occasionally attempted multi-subsystem refactors or "fixed" a divergence by
weakening the oracle. → Reverts, wasted effort, and near-miss silent
regressions. → *The smallest coherent unit per iteration; never commit red; a
blocked slice is fully reverted and logged as a blocker
(`docs/stix/blockers.md`), not worked around.*

**20. Stopping at the symptom.** [DOS lineage: OK] A long-open "player death
divergence" blocker was attacked at the death logic repeatedly. → No progress
until the actual cause — a missing contact predicate one layer *below* — was
recovered. → *When a divergence resists two focused trace attempts, log it and
move on; returning later with more of the lower layer recovered often
dissolves it.*

**21. Fluent semantic hallucination.** [DOS lineage: P2] An AI agent watched
bridge tiles bend under the player and confidently described the player
*eating something* — a coherent, plausible, completely false story. → Any name
or model built on that reading would have encoded fiction into the port. →
*Narrative sense is a hypothesis generator, never a source. Semantics are
earned per the status ladder (multiple independent evidence paths), and the
oracle is the only judge. This is WHY the framework constrains AI rather than
trusting it.*

**22. A demo corpus that flatters the code.** [DOS lineage: both] Early demo
suites exercised the happy path (short runs, few transitions). → Divergences
in death/respawn, level-end, game-over, and rare spawns survived long past the
point they "should" have been caught; cold-start testing later exposed paths
no bounded demo reached. → *Corpus coverage is a measured artifact: track
which levels, transitions, behaviours, and RNG paths the demos exercise, and
treat the blind spots as open risks in every status report. Record death,
game-over, and full-playthrough demos early — they are the proof spine's
spine.*

**23. Presentation quietly mutating the simulation.** [DOS lineage: P2] The
tempting widescreen shortcut — advancing the object producer/spawner so
entities exist in the margins — changes gameplay state; camera/render helpers
"just poking" one state byte have the same shape. → The enhanced build
silently forks from the verified game; demos recorded on one desync on the
other. → *Enhancements read state and write none, enforced by a parity gate
(enhanced-at-neutral ≡ faithful, pixel- and state-exact). Anything that needs
to write is not an enhancement.* (Full doctrine: the DOS lineage's
`enhancements.md`.)

**24. Building presentation backends during recovery ("cyborgization").**
[DOS lineage: P2] Early in the project, faithful/enhanced *viewer* backends
were grown alongside hook-based recovery, before the native game was complete.
→ It required a whole policing apparatus: transitional "faithful-only, not yet
grounded" states to track, one-implementation audits to stop parallel truths,
and presentation effort spent while gameplay was still unrecovered. It worked,
but the project's own retrospective verdict is: not recommended. → *The
enhanced layer is the ENDGAME — after the faithful VM-less game is complete
and stable. The only sanctioned exception class is audio-style disruptions:
small, separable fixes for something that actively impedes the recovery
workflow itself.*

## Anticipated C64-specific pitfalls (not yet burned by them — candidates, not scripture)

Everything above is paid-for experience. The entries below are *predictions*
from the C64's architecture and from what Stix's bring-up already brushed
against. Same shape, lower confidence: treat each as a watchpoint, and promote
it to the numbered list only when a real port pays for it.

**A. Badline/cycle-stealing drift vs the line-granular VIC model.** Our VIC-II
model is line-granular: no badline DMA stalls, no sprite cycle stealing. →
Raster-counting code (waits on $D012, cycle-timed effects) lands on slightly
different lines than real hardware — deterministically, but differently; a
port "verified" against our timing could mismatch hardware captures. → *Treat
the VM's timing as the oracle's timing and say so in the ledger. Don't chase
pixel-perfect raster timing before it demonstrably matters to gameplay; when
it does matter, upgrade the model, don't fudge the game.* (Stix so far: no
observed effect — run_status.md tracks it.)

**B. KERNAL shim divergence — ROM *data* is part of the contract.** Games
read the ROMs as data, not just as services: Stix block-copies the $FD30
vector-table image and copies the character generator ROM to $0800 at init. →
A shim ROM that only honours *call* contracts silently feeds wrong bytes to
table copies and font blits; the failure surfaces far away, as garbled glyphs
or wild vectors. → *Shim-ROM data reads are observable contract. When a game
touches ROM as data, capture what it reads, make the shim serve the authentic
image for that range, and log the range in the ledger. Expect more of these.*

**C. IRQ chains and the stage clock.** C64 renderers routinely re-arm $D012
mid-frame so one IRQ handler becomes a multi-stage chain (top border → screen
split → music, each stage setting the next raster line). → A hook boundary
chosen "per routine" can straddle two stages of the chain; verifying it
against a whole-frame oracle mixes stage states and diverges confusingly. →
*Identify the chain first (trace the $D012/$D019 writes), name the stages, and
choose hook boundaries that respect the chain's stage clock — one stage, one
boundary, its entry state captured at that stage's IRQ entry (pitfall #10's
logic, per stage).*

**D. VIC bank/pointer confusion.** $D018 screen/charset pointers are relative
to the 16KB bank selected by $DD00, and sprite pointers live at the end of the
*current* screen — three indirections that all move together. → Reading
registers and guessing "the screen is at $0400" renders the wrong memory and
every conclusion built on that frame is fiction. → *Never trust a register
read alone; verify against rendered frames (the pngout evidence chain) before
recording any screen/charset/sprite address in the ledger.*

**E. Zero-page aliasing.** Zero page is the 6502's register file; games pack
it and reuse it — two routines sharing a zp byte with different meanings
per phase, or a byte read as half of a pointer in one place and as a counter
in another. → A recovered rule that names the byte once encodes one phase's
meaning and corrupts the other's; this is pitfall #2 wearing its C64 face. →
*One zp address may need several named descriptors, scoped by routine/phase,
each with its own evidence. The symbol ledger records the address, the width,
AND the phase; a second meaning for a known byte is a finding, not a
contradiction.*

**F. Fastloaders and IEC bit-banging.** Many originals replace the KERNAL
loader with a fastloader that bit-bangs the serial bus (or a crack's custom
loader reading raw sectors). → The shim KERNAL's LOAD trap never fires; the
game hammers CIA2 port lines expecting a 1541 on the other end, and any
"helpful" silent skip would boot a corrupt image. → *Fail loud at the IEC
traps, always. A fastloader is bootstrap (methodology: extraction, not
gameplay): recover it as game-specific loader HLE that serves the same bytes
the real drive would, verified against the D64 — never a silent skip, never a
generic guess.* (Stix dodges this: single-PRG KERNAL load.)
