# stix_port documentation (the future template_c64_port)

**Audience: the AI porting agent.** Everything under `docs/` is the agent's
operating manual; a human only needs the repo [README](../README.md) and the
`docs/<game>/run_status.md` the agent writes. These method docs live in
`stix_port` for now and will be extracted into `template_c64_port` later —
the same way `template_dos_port` was extracted from `pre2_port`.

Start at [`../AGENTS.md`](../AGENTS.md) (the operating card) →
[`../START_HERE.md`](../START_HERE.md) (the boot sequence) if you haven't.
Reading order: `lifecycle.md` → `ai_porting_charter.md` → `pitfalls.md` →
`porting_new_game.md`.

| Doc | What it covers |
|---|---|
| [`lifecycle.md`](lifecycle.md) | **The story in order**: PRG-in-VM → hot-path islands → gameplay recovery → islands merge into subsystems → complete faithful VM-less game → VM retires into the oracle seat → enhanced presentation layer last. Defines the shared vocabulary (oracle, island, golden, hybrid, native). |
| [`ai_porting_charter.md`](ai_porting_charter.md) | **The method, complete.** VM-as-oracle, the two invariants, the lifting loop, the proof spine, the determinism trap, the phased roadmap, the rules of engagement. Written for the AI agent given this framework and a C64 game. |
| [`pitfalls.md`](pitfalls.md) | **The real mistakes** already made for you — naming, hook bloat, verification narrowing, state-capture timing, determinism traps, SMC, layering, AI hallucination, premature presentation work — each with the consequence and the rule that fixed it. Mostly DOS lineage (P2/OK), plus the C64 lessons Stix has already paid for. |
| [`porting_new_game.md`](porting_new_game.md) | The concrete bring-up checklist for a new game, step 0 → the lifting loop, plus the endgame steps. |

Three docs stay in the DOS template for now — one is endgame-gated, two are
extracted from DOS worked examples that have no C64 equivalent yet
(`D:\Games\DOS\dos_recosystem\template_dos_port\docs\`):

- `cookbook.md` — problem-indexed techniques living as worked examples in the
  DOS source repos (timing fast-forward, shadow caches, staticizing patched
  code, layered audio recovery, overnight loops). Consult it the moment your
  game hits a wall; translating a technique to the C64 is usually mechanical.
- `enhancements.md` — the enhanced layer as the ENDGAME (sequencing rule +
  the audio exception, the parity gate).
- `post_endgame.md` — **GATED — read only after the flip.**

## Method machinery → c64_re status

The docs teach the FULL method (it is the target). Where the machinery
doesn't exist yet in `c64_re`, the docs mark it "(planned)"; this is the
authoritative map (see also `c64_re/README.md` §Deliberately not built yet):

| Machinery | Status |
|---|---|
| The machine: `cpu.py` (replacement/service hook dispatch, trace, cycle telemetry), `memory.py` (PLA banking), `machine.py` (chip glue + `key_down/key_up/set_joy1/set_joy2`), `vic.py` (per-raster-line latching, renderer, collisions), `cia.py`, `sid.py` | EXISTS |
| The KERNAL seam: `kernal.py` (clean-room JAM-filled shim ROM, HLE traps, fails loud with the exact address), `d64.py` | EXISTS |
| `hooks.py` (`registry.replace(pc, name)`, live-code signature guards, `C64_RE_DISABLE_HOOKS`), `runtime.py` (`create_runtime`/`run_frames`/`run_until`) | EXISTS |
| Frontend: `player.py` (pygame viewer + `GameFrontend`; F9 pause, F10 screenshot, F11 demo-record toggle, F12 snapshot), `pngout.py`, `dis6502.py`; framework tests | EXISTS |
| `snapshot.py` (`capture`/`restore`, `clone_runtime`, `write_snapshot`/`load_snapshot` — `.c64snap` files) | EXISTS |
| `input_demo.py` (`InputDemoRecorder`/`InputDemoPlayback`; snapshot-anchored and cold-start demos, `write_suffix`, `playback.make_runtime()`) | EXISTS |
| `verification.py` (differential hook oracle: `HookOracle`, `HookStop` metadata mode, strict JSR-return mode, `install_live_verifier`, `C64_RE_TRACE_HOOK`) | EXISTS |
| `frame_verify.py` (`run_frame_verifier`, ref/cand/diff artifacts on divergence), `checkpoints.py` (`run_to_next_checkpoint`) | EXISTS |
| `gaps.py` (`HybridGap`, `HookVerifyStats`, `HookTraceStats`, `report()`) | EXISTS |
| `islands.py` (`@oracle_link`, `collect_islands`), `coverage.py` (`CoverageCollector`), `tick_demo.py` (`record_ticks`/`verify_ticks`, `masked_digest`) | EXISTS |
| The lifter: `lift/` (decode/cfg/emit/runtime/manifest) + `tools/liftgen.py` (census), `tools/liftverify.py` (in-situ install + per-call oracle verification) | EXISTS |
| Tools: `lint.py`, `audit_layers.py`, `gen_island_manifest.py`, `check_undefined_names.py`, `render_frame.py`, `view.py` | EXISTS |
| The `GameFrontend` standard CLI (`--record-demo`/`--play-demo`/`--headless`/`--no-replacements`; F9 pause, F10 screenshot, F11 demo-record toggle, F12 snapshot) | EXISTS |
| SID audio sink for the viewer, `overlay_menu` (post-endgame), hotspot profiler, VICE-savestate importer, overnight-loop shell harness | PLANNED |

Related, outside `docs/`:

- [`stix/`](../stix/__init__.py) and [`docs/stix/`](stix/run_status.md) — the
  live adapter and ledgers of the first port (Stix boots to gameplay
  deterministically; `tests/test_boot.py` is the digest-test pattern).
- The framework itself is the **sibling** repo
  [`../../c64_re/README.md`](../../c64_re/README.md) (what exists, what's
  deliberately deferred, hardware limits in `docs/hardware_support.md`) and
  [`../../c64_re/AGENTS.md`](../../c64_re/AGENTS.md) (rules for working on
  the framework, as opposed to your adapter). Not a submodule yet — scripts
  and tests put `../c64_re` on `sys.path` themselves.
- The DOS template's `prompts/` (task rituals + REPORT blocks) and
  `examples/ledgers/` (annotated ledger templates) apply unchanged:
  `D:\Games\DOS\dos_recosystem\template_dos_port\`.
