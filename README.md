# stix_port — recovering Stix (1983, Supersoft) with c64_re

The first C64 recovery port, built on [`../c64_re`](../c64_re/README.md)
exactly the way the DOS ports are built on `dos_re`: the original game runs
as the oracle in a deterministic VM; recovery replaces one proven routine
at a time.

## Layout

```text
assets/       Stix.d64 (original disk image — never committed)
stix/         the game adapter package: all Stix-specific knowledge
scripts/      boot.py (headless bring-up + frame evidence)
              play.py (interactive viewer — actually play the game)
docs/stix/    run_status.md (current phase), symbol_ledger.md (addresses -> evidence)
tests/        boot + determinism tests (skip when assets/ is missing)
artifacts/    rendered frames, screenshots (generated)
```

## Play it

```bash
python scripts/play.py --start        # straight into the game (trainer all-N)
python scripts/play.py                # from the title screen
```

Arrows + Right-Ctrl = joystick port 1. F12 screenshot, F11 pause.
At the title: SHIFT opens the trainer menu (answer Y/N five times),
holding fire starts the game.

## Status

Bring-up complete: boots from the original D64 through decruncher →
trainer → gameplay → game over, deterministic across runs
(`tests/test_boot.py`). The proof engines are live on the real game:
snapshots resume bit-identical, and six lifted Stix routines pass the
differential hook oracle on every call (`tests/test_lift_stix.py`,
census in `artifacts/lift_manifest.json`). Next: input-demo recording in
`c64_re`, so a human-played demo can anchor the recovery work. See
[docs/stix/run_status.md](docs/stix/run_status.md) and the method docs
starting at [START_HERE.md](START_HERE.md).
