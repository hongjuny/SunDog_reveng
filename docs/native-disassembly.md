# Mixed-archive native 6502 disassembly

The 31 native procedures in SYSTEM.LIBRARY slots 1, 2, 3 and 5 (segments 22, 23, 24 and 26) now have bounded Ghidra 12.1.4 disassembly. Their bodies contain 1,995 instructions occupying 3,712 bytes, plus 770 bytes of supported inline tables, mutable state, pointers and alignment. The four relocation arrays per procedure occupy another 556 bytes and describe 154 relocated words. No native body byte remains unclassified. This is structural disassembly coverage; gameplay semantics and targets supplied at runtime remain separate research questions.

Machine-readable evidence is in [native-archive-disassembly.json](../analysis/native-archive-disassembly.json). Each procedure carries its archive/slot/number key, Utility disk track/sector and byte-within-sector provenance, original payload hash, body and relocation boundaries, instruction spans, references and data evidence. Original archive binaries and full assembly remain private under `analysis/regions/archives/` and `analysis/local/native-complete/`. The persisted Ghidra project is `ghidra/projects/SunDogNativeComplete`.

## Relocation format

The original native loader at `$E5C7..$E630` calls `$E3FD..$E43C` four times. These instruction ranges are visible in the retained interpreter-ready listing. A native procedure has a tag byte and a self-relative entry word immediately before it. If the tag offset is `t`, its entry is `(t-2)-word(t-2)`. The first relocation count is at `t-4`.

For a count at `c`, the preceding `N=word(c)` words are relocation cells. A cell at `r` points to the word at `r-word(r)`. The next group's count is at `c-2*(N+1)`. After four groups, the body ends immediately before their arrays. Groups add, in order:

1. The selected native data/global base. Tag+1 selects a segment-table pointer+2, or the caller global frame when zero.
2. The loaded segment base.
3. The procedure's loaded native entry address.
4. The word at `$D1AD` (the retained baseline value is `$D1AF`).

The parser checks count bounds, body/array separation, target bounds and overlapping relocation words. It does not search for a plausible terminator or infer the boundary from opcode appearance. Segment 22 procedure 9 has group counts 17/3/2/0; all 22 fixups reproduce its retained runtime body exactly. Confidence: high, supported by original loader control flow, all 31 consistent records and runtime-body comparisons.

## Address normalization and corroboration

For Ghidra, the tool creates a **derived synthetic view** with segment base `$4000`, global data base `$9000`, and kernel base `$D1AF`. These addresses are declared in every export; they are not asserted to be original runtime placements. Only the 31 validated native bodies are eligible for disassembly. Other segment bytes, relocation arrays and explicitly identified inline data are protected from speculative instruction decoding. The full 140 KB disk is never imported as a contiguous executable.

A second independent relocation application uses retained Utility menu RAM: segment 22 base `$95BE`, native data base `$ADBC`, capture `analysis/local/reference/advance-20261023-122315/advanced-main.bin`. Sixteen of eighteen native bodies match byte for byte. The two others differ only in explicit mutation sites:

- Procedure 2: installed flag `$0CDC` and saved-handler JMP operands `$0CF4/$0CF5`. The installer copies the old `$D004` p-code ADD dispatch target into those operands; the capture contains `$D71D`.
- Procedure 25: JMP operands `$0F59/$0F5A`, explicitly written by STA instructions at `$0F4B/$0F4F` from native stack arguments.

These differences are recorded, rather than ignored during comparison. Their roles follow direct writes in the assembly. The destination of procedure 25 still depends on its caller's argument.

## Code/data boundary evidence

The installed procedure 2 hook at source offset `$0CDD` is separately seeded. Its pointer at `$0CD2` is relocated data, followed by four pending-input bytes, four prior-input bytes and the installed flag. The preceding LDA immediate zero and BEQ always skip these bytes. Treating the pointer as fallthrough instructions would create false CMP/BRK decoding.

The remaining larger data spans have direct indexed-reader or mathematical evidence:

| Segment/procedure | Source offsets | Evidence |
|---|---|---|
| 22/4 | `$0D8F..$0D90` | Explicit reads, writes and increments of mutable state |
| 22/7 | `$132A..$1345` | Four seven-position HGR mask tables, exact mask formulas |
| 22/8 | `$10F0..$10FE` | Seven single-bit masks; two four-entry mode tables with index masked to 3 |
| 22/55 | `$163E..$175F` | Two twelve-entry colour-mask tables; 266 entries matching packed horizontal-coordinate formula |
| 23/2 | `$006B..$00A6` | Four exact two-bit constants after RTS, then indexed four-column transition matrix |
| 24/3 | `$0F23..$0F46` | Three twelve-entry parameter tables, with Y loop bounded at 12 |
| 24/4 | `$0FDD..$0FFD` | 33-entry waveform table; index mask and mirror transform bound reads to 0..32 |
| 26/18 | `$0A94..$0BAB` | All 280 bytes equal floor(x/7); two page-indexed helper reads |

The last ten of the 266 packed-coordinate entries are an exact contiguous table continuation. A lone eight-bit X index does not establish that those last ten entries are read. The four constants at segment 23 `$006B` have no identified reader; their mathematical identity and position after a terminating RTS are recorded without inventing a gameplay role.

Single zero alignment bytes are classified only after a Ghidra-confirmed RTS/JMP terminator or an explicitly bounded data block. Indexed 6502 absolute operands are visible in the private listing, although Ghidra does not always emit them as ordinary static memory references. Entropy is not used to infer a data type.

## Reproduction

Run from the repository root with original derived archives and retained capture available locally:

```sh
python3 -m unittest discover -s tests -p test_native_archive_disassembly.py
python3 tools/native_archive_disassembly.py --ghidra
```

The tests use synthetic relocation words and cover four group bases, backward boundaries, malformed counts, truncation and invalid/duplicate targets. The analysis command checks source and normalized hashes, runs the actual Ghidra 6502 processor, verifies the export and project save, checks every native entry (including the installed hook), and emits private assembly plus public metadata. Without `--ghidra`, it reproduces the normalized specifications and public report using existing Ghidra exports.

`tools/native_stage_disassembly.py` additionally reproduces the seven retained boot/runtime native views in the separate `SunDogNativeStages` Ghidra project and exports metadata to `analysis/native-stage-disassembly.json`. Known dispatch, mask and p-code data remain protected. Remaining unreferenced bytes retain the explicit `unreferenced_DB_untyped` classification; that name does not establish either code or semantic data. The overlapping `$D5D3` CLC entry in Language Card bank 2 is represented as an alternate instruction context, because it enters the operand of the normal `$D5D2` BIT instruction. A second alternate entry at `$D029` executes `LDY #1` inside the operand of the normal `$D028` `BIT $01A0`; the preceding normal path selects `LDY #2`. Both join at `$D02B`. Parent REA analysis independently checks both overlaps.

## Remaining uncertainty

Decoded instructions and validated relocation arrays do not prove every input-dependent destination or establish all parameter meanings. The native stack-patched jump, input hook timing, external ROM/soft-switch behavior, table callers and larger gameplay contracts still need semantic reconstruction. Untyped bytes in staged RAM views may represent data, stale overwritten code or unused memory; they are preserved without claiming otherwise. These limits do not change the complete byte accounting of the 31 native archive bodies.
