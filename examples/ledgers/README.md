# Ledger templates

Copy these into `docs/<game>/` when you start a port and keep them current —
they are the resume state: **the next session (or the next agent) continues
from git + these files alone.** Each template is a shape, not a form; delete
what your game doesn't need, but keep the section names so every port's
ledgers read the same way. The live Stix instance is `docs/stix/` — these
templates are its reference shape, never the other way around.

| Template | Purpose | Updated |
|---|---|---|
| [`run_status.md`](run_status.md) | Current phase + recent findings. The top summary doubles as the **human's progress report** — keep it readable by a non-engineer. | Every session (`prompts/write_recovery_status.md`) |
| [`blockers.md`](blockers.md) | Reverted slices with evidence — a logged blocker is progress; a workaround is debt. | The moment a slice is reverted |
| [`symbol_ledger.md`](symbol_ledger.md) | Address → name → evidence → status. The evidence trail behind every semantic name. | Every slice that names something |
| [`demo_manifest.md`](demo_manifest.md) | The demo corpus: what each demo covers, and the corpus's blind spots. | Every promoted demo |
| [`overnight_goal.md`](overnight_goal.md) | The standing goal brief for unattended runs (overnight loop harness, planned): done-condition, gates, work-queue buckets. Stable by design — the live frontier lives in `run_status.md`. | When the campaign's phase changes |

The island manifest (`docs/recovered_islands.md`) is **generated**
(`python c64_re/tools/gen_island_manifest.py <packages> -o
docs/recovered_islands.md`), never hand-edited — it has no template here.
