# Research log

## 2026-10-23 — initial milestone

Started from two WOZ originals and two supplied logical images; no existing source
or Git repository. Read the REA skill and inspected its live session. REA 6.7.0 is
connected, but its Ghidra candidate is unavailable because `GHIDRA_INSTALL_DIR`
is unset in that server. No client configuration was changed.

The `/Applications/ghidra_12.1.4_PUBLIC` directory contains only an ARM decompiler.
The complete installation is `/Users/ay5/Applications/ghidra_12.1.4_PUBLIC`.
Java 21 is `/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home`.
Direct headless Ghidra is used for persistent projects, annotations, references,
and disassembly. REA interactive native analysis was therefore not used.

Initial Ghidra launch could not save its JDK selection outside the workspace.
The reproducible wrapper redirects Java user home and temporary files locally.
First successful run also warned about an external cache-maintenance path; the
wrapper's explicit temporary directory was an attempted remedy. Later runs still
log the external cache-maintenance warning; it does not prevent analysis or saving
the project. The earlier assumption that the temporary-directory override fixed
Ghidra's separate file cache was incorrect.

Corrected an initially inverted DOS skew table before final artifacts: the inverse
is not interchangeable. A wrong skew produced table/graphics bytes at loader
continuations. CiderPress2 source tables and the contiguous Ghidra disassembly
support the corrected mapping. This is a documented failed working hypothesis.

The sector comparison reproduces 103 equal corresponding sectors and five equal
tracks. Deterministic synthetic tests validate offsets, size checks, histogram
statistics, mapping anchors, and exclusion of unreadable sectors.

Historical context: Bruce Webster identifies v2.0 as an October 1984 revision that
used 64KB more fully and swapped less. This is developer testimony, not a measured
performance finding: https://brucefwebster.com/past-projects/sundog/ (accessed today).
The Atari ST port at https://github.com/laanwj/sundog was inspected as background;
its VM format has not been applied to Apple II bytes.

Disk II ROM behavior was cross-checked against the listing at
https://6502disassembly.com/a2-rom/APPLE2.ROM.html (C658–C6F8). That listing represents
an emulator ROM and explicitly warns about errors; a particular physical ROM was
not supplied. Boot conclusions are conditional on matching Disk II ROM behavior.

## Outstanding work

Reproduce complete WOZ extraction and record decoder identity/options. Establish
an actual ROM/emulator configuration and observe sector reads, memory writes and
Language Card transitions. Validate active directories and segment descriptors;
embedded old directory records may be misleading. Identify the interpreter from
its dispatch loop before implementing any p-code disassembly. Measure performance
only after booting a controlled emulation.

The final bank-aware boot trace reaches `$0801 → $08FF → $4000`, then the loaded
`$FFF8` vector `$FEF2`, bank 1 `$D152`, common `$F269`, relocated `$6800`, and
bank 2 `$DAA9`. `$F290–$F78F` is copied to `$6800–$6CFF`; the relocated initializer
clears earlier boot RAM. These are static, conditional execution paths.

All 192 graphics row table entries in the first native region match the HGR
formula. Four directory-shaped groups cover contiguous blocks 3–279, but no
active filesystem or p-code format is proven. CiderPress2 independently matched
13 selected readable sectors and failed on all 16 unknown Play Track 34 sectors.
Both WOZ CRCs match and their INFO creators are `Applesauce v1.48b10`.

A scoped REA CLI doctor with explicit Ghidra and Java locations failed building
its Swift ownership helper because the external module cache was read-only.
This does not block direct Ghidra exports. No persistent REA configuration changed.

The workspace policy prohibits creating the root `.git` path. Local Git metadata
was created at `analysis/local/repository/.git`, with repository root supplied as
an explicit work tree by `tools/git-local.sh`. Use that wrapper for `status`,
`log`, and other local Git commands. No original images, derived binaries, raw
string dumps or disassembly exports are staged. Nothing was published or pushed.


## 2026-10-23 — milestone 2: native-to-Pascal handoff

Followed synthetic returns 68B9 and 68C4, then the initializer through the custom
directory read at block 79 and SYSTEM.PASCAL header read at block 251. Native code
copies sixteen block/length descriptors into six-byte runtime records at BE3E.
The version predicate is header byte 103 hex masked by E0 equals A0; the A2 byte
passes, and failure names version 1.2. This supports a 1.2-family requirement,
not byte-for-byte stock runtime identity.

Identified bank 1 fetch D293, primary D000 words, and secondary D100 cells reached
by opcode 9E. Both dispatches patch native JMP operands. No full p-code decoder
was built. Identified 21 BIOS wrappers that switch to bank 2 and restore bank 1;
the apparent FF3F wrapper does not pass the same JMP-shape check. D026/D029 are
overlapping instruction streams; independent Ghidra views preserve both.

Native allocation arithmetic loads slot 15's 170 bytes to BC72 and segment 0's
3124 bytes to F248. The latter overwrites the original initializer. All 39 procedure
records resolve, including procedure 38's cross-region pointer to the BC72 helper.
The final initialization clear removes 6000..6C30 and jumps to D293, with the first
p-code pointer resolving to F248 (initial byte 9F, native handler D2D7).

Archive inventory found the whole SYSTEM.LIBRARY extent identical across both
disks. Four stored descriptors have 6502 machine-type metadata, three have
little-endian p-code metadata, and three data allocations have no stored payload.
A naive SYSTEM.STARTUP slicing hypothesis failed: four descriptors exceed the
79-block directory extent; other in-range bytes overlap Utility boot-native data.
Those conflicts are retained rather than exported as validated out-of-file code.
The metadata fields were compared to local CiderPress2 ApplePascal_Code.cs; its
schema was used as an independent Apple reference, not an Atari compatibility assumption.

Full CiderPress2 decoding reproduced all 1,104 readable sectors from the original
WOZ files. All sixteen Play Track 34 reads failed; complete known tracks alone
were exported. Decoder executable and assembly hashes are recorded. Original
media hashes remain unchanged.

Validation: thirteen deterministic tests pass without game media; reports
reproduce byte-for-byte. Seven bounded Ghidra Programs save successfully, including
the interpreter-ready view with segment 0 classified as p-code data. A controlled
emulator trace, exact interpreter variant, opcode operand semantics, and the
transition into game-specific startup remain unresolved.

## 2026-10-23 — ordered checkpoint 1: REA connection recovery

The user requested active use of both tools and ordered checkpoints. Re-read the
REA recovery guide for the observed provider blocker. The connected MCP server's
raw-binary open request still returns provider_unavailable: no GHIDRA_INSTALL_DIR.
The current Codex server entry has no selected Ghidra/Java/Swift environment values.
A later full key-name check confirmed an existing HOPPER_LAUNCHER_PATH entry; it
must be preserved. No client files changed.

Corrected the installation diagnosis: /Applications contains a 14-byte 404 text
file, but the complete user installation already has a valid ARM64 decompiler
under Decompiler/build/os/mac_arm_64. A redundant local native build completed
before this location was checked; it did not replace either installation.

Setting REA_DARWIN_MODULE_CACHE_PATH, REA_DARWIN_SWIFTC_PATH and SDKROOT solved the
previous Swift module-cache compilation failure. The next CLI doctor reports
Java spawn EPERM during its owned process probe. Direct Java works, and direct
ps is denied; REA's owned launcher requires a process baseline. Both detached and
non-detached direct Node Java probes worked, so detachment alone is not the cause.
No provider ownership protection or sandbox restriction was bypassed.

Prepared a project environment launcher and an unapplied minimal client-env
fragment, checked against official OpenAI MCP documentation. Client config lies
outside writable roots and the running server needs reconnection with those
variables. Recorded this as pending, not passed.

Prepared a 37-byte, source-verified native entry slice at D27B to avoid seeding the
D000 data table as executable code. Direct Ghidra saved the reference disassembly
and finds A000 (LDY #0) at D293. Actual REA Evidence is still required. A validator
and three added deterministic tests distinguish installed-file/readiness checks
from matching native instruction Evidence. Sixteen tests pass.

## 2026-10-23 — continued independent checks and selected opcode semantics

The user requested continued progress. Rechecked the live REA session and existing
client environment: GHIDRA_INSTALL_DIR remains absent. No duplicate failing open
request, configuration rewrite, safety bypass or false connection-pass claim was
made. Checkpoint 1 remains pending. Independent direct Ghidra/source checks and
handler investigation proceeded with that limitation recorded.

Memory-view verification now checks low-bank composition, common upper RAM,
segment 0 overlay and unchanged bytes outside it. Ghidra explicitly classifies
the two dispatch tables as word arrays and the p-code overlay as byte data, with
zero native instructions in those spans. The loaded initialized-block hash agrees
with the source snapshot. A first validator assumed a single total memory block;
it failed because Ghidra creates uninitialized ZERO_PAGE and STACK blocks too.
The corrected check examines initialized bytes and preserves those blocks as
unknown/uninitialized rather than treating them as zero-filled observations.

A key semantic finding: high opcode dispatch preserves A=(opcode*2)&FF, Carry=1,
and Y=0. Shared handlers use that state, so collapsing all aliases by native
address would lose local/global/indirect offsets. D155 returns twice a 7-bit or
15-bit encoded index, unlike the little-endian literal word instruction.

Added a limited binary-mode 6502 handler-replay tool, not an Apple II emulator.
Eight native-model unit tests exercise flags, rotates, calls, page-wrap behavior,
branches and explicit unsupported/budget failures. With actual snapshot bytes,
908 declared synthetic cases check all 128 short constants, 62 ordinary high
opcode values, and the prefix of the shared error-111 path for 18 more. Forty-eight
high opcode values remain unresolved. All 407 distinct native addresses visited
by these selected probes are defined instructions in the Ghidra listing.

Ghidra labels/comments were persisted at 26 native entries. Comment readback and
alias membership are exported and checked; the project save succeeded. Tables and
p-code remain data. Opcode facts, source locations, synthetic case counts and
limitations are in analysis/opcode-evidence.json and docs/opcode-semantics.md.

A bounded replay of original startup p-code on synthetic frame/stack state checks
F248 push-zero, F249 store-local index 5, and F24B push-one. The following 9E/26
selector reaches EF7D and then FF06, with pointer-word arguments D1E3 and BDDE.
It stops before the BIOS wrapper and bank switch. The mapped bank 2 target is
D7EF; hardware/device behavior and actual startup frame values remain unobserved.
The prefix's visited native instruction boundaries also agree with Ghidra.

Validation: 27 deterministic tests (without game media), 908 native-binary model
cases, direct Ghidra memory/type/annotation checks, and reproducible reports.
REA cross-validation and a controlled hardware/ROM execution trace remain open.

The complete Ghidra pipeline was rerun successfully with the new classification,
annotation/readback and replay checks integrated. A conditional follow-up seed was
also recorded without simulating BIOS success: normal return would resume at
F24E, where CD selects SYSTEM.PASCAL slot 4 / procedure 1. Native operand selection,
archive extent and all ten procedure records agree; entry offset 060A maps to
Utility T33/DOS9 byte 10. Runtime allocation and actual call execution remain open.

## 2026-10-23 — explicit REA setup request: scoped apply attempted

The user made actual Ghidra+REA usage a priority and explicitly authorized REA
configuration. Added a review/apply tool that merges only the five prepared REA
path variables, validates full parsed preservation of unrelated settings, backs
up the original, retains the existing symlink and supports idempotent reapplication.
Four deterministic tests cover those behaviors and reject changes to tool policy.

The real global config resolves to OneDrive Settings/codex_sync/config.toml.
Attempted --apply under the available permissions. O_RDWR was denied with EPERM
before any backup or write. Re-read the original and confirmed its hash is unchanged,
no backup was created and the five requested REA environment values are still absent. No other analysis
was substituted for the requested integration. A concrete one-command operator
apply is documented; reconnecting REA and obtaining actual Ghidra-provider Evidence
remain required. Checkpoint 1 is not passed. Total deterministic tests: 31.

## 2026-10-23 — Actual REA/Ghidra connection passes

The user's terminal apply supplied the Ghidra/Java/Swift environment. A live MCP
query then failed because one Swift cache was addressed through both workspace
aliases. Preserved that generated cache by renaming it, then used a fresh cache.
REA successfully opened the D27B..D29F native slice with Ghidra 12.1.4. Load-image
verification passed all 23 checks; D293 decoded A000, LDY #0, length 2; incoming
references were D282/D286/D28F, matching the bounded direct Ghidra export. Saved
four actual Evidence records plus snapshot locally, ran verify_rea_probe.py, and
closed the session. High confidence for this bounded static integration check;
no claim of observed Apple II execution or independent decoder agreement.

## 2026-10-23 — Bounded REA memory-view acceptance

Prepared six immutable slices with per-byte checks back to Utility DOS sectors:
bank 1 and bank 2 D152 entries, common memory before/after the segment 0 load,
the native copy routine, and its relocated initializer. Actual REA/Ghidra 12.1.4
verified 23 load checks per target and read all 7,825 requested bytes completely.
D152 is JMP F269 in bank 1 and JSR D26B in bank 2. The after-load F248–FE7B range
equals all 3,124 archive bytes; 2,818 byte values differ from the before-load view.
The original F267 pointer is F290, and its 1,280-byte source matches the 6800
initializer. REA assembly preserves the five-page copy loop and entry's RAM clear.

The common-data probes use the existing F1CA RTS as a deliberately bounded import
seed, not a boot entry. This avoids seeding native execution in p-code. REA's F248
observation is undecodable and its common-after inventory reports one procedure;
these do not establish full p-code semantics or full-range type classification.
Fresh direct Ghidra analysis confirms the full table and p-code array types and
zero native instructions in their ranges. Ghidra annotations are not transferred
to REA. Bank hardware, actual reads and boot execution remain unobserved.

Saved complete Evidence and snapshots locally and closed all six REA sessions.
Versioned manifests/results contain hashes, sector provenance and Evidence IDs.
Added tools/rea_memory_views.py and five validator tests, rejecting partial reads,
wrong target/operation/address and same-address wrong-bank bytes. All 36 tests
pass; the focused Ghidra pipeline also passes 908 controlled handler cases,
memory/type checks, annotation readback and the bounded startup-prefix probe.
Checkpoint 2 passed within the documented bounded scope; checkpoint 3 is next.

## 2026-10-23 — Ten additional opcodes with actual REA native Evidence

Inspected the 48 unresolved primary handlers and selected ten bounded operations:
A1/B9 branching, 9D/D1/A7 table-based access, 9A indirect store, BE/BF indexed bytes,
and 8F/98 multiplication/squaring. Exported eleven native-only slices including
D75F's multiply helper, checked every source byte against readable Utility T30
sectors, and used actual REA/Ghidra 12.1.4 for each import. All 357 bytes, 253 load
checks and 200 native instructions agree with source/direct Ghidra. Retained 44
actual Evidence records and eleven snapshots locally, then closed every target.

A1 tests condition bit zero, so nonzero even words branch. B9's high-bit operand
selects cell=word(54)+b-256, then target=cell-word(cell); treating it as a negative
PC displacement would be wrong. This was a hypothesis to exclude, not a former
accepted repository conclusion. The initial replay stopped explicitly on unsupported
F1 at D2C9; added SBC (zp),Y to the limited model and tested borrow/flag/pointer
behavior. No instruction was silently bypassed.

Added 768 synthetic native-handler cases, including backward/forward table targets,
address wrap, selector aliases, neighbor-byte preservation and arithmetic limits.
Total is 1,676 cases: 72 ordinary high opcodes, 18 shared-error prefixes and all
128 short constants. Thirty-eight high opcodes remain unresolved. Ghidra's
persistent annotations cover 36 entries, ten linked to actual REA assembly IDs;
all 607 visited native PCs match defined Ghidra instructions. The focused pipeline
also retains correct p-code/table data types and the earlier startup boundary.

All 40 deterministic tests pass. See docs/opcode-semantics.md and
analysis/rea-opcode-crosscheck.json for reproduction and Evidence IDs. This remains
bounded static evidence plus declared synthetic replay, not observed Apple II
execution, complete table ownership, complete arithmetic semantics or p-code
disassembly. Checkpoint 3 continues with 38 unresolved opcodes.

## 2026-10-23 — Scalar comparisons, pointer offsets and forward word copy

Resolved ten more high values: C3/CB equality and inequality; C9/C5/C8/C4 signed
relations; A2/A3 pointer offset and indexed word load; A4 scaled indexed address;
and A8 forward word copying. Added 945 controlled native-model cases. Total is
2,621 cases, covering 82 ordinary high values, 18 shared-error prefixes and all
128 short constants. Twenty-eight high values remain unresolved.

Actual REA/Ghidra inspected fourteen new native slices (299 bytes, 165 native
instructions), including signed comparison, result-mask, scaled-index and copy
helpers. Every slice passed 23 load checks and complete source-byte/instruction
comparisons. Existing eleven Evidence sets were reused without reanalysis.
Cumulative opcode-specific REA coverage is 25 targets, 656 bytes, 365 instructions
and 575 load checks. Complete Evidence/snapshots remain local; all targets were
closed. The versioned input manifest records Utility sector/offset provenance;
the cross-check report links each actual Evidence ID.

Unsigned ordering was excluded by explicit opposite-sign branches and signed
boundary cases. A2/A3 have no frame-header offset. A4 multiplies stack index by
twice an encoded word stride; stride one takes a shift path. A8 copies increasing
addresses; an overlapping destination at source+2 propagates overwritten bytes,
excluding overlap-safe memmove semantics. Copy tests cover zero, page boundaries,
512-byte payloads and trailing guards. Ownership, legal Pascal bounds/overlap and
larger counts remain unresolved.

No new native instruction was required. Added a declared per-probe instruction
budget for long copy loops (up to 4,196 steps in this case set), recorded maximum
budgets per rule, and tested exact budget enforcement with a synthetic NOP fixture.
All 41 deterministic tests pass. Fresh Ghidra analysis verifies all 761 visited
native addresses, 46 persisted annotated entries and twenty entries linked to
actual REA IDs; p-code/tables remain data. Startup replay still stops before BIOS
FF06. No Apple II execution or timing measurement is claimed.

The typed comparison family remains unresolved; its type-dependent operand and
stack formats are not implied by the scalar comparisons established here.
Checkpoint 3 continues with 28 unresolved high opcodes.

## 2026-10-23 — Remaining 28 primary entries identified

Continued without stopping at another partial batch, as requested. All 128 high
entries now have checked native paths and per-opcode case accounting; all 128
short constants were also checked. The catalogue has zero unidentified primary
entries. Added 2,355 cases for 4,976 total, including typed comparisons, division,
bounds/string checks, inline/multiple words, packed fields, case tables, dispatch,
reset stub generation and call/return frame behavior. All 49 deterministic tests
pass. This closes primary identification, not exhaustive runtime verification.

Acquired 45 additional actual REA/Ghidra 12.1.4 targets, reusing the earlier 25
without unchanged reanalysis. Cumulative source coverage: 70 imports, 3,092 bytes,
1,656 native instructions and 1,610 load checks. All complete reads and bounded
instruction sets match source and direct Ghidra. Retained complete Evidence and
snapshots locally and closed all targets. Actual assembly Evidence IDs now link
all 48 formerly unidentified high entries to persistent Ghidra annotations.

Fresh Ghidra analysis confirms 2,049 visited native PCs and verified comments at
74 entries. Packed masks at DDD6 (17 words), native return data at E189/E18B and
initial p-code/dispatch tables remain data. E17E was added as an explicit seed:
the resolver pushes E17D from source data and native RTS reaches that trampoline.
A declared synthetic RTS callee checks the interface, never shipped native callee
behavior. Segment-release and nonresident-load paths stop at explicit boundaries.

Important corrections made during investigation: the bitmap word nearest its count
is least significant, rather than the first word pushed; a failing oracle exposed
the ordering and the native stack walk confirmed it. C2/CD global setup copies the
old global frame's first word as static link, not the old global pointer. AE's
search examines saved procedure anchors in frames; its predecessor selection was
checked with one- and two-level fixtures. These provisional interpretations were
corrected before inclusion in the accepted catalogue.

The raw B3/BC zero and high counts expose u8 source/stack wrapping and PC aliases;
they are documented, not normalized into an assumed safe load. Packed descriptor
C0 uses magnitude division for negative-looking indices and pushes its low-byte
offset twice. Typed kind 02 establishes sign-magnitude four-byte ordering, not
numeric-format compatibility. Set kind 08's less/greater masks use a superset
fallback; legal Pascal combinations remain open. Native instruction admission was
extended only for encountered addressing forms and independently microtested;
unsupported forms still fail explicitly.

Added tools/extended_opcode_evidence.py, tools/call_opcode_evidence.py and
tools/export_opcode_catalogue.py. The focused Ghidra pipeline now exports the
generated docs/opcode-reference.md and analysis/opcode-coverage.json. Coverage
tests require a checked case rather than merely a label, reject duplicate primary
values and retain exhaustive_runtime_verified=false even when identification is
complete. The report separates ordinary selected paths, eighteen error prefixes,
secondary dispatch and external boundaries. Current 9E services, ROM/MMIO,
nonresident I/O, exact p-system modifications and observed game execution remain
next-layer work. See docs/primary-opcode-completion.md for scope and reproduction.

## 2026-10-23 — original boot, input and native graphics milestone

Executed the supplied game in the locally available pinned a2m 3.0.0 reference
using inherited socketpair control. Preserved original media and mounted private,
write-disabled copies. Actual breakpoints reached 0801, 08FF, 4000, FEF2, 6800,
D293 and FF06; initial sector, relocation and initial Pascal segment matched the
static reconstruction. BIOS bank-2 D7EF and return to p-code F24E were observed.
This supersedes earlier statements of no observed execution for these boundaries;
it does not turn earlier synthetic handler tests into actual runtime observations.

Original WOZ and re-encoded logical-sector continuations differ: the bounded WOZ
run remained in bank-2 disk work while the logical-sector run displayed the title
caption and, following controlled Ctrl-U input, the utility menu. The compatibility
cause is open. Play Track 34 remains unknown; Play media was not executed here.

REA with actual Ghidra 12.1.4 rechecked D6A5 input polling and D6E0 keyboard read.
Full Evidence and snapshot were retained privately and the session closed.
The loader sector map locates these at Utility T27/S3, bytes A5/E0. Runtime
Ctrl-U produced A=95 after LDA C000. Failed late-input waits, the initial wrong
frame channel conversion, and an input ordering race were retained and explained
in docs/reference-execution.md. a2m's key command resumes execution; arming the
post-read breakpoint before injection removed the race without game patches.

Implemented Swift AppleIIVideo, a hash-validating captured-memory adapter, CLI
comparison tool and SwiftUI/AppKit/MetalKit reference viewer bundle. Twenty-four
supported captured HGR screens match the CPU decoder exactly; seven incorrect
legacy conversions are excluded and two text-mode frames are unsupported.
Metal device creation is unavailable in the CLI environment, so GPU equivalence
is open. The GUI process smoke test aborted without diagnostic output; actual
window presentation is unverified. This app is a reference viewer, not a playable
port or a completed VM.

SwiftPM nested sandbox execution failed with sandbox_apply Operation not permitted.
Used direct swiftc compilation under existing restrictions, without disabling the
sandbox. Native bundle ad-hoc signing/verification and six Swift tests pass;
55 deterministic Python tests pass. Media, snapshots, ROM bytes and captured
screens remain ignored. See fidelity-spec.md and reference-execution.md.

## 2026-10-23 — restart around original game reconstruction

The user rejected the emulator-backed app direction. Quarantined its uncommitted
C/Swift bridge, build scripts/tests and native app under
analysis/local/abandoned-emulator-app, preserved the diff, and restored tracked
prototype files. No new reference emulator was executed during this restart.
The final product is to implement reconstructed game rules, state and rendering
in native code; an emulator/bytecode executor embedded in a shell is not that port.
Earlier app-building results must not be counted as game-logic reconstruction.

Implemented bounded p-code decoding using the established Apple II native operand
rules. Rechecked frame/trailer branch-base setup with actual REA/Ghidra 12.1.4.
Discovered mixed native/Pascal procedures in machine-type-7 segments; segment 22
has 45 p-code and 18 native procedures. Unsupported secondary-service paths stop.
Full listings remain local rather than publishing proprietary instruction bytes.

Validated the shared block-140 dictionary against Play, rather than imposing the
Utility file extent on both sides. All 13 SYSTEM.STARTUP payloads have matching
segment tags and valid self-relative procedure entries: 327 procedures, including
segments 18–21 previously excluded. All source sectors match independent WOZ
verification; the final storage end is block 272 exclusive. Play T34 is not used.
This is a structural resolution; actual runtime disk-selection remains open.

Generated a combined 590-procedure inventory and static call graph: 43,471 reachable
p-code instructions and 3,310 call sites, with all service/native boundaries retained.
These are analysis counts, not a percentage of verified game behavior. A text-and-
procedure-context index prioritizes 21 candidate gameplay procedures, notably
trade/cargo candidates in segment 20 and navigation/ship candidates in segment 13.
Roles remain hypotheses until state transitions and contracts are reconstructed.

Traced library string P48 → character placement P47 → native glyph P9. Matched
the captured segment-22 directory binding and native source changes to three bases;
22 relocated operand words explain all 44 changed bytes. Reused retained reference
RAM only for corroboration, not as an application backend. Actual REA source,
captured native function and coordinate-helper disassemblies were retained and
sessions closed. Normal eight-row two-byte HGR composition was reconstructed as
independent bit expressions and matched 420 declared synthetic fixtures using the
existing bounded native-analysis probe. Added only the needed OR-absolute
instruction to that probe, with a deterministic flags test. No game VM was built.

Persisted six labels/comments in the Ghidra project with readback verification.
An initial annotation hash checked total Program memory rather than the imported
span and failed; a bounded imported-span hash passed. Full assembly and project
remain private. Tests: 67 deterministic Python tests pass. Remaining work includes
secondary-service continuation, actual game-entry/input flow, text layout/clipping,
mode-2 glyph behavior, native relocation tables and gameplay state/rule reconstruction.

## 2026-10-23 — startup dispatcher, input modification and first rewritten rule

Used actual REA/Ghidra on five bounded 9E handlers (15, 16, 20, 21, 22 in hex).
Preserved Evidence/snapshots and closed each session. Verified 72 declared native
cases for resident segment reference counts, the nonresident boundary, allocation
cursor save/restore, I/O-result reads and conditional PC+2 continuation. Complete
nonresident loader/device behavior remains unverified. Added the missing LDX
absolute, STA absolute-X and DEC absolute-X instructions to the bounded analysis
probe, with flags/cross-page tests; this is not an application execution backend.
Persisted five service interface comments in the existing Ghidra interpreter project.

Enabled those evidenced continuations in the static decoder. All six Play startup
segment-1 procedures now have complete CFGs under the selected normal-return
model. Root control reads bits 8..11 of table-29 word index 45, splits low states
through P3 and others through P4, and exits at state >=11. Case tables identify
calls into segments 13/15/16/17/18/19/20/21 and the P5 subdispatch to 14/8. Detailed
semantic state names, the eight reference-argument contracts of segment 21 and
physical input timing remain open. Current combined graph: 45,033 reachable
instructions and 3,462 static call sites across the same 590 procedure records.

Reconstructed segment-20/P18's nonnegative-domain integer scaling helper from its
actual short-local operands, 10 parameter bytes, branches and native handler
results. The branch changes multiplication/division order and creates observable
rounding discontinuities (x=8,y=4095,d=8 returns 4088). Compared 733 synthetic cases
and three zero-divisor/error-106 boundaries. Only after that check, rewrote the
selected contract as native/SunDogLogic/GameIntegerScale.swift. Direct Swift
compilation matched all 733 native-backed cases; negative inputs are explicitly
outside the exposed contract. This is one original game function port, not a
complete trading system. Caller value meanings, balance and inventory ownership
remain open. No app shell or emulator core was added.

Traced SYSTEM.LIBRARY/native P2 as an edge/level channel filter. Static installation
patches D004/D005; the retained Utility-menu LC1 points from the initial ADD16
handler D71D to hook A29B. The hook ORs C061/C062 into pending bytes, preserves
A/status and jumps via a saved operand back to ADD16. This is a concrete modified
p-system dispatch path. The first hook slice omitted the trailing JMP operands;
retained it and reimported the full three-byte JMP before asserting the chain.
Actual REA IDs, hashes and capture scope are in button-input-evidence.json.

Compared 512 native filter fixtures, 256 latch-body fixtures and two install/restore
fixtures against reconstructed expressions. Hardware reads were declared RAM
samples, not live device execution. Added OR absolute-X and a flags/cross-page test.
Persisted six input/hook labels with Ghidra comment readback and project-save checks.
No new reference emulator was run; the existing capture was used only as corroboration.
Python suite: 77 deterministic tests. Native Swift rule: 733 cases, three zero-error
cases and an explicit unverified-domain rejection. Complete joystick/keyboard event
construction, game-state ownership, transaction rules and rendering edge cases remain.

## 2026-10-23 — Complete structural disassembly milestone

Completed all 590 format-defined archive procedures: 559 p-code procedures with
49,384 instructions, and 31 native procedures with 1,995 instructions. The native
loader's four backward relocation groups account for 154 fixups. Actual Ghidra
exports persist all native bodies and seven recovered boot/runtime memory views.
REA confirms both overlapping 6502 entries at D029 and D5D3 without overwriting
their canonical BIT instruction contexts.

Resolved the former service decoding boundaries by native instruction-format
evidence for 41 baseline selector cells. EXIT is a nonlocal transfer, not ordinary
fallthrough. Explicit procedure EXIT-IC metadata recovers separate epilogues;
13 otherwise unreachable compiler jumps require independently matching adjacent
boundaries and existing destinations. The generated reset stub is accounted for
through exact handler writes, stopping before hardware or ROM execution.

Independent coverage accepts all identified procedure byte envelopes with zero
unclassified bytes or ownership conflicts. Inferred zero alignment is separately
identified; unreferenced boot/runtime DB stays unknown-role. Completion is
structural, not a claim of complete game semantics or reconstruction of unreadable
Play track 34. Next: assign state/data ownership and reconstruct native input,
graphics and gameplay interfaces for a direct macOS implementation.

Reproduction: `python3 tools/disassemble_all.py`; listing index and report hashes
are in `analysis/disassembly-index.json`. Full listings and source media remain
ignored. Validation: 94 deterministic Python tests pass. Publication requires a
separate all-history media/secret audit and a configured destination remote.
