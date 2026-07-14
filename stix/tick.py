"""The Stix game tick — the mode-independent equivalence seam (see c64_re.tick_demo).

Stix runs its whole game step inside a CIA-timer IRQ whose handler is
installed at ``$66B8`` (the gameplay init at ``$6000`` writes the vector to
``$0314/$0315`` and enables the timer).  The handler is the game tick:

    $66B8  LDA $4B0C / BNE $66FA      re-entrancy guard (skip if a tick runs)
    $66C5  INC $4B25                  tick counter          <- SEED / real-tick start
           JSR $739E                  read joystick  }
           JSR $6CF8                  read keyboard  }  input decode -> $4B02-$4B0B
           JSR $7183 / $7479          hazard AI + move (sprites 6/7)
           JSR $73EC                  collision -> $4B2B
           JSR $6AAC                  move; JSR $73EC collision
           JSR $6C41                  move sprite 3; JSR $73EC collision
    $66F5  STA $4B0C(=0)              tick done             <- COMMIT (real ticks only)
    $66FA  LDA $DC0D / PLA.. / RTI    ack + return

``$66C5`` is reached only when the guard passes (a real tick); ``$66F5`` is
reached only on the real-tick path (the skip branch jumps straight to
``$66FA``), and both collision-branch tails converge on it — so the
seed/commit pair frames exactly one gameplay tick with no spurious records.

Ownership map (what the tick's digest fingerprints — the same boundary a
native tick must reproduce):

- ``$4B00-$4B4F`` — the game-state page (player/sprite grid, hazard code,
  counters), EXCEPT the input cells ``$4B02-$4B0B`` which are *injected*
  each tick (input plumbing, not owned output — see ``INPUT_CELLS``).
- The VIC sprite registers ``$D000-$D02E`` — positions/MSB/enable/expand/
  colors: the hazards and player the tick moves live here.

Not yet handled (documented so the native tick knows): the hazard AI reads
SID ``$D41B`` (OSC3 noise) for randomness.  The VM's LFSR is deterministic
(``c64_re.sid``) but lives outside RAM, so a native tick must either carry
that LFSR in its own state or take the per-tick values as tick-demo
sidebands.  The recording below captures the *result* (the digest), so this
is a native-tick concern, flagged here for when that lands.
"""
from __future__ import annotations

from c64_re.tick_demo import masked_digest, record_ticks

# --- the seam (game knowledge) ------------------------------------------------------
TICK_IRQ_ENTRY = 0x66B8   # the installed IRQ handler (re-entrancy guard)
SEED_PC = 0x66C5          # real-tick body start (guard passed, counter bumped)
COMMIT_PC = 0x66F5        # real-tick end (clears $4B0C); never on the skip path
INPUT_OBSERVE_PC = 0x66CB  # after $739E + $6CF8 decoded input, before the moves read it

STATE_BASE = 0x4B00
STATE_LEN = 0x50          # $4B00-$4B4F
# Input cells (offsets from STATE_BASE): the flags $739E/$6CF8 write and the
# moves consume — up/down/left/right ($02-$05), $06, draw-2 $07, fire $08,
# fire-release-enable $09, $0A, abort $0B.  Captured as the per-tick input
# record and zeroed in the digest (injected, not owned).
INPUT_CELLS = tuple(range(0x02, 0x0C))

# VIC sprite state the tick owns ($D000-$D02E within the register file).
VIC_SPRITE_REGS = tuple(range(0x00, 0x2F))


def _sprite_bytes(rt) -> bytes:
    regs = rt.machine.vic.regs
    return bytes(regs[r] for r in VIC_SPRITE_REGS)


def digest(rt) -> str:
    """Fingerprint the gameplay state the tick owns (state page + sprites),
    with the injected input cells neutralised."""
    region = bytes(rt.mem.ram[STATE_BASE:STATE_BASE + STATE_LEN]) + _sprite_bytes(rt)
    return masked_digest(region, zero=INPUT_CELLS)


def _capture_input(pending: dict, rt) -> None:
    ram = rt.mem.ram
    pending["keys"] = bytes(ram[STATE_BASE + INPUT_CELLS[0]:STATE_BASE + INPUT_CELLS[-1] + 1])


def _commit(pending: dict, rt):
    keys = pending.get("keys")
    if keys is None:            # commit reached before the observe site: not a full tick
        return None
    return keys, {}             # no sidebands yet (see module docstring)


def record(rt, advance_one_frame, *, max_ticks: int = 100_000):
    """Record the game-tick timeline of ``rt`` (the oracle) — the equivalence
    target a VM-less native tick must reproduce.  ``advance_one_frame()``
    drives one frame and returns False when the demo is exhausted."""
    return record_ticks(
        rt,
        seed_pc=SEED_PC,
        commit_pc=COMMIT_PC,
        observe={INPUT_OBSERVE_PC: _capture_input},
        commit=_commit,
        digest=digest,
        advance_one_frame=advance_one_frame,
        max_ticks=max_ticks,
    )
