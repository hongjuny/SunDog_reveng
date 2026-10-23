# SunDog: Frozen Legacy — Apple II v2.0 investigation

Evidence-based reverse engineering of the supplied Utility and Play WOZ images.
Original media and derived game binaries are local-only and ignored by Git. No
Atari ST binary compatibility is assumed.

Reproduce from repository root (Python 3, standard library only):

```sh
python3 -m unittest discover -s tests -v
python3 tools/disk_analysis.py
python3 tools/verify_woz.py
sh tools/run_ghidra.sh
```

`verify_woz.py` accepts `--cp2 PATH`. `run_ghidra.sh` accepts
`GHIDRA_INSTALL_DIR` and `JAVA_HOME` environment overrides. Place the two original
WOZ files in `disk/` and the supplied DOS-order images in `extracted/utility.do`
and `extracted/play.do`. Neither input directory is modified by these tools.
The extraction that produced the supplied `.do` files is not yet reproduced;
WOZ spot-checks are separate from complete extraction validation.

Start with [disk layout](docs/disk-layout.md), [boot process](docs/boot-process.md),
and [research log](docs/research-log.md). The first milestone is static analysis,
not an observed emulator boot. Unreadable Play Track 34 remains unknown.
