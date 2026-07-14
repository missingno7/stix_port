"""stix — the game adapter package for the Stix recovery port.

Game-specific knowledge lives HERE, never in c64_re (the framework stays
game-agnostic; that boundary is the method's one hard rule).

Evidence so far (from running the oracle VM — see docs/stix/symbol_ledger.md):

- Disk: single PRG ``STIX+5      /REM`` (7839 bytes packed), BASIC stub
  ``SYS 2059`` ($080B) -> decruncher (runs from the stack page, ~200 frames)
  -> unpacked game fills RAM to ~$7FFF.
- Init at $0C40: colors, JSR $E536 (KERNAL clear-screen internal), copies
  the character ROM to $0800, block-copies the ROM vector table $FD30 ->
  $0314 (why the shim KERNAL carries a real table image), NMI -> $FEC1
  (RESTORE neutralized), game IRQ at $0D7D during init, then $EA31.
- Title/attract loop at $2306: polls $DC01 raw; exactly $7F (a row-7 key,
  e.g. SHIFT) -> trainer menu at $2352; $EF = joystick PORT 1 fire -> start
  fade (counter at $02/$03 must count down to $21A0).
- Trainer menu ($2352): five Y/N questions via KERNAL GETIN; patches the
  decrunched game body ($6213, $74B2, $66D7/$66F1/$67E0, $68B7, $6B22).
- Gameplay: bitmap mode ($D011=$3B, $D018=$1F), 7 sprites enabled; player
  crosshair is sprite 0; joystick port 1; game code observed around
  $61xx-$6Exx.
"""
from __future__ import annotations

from c64_re.runtime import Runtime, create_runtime, run_frames

DISK_FILE = "STIX+5      /REM"

# title-screen poll loop (PC range) — useful as a "game is at title" marker
TITLE_LOOP = range(0x2306, 0x2311)


def boot(asset_dir) -> Runtime:
    """Boot the original into the oracle VM, up to the title screen."""
    from pathlib import Path

    rt = create_runtime(Path(asset_dir) / "Stix.d64")
    run_frames(rt, 400)  # decrunch + init + title fade-in
    return rt


def start_game(rt: Runtime, *, trainer_answers: str = "NNNNN") -> None:
    """Drive the trainer menu from the title screen: SHIFT opens it, then
    one Y/N answer per option; the game starts after the last answer."""
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
