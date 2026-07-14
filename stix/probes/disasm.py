"""Disassemble a routine (or a set) from the demo's live code image.

    python -m stix.probes.disasm $6A0B $72A0 [--demo DIR] [--frame 900]

Boots/replays the demo to a gameplay point (so decrunched + self-modified
code is in place), then prints each routine's full address-ordered body.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PORT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))
sys.path.insert(0, str(PORT_ROOT))

from c64_re.dis6502 import disassemble_one  # noqa: E402
from c64_re.input_demo import InputDemoPlayback  # noqa: E402
from c64_re.lift.cfg import scan_function  # noqa: E402
from c64_re.runtime import run_frames  # noqa: E402

from stix.input_waits import is_input_wait  # noqa: E402


def image_runtime(demo_dir: str, frame: int):
    demo = InputDemoPlayback.load(demo_dir)
    rt = demo.make_runtime()
    while rt.machine.vic.frame < frame:
        b = rt.machine.vic.frame
        demo.apply_to_runtime(b, rt, single=is_input_wait(rt))
        run_frames(rt, 1)
    return rt


def dump(rt, entry: int) -> None:
    scan = scan_function(rt.mem.rb, entry)
    tag = f"{len(scan.insns)} insns" if scan else f"REFUSED: {scan.reason}"
    print(f"===== ${entry:04X} ({tag}) =====")
    if scan:
        for pc in sorted(scan.insns):
            print("  " + disassemble_one(rt.mem.rb, pc)[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("entries", nargs="+", help="routine addresses, e.g. $6A0B")
    ap.add_argument("--demo", default=str(PORT_ROOT / "artifacts" / "demos"))
    ap.add_argument("--frame", type=int, default=900)
    args = ap.parse_args()
    demo_dir = args.demo
    if Path(demo_dir).is_dir() and not (Path(demo_dir) / "input_demo.json").exists():
        demos = sorted(Path(demo_dir).glob("demo_*"))
        if not demos:
            ap.error(f"no demo under {demo_dir}")
        demo_dir = str(demos[-1])
    rt = image_runtime(demo_dir, args.frame)
    for e in args.entries:
        dump(rt, int(e.lstrip("$"), 16))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
