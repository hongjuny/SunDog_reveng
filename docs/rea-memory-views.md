# REA/Ghidra bounded memory comparison

Checkpoint 2 passed its bounded static acceptance on 2026-10-23. Six actual REA
imports with Ghidra 12.1.4 returned 7,825 complete memory bytes; each import passed
23 independent source/mapping checks. All bytes agree with disk-derived snapshots.
This verifies representation of selected states, not an executed boot or hardware
bank switching. The two analysis routes share Ghidra's decoder.

| View | Address, inclusive | Size | Result |
|---|---|---:|---|
| Bank 1 entry before segment load | D152–D154 | 3 | JMP F269 |
| Bank 2 entry | D152–D154 | 3 | JSR D26B |
| Common memory before load | F1CA–FE7B | 3250 | Complete bytes match native boot snapshot |
| Common memory after load | F1CA–FE7B | 3250 | Complete bytes match interpreter-ready snapshot |
| Native copy routine | F269–F28F | 39 | Five-page copy loop, then JMP 6800 |
| Relocated initializer | 6800–6CFF | 1280 | Matches original common-memory F290–F78F |

Every exported byte is checked against readable Utility sectors. The versioned
`analysis/rea-memory-inputs.json` records each sector, physical sector, DOS image
offset, source snapshot hash and destination memory address. For example, bank 1
D152 is Utility T30/DOS8 byte82 (image offset125010); bank 2 D152 is T27/DOS8
byte82 (112722). The copy routine starts T29/DOS7 byte105 (120681), and the
relocated payload starts at byte144 of that sector (120720).

`analysis/rea-memory-crosscheck.json` links the actual Evidence IDs for load
verification, byte reads, instruction observations and native assembly. Complete
Evidence and six saved snapshots are local-only under `analysis/local/rea/memory/`.
All sessions were closed after saving. Binary slices are ignored under
`analysis/regions/`.

## Overlay and relocation

The two common-memory reads have an identical prefix F1CA–F247. In the after-load
view, F248–FE7B equals the complete 3,124-byte SYSTEM.PASCAL slot 0 payload. There
are 2,818 changed byte values, which must not be confused with the copy length.
The pre-load pointer at F267/F268 is F290. Its 1,280-byte source matches the
relocated initializer at 6800; actual REA assembly confirms the copy routine's
five-page loop and terminal jump. Confidence is high for source equality and
static control flow; successful disk I/O and observed execution remain unverified.

The native code previously at F269/F290 belongs to the before-load view. It must
not be retained as native code after the p-code overlay. The relocated initializer
is a separate earlier snapshot; its later self-clearing state is not represented
by the original 1,280-byte export.

## Preventing a false native entry

REA's raw import couples file offset zero, load address and entry seed. Opening
the full interpreter image at D000 would seed execution in a dispatch data table.
Opening p-code at F248 would seed it as 6502 code. Neither operation was used.

Both common-memory probes instead start at the existing F1CA RTS boundary, which
is confirmed in the direct Ghidra listing and actual REA instruction observation.
This is a deliberately selected static analysis seed, not a reconstructed boot
entry. No bytes were patched or prepended. In the after-load probe REA reports
one procedure and no defined native instruction at F248 (`undecodable`). That
status describes this listing, not the validity or semantics of Pascal bytecode.
Only this entry address was directly queried for instruction classification.

Full-range data typing is retained and freshly verified in the persistent direct
Ghidra Program: D000 is word[128], D100 is word[41], and F248 is byte[3124], with
zero native instructions in those ranges. REA does not import those annotations.
Its language-defined ZERO_PAGE and STACK remain uninitialized, with no byte
digest; neither is an observed zero-filled runtime state. The bounded low-bank
REA probes cover only D152–D154; full low-bank composition is checked separately
by `tools/verify_memory_views.py`.

## Reproduction

After generating the original boot/archive snapshots:

```sh
python3 tools/rea_memory_views.py
sh tools/run_opcode_analysis.sh
```

For each manifest view, use actual REA `open_binary` with provider ghidra, format
raw-binary, architecture 6502, and the stated base/entry. Retain
`inspect_native_load_image`, a complete `read_bytes` for the stated length, and
`inspect_native_instruction` at the entry as load.json, bytes.json and entry.json
under `analysis/local/rea/memory/<view>/`. Also retain the common-after F248
instruction observation as pcode-start.json and native procedure assembly for
copy-routine and relocated-init as assembly.json. Save a snapshot and close each
session before opening the next view.

```sh
python3 tools/rea_memory_views.py --verify analysis/local/rea/memory
python3 -m unittest discover -s tests -v
```

The validator rejects wrong target identities, operations, addresses, incomplete
reads, byte mismatches and failed mappings. Five deterministic tests use explicit
synthetic fixtures; those fixtures are never retained as actual REA Evidence.

Next is checkpoint 3: extend the Apple II native-handler evidence for unresolved
opcodes and their operand/stack effects, before implementing any broader p-code
disassembler. BIOS/device execution, runtime allocation addresses and conflicting
SYSTEM.STARTUP descriptors remain separate open questions.
