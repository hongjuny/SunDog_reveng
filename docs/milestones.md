# Investigation checkpoints

The existing disk/native-to-Pascal milestones remain completed static analysis.
The following ordered checkpoints add active REA–Ghidra cross-checking. A blocked
connection is not counted as passed merely because a launcher exists.

| Checkpoint | Current state | Acceptance evidence |
|---|---|---|
| 1. REA–Ghidra connection | Installation verified; client environment/reconnection pending | Actual REA load verification, D293 instruction and bounded references agreeing with direct Ghidra |
| 2. Memory views | Existing views prepared; cross-tool review queued | Bank/overlay state and source bytes agree; p-code data never decoded as native code |
| 3. Instruction semantics | Native dispatch identified; opcode catalogue queued | Operand lengths, stack effects and branches established from Apple II handlers |
| 4. Calls and segment loading | Initial load/procedure pointers known; general mechanism queued | Verified call/return, relocation and allocation paths |
| 5. SYSTEM.STARTUP conflicts | Four descriptors exceed Utility directory extent | Explain disk selection and descriptor addressing without slicing unrelated bytes |
| 6. P-code analysis tool | Not implemented | Implement only verified instructions and segment structures, with deterministic tests |
| 7. Controlled execution | Not yet observed | Reproducible ROM/emulator setup and memory/disk/bank trace |
| 8. Game subsystems | Initial HGR addressing known | Trace UI/input, ship, trade, navigation, environments and persistence with provenance |
| 9. Performance | Not measured | Repeatable interpreter, disk, graphics and memory-management measurements |

See [connection checkpoint](rea-integration.md) for the exact prepared change and
verification target. Continue checkpoint 1 after reconnection; do not silently
substitute shell-only Ghidra results for REA Evidence.
