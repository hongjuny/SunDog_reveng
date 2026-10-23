# Pascal runtime — milestone 2

## Established native evidence

The bank 1 interpreter fetches p-code at `$D293` through `$58/$59`. Its primary
128-word dispatch table is at `$D000–$D0FF`, and opcode `$9E` uses a secondary
selector table beginning at `$D100`. Dispatch patches native JMP operands, so
ordinary static references do not enumerate the actual runtime edges.
`analysis/runtime-dispatch.json` records all primary cells, 41 secondary cells
(including unknown zero cells), source sectors and 21 native service wrappers.
This is an address catalogue, not a full p-code disassembler.

The bootstrap reads a custom directory at **block 79**, finds SYSTEM.PASCAL at
**blocks 251–279**, reads its dictionary, and loads the initial segments. Native
load arithmetic and procedure metadata put the first p-code fetch at **`$F248`**.
All 39 numbered procedure records resolve consistently, including procedure 38
in a separate helper at `$BC72`. See [runtime handoff](runtime-handoff.md).

The version test requires `$6103 & $E0 == $A0`; the actual byte is `$A2`. The
failure string names version **1.2**. This supports an Apple Pascal 1.2-family
requirement with version bits 5. Exact stock interpreter identity, compiler
lineage, and game-specific opcode modifications still require comparison.
An unchanged stock p-system has not been established.

## Directory and archive inventory

Four directory-shaped groups were found at DOS image offsets `$9100`, `$A000`,
`$AB00`, and `$AD00`. Native initialization now supports the first one (`$9100`,
Utility T9/DOS1, first half of block 79) as the bootstrap directory. The other
three remain candidates; they have different name/kind assignments and may be
historical copies, templates or application data.

The supported directory contains these extents (end exclusive):

| Name | Blocks | Directory kind | Dictionary investigation |
|---|---|---:|---|
| SYSTEM.DATA | 3–85 | 5 | not parsed as a code dictionary |
| SUNDOG.LIBRARY | 85–103 | 2 | one populated descriptor, segment number 1 |
| SYSTEM.LIBRARY | 103–140 | 5 | seven stored descriptors, three allocation-only descriptors |
| SYSTEM.STARTUP | 140–219 | 2 | thirteen populated descriptors; four exceed this directory extent |
| SYSTEM.APPLE | 219–251 | 5 | native boot loads cover this exact range |
| SYSTEM.PASCAL | 251–280 | 2 | eight populated descriptors; initial loads directly supported by bootstrap |

`analysis/archive-inventory.json` provides descriptors, byte lengths, hashes,
sector provenance and cross-disk comparisons. Names in the dictionary's segment
name fields are all zero; meaningful module names have not been recovered.

The descriptor interpretation comes from `$6B32–$6B7A` and `$E46D`, with additional
header fields compared to the local CiderPress2 `ApplePascal_Code.cs` implementation.
That implementation identifies machine type 2 as little-endian p-code and type 7
as 6502. It is an independent comparison, not proof that every later file in this
modified game follows an unmodified Apple format.

SYSTEM.LIBRARY's entire 37-block extent is identical on both disks. Its seven
stored descriptors carry segment numbers 22–28: 22, 23, 24 and 26 have type 7;
25, 27 and 28 have type 2. Segment numbers 29–31 have zero disk address, kind 7
and nonzero length, consistent with allocation-only data segments. They are not
exported by treating block zero as their payload.

SYSTEM.STARTUP is a useful failed straightforward interpretation: descriptors
for segment numbers 18–21 extend beyond its directory extent. They are recorded
as conflicts and are not exported as validated payloads. Even the in-range
payloads are only candidates: this Utility range overlaps independently verified
boot graphics/native data, and the Play-side execution layout may differ. The
complete codefile cannot yet be reconstructed by blindly slicing its directory
extent. Four rejected descriptors and the alternative disk contents need analysis.

Raw extracted payloads remain local under `analysis/regions/archives/`; only
structural metadata and hashes are versioned. No bytecode instruction parser
assumes Atari ST p-system IV encodings.

## Next questions

Follow the first p-code procedures into game startup and library loading. Validate
individual handler semantics and operand sizes from the Apple II native code.
Resolve SYSTEM.STARTUP's out-of-extent descriptors and identify when the Play disk
is selected. Then reconstruct procedure calls, segment relocation, and stack/heap
management beyond the initial native handoff. Observe the boot in a controlled
emulator before describing hardware-specific branches as executed facts.

## Milestone 3: selected handler semantics

[Selected opcode semantics](opcode-semantics.md) now records the Apple II native
basis for arithmetic/bitwise operations, short constants, local/global/nonlocal
addressing, literal words, inline pointers and the variable-width scaled index.
4,976 native-model probes exercise 110 ordinary high opcode values, 18 shared error
slots, and all 128 short-immediate values. No high primary entry remains unidentified; dispatcher/error/service boundaries
remain explicitly distinct from complete runtime verification. Aliases depend on the opcode-derived A/Carry/Y state; pointer equality
alone is insufficient. Full p-code disassembly and complete interpreter emulation
are still deferred. The startup prefix now reaches BIOS FF06 in controlled
synthetic replay, stopping before its bank switch/device behavior.

Actual REA/Ghidra native analysis now confirms all 48 formerly unidentified handlers for
conditional/unconditional branching, table-based load/store/address, indirect
word store, indexed bytes, multiplication, squaring, signed comparisons, pointer
offsets and forward word copies. Seventy bounded imports cross-check 1,656
native instructions. The branch operand's high-bit form selects
a self-relative word through 54/55; it is not a negative PC-relative displacement.
Synthetic replay and native static Evidence remain separate authorities.

The [completion report](primary-opcode-completion.md) documents typed comparisons,
packed layouts, call/return frames and the data-derived native return trampoline.
The generated [primary reference](opcode-reference.md) lists every high opcode.
This does not establish exact stock Apple Pascal compatibility or complete service
semantics for the modified runtime.

## Restart correction: mixed procedures and Play application payloads

`machine_type=7` does not classify every procedure in a segment as native.
Native call resolution at E14F branches on the procedure tag: zero selects the
native self-relative entry, nonzero selects Pascal frame setup. Segment 22 has
45 p-code and 18 native procedures. The bounded static decoder in
`tools/pcode_analysis.py` uses those per-procedure tags and verified Apple II
operand rules, stopping at unsupported service boundaries.

The block-140 SYSTEM.STARTUP dictionaries are identical on both sides. All 13
payloads selected by those descriptors validate on Play, including the four
previously rejected against the Utility directory extent. Their 327 procedure
records and segment ordinals agree; the final storage block is 272 exclusive.
Every participating Play sector is checked against the independent WOZ decode
inventory. Runtime disk-selection behavior still needs verification. See
`analysis/play-startup-inventory.json` and [game-code analysis](game-code-analysis.md).


## Selected secondary services and an actual dispatch modification

Five selected 9E interfaces now have explicit normal-return lengths and native
memory/stack checks: segment acquisition/release (15/16), allocation-cursor
save/restore (20/21), and I/O-result read (22), using hexadecimal selector notation.
Seventy-two controlled cases and actual REA IDs are in `analysis/secondary-services.json`.
Nonresident loading remains a boundary. See [startup control flow](game-startup-flow.md).

The initial D004 ADD16 dispatch cell is not invariant across runtime states.
Library-native input P2 installs a pending-input latch hook there, chaining back
to the original D71D handler. The retained Utility-menu LC1 points to that hook.
[Input analysis](input-system.md) records the self-modified JMP operand and exact
probe/capture limits. The primary opcode catalogue describes the initial snapshot,
not every later patched dispatcher state.
