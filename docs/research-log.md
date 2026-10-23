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
wrapper's explicit temporary directory avoids that path on subsequent runs.

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
