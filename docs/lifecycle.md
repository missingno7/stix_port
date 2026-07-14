# The life of a port — from original PRG to native source port

The other docs each cover one mechanism in depth. This one tells the whole
story in order, so you can see where each mechanism belongs. The detailed
phase-by-phase treatment with exit criteria is
[`ai_porting_charter.md`](ai_porting_charter.md) §7; this is the narrative map.

The geography of recovery, in one picture:

```text
  raw ASM ocean          →   first verified islands   →   archipelagos        →   continents           →   recovered mainland
  (the original binary,      (hooked routines, each       (islands merged         (native subsystems:      (the VM-less source
   interpreted, opaque)       byte-exact vs oracle)        into subsystems)        renderer, gameplay)      port; VM = oracle)
```

## Vocabulary used throughout the docs

- **Oracle** — the original C64 program running interpreted in the `c64_re`
  VM. The single source of truth for all behaviour.
- **Island** — one coherent recovered unit (a routine, then later a whole
  subsystem) with its own verification contract: pure recovered logic + a thin
  hook adapter + a verifier. Recovery grows island-by-island.
- **Golden** — a recorded oracle fixture turned into a test: the captured
  inputs/outputs/memory-effects of the original routine, which the recovered
  island must reproduce exactly, forever.
- **Coastline** — the total surface where recovered code still borders
  interpreted ASM (every hook boundary). Progress = the coastline moving
  *upward*: fewer, higher-level contact points, not more hooks.
- **Hybrid runtime** — the workbench: the VM running the original game with
  recovered islands hooked over it, live.
- **Native runtime** — the product: recovered source only, no VM, no PRG.

## Stage 0 — the original game runs in the VM

The project starts by getting the original program to boot and run inside the
VM: D64 directory parsing and the BASIC-stub `SYS` entry, the cruncher
bootstrap (run once, snapshot past it — `c64_re.snapshot`
`write_snapshot`/`load_snapshot`, `.c64snap` files), KERNAL services as HLE
traps over the clean-room shim ROM
(everything unimplemented is JAM-filled and fails loud), VIC-II output you can
decode into an image, keyboard/joystick delivery the game's own polling and
IRQ code sees through the CIA1 matrix, and deterministic input demos that
replay a session byte-for-byte (`c64_re.input_demo` — proven bit-identical on
a scripted Stix gameplay demo, `stix_port/tests/test_demo_stix.py`). At this
stage the original game
**is** the game: it boots, runs, accepts input, renders frames, and every run
is replayable evidence. (Charter §9.)

Stix has completed this stage: it boots from its cracked single-PRG D64, the
decruncher runs from the stack page for ~200 frames, the trainer menu reads
keys via KERNAL GETIN, the crack restores vectors by block-copying the ROM
table at $FD30 over $0314, gameplay runs on joystick port 1, and full-state
digest tests (`stix_port/tests/test_boot.py`) prove the whole run is
deterministic.

Nothing is recovered yet — but the microscope works: you can trace any
routine, snapshot any state, and replay any moment.

## Stage 1 — first islands: the hot, well-bounded leaf routines

The first recovered pieces are usually the obvious low-level hot paths: asset
decompression and decoders, character/bitmap plotting, sprite handling,
screen-matrix and color-RAM builders — expensive or cleanly isolated routines.
They are the right first targets for three reasons: their boundaries are easy
to verify (clear inputs/outputs, a clean RTS), replacing them makes the
interpreted VM dramatically faster, and each one makes the system more
observable (decoded assets and frames you can look at). (DOS lineage: both
`dos_re` source ports started exactly here.)

Each replacement goes through the same loop (one routine, one verification,
per slice): trace → snapshot fixture → thin hook over a pure rule → verify
against the interpreted original — registers, flags, full memory, and for
visual paths, frames. (Charter §4; the differential verifier is
`c64_re/verification.py` — `install_live_verifier` wraps every hook with a
full-state diff against the ASM oracle, live.)

**Start the island ledger on the first island.** Every recovered function
carries `@oracle_link(boundary, contract, status, merge_target)`
(`c64_re.islands`), and the manifest is *generated* from the code
(`python c64_re/tools/gen_island_manifest.py <packages> -o
docs/recovered_islands.md`, plus a drift test), never
hand-maintained. (DOS lineage: the Prehistorik 2 port was steered by this
ledger, ~100+ islands at the end.) The `merge_target` field is what keeps
Stage 3 honest — every island declares, from birth, which larger subsystem it
will dissolve into.

## Stage 2 — recovery moves inward: gameplay rules

With the workbench fast and observable, recovery moves into the game itself:
object update, collision, spawning, input decoding, menus, the level state
machine. Islands multiply — one decodes assets, another draws sprites, another
updates objects, another handles collisions. Each is still an isolated,
verified unit hooked at its original address; the VM still owns the loop and
the memory. (Charter Phase 1.)

## Stage 3 — islands connect into subsystems

A pile of low-level hooks is scaffolding, not the goal. As neighbouring
islands are proven, the glue between them (tails, helpers, per-row scan steps
— `glue` in the hook taxonomy, DOS lineage: `dos_re`'s
`hooks_and_verification.md`) collapses into single native chains, and verified
behaviour is lifted into higher-level representations: objects instead of
zero-page slot bytes, render states, level data, input state, SID command
streams, animation state, game rules. Higher-level names are *earned* from
evidence, never invented up front (DOS lineage: `dos_re`'s `methodology.md` —
the crystallization pyramid). Correctness during each collapse is protected by
the frame/state verifier, not by preserving historical hook boundaries.
(Charter Phases 2–4.)

Two working rules govern this stage (DOS lineage: both source ports):

- **Coastline shortening.** Where a recovered island returns to ASM but the
  callee is itself a verified recovered function whose contract covers the
  side effects, call it directly: grow the recovered↔recovered surface, shrink
  the ASM boundary. Collapse leaves into larger islands **only** with evidence
  from the real original call graph — never into a modern invented design.
- **One recovered leaf, many adapters.** Each recovered function is the
  *single* implementation; the hybrid replacement hook, the verify checkpoint,
  and (later) the native runtime are thin adapters over that one function —
  never a second copy. Duplicating logic between the hook and the native
  backend is how ports silently fork from their own proof.

The end-state shape of a subsystem is a **standalone, replaceable unit**: e.g.
a `render_frame(state)` that composes all recovered render leaves and, given a
state captured from a snapshot, reproduces that frame's VIC-visible memory
byte-exact (screen matrix, bitmap, color RAM, sprite data + VIC/SID register
state) *without stepping the VM*. Prove that with a committed test — it is the
demonstration that the subsystem is a clean, VM-independent, drop-in unit, and
the per-hook coastline for it collapses to one entry hook plus the state
bridge.

One trap to respect: some original state is **history-dependent** (a
double-buffered screen flipped via $D018, a self-modifying draw routine, a
self-copying buffer). A from-scratch rebuild of such state is wrong even if a
single frame matches — it needs the real stateful model, recovered like
everything else. Mark such pieces *blocked* rather than guessing.

## Stage 4 — continents: the game separates from the VM

When the recovered subsystems cover the frame loop, data decoding, and the
backends (video/audio/input/timing), the game can run **without** the VM: a
native source port that cold-boots from the original data plus recovered boot
constants — the post-decrunch initialized state extracted once into native
data, so the shipped game needs **no PRG and no snapshot** at runtime
(snapshots and demos are recovery *evidence*, never a runtime dependency). No
emulator, no interpreted instruction in the hot path. (Charter Phases 5–6.)

This stage does not wait for Stage 3 to finish everywhere — convergence is
**bidirectional**. The native runtime starts as a backend *composing the same
recovered leaves* the hybrid runtime hooks (one leaf, many adapters), and an
unrecovered piece is a loud gap in native, never a silent fallback to the VM
or a guess from screenshots. Top-down pressure ("native needs X") is answered
by recovering X at the source layer, bottom-up — never by inventing it in the
backend.

**This early convergence applies to the FAITHFUL native runtime only.** The
enhanced presentation layer (modern scaling, interpolation, CRT shading…) is
*not* part of it — it waits for Stage 6, after the faithful game is complete.
(DOS lineage: the Prehistorik 2 project's early experiment with growing
enhanced/faithful *viewer* backends alongside recovery, "cyborgization", is
explicitly not recommended; see `dos_re`'s `enhancements.md`.)

**Verification is not lost at this step — that is the point of the state
mirror.** The native port keeps an address-shaped compatibility bridge: the
game state remains byte-compatible with the original memory layout where
verification needs it, but gameplay code reads it through human-named views
(`player.x`, `slot.sprite`), so readable code and byte-exact comparability
coexist. Offsets are quarantined in one bridge module; the "clean"
representation and the "verifiable" representation are the same bytes. (DOS
lineage: `dos_re`'s `state_mirrors.md`.) The mirror **verifies** the native
game; it does not **power** it — with verification off, no VM starts and no
projection runs.

### What "equivalent" means per subsystem

The VM preserves the original **machine**; the native port preserves the
original **game**. Byte-exactness is the contract only where the game *is*
bytes — insisting on machine-exactness everywhere (or nowhere) are both ways
to fail. The contracts (converged on by the DOS-lineage Prehistorik 2 port;
they translate directly):

| Subsystem | Contract |
|---|---|
| **Gameplay simulation** (player, objects, AI, collision, physics, score, **RNG**, timers, level state) | **strict / byte-exact**: same initial state + same input history + same tick → same game state. On the C64 the RNG is typically SID OSC3 ($D41B) reads or a software LFSR — it is gameplay state and must match. "Close enough" is not faithful. |
| **Rendering** | **pixel-exact, mechanism-flexible**: same recovered render state → same visible pixels + colors at the same frame boundary. The native renderer need not reproduce char fetch cycles, badlines, or $D018/$DD00 pointer tricks. |
| **Audio** | **SID-register-stream / timing-exact, synthesis-flexible**: which register, what value, at which frame/cycle boundary, in what order. The synthesis may be modern; it must never feed back into gameplay. |
| **Input** | **semantic/timing-exact, hardware-path-flexible**: the game-visible input state at tick boundaries must match; the CIA-matrix scan path may differ. |
| **Timing** | **same heartbeat, NOT same waiting machinery** (below). |

### The heartbeat

The native port must **not** reproduce the C64 waiting machinery — raster
polls on $D012, IRQ-flag spins, cycle-counted delay loops. It preserves the
**game tick cadence**: an explicit, fixed-step heartbeat at the original PAL
50Hz rate, with the frame/input/render/audio boundaries named in code.
Removing the spin is what creates the pacing obligation: the standalone runner
paces gameplay to the recovered tick rate — running "as fast as the display"
is a bug, not faithfulness.

## Stage 5 — the VM retires into the oracle seat

At the end, the VM is no longer a runtime dependency. It remains as the
offline proof harness behind a **verification switch**: ON, the oracle runs
beside the native game — a recorded demo replays through the ASM and the
native core **tick by tick** and the full game-RAM image is compared
byte-exact (render/async offsets aside); OFF, no VM starts and the native game
runs by itself. The VM is the microscope for regressions, the debugger for
divergences, and the standing proof that the native port still behaves like
the original game. The original binary was the source of truth on day one and
is still the source of truth on the last day — what changed is what *runs*.

**Mantra:** the VM preserves the original machine; the source port preserves
the original game. Hybrid prepares the code; native plugs it in; the oracle
proves it did not drift.

## Stage 6 — the enhanced layer: the real endgame

Only now — with a complete, stable, faithful VM-less game that passes the demo
corpus — does the enhanced presentation layer become the focus: modern
scaling, frame interpolation, smooth transitions, CRT/square-pixel aspect,
richer SID synthesis. This ordering is deliberate and learned: building
presentation backends *during* recovery is explicitly not recommended — the
enhanced engine is the reward for a finished faithful game, not a recovery
shortcut. (DOS lineage: the "cyborgization" lesson and the parity-gate rules
in `dos_re`'s `enhancements.md`.)

The faithful core stays frozen underneath: enhancements read state and write
none, every enhancement is proven state-equal to the faithful game at its
neutral setting, and the oracle suite from Stage 5 keeps running unchanged.

## The two invariants that hold through every stage

1. **Always runnable** — the game is playable/observable at every commit; no
   big-rewrite branch.
2. **Always verified** — nothing replaces original behaviour until it has been
   diffed against the original. An unrecovered path fails loud; it is never
   silently faked and never silently handed back to the ASM.
