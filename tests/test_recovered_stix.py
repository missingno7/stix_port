"""Recovered Stix logic: pure-function unit tests, the pure-layer audit, and
byte-exact verification of the recovered hooks against the demo oracle."""
import subprocess
import sys
from pathlib import Path

import pytest

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

from stix.recovered.audio import voice1_frequency  # noqa: E402
from stix.recovered.bitmap import plot_pixel  # noqa: E402
from stix.recovered.bitmap import test_pixel as read_pixel  # noqa: E402 (avoid pytest test_* collection)
from stix.recovered.input_decode import decode_joystick  # noqa: E402
from stix.recovered.sprites import sprite_to_grid  # noqa: E402

DISK = PORT_ROOT / "assets" / "Stix.d64"
DEMO = PORT_ROOT / "artifacts" / "demos" / "demo_run1_20260714_202142"
needs_demo = pytest.mark.skipif(not (DISK.exists() and DEMO.exists()),
                                reason="assets/Stix.d64 or the demo missing")


# ---- pure functions (always run; no assets) -----------------------------------
def test_voice1_frequency():
    assert voice1_frequency(0x00) == (0x00, 0x00)
    assert voice1_frequency(0xF0) == (0x00, 0x0F)   # high nibble only
    assert voice1_frequency(0x01) == (0x08, 0x00)   # low bit0 reverses to bit3
    assert voice1_frequency(0x08) == (0x01, 0x00)   # low bit3 reverses to bit0
    assert voice1_frequency(0xFF) == (0x0F, 0x0F)


def test_decode_joystick_active_low():
    idle = decode_joystick(0xFF)
    assert not any((idle.up, idle.down, idle.left, idle.right, idle.fire))
    assert decode_joystick(0xFF ^ 0x01).up
    assert decode_joystick(0xFF ^ 0x10).fire
    both = decode_joystick(0xFF ^ 0x08 ^ 0x10)
    assert both.right and both.fire and not both.left


def test_sprite_to_grid():
    assert sprite_to_grid(0x00, 0x30) == (0xF5, 0x00)   # (0>>1)-0x0B, 0x30-0x30
    assert sprite_to_grid((1 << 8) | 0x40, 0x50) == (((0x140 >> 1) - 0x0B) & 0xFF, 0x20)


def test_bitmap_bit_ops():
    assert plot_pixel(0b0000_0001, 0b0100_0000) == 0b0100_0001
    assert read_pixel(0b0100_0001, 0b0100_0000) != 0
    assert read_pixel(0b0000_0001, 0b0100_0000) == 0


# ---- the pure-layer boundary is enforced --------------------------------------
def test_recovered_layer_is_vm_free():
    r = subprocess.run(
        [sys.executable, str(PORT_ROOT / "c64_re" / "tools" / "audit_layers.py"),
         "stix/recovered"],
        cwd=str(PORT_ROOT), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# ---- the recovered hooks match the original, byte-exact, on the real demo -----
@needs_demo
def test_recovered_hooks_verify_against_demo():
    from collections import Counter

    from c64_re.input_demo import InputDemoPlayback
    from c64_re.runtime import run_frames
    from c64_re.verification import install_live_verifier
    from stix.hooks import registry
    from stix.input_waits import is_input_wait

    demo = InputDemoPlayback.load(DEMO)
    rt = demo.make_runtime()
    registry.install(rt.cpu)
    verified: Counter = Counter()
    diverged: Counter = Counter()
    reasons: dict = {}

    def on_result(name, ok, reason):
        (verified if ok else diverged)[name] += 1
        if not ok:
            reasons.setdefault(name, reason)

    # hand hooks tick 0 cycles; the verifier makes up the machine-time deficit
    install_live_verifier(rt, on_result=on_result, raise_on_divergence=False)
    while rt.machine.vic.frame < 1300:  # into gameplay so every hook fires
        b = rt.machine.vic.frame
        demo.apply_to_runtime(b, rt, single=is_input_wait(rt))
        run_frames(rt, 1)

    assert not diverged, f"recovered hooks diverged: {dict(diverged)} — {reasons}"
    # every recovered hook must actually fire in the window
    for name in ("sid_voice1_freq", "poke_cia1_pra", "sprite_to_grid", "read_joystick",
                 "bitmap_pixel_addr", "bitmap_plot", "bitmap_test"):
        assert verified[name] > 0, f"{name} never fired (no evidence)"
