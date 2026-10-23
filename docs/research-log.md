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
