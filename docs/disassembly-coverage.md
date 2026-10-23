# Disassembly coverage audit

This audit defines completion as structural disassembly of every format-defined archive procedure and every recovered native boot/runtime execution path. It does not claim complete gameplay semantics, all dynamically reachable targets, or a macOS port. Run `python3 tools/disassembly_coverage.py`, after regenerating the local p-code inventory and native Ghidra exports. The machine-readable result is `analysis/disassembly-coverage.json`; its `full_disassembly_accepted` field is the authoritative current acceptance result.

The combined refresh command is `python3 tools/disassemble_all.py`. It verifies the saved REA service-format evidence, regenerates p-code listings, runs the independent audit, and writes `analysis/disassembly-index.json` only on acceptance. The index identifies 39 private listing files (28 archive p-code views, four normalized native archive views and seven boot/runtime views) by path and SHA-256. It consumes the persisted native Ghidra exports; rebuild them with the commands in [native-disassembly.md](native-disassembly.md) when source inputs change. Actual alternate-entry REA records and generated reset-code evidence are also required by the audit. This command does not replace missing original media or establish new REA evidence automatically.

## Archive procedures

The independent byte audit covers 559 p-code procedures, 49,384 decoded p-code instructions, and 31 native procedures containing 1,995 native instructions. No identified procedure envelope has an unclassified byte, conflicting instruction/data ownership, or unresolved decoder boundary. Native bodies contain 3,712 instruction bytes and 770 evidence-supported inline-data bytes; the four relocation groups occupy another 556 bytes. Each source payload SHA-256 is checked before combining reports.

P-code encoding, literal payload, case tables, ignored alignment operands, backward branch cells, attributes, procedure tags, directory cells and segment trailer bytes have separate roles. Shared branch-cell/attribute words are permitted; instruction overlap with those structures is rejected. The 275 inferred separator bytes are each a single zero at an odd address, immediately before an even metadata or branch-pool word, with no control-flow target and no preceding fallthrough. They are an alignment-supported inference, not an entropy classification. Thirteen compiler jump instructions absent from entry reachability are retained as explicitly unreferenced instructions, with their existing branch targets and adjacent decoded boundaries checked.

The separate 170-byte SYSTEM.PASCAL slot 15 helper is already owned by segment 0 procedure 38 through its external code address. It is not counted as another native procedure. Machine type alone would have misclassified it.

## Native boot and runtime views

Seven source-identified memory contexts are independently checked against Ghidra exports. Their instruction starts are 301 (boot), 270 (initial $4000 image), 1,412 (Language Card bank 2), 3,369 (runtime bank 1), 499 (relocated $6800 image), 3,350 (interpreter-ready bank), and 93 (Play bootstrap). These are overlapping memory snapshots and banks; adding their bytes would not measure unique original disk code.

Every snapshot byte is classified as an instruction, defined data, or explicit unreferenced DB with unknown role. The audit checks an exact nonoverlapping partition, instruction lengths against independently extracted NMOS 6502 addressing-mode facts, recovered entry seeds, and direct transfers inside each context. Unsupported DB ranges are preserved as unknown-role bytes, never silently certified as data. Computed transfers and transfers outside a particular view are recorded with their addresses and context limitations; they are distinct from an undecoded identified instruction.

Two alternate-entry contexts require separate disassembly: at $D5D2, canonical `BIT` consumes the byte at $D5D3, while the conditional branch into $D5D3 executes `CLC` and rejoins at $D5D4 (`PLA`). At $D028, canonical absolute `BIT` consumes $D029–$D02A, while entry $D029 executes `LDY #1` and rejoins at $D02B. The ordinary entry $D026 executes `LDY #2`. Alternate imports must match exact source bytes and independently saved REA evidence; the audit refuses acceptance until both are verified.

Primary opcode $D6 additionally creates a six-byte native reset stub at $0000. A bounded native handler probe verifies its constant writes: a soft-switch read at $C08A followed by an indirect jump through $FFFC. The probe stops before MMIO or ROM execution. Generated code is therefore accounted separately from on-disk snapshots.

## Evidence and reproduction limits

The report links every procedure to its archive, disk side, slot, source digest and memory addresses. Archive inventory metadata supplies source track/sector provenance. Native reports retain relocation and inline-data evidence, while private Ghidra listings and REA records retain instruction details. Unknown Play track 34 remains unreadable; this audit cannot reconstruct absent original bytes and does not treat them as valid zero data. No complete semantic interpretation of all asset bytes is asserted.

Public audit artifacts contain hashes, addresses, lengths and classifications. Original disks, extracted payloads, detailed instruction operands and complete disassembly listings stay local under ignore rules. The analysis tools reproduce those private outputs from supplied media. This distinction should be checked again before publishing generated files.

Deterministic tests: `python3 -m unittest discover -s tests -p test_disassembly_coverage.py`. They exercise alignment rejection, instruction/branch-pool conflicts, inline/case-table ownership, permitted metadata aliasing and range normalization.
