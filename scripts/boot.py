"""Boot Stix in the c64_re oracle VM and dump frame evidence.

Usage:
    python scripts/boot.py [--frames N] [--out DIR] [--every M] [--trace-tail]

Runs the original PRG from assets/Stix.d64, renders PNG frames, and prints
the machine event log + a screen-RAM text dump.  On a crash it prints the
disassembly around PC — the crash *is* the next work item.
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

PORT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT_ROOT / "c64_re"))

from c64_re.dis6502 import disassemble, disassemble_one  # noqa: E402
from c64_re.pngout import save_frame_png  # noqa: E402
from c64_re.runtime import create_runtime, run_frames  # noqa: E402


def screen_text(rt) -> str:
    ram = rt.mem.ram
    base = ram[0x288] << 8 if ram[0x288] else 0x0400
    lines = []
    for row in range(25):
        chars = []
        for col in range(40):
            sc = ram[base + row * 40 + col] & 0x7F
            if sc == 0:
                chars.append("@")
            elif 1 <= sc <= 26:
                chars.append(chr(ord("A") + sc - 1))
            elif 32 <= sc <= 63:
                chars.append(chr(sc))
            else:
                chars.append(".")
        lines.append("".join(chars))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--every", type=int, default=50, help="PNG every M frames")
    ap.add_argument("--out", default=str(PORT_ROOT / "artifacts"))
    ap.add_argument("--trace-tail", action="store_true",
                    help="keep a ring buffer of executed PCs for crash context")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rt = create_runtime(PORT_ROOT / "assets" / "Stix.d64")
    print(f"booted {rt.program.file_name!r}: "
          f"load ${rt.program.load_addr:04X}-${rt.program.end_addr - 1:04X}, "
          f"entry ${rt.program.entry:04X}")

    tail: deque[int] = deque(maxlen=64)
    if args.trace_tail:
        rt.cpu.trace_fn = lambda cpu, pc, op: tail.append(pc)

    frame_done = 0
    try:
        while frame_done < args.frames:
            step = min(args.every, args.frames - frame_done)
            run_frames(rt, step)
            frame_done += step
            path = out / f"frame_{frame_done:05d}.png"
            save_frame_png(path, rt.machine.vic.render_frame(border=True))
            print(f"frame {frame_done}: PC=${rt.cpu.s.pc:04X} "
                  f"raster={rt.machine.vic.raster} "
                  f"instr={rt.cpu.instr_count} -> {path.name}")
    except Exception as exc:  # noqa: BLE001 - crash reporting is the point
        print(f"\nSTOPPED at frame~{rt.machine.vic.frame} "
              f"instr={rt.cpu.instr_count}: {type(exc).__name__}: {exc}")
        pc = rt.cpu.s.pc
        print(f"\nPC=${pc:04X}  A={rt.cpu.s.a:02X} X={rt.cpu.s.x:02X} "
              f"Y={rt.cpu.s.y:02X} SP={rt.cpu.s.sp:02X} P={rt.cpu.s.get_p():02X}")
        if tail:
            print("\nlast executed PCs:")
            uniq = list(tail)
            for tpc in uniq[-16:]:
                print("  " + disassemble_one(rt.mem.rb, tpc)[0])
        print("\ndisassembly at PC:")
        print(disassemble(rt.mem.rb, pc, 8))
        save_frame_png(out / "frame_crash.png", rt.machine.vic.render_frame(border=True))
        print(f"\ncrash frame saved to {out / 'frame_crash.png'}")
        raise SystemExit(1)

    print("\nmachine events:")
    for e in rt.machine.events:
        print("  " + e)
    print("\nscreen RAM:")
    print(screen_text(rt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
