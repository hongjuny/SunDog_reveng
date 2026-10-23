#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
export JAVA_HOME
mkdir -p analysis/local/home analysis/local/tmp ghidra/projects ghidra/exports
JAVA_TOOL_OPTIONS="-Duser.home=$PWD/analysis/local/home -Djava.io.tmpdir=$PWD/analysis/local/tmp"
export JAVA_TOOL_OPTIONS
python3 tools/prepare_boot.py
python3 tools/boot_regions.py
python3 tools/runtime_evidence.py
python3 tools/archive_evidence.py
python3 tools/boot_handoff.py
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/boot-stage.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 0800 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/boot.txt > analysis/local/ghidra.log 2>&1
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/initial-4000.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 4000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/initial-4000.txt 4000 > analysis/local/ghidra-4000.log 2>&1
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/lc-bank2.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/lc-bank2.txt "$(cat analysis/local/bios-seeds.txt)" > analysis/local/ghidra-lc.log 2>&1

"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/runtime-bank1.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/runtime-bank1.txt "$(cat analysis/local/runtime-seeds.txt)" > analysis/local/ghidra-runtime.log 2>&1

"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/relocated-6800.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 6800 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/relocated-6800.txt 6800,68b9,68c4 > analysis/local/ghidra-6800.log 2>&1

python3 - <<'PYCODE'
from pathlib import Path
p=Path('analysis/local/runtime-seeds.txt')
seeds=p.read_text().split(',')
Path('analysis/local/ready-seeds.txt').write_text(','.join(n for n in seeds if n!='fef2'))
Path('analysis/regions/bios-read-bank2.bin').write_bytes(Path('analysis/regions/lc-bank2.bin').read_bytes())
PYCODE
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/interpreter-ready.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/interpreter-ready.txt "$(cat analysis/local/ready-seeds.txt)" > analysis/local/ghidra-ready.log 2>&1
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/bios-read-bank2.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/bios-read-bank2.txt d029 > analysis/local/ghidra-read.log 2>&1
