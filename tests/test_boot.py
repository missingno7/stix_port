"""Stix boot/bring-up tests.  Skip when assets/ is empty (original game
files are never committed — same convention as the DOS ports)."""
import hashlib
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

DISK = PORT_ROOT / "assets" / "Stix.d64"
needs_assets = pytest.mark.skipif(not DISK.exists(), reason="assets/Stix.d64 missing")


def full_state_digest(rt) -> str:
    h = hashlib.sha256()
    h.update(rt.mem.ram)
    h.update(rt.mem.color_ram)
    h.update(bytes(rt.machine.vic.regs))
    h.update(rt.machine.vic.raster.to_bytes(2, "little"))
    h.update(rt.cpu.instr_count.to_bytes(8, "little"))
    h.update(rt.cpu.cycle_count.to_bytes(8, "little"))
    s = rt.cpu.s
    h.update(bytes((s.a, s.x, s.y, s.sp, s.get_p())))
    h.update(s.pc.to_bytes(2, "little"))
    return h.hexdigest()


@needs_assets
def test_boot_reaches_title_deterministically():
    import stix
    digests = []
    for _ in range(2):
        rt = stix.boot(PORT_ROOT / "assets")
        digests.append(full_state_digest(rt))
    assert digests[0] == digests[1]


@needs_assets
def test_trainer_to_gameplay():
    import stix
    from c64_re.runtime import run_frames
    rt = stix.boot(PORT_ROOT / "assets")
    stix.start_game(rt)
    run_frames(rt, 50)
    v = rt.machine.vic
    assert v.regs[0x11] & 0x20, "gameplay should be in bitmap mode"
    assert v.regs[0x15] != 0, "gameplay should have sprites enabled"


@needs_assets
def test_input_scripted_run_is_deterministic():
    """Same frame-keyed input -> byte-identical machine state.  This is the
    property the upcoming demo recorder builds on."""
    import stix
    from c64_re.cia import JOY_FIRE, JOY_UP
    from c64_re.runtime import run_frames

    def scripted_run():
        rt = stix.boot(PORT_ROOT / "assets")
        stix.start_game(rt)
        rt.machine.set_joy1(JOY_UP)
        run_frames(rt, 40)
        rt.machine.set_joy1(JOY_FIRE)
        run_frames(rt, 25)
        rt.machine.set_joy1(0)
        run_frames(rt, 60)
        return full_state_digest(rt)

    assert scripted_run() == scripted_run()
