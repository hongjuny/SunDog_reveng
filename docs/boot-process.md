# Boot-chain reconstruction — milestone 1

The later [ROM-to-title investigation](boot-to-splash.md) binds this path to the
actual retained slot6 ROM and original startup RAM, checks the header reentry,
clear loop and JSR/RTS stack, and links the complete [title reveal](splash-reveal.md).

All game bytes below originate on Utility. Confidence is high for decoded static
control flow and source mapping; actual hardware execution remains unobserved.
`analysis/boot-mapping.json` and `analysis/boot-regions.json` give exact disk offsets,
DOS and physical sectors, destination addresses, lengths and region hashes.

## ROM-assisted stage

The standard 16-sector Disk II ROM loads physical T0/S0 at `$0800`, compares its
incremented sector number with byte `$0800`, and transfers control to `$0801`.
The supplied header is `$01`, a sector-count threshold, not an executable opcode
or an address. This conclusion depends on the matching ROM; the original ROM
hardware has not been identified or supplied.

At `$0801`, `CPX #$60` requires slot 6. The failure path at `$08B3` displays the
slot error message and loops. At `$0808–$0818`, the loader raises the header by
two, increments zero-page `$3D`, and jumps back into ROM `$C65C`. With standard ROM
post-read increments, this skips physical sector 1, loads physical 2 at `$0900`,
skips physical 3, and loads physical 4 at `$0A00`. The header becomes `$03`, then
`$05`; the bootstrap then takes `$0819`. Corresponding DOS slots are 0, 14, 13,
with image offsets `$0000`, `$0E00`, `$0D00`. The continuation across `$08FF–$0900`
decodes coherently; CiderPress2 WOZ spot-checks independently match these bytes.

## Native disk loader

`$08FF` is the entry to a disk loader, not a Pascal procedure. Static data flow:

| Parameter | Meaning | Evidence |
|---|---|---|
| A : `$0F` | high : low starting 512-byte block number | `$08FF–$090E` computes block / 8 into track `$F0` |
| `$02` | number of 256-byte pages | `$0917–$091D` decrements once per successful read |
| `$3F` | destination page; low `$3E` cleared | `$0910–$0912`, `$091D` |
| `$00` | sector position within track | low three block bits doubled, advanced per page |
| `$F1` | physical sector sought | table lookup `$092B–$0930` |

The on-disk table at runtime `$093E` is
`0,2,4,6,8,10,12,14,1,3,5,7,9,11,13,15`. It must be composed with the DOS image
mapping; disk-image adjacency is not runtime adjacency. `$094E` reads a sector,
`$097A` reconstructs 6-and-2 bytes, `$0992` finds/reads a data field, `$09FA` reads
an address field, and `$0A56` is the track-seek path. These are game-disk-resident
native routines, with algorithms resembling firmware; authorship or exact
p-system lineage is unproved. The initial `$C65C` operation belongs to slot ROM.

## Staged loads and Language Card

| Call site | Blocks (end exclusive) | Pages | Destination |
|---|---|---:|---|
| `$0861` | 201–219 | 36 | `$4000–$63FF` |
| `$087B` | 219–243 | 48 | bank 2 `$D000–$DFFF`, common `$E000–$FFFF` |
| `$0894` | 243–251 | 16 | bank 1 `$D000–$DFFF` |

At `$0819` the bootstrap checks a possible resident signature at `$4000` against
its error-message bytes. A complete match can skip the first load and `$4000`
call. Otherwise `$082E–$0840` can clear `$2000–$3FFF`, graphics switches are read,
and the first region is loaded and called at `$0864`. Not every branch has been
observed dynamically. `$4000` contains native code; its row-address helper `$4200`
is confirmed against all 192 HGR page 1 rows (see graphics documentation).

Two reads of `$C081` enable writes with ROM reads and bank 2 selected. `$C089`
selects bank 1 while retaining write access; the second load fills that bank.
`$C080` selects bank 2 RAM reads and disables writes. The indirect jump at `$089A`
uses the now-loaded `$FFF8` vector, whose value is **`$FEF2`**.
At `$FEF2`, a read of `$C08B` selects bank 1 RAM, followed by `JMP $D152`.
Therefore following `$D152` against bank 2 bytes is incorrect. The first exploratory
bank 2 analysis exposed this trap; `runtime-bank1.bin` supplies the post-switch
view (bank 1 low 4KB plus shared upper 8KB). Further bank switching inside native
runtime code still requires stateful analysis.

Ghidra project `SunDog` and exports are local-only under `ghidra/projects/` and
`ghidra/exports/`. The wrapper imports bounded staged RAM regions, never a complete
disk as a flat executable. Function maps and references are static Ghidra output;
auto-analysis can find spurious instructions in data. Annotations and source maps
are reproducible from the scripts. ROM destinations are intentionally unmapped.

## Relocated initializer

In the bank 1 view, `$D152` jumps to `$F269`. The latter reads the pointer at
`$F267–$F268` (`$F290`), copies exactly five 256-byte pages to `$6800–$6CFF`, and
jumps to `$6800`. These source bytes are in the common upper bank, initially
loaded from Utility; `analysis/relocation.json` records their hash and source span.
`relocated-6800.bin` is imported at its execution address, not its disk/load address.

The relocated code begins with `CLD`, `SEI`, then a zeroing loop covering
`$0000–$1FFF` on the straight-line path. Thus the earlier boot loader and zero-page
parameters do not remain live unchanged. It calls common-bank `$F69A` while
scanning slot pages, sets graphics switches, reads `$C083` (selecting bank 2),
loads a synthetic return address from `$F35C–$F35D`, then jumps through `$FF52`.
The loaded vector there is `$DAA9`; it must be interpreted in bank 2. The final
bank 2 export is seeded at `$DAA9`, not at the earlier bank 1 path.
This traces static startup into native runtime initialization. The behavior of
its external calls, further disk loading, and eventual interpreter handoff still
need analysis and an observed boot trace.

The synthetic return address is `$68B8`, so an ordinary native `RTS` would
continue at `$68B9`. Ghidra does not infer this edge through the indirect jump;
that continuation and its bank state need an explicit follow-up analysis.

## Milestone 2 continuation

The continuation at `$68B9` and its second synthetic return at `$68C4` have now
been traced. The native initializer reads directory block 79, finds SYSTEM.PASCAL,
builds its segment table, loads a 170-byte helper at `$BC72` and a 3124-byte segment
at `$F248`, then jumps to the interpreter's fetch loop at `$D293`. The latter load
overwrites the original common-bank initializer, invalidating the earlier native
memory view. Detailed source mapping, version checks, procedure pointer arithmetic
and remaining branch assumptions are in [runtime handoff](runtime-handoff.md).
