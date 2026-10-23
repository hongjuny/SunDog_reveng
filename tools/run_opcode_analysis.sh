#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
JAVA_TOOL_OPTIONS="-Duser.home=$PWD/analysis/local/home -Djava.io.tmpdir=$PWD/analysis/local/tmp"
export JAVA_HOME JAVA_TOOL_OPTIONS
mkdir -p analysis/local ghidra/exports
python3 tools/opcode_evidence.py
python3 - <<'PYCODE'
from pathlib import Path
for name in ('ghidra-interpreter-memory','ghidra-opcode-annotations'):
    Path('analysis/local/'+name+'.next.json').unlink(missing_ok=True)
PYCODE
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/interpreter-ready.bin -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr d000 -scriptPath ghidra/scripts -postScript ExportBoot.java ghidra/exports/interpreter-ready.txt "$(cat analysis/local/ready-seeds.txt)" -postScript AnnotateOpcodes.java analysis/opcode-evidence.json analysis/local/ghidra-opcode-annotations.next.json -postScript ExportMemoryState.java analysis/local/ghidra-interpreter-memory.next.json > analysis/local/ghidra-opcodes.log 2>&1

python3 - <<'PYCODE'
from pathlib import Path
log=Path('analysis/local/ghidra-opcodes.log').read_text()
if 'native handler entries from verified' not in log or 'REPORT: Save succeeded' not in log:
    raise SystemExit('Ghidra annotations or project save did not complete; inspect the log')
PYCODE
python3 tools/verify_memory_views.py --state analysis/local/ghidra-interpreter-memory.next.json --annotations analysis/local/ghidra-opcode-annotations.next.json
python3 - <<'PYCODE'
from pathlib import Path
for name in ('ghidra-interpreter-memory','ghidra-opcode-annotations'):
    Path('analysis/local/'+name+'.next.json').replace('analysis/'+name+'.json')
PYCODE
python3 tools/probe_startup_prefix.py
