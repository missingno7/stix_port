# Roadmap — the C64 ecosystem

Where this repo and `../c64_re` are headed. The DOS lineage
(`dos_recosystem/dos_re` + `template_dos_port`, extracted from two completed
ports) is the proven shape we are growing toward; this file tracks the C64
side's own path. Ordering follows the user's standing directive: build
infrastructure when a real game needs it, not before.

## Done (2026-07-14, session 2)

- ~~**snapshot.py**~~ — freeze/thaw + `.c64snap` files + `clone_runtime`;
  Stix gameplay snapshot resumes bit-identical.
- ~~**verification.py**~~ — the differential hook oracle (strict JSR-return
  + `HookStop` metadata modes, full-state diff, `C64_RE_TRACE_HOOK`), with
  `gaps.py` ported.
- ~~**the lifter**~~ — `c64_re/lift/` decode/cfg/emit/manifest +
  `tools/liftgen.py` census + `tools/liftverify.py` in-situ driver.
  Proven on Stix: 41/76 candidates liftable, 6 gameplay-hot routines
  ORACLE_PASSING (781 verified calls, 0 divergences, strict cycle model).

## Done (2026-07-14, session 3 — the full dos_re mirror)

- ~~input_demo.py + the standard player CLI~~ — GameFrontend,
  `--record-demo`/`--play-demo`/`--headless`/`--no-replacements`/
  `--verify-hooks`/`--trace-hooks`, hotkeys F10/F11/F12; a scripted Stix
  gameplay demo replays bit-identically (tests/test_demo_stix.py).
- ~~frame_verify.py~~ (frame oracle), ~~tick_demo.py~~ (endgame engine),
  ~~checkpoints.py~~, ~~islands.py~~, ~~coverage.py~~, ~~hook_taxonomy~~,
  ~~frontier~~, ~~repro_artifacts~~, ~~runtime_code~~ (SMC support),
  ~~state_view~~, ~~testing~~ + tools: lint, audit_layers,
  check_undefined_names, gen_island_manifest, render_frame, view.
  Consolidated: 101 framework tests + 5 port tests green; lint clean.

## Now (in dependency order)

1. **Ask the human for the first played demos** (`python scripts/play.py
   --record-demo --demo-name NAME` — a cold-start demo from power-on;
   recording starts when the window opens, close to save; must include a
   death and a game-over — see pitfalls on flattering corpora).
2. **Input-wait registry** for Stix: `StixFrontend.is_input_wait` covers
   the $2306 title poll; find the gameplay poll and add it.
3. **Frame boundaries for Stix** → stand up the frame verifier with a
   no-op candidate (bring-up step 4).
4. Recovery proper: refactor the ORACLE_PASSING lifted routines ($73EC,
   $7183, $739E, ...) into named pure rules behind thin hooks; track with
   @oracle_link; generate the island manifest.

## Later

- SID **audio sink** for the viewer (observer-only, dos_re's
  audio_sink.py pattern) — presentation, so it waits.
- Hotspot profiler / VICE-snapshot importer / overnight harness as needed.
- PyPy validation for headless workloads (DOS lineage: 13-17x).

## Eventually

- **template_c64_port**: extract the method docs + skeleton from this repo
  once Stix proves them end-to-end (exactly how template_dos_port was
  extracted from pre2_port — see its MIGRATION.md). Until then, this repo
  IS the template-in-progress, and its docs/ carry the C64 method.
- c64_re as a proper git submodule with its own remote.
- A second game to force generalization (the "Overkill role" is Stix's;
  the second game plays "Prehistorik 2").

## Decided non-goals (for now)

- Cycle-exact VIC timing (badlines, sprite DMA stealing) — line-granular
  is enough until a game's *gameplay* provably depends on it.
- 1541 drive CPU / GCR emulation — KERNAL-level D64 HLE until a fastloader
  forces game-specific loader HLE.
- NTSC — PAL only until a target game is NTSC.
- Cartridge (.crt) mapping, REU, C128 modes.
