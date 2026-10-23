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
908 native-model probes exercise 62 ordinary high opcode values, 18 shared error
slots, and all 128 short-immediate values. Forty-eight high opcode values remain
unresolved. Aliases depend on the opcode-derived A/Carry/Y state; pointer equality
alone is insufficient. Full p-code disassembly and complete interpreter emulation
are still deferred. The startup prefix now reaches BIOS FF06 in controlled
synthetic replay, stopping before its bank switch/device behavior.
