# SunDog: Frozen Legacy — Apple II v2.0 investigation

Evidence-based reverse engineering of the supplied Utility and Play WOZ images.
Original media and derived game binaries are local-only and ignored by Git. No
Atari ST binary compatibility is assumed.

Reproduce from repository root (Python 3, standard library only):

```sh
python3 -m unittest discover -s tests -v
python3 tools/disk_analysis.py
python3 tools/verify_woz.py --full
sh tools/run_ghidra.sh
```

`verify_woz.py` accepts `--cp2 PATH`. `run_ghidra.sh` accepts
`GHIDRA_INSTALL_DIR` and `JAVA_HOME` environment overrides. Place the two original
WOZ files in `disk/` and the supplied DOS-order images in `extracted/utility.do`
and `extracted/play.do`. Neither input directory is modified by these tools.
The full verification independently decodes every WOZ sector slot, compares known
bytes, and exports only complete readable tracks. It reproduces all 1,104 readable
sectors; Play Track 34 remains unknown. Decoder file hashes are recorded.

Start with [native-to-Pascal handoff](docs/runtime-handoff.md), [disk layout](docs/disk-layout.md), [boot process](docs/boot-process.md),
and [research log](docs/research-log.md). The first milestone is static analysis,
not an observed emulator boot. Unreadable Play Track 34 remains unknown.

Run `python3 tools/structural_evidence.py` after generating disk and boot regions
to reproduce HGR table and directory-shape checks. Thirty-six deterministic tests
require no original media. Raw searches, binaries, projects and disassembly stay
local; structured statistics and provenance are versioned.

This workspace disallows writing root `.git`. Local history is stored separately;
use `sh tools/git-local.sh status` and `sh tools/git-local.sh log --oneline`.

Milestone 2 identifies the bank 1 fetch loop at `$D293`, primary and secondary
native dispatch tables, the custom bootstrap directory at block 79, and the first
p-code address `$F248`. `run_ghidra.sh` also generates the archive inventory and a
separate interpreter-ready memory snapshot. This remains static reconstruction,
not a hardware/emulator execution trace or a full p-code disassembler.

The current ordered tool-integration checkpoints are in
[checkpoints](docs/milestones.md). Actual REA with Ghidra 12.1.4 passed the native
connection test and [bounded memory comparison](docs/rea-memory-views.md).
Six memory imports verified 7,825 complete bytes, bank-specific D152 entries,
the initial p-code overlay and relocated initializer. Evidence IDs and limits are
in `analysis/rea-memory-crosscheck.json`; full Evidence and snapshots stay local.

Selected Apple II [opcode semantics](docs/opcode-semantics.md) are checked through
908 controlled native-handler replay cases, without claiming a full CPU/device
emulator or p-code disassembler. `sh tools/run_opcode_analysis.sh` updates the
focused Ghidra annotations, memory classification checks and startup-prefix probe.
These direct checks retain native/data annotations in the persistent project;
REA's temporary imports do not mirror them or emulate Language Card hardware.

To review the explicitly requested REA client environment merge, run
`python3 tools/configure_rea.py`. `--apply` performs the backed-up, scoped change
when executed with normal access to the global settings file. This restricted
session's earlier apply attempt was denied before writing; the user subsequently
applied it successfully and reconnected. See [connection record](docs/rea-integration.md).
No configuration reapplication is needed for the verified connection.
