"""Boot / navigation wiring for the Stix oracle runtime.

Where the game meets the framework: create a runtime from the original disk,
drive it to the title screen and (optionally) into gameplay, and install the
recovered replacement hooks for a hybrid run.  Game-specific knowledge lives
here and in the sibling adapter modules — never in ``c64_re``.
"""
from __future__ import annotations

from pathlib import Path

from c64_re.runtime import Runtime, create_runtime, run_frames

DISK_FILE = "STIX+5      /REM"

# title-screen poll loop (PC range) — "the game is at the title" marker.
# (also the input-wait head; see stix.input_waits)
TITLE_LOOP = range(0x2306, 0x2311)


def boot(asset_dir, *, install_hooks: bool = False) -> Runtime:
    """Boot the original into the oracle VM, up to the title screen.

    ``install_hooks=True`` installs the recovered replacement hooks (a hybrid
    run); the default is the pure-ASM oracle.
    """
    rt = create_runtime(Path(asset_dir) / "Stix.d64", install_hooks=False)
    if install_hooks:
        install_recovered_hooks(rt)
    run_frames(rt, 400)  # decrunch + init + title fade-in
    return rt


def start_game(rt: Runtime, *, trainer_answers: str = "NNNNN") -> None:
    """Drive the trainer menu from the title screen: SHIFT opens it, then one
    Y/N answer per option; the game starts after the last answer."""
    m = rt.machine
    m.key_down("LSHIFT")
    run_frames(rt, 30)
    m.key_up("LSHIFT")
    run_frames(rt, 30)
    for ch in trainer_answers.upper():
        if ch not in "YN":
            raise ValueError(f"trainer answers must be Y/N, got {ch!r}")
        m.key_down(ch)
        run_frames(rt, 10)
        m.key_up(ch)
        run_frames(rt, 20)
    run_frames(rt, 100)  # arena fade-in


def install_recovered_hooks(rt: Runtime) -> None:
    """Install the adapter's recovered replacement hooks onto a runtime."""
    from .hooks import registry
    registry.install(rt.cpu)
