"""Frame-oracle proof on Stix: lifted hybrid == pure ASM, pixel-exact
at every frame boundary (skips w/o assets)."""
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

DISK = PORT_ROOT / "assets" / "Stix.d64"
needs_assets = pytest.mark.skipif(not DISK.exists(), reason="assets/Stix.d64 missing")

LIFTED_ENTRIES = (0x73EC, 0x7183, 0x739E)


def gameplay_runtime(install_lifted: bool):
    import stix
    from c64_re.hooks import HookRegistry
    from c64_re.lift.emit import lift_and_compile
    from c64_re.runtime import run_frames

    rt = stix.boot(PORT_ROOT / "assets")
    stix.start_game(rt)
    run_frames(rt, 50)
    if install_lifted:
        reg = HookRegistry()
        for entry in LIFTED_ENTRIES:
            hook, _, _ = lift_and_compile(rt.mem.rb, entry)
            reg.replace(entry, f"lifted_{entry:04X}")(hook)
        reg.install(rt.cpu)
    return rt


@needs_assets
def test_lifted_hybrid_matches_pure_asm_frames(tmp_path):
    from c64_re.frame_verify import FrameVerifyConfig, run_frame_verifier

    ref = gameplay_runtime(install_lifted=False)
    cand = gameplay_runtime(install_lifted=True)
    cfg = FrameVerifyConfig(max_frames=30, dump_dir=tmp_path)
    rc = run_frame_verifier(reference=ref, candidate=cand, config=cfg)
    assert rc == 0, "lifted hybrid diverged from the pure-ASM oracle"


@needs_assets
def test_frame_oracle_catches_a_planted_difference(tmp_path):
    from c64_re.frame_verify import FrameVerifyConfig, run_frame_verifier

    ref = gameplay_runtime(install_lifted=False)
    bad = gameplay_runtime(install_lifted=False)
    bad.machine.vic.write(0x21, 1)  # planted divergence: background color
    cfg = FrameVerifyConfig(max_frames=5, dump_dir=tmp_path, stop_on_diff=True)
    rc = run_frame_verifier(reference=ref, candidate=bad, config=cfg)
    assert rc == 1
    assert list(tmp_path.glob("frame_*_diff.png")), "no divergence artifacts"
