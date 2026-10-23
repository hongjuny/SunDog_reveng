# Persistent native analysis

Run `sh tools/run_ghidra.sh` from the repository. The wrapper imports only bounded,
source-mapped native regions with `6502:LE:16:default` and explicit load bases.
All programs share local project `ghidra/projects/SunDog`; annotations are rebuilt
by `scripts/ExportBoot.java`. Instruction, reference, and function-body exports
are written to ignored `ghidra/exports/` and should not be published as game code.

Programs: boot stage at 0800, native graphics candidate at 4000, Language Card
bank 2 at D000, post-switch bank 1 view at D000, and relocated initializer at 6800.
The bank 2 program's automatic analysis must not be used for the D152 path after
FEF2 reads C08B. Even the bank 1 program is one snapshot: later switching can
invalidate its low-bank analysis. ROM and unobserved ordinary RAM are unmapped.

REA 6.7.0 was available but its connected provider lacked GHIDRA_INSTALL_DIR.
A separate read-only CLI doctor with the correct installation then failed while
compiling its ownership helper because Swift's external module-cache directory
was not writable. Evidence is retained locally in `analysis/local/rea-doctor.json`.
Direct Ghidra analysis completed independently. No REA setup or client config was
changed; a future session can supply proper provider and cache environment.
