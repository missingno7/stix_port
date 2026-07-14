# Task: stand up a new game adapter

You have this framework and a game's disk image. Goal of THIS task: the
original PRG boots from its .d64 in the VM, you can see its output and
deliver input, and a no-op frame verification passes — nothing recovered yet.

1. Read `stix_port/README.md` and `docs/roadmap.md`; the ordering there
   encodes the DOS lineage's mistakes. The Stix bring-up is the worked
   reference: cracked single-PRG D64, stack-page decruncher, trainer via
   KERNAL GETIN (`stix_port/tests/test_boot.py`).
2. Create the adapter package modeled on `stix_port/stix/`. Wire
   `c64_re.runtime.create_runtime` with the real .d64 path and the program
   name to LOAD. All game addresses live in the adapter, never in `c64_re/`.
3. Boot. When the interpreter fails loud on an opcode / JAM-filled KERNAL
   address / unmapped I/O register, that is the work: trace the exact
   instruction, implement the *observed* behaviour in the core (rules in
   `c64_re/AGENTS.md`), add a `c64_re/tests/`-style case. Log every such
   extension in your run_status ledger.
4. If the PRG is crunched: run the decruncher once, snapshot past it
   (`c64_re.snapshot.write_snapshot(rt, path)`; `load_snapshot(path)` resumes
   bit-identically), record the cruncher + frontier in the ledger. Bootstrap
   is extraction, not gameplay.
5. Render a frame to PNG (`c64_re.pngout` via the runtime); deliver a key
   through the CIA keyboard matrix (Stix polls `$DC01` raw at the title) or
   joystick and prove the game's input state changed. Screenshot + memory
   evidence into the ledger.
6. Find the CIA-timer wait, the raster wait (`$D012`), and the present
   routine — read them with `c64_re/dis6502.py` (the hotspot profiler is
   still planned; sample executed PCs by hand). Stand up the frame verifier
   (`c64_re.frame_verify` — `run_frame_verifier`/`FrameVerifyConfig`) with a
   no-op candidate; it must match the oracle frame-for-frame before you hook
   anything.

Constraints: no hooks yet, no recovered logic yet, no guessing what the game
"is doing" — only what the trace shows. Finish with the REPORT block
(`prompts/README.md`); the status for everything here is OBSERVED at most.
