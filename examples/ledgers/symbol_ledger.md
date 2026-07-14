# <GAME> — symbol ledger

<!-- Address → name → evidence. Every semantic name must be reversible to
     oracle evidence: a name here without an evidence entry is a GUESS and
     must say so. Address-level names (scan_4537, decode_81AE) are fine and
     often permanent — a kept address name is cheaper than an encoded false
     abstraction (pitfall #1). Addresses are flat 16-bit $XXXX. -->

## Code

| Address | Name | Status | Evidence |
|---|---|---|---|
| $4537 | <name or candidate?> | OBSERVED | <trace/snapshot/golden paths, one line why> |

## Data / state

<!-- Zero-page bytes, tables, buffers, lo/hi pointer pairs. Width matters:
     the same bytes read at two widths (or as a split lo/hi pair vs single
     bytes) are TWO entries (pitfall #2). -->

| Address | Width | Name | Status | Evidence |
|---|---|---|---|---|
| $27D8 | byte | <name> | OBSERVED | <who reads/writes it, seen where> |

## Naming candidates (not yet earned)

<!-- Hypotheses awaiting a second independent evidence path. -->
