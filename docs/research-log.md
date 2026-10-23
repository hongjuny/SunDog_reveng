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
