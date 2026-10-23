#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
JAVA_TOOL_OPTIONS="-Duser.home=$PWD/analysis/local/home -Djava.io.tmpdir=$PWD/analysis/local/tmp"
export JAVA_HOME JAVA_TOOL_OPTIONS
python3 tools/button_input_evidence.py
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -import analysis/regions/rea-library22-input2-captured.bin \
  -overwrite -processor 6502:LE:16:default -loader BinaryLoader -loader-baseAddr a208 -scriptPath ghidra/scripts \
  -postScript ExportBoot.java ghidra/exports/library22-input.txt a208,a29b \
  -postScript AnnotateInput.java analysis/button-input-evidence.json analysis/local/ghidra-input.json \
  > analysis/local/ghidra-input.log 2>&1
python3 - <<'PYCODE'
import json
from pathlib import Path
log=Path('analysis/local/ghidra-input.log').read_text()
if 'Persisted six original input/hook annotations.' not in log or 'REPORT: Save succeeded' not in log:raise SystemExit('Input project annotations failed')
rows=json.loads(Path('analysis/local/ghidra-input.json').read_text())
if len(rows)!=6 or not all(r['readback_matches'] for r in rows):raise SystemExit('Input annotation readback incomplete')
Path('analysis/ghidra-input-annotations.json').write_text(json.dumps(dict(program='rea-library22-input2-captured.bin',project_save_verified=True,annotations=rows),indent=2)+'\n')
PYCODE
