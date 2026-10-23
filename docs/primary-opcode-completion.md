# Primary opcode identification checkpoint

The remaining 28 primary opcodes were identified on 2026-10-23. The catalogue now
accounts for all 256 primary byte values: 128 short constants and 128 high entries.
Every high entry has at least one checked native path; there are no unidentified
primary entries. This is a completed identification checkpoint, not exhaustive
verification of every runtime input, subordinate service or Apple II execution.

`analysis/opcode-coverage.json` records that distinction explicitly:
`all_primary_entries_identified=true`, `unresolved_high_opcodes=[]`, and
`exhaustive_runtime_verified=false`. The generated
[complete reference](opcode-reference.md) gives each high opcode's handler,
operands, stack effect, continuation and checked-case count. The full machine
catalogue retains source sectors, native PCs, variant checks and REA Evidence IDs.

## Evidence and validation

- 4,976 controlled native-handler cases; 49 deterministic tests pass.
- 70 actual REA/Ghidra 12.1.4 imports: 3,092 bytes, 1,656 native instructions and
  1,610 load checks agree with disk-derived sources and direct Ghidra.
- All 2,049 native PCs visited by controlled cases are defined Ghidra instructions.
- 74 native entries have persisted labels/comments with verified readback;
  all 48 formerly unidentified high entries link to actual REA assembly Evidence.
- Dispatch tables, packed masks, native-return data and the initial p-code region
  remain typed data, with zero native instructions in those ranges.

All REA targets were closed after retaining complete Evidence and snapshots under
ignored `analysis/local/rea/opcodes/`. Original media were not modified. Structured
reports and source locations are versioned; game binaries and bulk assembly are
not. Both native analysis routes use Ghidra, so agreement is not an independent
decoder proof. Model fixtures are declared synthetic and are not REA runtime
observations.

## Last 28 entries

| Opcodes | Established operation |
|---|---|
| 86, 8E | Signed quotient truncated toward zero; nonnegative magnitude remainder |
| 88, 9B | Inclusive signed range check; length-prefixed string index check |
| AA | Capacity-checked string/character assignment |
| AC | Aligned signed case selector with self-relative target cells |
| B3 | Inline word push with explicit 8-bit count/index wrapping |
| BC, BD | Multi-word memory load/store and native stack-space check |
| C0 | Packed-array address/width/bit-offset descriptor |
| BA, BB | Masked packed-field load/store |
| AF, B0, B1, B4, B5, B7 | Type-dependent equality/order/bitmap comparisons |
| 9E | Secondary dispatcher; all 256 selector bytes mapped without executing targets |
| D5 | Decode and discard an encoded index while advancing PC |
| D6 | Generate reset stub at 0000, then jump there |
| AE, CE, CF, CD, C2 | Current/external procedure calls and static/global link selection |
| AD, C1 | Return values and restore caller state; C1 also restores global frame |

Division by zero and C0's zero divisor enter error 106. Range/string-index failure
enters 101; excessive native stack or parameter requirements enter 104; oversized
string assignment enters 113. Probes stop at the shared exception boundary rather
than claim a complete exception implementation. The eighteen previously identified
shared-error slots remain explicitly classified as error-prefix coverage.

8E returns the remainder of operand magnitudes, including for negative dividends.
No stock-language MOD name is assumed. C0 also uses magnitude division for a
signed-looking index; native quotient sign correction is not applied on that path.
Its low-byte bit-offset product is pushed twice, as observed, rather than repaired
into an assumed conventional descriptor.

B3's zero count runs 256 iterations. Its source offset wraps in a 256-byte window,
and its PC advance is `((2*(count+1))&FF)+(PC&1)`. Counts 0/127/128/255 were checked,
including hardware-stack wrap in the model. BC also has zero/128 aliases in its
8-bit loop/preflight arithmetic. These are raw native behaviors; they do not prove
that the Pascal compiler emits those edge operands or that such programs are valid.

## Typed comparisons

The six comparison entries set a result mask and share a kind dispatcher:

| Kind byte | Observed representation and operand rule |
|---|---|
| 02 | Two four-byte values, high word then low word on stack; sign-magnitude byte ordering |
| 04 | Two Pascal-style length-prefixed strings, or zero-high-byte character words |
| 06 | Two words, comparing only bit zero |
| 08 | Each bitmap's most-significant words first, followed by its word count |
| 0A | Two pointers plus an encoded byte count |
| Other | Two pointers plus an encoded word count; comparison reads twice that many bytes |

String, character, boolean, block and set cases were checked separately. Zero
bitmap padding makes differently sized equivalent sets compare equal. Set subset
and superset relations are checked; the masks normally named less/greater take the
superset fallback in this native kind path. Legal language-level kind/mask
combinations remain unestablished. The four-byte ordering rule alone does not
establish IEEE compatibility or the original source numeric type.

## Call and return reconstruction

The common resolver locates a procedure through backward self-relative cells.
For the tested p-code branch, frame = old top − locals − parameters − 12; the
allocation pointer then moves to frame − 2. It checks space, copies parameters
from the native stack and selects the procedure's p-code entry. Parameters are
copied top-first. Tests cover three
procedure numbers, zero/two/four parameter bytes and lexical/global calling paths.

| Frame offset | Observed field |
|---|---|
| −2 | Saved allocation top |
| +0 | Selected static link |
| +2 | Previous local frame |
| +4 | Previous branch/procedure anchor |
| +6 | Previous segment descriptor pointer |
| +8 | Caller p-code continuation |
| +10 | Saved native stack pointer |
| +12 onward | Parameters/result storage as selected by procedure metadata |

CE uses the saved caller local frame as static link. CF uses the current global
frame pointer. AE walks the dynamic chain using lexical-level metadata and selects
the matching predecessor. C2 pushes the old global pointer and establishes a new
global frame; its static link is copied from the old global frame's first word.
CD reads segment/procedure bytes, acquires nonzero segments and selects its global
or lexical path from procedure metadata. Resident reference increments and the
nonresident request boundary were tested independently.

AD/C1 restore the saved native SP, copy result words so the first result is on top,
and restore allocation/local/branch/segment/PC state. C1 first pops the old global
pointer. A changed first-byte segment identifier invokes E646; that release path
is retained as an explicit boundary.

A tag-zero native procedure bypasses p-code frame allocation. The resolver pushes
the source data word E189 = E17D; a native RTS therefore reaches E17E. A declared
synthetic RTS callee tests that return contract. The trampoline reads the patched
segment marker E18B: negative markers resume fetch; nonnegative markers invoke
E646 first. The synthetic callee is not shipped game code. E17E is now an explicit
Ghidra seed, and E189/E18B remain data.

## Reproduction and remaining boundaries

```sh
python3 tools/rea_opcode_views.py --verify analysis/local/rea/opcodes
sh tools/run_opcode_analysis.sh
python3 -m unittest discover -s tests -v
```

The focused pipeline regenerates selected cases, persists and verifies Ghidra
annotations/data types, checks the startup boundary and exports the complete
reference/coverage reports. Fresh REA acquisition uses the versioned manifest and
the [retention procedure](opcode-semantics.md); retained actual Evidence is required,
not a readiness result or invented fixture.

Open questions now belong to the next layers: individual 9E services and their
valid selector domain, nonresident disk loading, segment release/device effects,
actual ROM/reset and Language Card behavior, exact p-system modifications, legal
compiler operand domains, and game-specific execution. No primary entry remains
unidentified, but those broader questions are not marked complete.
