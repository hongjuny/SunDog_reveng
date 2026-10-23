# Selected Apple II p-code semantics — milestone 3

## Evidence and scope

The initial interpreter-ready snapshot supplies the actual native handler bytes.
Ghidra disassembly establishes instruction boundaries and control flow.
`tools/native_probe.py` then interprets a deliberately limited set of native 6502
instructions on declared synthetic memory/stack inputs. It is not an Apple II
emulator, a hardware observation, or REA Evidence. Decimal mode, V-flag branches,
interrupts, devices, timing and unknown-memory behavior are not modeled.
Unsupported native instructions and instruction-budget overruns fail explicitly.

`python3 tools/opcode_evidence.py` reproduces **4,976** checked cases. These cover
all 128 short-immediate opcode values, selected semantics for **110 ordinary high
opcodes**, and the initial shared error path of **18 high opcodes**.
**No high primary entry remains unidentified.** Coverage includes explicit dispatcher,
error and external-service boundaries; it is not exhaustive runtime verification.
Counts include alias families, not 128 distinct algorithms. No complete p-code disassembler is implemented.

`analysis/opcode-evidence.json` includes each high opcode's handler, original
Utility source location, operand rule, stack-word delta, continuation, and native
instruction addresses visited by the probes. All **2,049 distinct visited native
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
| `$8F` | replace two words by low 16 bits of their product | none | −1 |
| `$98` | replace top word by low 16 bits of its square | none | 0 |
| `$9A` | pop value and pointer; store word at pointer | none | −2 |
| `$BE` | pop index and base; push zero-extended byte at base + index | none | −1 |
| `$BF` | pop value, index, base; store low byte at base + index | none | −3 |
| `$9D`, `$D1`, `$A7` | load/store/address at word(BD9E + 2*(selector & 7F)) + 2*index | u8 selector, encoded index | +1/−1/+1 |
| `$B9` | unconditional branch using rule below | u8 branch operand | 0 |
| `$A1` | pop condition; branch when bit 0 is clear | u8 branch operand | −1 |
| `$C3`, `$CB` | full-word equal, not equal; canonical boolean result | none | −1 |
| `$C9`, `$C5`, `$C8`, `$C4` | signed less, greater, less-or-equal, greater-or-equal | none | −1 |
| `$A2` | replace pointer by pointer + 2*index | encoded index | 0 |
| `$A3` | replace pointer by word at pointer + 2*index | encoded index | 0 |
| `$A4` | pop index and base, push base + 2*stride*index | encoded word stride | −1 |
| `$A8` | pop source and destination; copy 2*count bytes forward | encoded word count | −2 |

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

## First ten additions: actual REA and controlled replay

On 2026-10-23, actual REA/Ghidra 12.1.4 inspected ten previously unresolved
handlers and the multiply helper. Eleven native-only slices comprise 357 bytes;
each passed 23 load-image checks, a complete byte read and an entry instruction
check. All 200 bounded native instructions agree with the persistent direct
Ghidra listing. Sources are readable Utility Track 30 sectors, not inferred
Atari/ST opcode assignments. `analysis/rea-opcode-inputs.json` provides the exact
DOS sectors, byte offsets, memory addresses and hashes;
`analysis/rea-opcode-crosscheck.json` links actual Evidence IDs. Complete Evidence,
assembly and eleven saved snapshots remain local under `analysis/local/rea/opcodes/`.
All REA targets were closed after saving.

The ten additional handlers contribute 768 checked native-model cases:

| Opcode | Native entry | Cases | Selected operation |
|---|---|---:|---|
| A1 | D2A0 | 312 | Pop condition, branch when low bit is clear |
| B9 | D2A8 | 39 | Unconditional encoded branch |
| 9D | D442 | 30 | Table-based indexed word load |
| D1 | D467 | 30 | Table-based indexed word store |
| A7 | D48C | 30 | Table-based indexed address |
| 9A | D4BC | 36 | Indirect word store |
| BE | D567 | 60 | Base-plus-index byte load, zero extended |
| BF | D581 | 75 | Base-plus-index byte store, high value byte discarded |
| 8F | D786 | 144 | Product modulo 65536 |
| 98 | D7CD | 12 | Square modulo 65536 |

Stack arguments in the table follow bottom-to-top order: 9A takes pointer, value;
BE takes base, index; BF takes base, index, value. Byte indices are not scaled.
The BF probes also check that the neighboring byte remains unchanged. These are
raw operations on controlled synthetic addresses, including page and 16-bit wrap;
they do not establish valid Pascal array bounds or the real program's RAM values.

9D/D1/A7 read a selector byte, double it in an 8-bit register, then add twice the
encoded index to the word fetched at BD9E plus that doubled selector. Thus selector
bit 7 is discarded by this native path. No local/global ownership, legal selector
range or allocation lifetime is established by these synthetic table entries.

The D75F helper makes 16 shift/add iterations. D786 returns the low word; D7CD
duplicates the top word before entering it. Tested inputs cover zero, sign
boundaries and wraparound. This is not a claim about checked Pascal arithmetic,
all possible operands, or the helper's complete wider-result semantics.

### Branch operand rule

Let PC be the opcode address, b the following unsigned byte, and P the word in
54/55. All address calculations wrap modulo 65536:

- If b is below 80 hexadecimal: target = PC + 2 + b.
- Otherwise: cell = P + b - 256; target = cell - word(cell).

The high-bit case is a table selection through P, followed by a backward
self-relative word; it is not a signed PC displacement. Tests include table-cell
address wrap and targets before PC, after PC and near FFFF.

A1 pops an entire word but tests only bit zero. Odd values skip the branch operand
and continue at PC+2; even values enter B9's decoder. Thus 0100 branches while
0101 falls through, despite both being nonzero. When bit zero is clear, BNE at
D2A6 falls through to D2A8; those routines are separately bounded REA imports.
Their incomplete external branch graphs must not be presented as a full runtime
control-flow trace.

The first attempt to replay the table form explicitly failed on native F1 at
D2C9, SBC (zp),Y. That addressing form was added to the limited model and checked
with independent microprogram cases for borrow, N/Z flags and zero-page pointer
wrap before admitting the branch cases. No unsupported instruction was skipped;
the model still omits V/decimal/device behavior.

### Reproduce the static cross-check

```sh
python3 tools/rea_opcode_views.py
```

For each manifest slice, use actual REA open_binary with provider ghidra,
format raw-binary, architecture 6502 and its stated base/entry. Save the actual
load-image, complete read_bytes, entry instruction and procedure_assembly Evidence
as load.json, bytes.json, entry.json and assembly.json in the corresponding
analysis/local/rea/opcodes/<name>/ directory. Save a snapshot and close the target.
Then run:

```sh
python3 tools/rea_opcode_views.py --verify analysis/local/rea/opcodes
sh tools/run_opcode_analysis.sh
python3 -m unittest discover -s tests -v
```

The assembly validator rejects partial, duplicate, out-of-range and differing
instruction observations. Actual REA Evidence IDs are linked in the catalogue
and read back from Ghidra entry comments. Native static agreement and synthetic
semantics are separate checks; both analysis routes use Ghidra, not independent
decoders. Confidence is high for the attested bytes and selected sampled effects;
hardware execution and untested semantic paths remain unobserved.

## Second ten additions: comparisons, pointer arithmetic and copying

The next pass added 945 synthetic cases and fourteen new actual REA imports,
reusing the first eleven Evidence sets without reissuing unchanged analyses.
The new imports cover 299 source bytes and 165 native instructions, including
shared signed-comparison, result-mask, scaled-index and copy helpers. Each source
byte is checked against Utility sector provenance in the manifest. Cumulative REA
coverage is now 25 bounded imports, 656 bytes, 575 load checks and 365 instructions.
The comparison entries and shared helpers are separate bounded slices; external
branches remain explicit, rather than being treated as an observed joined graph.

| Opcode | Native entry | Cases | Selected operation |
|---|---|---:|---|
| C3 | DFA9 | 144 | Word equality |
| CB | DF7F | 144 | Word inequality |
| C9 | DF6F | 144 | Signed less than |
| C5 | DF73 | 144 | Signed greater than |
| C8 | DF77 | 144 | Signed less than or equal |
| C4 | DF7B | 144 | Signed greater than or equal |
| A2 | D9CB | 15 | Pointer plus twice the encoded index |
| A3 | D9AF | 15 | Word load at pointer plus twice the encoded index |
| A4 | D9DE | 36 | Base plus index times twice the encoded stride |
| A8 | D59B | 15 | Increasing-address copy of encoded word count |

The signed comparison helper first XORs the two high bytes and handles opposite
signs before comparing bytes. Result masks select less/equal/greater; output is
always a word 0 or 1. Equality compares all 16 bits. Each opcode is checked against
all pairs of the twelve declared boundary values, including 8000, 7FFF, FF00 and
FFFF. Treating these relational operations as unsigned would fail those cases.

A2/A3 have no local/global frame bias. Their index uses the D155 encoding already
documented above. A4 takes base then index on the stack, multiplies the index by
twice the encoded word stride, adds the base and keeps the low 16 address bits.
Stride one uses a shift path; other strides use D75F. Synthetic cases include
stride zero, 7FFF, signed-looking indices and non-minimal operand encodings.
These raw address calculations do not establish valid array bounds or ownership.

A8 pops source first, then destination. D155 doubles the count and E8AA copies
bytes at increasing addresses, first full pages and then the residual bytes.
Fourteen non-overlapping cases check counts 0, 1, 2, 16, 127, 128 and 256 at two
address alignments; all payload bytes and a trailing guard are checked. A fifteenth
case places the destination two bytes after the source and confirms propagation
of already overwritten bytes. Thus the routine has forward-copy semantics; it
does not provide overlap-safe memmove behavior. Legal Pascal overlap requirements
and larger counts remain unestablished.

Copy cases use a declared native instruction budget of 8*byte_count+100 (maximum
4,196 in these tests); the small overlap case retains the normal 500-step budget.
Budgets are recorded per rule in the catalogue. A deterministic synthetic test
confirms that the wrapper respects an explicit budget and fails when it is short.
No additional native instruction or device behavior was admitted in this pass.

In that pass, all 41 deterministic tests passed. Ghidra annotations covered 46 native
entries, including twenty linked to actual REA assembly Evidence IDs. Every one of
the 761 native PCs visited in that pass was a defined Ghidra instruction;
the dispatch tables and initial p-code array remain typed data with no native
instructions. Confidence remains high for these sampled effects and attested bytes,
with no claim of exhaustive semantic proof or Apple II execution.

## Completion of the remaining 28 primary entries

The final pass identifies all previously remaining entries with 2,355 additional
cases, for 4,976 total. It adds 45 actual REA imports while reusing the earlier 25.
Cumulative native coverage is 3,092 bytes, 1,656 instructions and 1,610 load checks.
All 49 deterministic tests pass; 74 native entries have persisted annotations,
including actual REA links for all 48 formerly unknown high entries.

See [completion findings and limits](primary-opcode-completion.md), the generated
[complete reference](opcode-reference.md) and `analysis/opcode-coverage.json`.
That report separates complete primary identification from selected semantic
coverage, error prefixes, secondary dispatch and external service boundaries.
Individual 9E services, ROM/device execution and full p-system reconstruction
remain open. No full p-code disassembler is claimed.

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

`AnnotateOpcodes.java` writes snapshot-specific labels/comments at 74 native entry
addresses and explains the implicit A/Carry/Y interface. Comment readback and
alias membership are checked and exported to `analysis/ghidra-opcode-annotations.json`.
The project save is checked by the wrapper. No copied game disassembly is committed;
full exports remain under ignored `ghidra/exports/`.

Run the focused analysis after the base regions/seeds exist:

```sh
sh tools/run_opcode_analysis.sh
```

The full `tools/run_ghidra.sh` pipeline includes this step. Actual REA checks now
cover all 48 formerly unidentified high-opcode handlers and shared helpers, as described
below. Native static Evidence IDs are persisted beside the selected semantics;
they attest the bounded native analysis, not execution of the synthetic cases.

For the **unexecuted normal-return case** through `$F008 → $D27B`, the next
p-code address would be `$F24E`. Original bytes there select opcode `$CD`, whose
native `$E306` reads segment slot 4 and procedure 1. The dictionary maps slot 4
to absolute block 264, 1998 bytes. All ten of that payload's procedure records
resolve in-file; procedure 1's entry offset is `$060A` (Utility T33, DOS sector 9,
byte 10). This is a conditional static follow-up target, not a call observed in
replay. Its actual RAM load address depends on allocation state and is unresolved.
CD is now identified and checked on synthetic resident/native/global/lexical call
fixtures. The actual startup allocation and nonresident/device execution remain
unobserved; see the completion report.
