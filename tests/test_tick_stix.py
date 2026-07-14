"""Stix game-tick recording is deterministic and non-trivial (skips w/o assets).

This is the equivalence-target harness for play_native: if the recording is
deterministic and its digest evolves per tick, it is a valid oracle to prove
a future VM-less native tick against."""
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

DISK = PORT_ROOT / "assets" / "Stix.d64"
DEMO = PORT_ROOT / "artifacts" / "demos" / "demo_run1_20260714_202142"
needs_assets = pytest.mark.skipif(
    not (DISK.exists() and DEMO.exists()),
    reason="assets/Stix.d64 or demo_run1 missing",
)

# A window that reaches active gameplay (the tick IRQ only runs in-game).
FRAME_LIMIT = 1500


@needs_assets
def test_tick_recording_is_deterministic_and_evolving():
    from scripts.tickdemo import record_from_demo

    td1 = record_from_demo(str(DEMO), frame_limit=FRAME_LIMIT)
    td2 = record_from_demo(str(DEMO), frame_limit=FRAME_LIMIT)

    assert td1.n_ticks > 100, f"expected many gameplay ticks, got {td1.n_ticks}"
    # deterministic: same seed, same consumed input, same per-tick digests
    assert td1.seed == td2.seed
    assert td1.keys == td2.keys
    assert td1.digests == td2.digests
    # the digest actually tracks gameplay (not a constant/stuck fingerprint)
    assert len(set(td1.digests)) > td1.n_ticks // 2
    # input was captured (the demo holds a direction during this window)
    assert any(any(k) for k in td1.keys)
    # each key record is the $4B02-$4B0B input-cell span
    from stix.tick import INPUT_CELLS
    assert len(td1.keys[0]) == INPUT_CELLS[-1] - INPUT_CELLS[0] + 1


@needs_assets
def test_tick_demo_save_load_roundtrip(tmp_path):
    from c64_re.tick_demo import TickDemo
    from scripts.tickdemo import record_from_demo

    td = record_from_demo(str(DEMO), frame_limit=600)
    path = tmp_path / "rt.tickdemo"
    td.save(path)
    back = TickDemo.load(path)
    assert back.seed == td.seed
    assert back.keys == td.keys
    assert back.digests == td.digests
