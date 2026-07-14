"""Lift + differential-verify real Stix routines in situ (skips w/o assets)."""
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

DISK = PORT_ROOT / "assets" / "Stix.d64"
needs_assets = pytest.mark.skipif(not DISK.exists(), reason="assets/Stix.d64 missing")

# gameplay-hot JSR targets from the 2026-07-14 census (artifacts/lift_manifest.json):
# $73EC fires ~2.4x/frame, $7183 (96 insns, 7 call deps) and $739E ~0.8x/frame
HOT_ENTRIES = (0x73EC, 0x7183, 0x739E)


@needs_assets
def test_lifted_stix_routines_pass_oracle():
    import stix
    from c64_re.hooks import HookRegistry
    from c64_re.lift.emit import lift_and_compile
    from c64_re.runtime import run_frames
    from c64_re.verification import install_live_verifier

    rt = stix.boot(PORT_ROOT / "assets")
    stix.start_game(rt)
    run_frames(rt, 50)

    registry = HookRegistry()
    for entry in HOT_ENTRIES:
        hook, _, scan = lift_and_compile(rt.mem.rb, entry)
        registry.replace(entry, f"lifted_{entry:04X}")(hook)
        assert scan.exits, f"${entry:04X} scan has no exits"
    registry.install(rt.cpu)

    oracle = install_live_verifier(rt, strict_cycles=True)
    run_frames(rt, 30)

    assert oracle.stats.verified >= 30, (
        f"expected the hot routines to fire; verified={oracle.stats.verified}"
    )
    assert not oracle.stats.diverged
