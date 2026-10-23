#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
JAVA_TOOL_OPTIONS="-Duser.home=$PWD/analysis/local/home -Djava.io.tmpdir=$PWD/analysis/local/tmp"
export JAVA_HOME JAVA_TOOL_OPTIONS
python3 tools/secondary_services.py
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog -process interpreter-ready.bin -noanalysis \
  -scriptPath ghidra/scripts -postScript AnnotateServices.java analysis/secondary-services.json analysis/local/ghidra-services.json \
  > analysis/local/ghidra-services.log 2>&1
python3 - <<'PYCODE'
import json
from pathlib import Path
log=Path('analysis/local/ghidra-services.log').read_text()
if 'Persisted five selected service interface annotations.' not in log or 'REPORT: Save succeeded' not in log:raise SystemExit('Service annotations/project save failed')
rows=json.loads(Path('analysis/local/ghidra-services.json').read_text())
if len(rows)!=5 or not all(r['readback_matches'] for r in rows):raise SystemExit('Incomplete annotation readback')
Path('analysis/ghidra-service-annotations.json').write_text(json.dumps(dict(program='interpreter-ready.bin',project_save_verified=True,annotations=rows),indent=2)+'\n')
PYCODE
python3 tools/pcode_analysis.py
python3 tools/startup_flow.py
python3 tools/trade_scaling_evidence.py
python3 tools/verify_native_rules.py
