"""Record/replay a scripted Stix gameplay demo — bit-identical (skips w/o assets)."""
import hashlib
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

DISK = PORT_ROOT / "assets" / "Stix.d64"
needs_assets = pytest.mark.skipif(not DISK.exists(), reason="assets/Stix.d64 missing")


def digest(rt) -> str:
    h = hashlib.sha256()
    h.update(rt.mem.ram)
    h.update(rt.mem.color_ram)
    h.update(bytes(rt.machine.vic.regs))
    h.update(str((rt.cpu.s.as_dict(), rt.cpu.cycle_count,
                  rt.machine.vic.frame)).encode())
    return h.hexdigest()


@needs_assets
def test_recorded_gameplay_demo_replays_bit_identically(tmp_path):
    import stix
    from c64_re.cia import JOY_DOWN, JOY_FIRE, JOY_UP
    from c64_re.input_demo import InputDemoPlayback, InputDemoRecorder
    from c64_re.runtime import run_frames

    rt = stix.boot(PORT_ROOT / "assets")
    stix.start_game(rt)
    run_frames(rt, 30)

    rec = InputDemoRecorder(root=tmp_path, name="scripted")
    demo_dir = rec.start(rt)
    script = {0: JOY_UP, 25: 0, 40: JOY_DOWN | JOY_FIRE, 60: 0}
    for i in range(80):
        if i in script:
            rt.machine.set_joy1(script[i])
            rec.record_joy(boundary=rt.machine.vic.frame, port=1, mask=script[i])
        run_frames(rt, 1)
    rec.stop(boundary=rt.machine.vic.frame)
    reference = digest(rt)

    pb = InputDemoPlayback.load(demo_dir)
    rt2 = pb.make_runtime()
    while True:
        b = rt2.machine.vic.frame
        pb.apply_to_runtime(b, rt2)
        if pb.finished(b):
            break
        run_frames(rt2, 1)
    assert digest(rt2) == reference
