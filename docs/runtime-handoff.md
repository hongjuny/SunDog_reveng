# Native startup to the first p-code instruction — milestone 2

## Scope and confidence

This is a static reconstruction from Utility disk bytes and native 6502 data flow,
not an emulator trace. Successful disk reads and the documented initialization
branches are assumptions. Every load is mapped through the demonstrated native
sector table; Atari ST formats are not used. Reports:

- `analysis/runtime-dispatch.json`: native dispatch cells and BIOS wrappers, with disk provenance.
- `analysis/archive-inventory.json`: the bootstrap directory and dictionary descriptors.
- `analysis/boot-handoff.json`: load arithmetic and procedure pointers.
- `analysis/woz-full-checks.json`: independent complete WOZ sector decoding.

## The two synthetic returns

At `$68B6`, the initializer jumps through `$FF52` to bank 2 `$DAA9`, after pushing
`$68B8`. An ordinary native RTS therefore continues at `$68B9`. It then pushes
`$68C3`, jumps through `$FF54` to bank 2 `$D83D`, and returns at `$68C4`.
Ghidra cannot infer these stack-created return edges automatically; both
continuations are explicitly seeded in the reproducible export.
`$DAA9` manipulates 24 rows and `$D83D` reaches the native display path. Their exact
high-level API names have not been assigned.

At `$68C4` the bank 2 routine `$D00E` initializes disk-controller state, followed
by ROM/hardware checks and bank 1 selection. Some branches depend on actual
soft-switch reads, so the exact machine-specific path remains unobserved.

## Directory and first file read

The stack arguments at `$69C8–$69FF`, together with the bank 2 disk-read routine,
establish a 512-byte read of **block 79** into `$6000`. This is not the standard
Pascal directory block 2. `$6A33–$6AB8` scans 26-byte directory entries, compares
the short name against the length-prefixed `SYSTEM.PASCAL` at `$F23E`, and
extracts the matching entry's start block. The directory bytes name start block
**251**, end-exclusive **280**. The initializer reads that file's first 512-byte
block back into `$6000`.

The root directory record count is six; those records and their block mappings
are recorded in the archive inventory. The scan itself allows more records than
are present; the successful match is within the first sector. This identifies
which candidate directory the bootstrap uses, but does not establish every other
entry as a complete, ordinary filesystem file.

## Version check and 16-slot dictionary

At `$6B0F–$6B19`, the code tests `[$6103] & $E0 == $A0`. The actual byte is `$A2`.
A failed test prints the message at `$F23E`, identifying the rejected file as not
version 1.2. Thus the runtime expects the version-field value **5**, and identifies
its required SYSTEM.PASCAL generation as **1.2**. This does not prove that the
interpreter or the rest of the game is unmodified stock Apple Pascal 1.2.

At `$6B32–$6B7A`, the first 64 dictionary bytes become sixteen six-byte records
at `$BE3E`: unit word 4, absolute block word (file start + relative block), and
byte-length word. `$E46D` later computes a record offset as `segment*6`, subtracts
the byte length from `$5C/$5D`, and calls the disk-read service with that address.
The native code directly supports the dictionary's block/length interpretation.
Other header fields are cross-checked against CiderPress2's Apple Pascal codefile
parser, not assumed from the Atari port. Segment names in these headers are zero.

## Loads that replace the initializer

| Descriptor slot | Relative block | Absolute block | Bytes | Initial destination |
|---|---:|---:|---:|---|
| 15 | 8 | 259 | 170 | `$BC72–$BD1B` |
| 0 | 1 | 252 | 3124 | `$F248–$FE7B` |

The initial allocation top is the word `$BD1C` at `$F1F3`; subtracting 170 gives
`$BC72`. The initializer then explicitly sets `$5C/$5D` to `$FE7C` and loads slot 0;
subtracting 3124 gives `$F248`. The latter load overwrites the original `$F269`
copy routine and `$F290–$F78F` initializer source. This explains why the initializer
had to be copied into ordinary RAM first. Ghidra's initial common-bank view is
invalid for this interval after the load.

The final zeroing loop at `$6C28–$6C43` clears `$6000–$6C30`, preserving its own
last loop/jump instructions. The surviving jump at `$6C43` reaches `$D293`.

## Procedure directory and initial p-code address

Native `$E129–$E14F` selects a procedure by subtracting twice the procedure number
from the segment trailer pointer, then subtracts the relative word stored in that
cell. `$E18C–$E237` uses an attribute area eight bytes before the resulting
procedure trailer; the entry address is `(attributes+6) - word(attributes+6)`.

Applying those operations gives 39 consistent numbered procedure records in
SYSTEM.PASCAL segment 0. Procedure 1 resolves to **`$F248`**. Procedure 38 resolves
outside that segment, to the separately loaded helper's trailer at `$BD1A` and
entry at **`$BC72`**. This cross-region pointer agrees with the independently
derived helper load address; it is not discarded as an invalid in-file offset.
The helper's header machine-type field is unspecified, so it must not be called
6502 code merely because it was loaded by a native routine.

The first byte fetched at `$F248` is `$9F`, whose actual native table entry is
`$D2D7`. That handler pushes a zero word and advances the p-code pointer by one.
This is a measured byte/native-handler relationship, not a borrowed opcode name.

## Interpreter and BIOS boundary

Bank 1 `$D293` fetches through zero-page `$58/$59`. Bytes `$00–$7F` take the path
at `$D288`, pushing a zero high byte and the fetched low byte with native PHA
instructions, then advancing the pointer by one. Bytes `$80–$FF` are doubled;
the low-byte result patches `$D29E`, the operand of `JMP ($D000)` at `$D29D`.
There are 128 directly indexed handler words at `$D000–$D0FF`.

Opcode `$9E` selects `$E67F`, which reads the following byte and patches the operand
at `$E688` to dispatch through `$D100`. There are 41 word-shaped cells before
executable `$D152`; zero cells exist and the valid selector range is not proven.
Self-modifying dispatch means a fixed indirect edge in Ghidra is incomplete.

The 21 validated service wrappers `$FF00–$FF3C` call `$FF9E`. That routine adds
`$5A` to its own saved return address, switches to bank 2, and jumps through the
computed pointer. This reaches three-byte JMP trampolines beginning at `$FF5C`.
It preserves the caller's native return address in `$BF1A/$BF1B`, then restores
bank 1 on return. Example: `$FF12 → $FF6E → bank 2 $D029` is the disk-read path.
The apparent wrapper at `$FF3F` does not have the same validated JMP target shape
and is deliberately excluded.

Bank 2 has overlapping entry streams: `$D026` starts `LDY #2` followed by a BIT
instruction that consumes the bytes of `LDY #1` at `$D029`. The latter is the read
entry; the former selects the alternate operation. Separate Ghidra programs
preserve the two decoding contexts instead of forcing one linear interpretation.

## Remaining boundaries

No full p-code instruction disassembler is implemented. The fetch mechanism and
initial dictionary/procedure structure are supported, but operand encodings,
control-flow rules, native procedures and later segment loading still need checks.
The next step is to follow the initial Pascal procedures into SYSTEM.STARTUP and
library loading, using the actual Apple II handler semantics and banked memory
state. A controlled emulator trace remains necessary to observe the hardware path.
