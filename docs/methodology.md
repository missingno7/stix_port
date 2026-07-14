# C64_RE source-port methodology

`c64_re` is the reusable C64 oracle layer.  It should run original C64
PRG programs from their disk images, expose deterministic snapshots/traces,
and provide enough device/KERNAL behaviour for the target game to reach
useful runtime states.

Target-specific knowledge belongs outside `c64_re`, in a per-game adapter
package that you create (`stix/` in this repo is the live example; the DOS
lineage's `examples/adapter_skeleton/` shows the same shape).

This document is the **naming / altitude discipline** that keeps recovery honest.
For the full porting *process* — proof spine, determinism trap, phased roadmap,
and the per-slice lifting loop — see the DOS charter
(`template_dos_port/docs/ai_porting_charter.md`), which is platform-neutral.

## The one rule

```text
Do not write a source port first and hope it matches.
Exhaust truth from the original first, then let the source port crystallize from that evidence.
```

The original program is the oracle. A clean native routine is a *hypothesis*
until it is diffed against the original ASM. Never infer behaviour from what
"probably" happens in other C64 games — the only oracle is this program and
its observed state transitions.

## Evidence ladder

1. Run original code in the VM.
2. Save snapshots at stable boundaries (`c64_re.snapshot` —
   `write_snapshot`/`load_snapshot`, `.c64snap` files; resume is bit-identical).
3. Identify inputs, outputs, memory writes, registers, flags, and chip/KERNAL
   side effects (VIC, SID, CIA, zero page, IEC).
4. Add a narrow replacement only after the original behaviour is understood.
5. Keep the original VM path as a regression oracle.

## Status ladder

Every recovered module carries an explicit confidence status. A name may only
climb this ladder on evidence, never on appearance. This is the same ladder
the islands module enforces on `@oracle_link` metadata (`c64_re.islands` —
its `STATUSES` ladder; the ladder applies from day one regardless, via the
symbol ledger):

```text
GUESS        hypothesised from a reference/heuristic, not yet checked vs ASM
OBSERVED     behaviour watched in the running ASM, not yet reimplemented
RECOVERED    reimplemented as clean source, not yet diffed vs ASM
ASM_MATCHED  output diffed against ASM on captured cases
VERIFIED     byte-exact vs ASM under in-VM lockstep over real runs
CANONICAL    verified and adopted as the source of truth (ASM retired for it)
```

A semantic name must be reversible back to evidence:

```text
semantic name -> runtime slot/fields -> verified lifted routine -> original ASM trace/snapshot
```

If that chain does not exist, use a candidate name plus evidence and confidence,
not a definitive label.

## Crystallization pyramid

Recovery starts from very low-level facts and lets higher-level meaning *emerge*.
Early hooks do not need to know whether a slot is a player, projectile, or enemy.
They only need to prove what the original code did at that boundary.

```text
8. Modern / enhanced port layer
7. Semantic game model layer
6. Gameplay archetype layer
5. Game systems layer
4. Runtime object/data model layer
3. Verified lifted routine layer
2. ASM-compatible hook/runtime layer
1. Original binary oracle layer
```

- **Layer 1 — oracle.** The disk image, original PRG(s), interpreted ASM,
  snapshots, traces, frame/SID/CIA captures, sector-level state. Answers "what
  really happened?".
- **Layer 2 — ASM-compatible hooks.** Exact PC (`$XXXX`) wrappers that still
  think in A/X/Y, flags, zero-page bytes, stack shape, vector slots,
  continuation PCs.
- **Layer 3 — verified lifted routines.** Source-level reimplementations of
  bounded routines that passed ASM-oracle comparison. A technical name tied to
  an address (`decrunch_$0801`) is correct here; correctness before meaning.
- **Layer 4 — runtime data model.** Stable structures emerge: slots, fields,
  pointer tables, sprite records, char/tile probes, buffers. An object may
  still be just "a record with coordinates, a sprite pointer, and a behaviour
  id".
- **Layer 5 — game systems.** Repeated routines form systems: loading, screen
  building, renderer, input, IRQ/timer, sound driver, object update,
  collision, state.
- **Layer 6 — archetypes.** Only now name player/enemy/projectile/pickup/boss,
  backed by observed ids, field usage, sprites, collision behaviour, call sites.
- **Layer 7 — semantic model.** Levels, scoring, transitions — the game's actual
  rules.
- **Layer 8 — enhancements.** Optional non-vanilla improvements that depend on
  the semantic model rather than replacing oracle work.

Climb by crystallization, not by guessing. A higher-level name is *earned* when
several verified lower-level facts point to the same concept.

### Naming altitude — concrete

```text
ObjectSlot  is a fact from memory.
Enemy       is an interpretation.
```

Bad shape (three layers fused, name unearned):

```python
def run_enemy_ai_from_cpu_memory_and_draw_sprite(cpu): ...
```

Better shape (each function at one altitude):

```python
def run_object_behavior_$4537(cpu): ...            # layer 2/3, address-named
def decode_object_slot(memory, base) -> Slot: ...  # layer 4, factual
def classify_object(slot, evidence) -> Candidate:  # layer 6, candidate+evidence
```

## Hook lifecycle

Use the same loop for every candidate routine:

```text
observe -> classify -> choose boundary -> build ASM oracle -> implement hook -> verify -> document
```

1. **Observe.** Gather evidence first: coverage/hotspots, executed-address
   traces, snapshots at/before the target, verifier divergence, fail-fast
   dumps (a JAM-filled KERNAL trap firing IS evidence). Do not pick a hook
   just because the address is hot — determine its role.
2. **Classify.** Decruncher/loader, screen or charset builder, renderer
   primitive, coordinate helper, input/menu wait, IRQ/timer/sound path,
   object behaviour, collision tail, startup table builder, or transient
   bootstrap/relocation code. If unclear, keep it a candidate and gather more
   evidence.
3. **Choose a boundary.** The smallest coherent unit that can be verified: a
   leaf loop with deterministic I/O, a routine with a clean `RTS`/`RTI`, an
   inner loop with a clear continuation PC, or a parent that only composes
   already verified children. Avoid broad parents that hide unverified
   behaviour. Beware IRQ-chained code: a boundary inside a raster-IRQ stage
   must respect the chain's stage clock.
4. **Build an oracle.** Run the interpreted original ASM from the same entry
   state and record every observable effect the boundary touches — including
   zero-page and chip-register writes.
5. **Implement the hook** as a **thin VM adapter over a pure recovered rule**:
   the adapter reads/writes VM memory and registers and preserves exact return
   mechanics; the rule is side-effect-free, unit-testable game logic that knows
   nothing about the 6510/zero page/`c64_re`.
6. **Verify** against the ASM oracle (registers + flags + full memory + chip
   state) with the differential verifier — `c64_re/verification.py`,
   `install_live_verifier` — and against the frame oracle for visual paths
   *(`c64_re/frame_verify.py`, `run_frame_verifier`; a hook proven
   only per-call, not per-frame, is ASM_MATCHED for its body, no more)*. A
   hook that passes only because a nested hook hides original behaviour is
   not proven.
7. **Document** the finding, update the symbol ledger and status doc, and add a
   test that makes the finding executable.

Never add a hook because it looks right. Every hook needs oracle evidence.

## Bootstrap is extraction, not target gameplay

Crunchers, crack intros, trainer menus, and self-relocating loaders are not the
source port. They are the oracle's way of preparing itself. (Stix's cracked
single-PRG runs its decruncher out of the stack page before the game exists in
memory — that code is bootstrap, not Stix.)

```text
original disk -> faithful bootstrap/extraction -> stable initialized snapshot -> clean source-port runtime
```

They may be accelerated in `c64_re` when the algorithm is target-neutral, but
the clean source port must not grow a permanent dependency on the decruncher.
Run the bootstrap once, snapshot past it (`write_snapshot` to a `.c64snap`),
and lift from the decrunched image.

## Fail-fast over guessed fallback

Fail-fast paths turn unknown behaviour into a precise snapshot + state dump.
This is why the shim KERNAL is JAM-filled: an unimplemented service halts with
the exact address instead of guessing. Do not replace fail-fast paths with
guessed fallbacks merely to keep the game running. When one triggers: treat
the dump as a new oracle candidate, reproduce it, diff original ASM against
the current lift, add the smallest missing branch, and keep the failure
message specific if the branch stays unknown.

## Duplication control

The long-term risk is bloat: a new hook that reimplements an existing tail with
slightly different behaviour. Before implementing one, search for the same
address suffix in function names, the same continuation PC, the same zero-page
or field offsets, or the same helper in the island module. Prefer shared
helpers named after the original address (`decode_$4CC0`, `scan_$4537`) so it
is obvious when two hooks want the same tail.

## Short rules

```text
1. Fidelity first, readability second, meaning third.
2. No higher abstraction without evidence from the layer below.
3. Refactor must not change behaviour.
4. Fix must not introduce a semantic model.
5. Hooks are minimal boundary adapters, not where logic lives.
6. Factual structure before interpreted name; candidate before definitive.
7. Every semantic name needs an evidence trace.
8. Lower layers must not import higher layers.
9. The original program stays the oracle until a subsystem is VERIFIED.
```
