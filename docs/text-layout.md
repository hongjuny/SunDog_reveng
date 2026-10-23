# Original Pascal text layout

SYSTEM.LIBRARY segment 22 procedures 48, 47, 45, 12 and 11 define a useful
recoverable text-rendering layer above native P9. `tools/text_layout_evidence.py`
checks their decoded operands, branches and calls against source bytes and the
Apple II native-backed opcode catalogue. It follows only these five procedures,
with explicit stop boundaries and a placement hook for P9. It is an analysis
fixture generator, not a general p-code interpreter or application backend.

The public report is `analysis/text-layout-evidence.json`. It records original
Utility-side sector coordinates, source hashes and the selected native helper
check. Fifty synthetic fixtures are private under `analysis/local/text-layout/`.
No original text or complete disassembly is exported in the report.

## State and setup

All indices below are words relative to table[29], not native assembler data
offsets. Native data base is table[29]+2. P48 begins with P11(3), setting word367
to 3 and word357 to63. These map to P9's ordinary drawing mode and mask word
respectively. P48's capacity80 string assignment raises error113 on excess input;
it does not truncate to80 characters.

| Field | Proven selected use |
|---|---|
| 14 | Line-start boundary; next-line x is this word+2 |
| 17 | Right boundary used by word and per-character wrapping |
| 11 | Bottom boundary checked after advancing to another line |
| 19 | Logical text x |
| 18 | Logical text y/baseline |
| 365 | Native drawing x saved by P12 |
| 364 | Native drawing y saved by P12 |
| 366 | When positive, P12 calls P57 before storing the new position |

P12 is not a clipping routine. Its optional P57 call computes a line between old
and new positions. The selected text contract requires word366 zero, so that
unimplemented drawing path is not silently omitted.

P9 reads x from native offset02D8 (table365) and y from offset02D6 (table364,
low byte); it adds no window origin. Relocated native helper1607 maps x to HGR
column and shift. The original helper matches `x//7,x%7` for every x0..272 in273
bounded checks, with every visited address a Ghidra-defined instruction. Thus the
selected logical x/y values can feed the verified normal glyph compositor
directly when x0..272 and baseline7..191. The source's procedure-relative table
operand must first be relocated; executing its raw bytes at segment offsets
would address the wrong table.

## String processing

P48 distinguishes three separator bytes, independently of macOS text conventions:

| Byte | Actual selected behavior |
|---|---|
| Space32 | Draw space through P47 only when x>word14+2; otherwise consume without advancing |
| Backslash92 | Call P45 only when x>word14+2; repeated or leading backslashes do not add empty lines |
| Vertical bar124 | Always draw a space through P47, including at line start |

ASCII LF10 is an ordinary glyph value in P48, not a newline command. A macOS
newline-to-backslash conversion, if offered, must be identified as host policy.

Other bytes are accumulated until one of those separators. Before drawing the
word, P48 calls P45 if `x+6*wordLength>right`. It then passes each byte to P47.
P47 itself checks `x>right-5` both before and after each glyph; either true check
calls P45. P47 calls P12(x,y), native P9(character), then advances logical x by6.
P9 also advances its own native x field by6. The two fields must not be merged:
post-glyph wrapping may reset logical x/y without another P12 call.

P45 sets x to word14+2, increments y by8, and calls P44 when y>word11. P44 calls
P19 with word11's address and8, then resets several text/window state fields.
The full P19 side effects are outside this first contract. The evaluator and
native contract therefore stop at P44 instead of inventing scrolling or clearing.

The word buffer begins at local49; scalar local59 begins20 bytes later. This
establishes an alias boundary, not safe unbounded word storage. The initial
native contract excludes words longer than20 consecutive nonseparator bytes
until their original aliasing behavior is separately analyzed. Total input is
at most80 bytes, and original byte-based strings have no inferred Unicode mapping.

## Evidence limits and reproduction

The source procedure entries are P11 $0052, P12 $016C, P45 $085E, P47 $08AA and
P48 $08E4; detailed track/sector/byte provenance is generated in the report.
These rules are high-confidence static dataflow supported by the verified native
opcode semantics. Fixtures execute the original decoded text CFG and byte-addressed
locals; they do not execute an Apple II device, disk loader, or complete game.
P9 is a hook recording character/position and applying the separately verified
native x advance. Raster equivalence is established by the existing420 native
glyph fixtures, not by pretending the CFG hook draws pixels.

Run `python3 tools/text_layout_evidence.py` to reproduce50 fixtures and273 native
coordinate checks. Four deterministic media-independent tests cover low-bit branch
truth, local byte aliasing, capacity failure and explicit unsupported-call stops.
The parent native verifier compares the resulting fixtures with Swift layout.
