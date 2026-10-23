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
