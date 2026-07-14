"""Play Stix in the oracle VM — the standard c64_re play runner.

    python scripts/play.py                      # boot to the title screen
    python scripts/play.py --start              # through the trainer (all N)
    python scripts/play.py --start --trainer YNNNY
    python scripts/play.py --record-demo                # cold-start demo (whole session)
    python scripts/play.py --record-demo --demo-name run1
    python scripts/play.py --play-demo artifacts/demos/demo_NAME_...
    python scripts/play.py --headless --play-demo ... [--frames N]
    python scripts/play.py --snapshot artifacts/gameplay.c64snap
    python scripts/play.py --no-replacements    # pure-ASM oracle mode

--record-demo records a true COLD-START demo: the whole session from
power-on.  It starts the moment the window opens (no keypress needed) and
skips the auto-trainer, so YOU drive everything — watch the decrunch, open
the trainer with SHIFT, answer five Y/N, and play.  All of it is captured.
Close the window to save (or F11 to stop/start a fresh take).  --demo-name
sets the name (default "stix").  (--snapshot + --record-demo instead
records a snapshot-anchored demo from that resume point.)

Sound plays through the speakers by default (the SID register stream,
synthesized); pass --no-audio to mute.

Controls: arrows + Right-Ctrl = joystick port 1 (the game's port); the C64
keyboard is mapped 1:1.  Hotkeys: F10 screenshot, F11 demo stop/restart,
F12 snapshot, F9 pause.  At the title: SHIFT opens the trainer, five Y/N
answers start the game.
"""
from __future__ import annotations

import sys
from pathlib import Path

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

from c64_re import player  # noqa: E402
from c64_re.runtime import run_frames  # noqa: E402
import stix  # noqa: E402


class StixFrontend(player.GameFrontend):
    name = "Stix"
    default_image = "assets/Stix.d64"
    default_joy_port = 1  # observed: the game reads joystick port 1

    def add_arguments(self, ap) -> None:
        ap.add_argument("--start", action="store_true",
                        help="drive the trainer menu and start the game")
        ap.add_argument("--trainer", default="NNNNN",
                        help="five Y/N trainer answers (with --start)")

    def boot_to_start(self, rt, args) -> None:
        run_frames(rt, 400)  # decrunch + init + title fade-in
        if args.start:
            stix.start_game(rt, trainer_answers=args.trainer)

    def demo_metadata(self, rt, args) -> dict:
        return {"frontend": self.name, "trainer": getattr(args, "trainer", ""),
                "started": bool(getattr(args, "start", False))}

    def is_input_wait(self, rt) -> bool:
        # the title poll samples $DC01 per iteration — deliver demo events one
        # per frame there so same-frame release/press pairs are observed
        # separately (the shared input-wait registry, stix.input_waits)
        from stix.input_waits import is_input_wait
        return is_input_wait(rt)


def main() -> int:
    return player.main(StixFrontend(PORT_ROOT), description=__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
