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
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/boot-stage.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 0800 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/boot.txt > analysis/local/ghidra.log 2>&1
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/initial-4000.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 4000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/initial-4000.txt 4000 > analysis/local/ghidra-4000.log 2>&1
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/lc-bank2.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/lc-bank2.txt daa9 > analysis/local/ghidra-lc.log 2>&1

"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/runtime-bank1.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/runtime-bank1.txt fef2 > analysis/local/ghidra-runtime.log 2>&1

"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/relocated-6800.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr 6800 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/relocated-6800.txt 6800 > analysis/local/ghidra-6800.log 2>&1
