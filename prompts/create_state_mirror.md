# Task: create a state mirror for an island

Requires: the `c64_re` state-view layer — `c64_re.state_view`
(`StructView`/`StructArray`, `U8/U16/S8/S16` descriptors over
`ByteBackend`/`RamBackend`/`OverlayBackend`/`WidthContractBackend`).

Move an island's raw addresses behind human-named typed views — without
changing behaviour and without weakening byte-exact verification.

1. **Scope**: one island per slice. List every raw address access
   (`mem[0x4537]`, zero-page bytes, lo/hi table pairs) it performs.
2. **Define the view** in the adapter's bridge module (`StructView` subclass
   + `U8/U16/S8/S16/U16Array/StructArray` descriptors over flat 16-bit
   addresses). The bridge module is the ONLY place these addresses may
   appear. Name fields by *evidence* (what the verified lift proved), not by
   guess.
3. **Width aliases**: if the ASM reads the same bytes at two widths — or as
   a split lo/hi pair vs single bytes — define two named fields
   (pitfall #2). Genuinely union-typed addresses (different meaning per
   entity type) may stay raw backend access with a comment — three aliases
   for one triple-typed address is noise.
4. **Backend choice is dictated by the island's golden**: byte-backed for
   in-place mutation; overlay/contract backends for contract-returning
   passes. Match the golden; don't redesign it.
5. **Migrate the logic** to speak `view.field` only. Behaviour must be
   byte-identical: the island's existing golden passes with the SAME hashes,
   and the hook/frame verifiers show zero new divergence. If any hash
   changes, the migration is wrong — revert.
6. Regenerate the island manifest (`python c64_re/tools/gen_island_manifest.py
   <packages> -o docs/recovered_islands.md`); note the drained addresses in
   run_status (the count of raw addresses remaining in logic is a progress
   metric).

The rule that governs everything here: *the bridge keeps the old
address-shaped world alive for verification, but prevents raw addresses from
becoming the language of the recovered game.* Finish with the REPORT block.
