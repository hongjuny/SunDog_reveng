# Selected Apple II p-code semantics — milestone 3

## Evidence and scope

The initial interpreter-ready snapshot supplies the actual native handler bytes.
Ghidra disassembly establishes instruction boundaries and control flow.
`tools/native_probe.py` then interprets a deliberately limited set of native 6502
instructions on declared synthetic memory/stack inputs. It is not an Apple II
emulator, a hardware observation, or REA Evidence. Decimal mode, V-flag branches,
interrupts, devices, timing and unknown-memory behavior are not modeled.
Unsupported native instructions and instruction-budget overruns fail explicitly.

`python3 tools/opcode_evidence.py` reproduces **908** checked cases. These cover
all 128 short-immediate opcode values, selected semantics for **62 ordinary high
opcodes**, and the initial shared error path of **18 high opcodes**. The remaining
**48 high opcodes** are explicitly unresolved. Counts include alias families, not
80 distinct algorithms. No complete p-code disassembler is implemented.

`analysis/opcode-evidence.json` includes each high opcode's handler, original
Utility source location, operand rule, stack-word delta, continuation, and native
instruction addresses visited by the probes. All **407 distinct visited native
addresses** are defined instructions in Ghidra's interpreter-ready listing.
This cross-check validates alignment and provenance; it is not independent proof
that the limited CPU model implements all 6502 behavior.

## Dispatch entry state matters

For every high opcode, `$D299` executes ASL before the indirect jump. Handler
entry has `A=(opcode*2)&$FF`, `Carry=1`, and `Y=0`. STA and JMP preserve those
values. Several shared handlers depend on A and Carry. Consequently, equal
handler pointers do not establish identical opcode semantics. Calling them as
ordinary independent C functions in a decompiler loses this implicit interface.

Examples:

- `$D8–$E7` share `$D2EA`, whose first operation is `SBC #$A3`. This yields high
  byte offsets 13,15,...,43; the subsequent low byte is at offset one less.
- `$E8–$F7` share `$D359`, beginning `SBC #$C3`, with the same offsets in another frame.
- `$F9–$FF` share `$D4A8`, beginning `SBC #$F0`; `$F8` enters at `$D4AB` with Y=0.

The probe starts at the real fetch loop, not directly at the handlers, preserving
these conditions and exercising the self-modified JMP operand. Frame bases and
stack values are synthetic; no claim is made about the actual boot frame values.

## Established selected operations

The names below describe observed operations; they are not imported Atari or
stock UCSD mnemonic assignments. Words and arithmetic results are 16-bit.

| Opcode | Observed operation | Operand bytes after opcode | Stack words |
|---|---|---|---:|
| `$00–$7F` | push opcode value with zero high byte | none | +1 |
| `$80` | two's-complement absolute value | none | 0 |
| `$82` | add lower and top words, modulo 65536 | none | −1 |
| `$84`, `$8D` | bitwise AND, OR | none | −1 |
| `$91`, `$93` | two's-complement negate, bitwise NOT | none | 0 |
| `$95` | lower word minus top word, modulo 65536 | none | −1 |
| `$9F` | push zero word | none | +1 |
| `$C7` | push literal word | little-endian u16 | +1 |
| `$D2`, `$D7` | advance only; leave stack unchanged | none | 0 |
| `$D8–$E7` | load at `[$52/$53] + 12 + 2*(opcode−D8)` | none | +1 |
| `$E8–$F7` | load at `[$50/$51] + 12 + 2*(opcode−E8)` | none | +1 |
| `$F8–$FF` | replace pointer by word at `pointer + 2*(opcode−F8)` | none | 0 |
| `$CA`, `$A9` | load local/global word at frame + 10 + 2*index | encoded index | +1 |
| `$CC`, `$AB` | store popped word at local/global frame + 10 + 2*index | encoded index | −1 |
| `$C6`, `$A5` | push local/global address at frame + 10 + 2*index | encoded index | +1 |
| `$B6`, `$B2`, `$B8` | nonlocal load/address/store after following frame links | u8 depth, encoded index | +1/+1/−1 |
| `$A6` | push address of length byte, skip inline payload | u8 length, payload | +1 |
| `$D0` | push address after length byte, skip inline payload | u8 length, payload | +1 |

Local and global here identify the observed bases `$52/$53` and `$50/$51`.
`$D171` follows static links at frame offset zero for the nonlocal operations.
These are address/data-flow descriptions, not a complete activation-record model.
For raw native arithmetic, absolute/negate of `$8000` retains `$8000`; no overflow
trap is encountered in those handler paths. Source-language legality is separate.

## The scaled index is not a little-endian word

`$D155–$D170` implements an index operand:

- First byte below `$80`: `index=first`, one byte.
- First byte at least `$80`: `index=((first&$7F)<<8)|second`, two bytes.

The helper returns `2*index` in `$68/$69`. The long form increments `$58/$59` by
one extra byte; the caller's normal continuation consumes the remaining fixed
width. For example `$80 $80` encodes 128, `$81 $00` encodes 256, and `$FF $FF`
encodes 32767. A non-minimal two-byte encoding of a small index is accepted by
these native paths. This differs from `$C7`'s little-endian literal word.

The probes include zero, one-byte limit, long-form limits, non-minimal form,
16-bit address wrap, and a p-code pointer starting at `$40FF` to exercise page
carry. Boundary inputs test raw address calculation, not valid Pascal variables
or allocated frame bounds.

## Shared error path

In this snapshot, these 18 slots dispatch to `$D1EF`:

`81 83 85 87 89 8A 8B 8C 90 92 94 96 97 99 9C A0 D3 D4`.

The tested prefix loads 11, adds 100, and stores **111** at `$BDDE/$BDDF`.
Replay stops at `$D20A`, before the exception/procedure-call machinery. This does
not establish a full error implementation or that these slots are invalid in
all Apple Pascal variants or all later runtime states. No stock-opcode names
or presumed floating-point meanings are assigned to them.

## Initial Pascal prefix and next boundary

`tools/probe_startup_prefix.py` uses original segment 0 bytes at `$F248`, with an
explicitly synthetic local frame, global frame and native stack. It reproduces:

| P-code address | Selected effect | Next address |
|---|---|---|
| `$F248` | `$9F`: push zero | `$F249` |
| `$F249` | `$CC` index 5: store zero at local frame + 20 | `$F24B` |
| `$F24B` | `$01`: push one | `$F24C` |

The next `$9E` selector `$26` reaches native `$EF7D` with top word 1. Under the
initial unit-mapping table, this path clears `$A1/$A2`, pushes words `$D1E3` and
`$BDDE`, and reaches **BIOS wrapper `$FF06`**. Replay stops before executing that
wrapper. Its independently mapped trampoline reaches **bank 2 `$D7EF`**; that bank
switch and device path are not simulated. `$D7EF`'s static disassembly stores
`$BDDE` in `$F8/$F9` and `$D1E3` in `$BF16/$BF17`; actual device behavior
and subsequent Pascal execution still need observation or further scoped analysis.
`analysis/startup-prefix-probe.json` preserves the boundary and assumptions.

## Persistent Ghidra annotations

`AnnotateOpcodes.java` writes snapshot-specific labels/comments at 26 native entry
addresses and explains the implicit A/Carry/Y interface. Comment readback and
alias membership are checked and exported to `analysis/ghidra-opcode-annotations.json`.
The project save is checked by the wrapper. No copied game disassembly is committed;
full exports remain under ignored `ghidra/exports/`.

Run the focused analysis after the base regions/seeds exist:

```sh
sh tools/run_opcode_analysis.sh
```

The full `tools/run_ghidra.sh` pipeline includes this step. REA's connection remains
pending; these results must not be substituted for the missing REA cross-check.

For the **unexecuted normal-return case** through `$F008 → $D27B`, the next
p-code address would be `$F24E`. Original bytes there select opcode `$CD`, whose
native `$E306` reads segment slot 4 and procedure 1. The dictionary maps slot 4
to absolute block 264, 1998 bytes. All ten of that payload's procedure records
resolve in-file; procedure 1's entry offset is `$060A` (Utility T33, DOS sector 9,
byte 10). This is a conditional static follow-up target, not a call observed in
replay. Its actual RAM load address depends on allocation state and is unresolved.
The full `$CD` call semantics remain in the unresolved high-opcode count.
