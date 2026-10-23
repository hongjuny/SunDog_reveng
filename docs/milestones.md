# Investigation checkpoints

The existing disk/native-to-Pascal milestones remain completed static analysis.
The following ordered checkpoints add active REA–Ghidra cross-checking. A blocked
connection is not counted as passed merely because a launcher exists.

| Checkpoint | Current state | Acceptance evidence |
|---|---|---|
| 1. REA–Ghidra connection | Passed 2026-10-23: actual REA/Ghidra 12.1.4 load, instruction, assembly and xrefs verified | Actual REA load verification, D293 instruction and bounded references agreeing with direct Ghidra |
| 2. Memory views | Bounded static acceptance passed: six actual REA imports, 7,825 bytes; direct Ghidra array/type checks pass | Bank-specific D152, overlay and relocation agree; full bank emulation and annotation transfer remain outside this check |
| 3. Primary opcode identification | Passed within selected scope: all 256 values identified, 4,976 cases; zero unidentified high entries; service/runtime boundaries explicit | Operand lengths, stack effects and branches established from Apple II handlers |
| 4. Calls and segment loading | Synthetic call/return frames and native trampoline checked; nonresident/release/device paths and actual startup execution remain open | Verified call/return, relocation and allocation paths |
| 5. SYSTEM.STARTUP conflicts | Four descriptors exceed Utility directory extent | Explain disk selection and descriptor addressing without slicing unrelated bytes |
| 6. P-code analysis tool | Not implemented | Implement only verified instructions and segment structures, with deterministic tests |
| 7. Controlled execution | Not yet observed | Reproducible ROM/emulator setup and memory/disk/bank trace |
| 8. Game subsystems | Initial HGR addressing known | Trace UI/input, ship, trade, navigation, environments and persistence with provenance |
| 9. Performance | Not measured | Repeatable interpreter, disk, graphics and memory-management measurements |

See [connection checkpoint](rea-integration.md) and
`analysis/rea-crosscheck.json` for connection acceptance. See
[memory comparison](rea-memory-views.md) and `analysis/rea-memory-crosscheck.json`
for checkpoint 2. Primary identification is now complete; see the
[completion report](primary-opcode-completion.md). Next work concerns secondary
services, nonresident segments/device behavior and observed execution, rather than
unidentified primary entries.
