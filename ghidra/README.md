# Persistent native analysis

Run `sh tools/run_ghidra.sh` from the repository. The wrapper imports only bounded,
source-mapped native regions with `6502:LE:16:default` and explicit load bases.
All programs share local project `ghidra/projects/SunDog`; annotations are rebuilt
by `scripts/ExportBoot.java`. Instruction, reference, and function-body exports
are written to ignored `ghidra/exports/` and should not be published as game code.

Programs: boot stage at 0800, native graphics candidate at 4000, Language Card
bank 2 at D000, post-switch bank 1 view at D000, relocated initializer at 6800, interpreter-ready bank 1 view, and a separate
bank 2 disk-read view.
The bank 2 program's automatic analysis must not be used for the D152 path after
FEF2 reads C08B. Even the bank 1 program is one snapshot: later switching can
invalidate its low-bank analysis. ROM and unobserved ordinary RAM are unmapped.

REA 6.7.0 was available but its connected provider lacked GHIDRA_INSTALL_DIR.
A separate read-only CLI doctor with the correct installation then failed while
compiling its ownership helper because Swift's external module-cache directory
was not writable. Evidence is retained locally in `analysis/local/rea-doctor.json`.
Direct Ghidra analysis completed independently. No REA setup or client config was
changed; a future session can supply proper provider and cache environment.

Milestone 2 seeds the synthetic return continuations 68B9 and 68C4 explicitly.
The interpreter-ready Program marks F248..FE7B as p-code data, replacing the old
native initializer view. Primary/secondary handler seeds come from native table
bytes and exact fetch signatures (`tools/runtime_evidence.py`), not a borrowed VM.
Separate disk-read and general bank 2 Programs preserve the overlapping D026/D029
instruction streams. Ghidra still cannot model later bank switching or changing
JMP operands automatically; reports must be read with those state limits.

Milestone 3 adds `AnnotateOpcodes.java` and `ExportMemoryState.java`. The focused
wrapper `tools/run_opcode_analysis.sh` verifies that tables and p-code are data,
checks annotation readback, and saves snapshot-specific selected handler semantics.
The alias handlers rely on A/Carry/Y left by dispatch; decompiling them as normal
independent functions loses this interface. Reports distinguish the 908 controlled
native-model cases from actual hardware execution and from missing REA Evidence.
