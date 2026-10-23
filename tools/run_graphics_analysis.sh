#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
JAVA_TOOL_OPTIONS="-Duser.home=$PWD/analysis/local/home -Djava.io.tmpdir=$PWD/analysis/local/tmp"
export JAVA_HOME JAVA_TOOL_OPTIONS
mkdir -p ghidra/projects ghidra/exports analysis/local
python3 tools/play_startup_evidence.py
python3 tools/pcode_analysis.py
python3 tools/graphics_call_evidence.py
python3 tools/glyph_evidence.py
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" ghidra/projects SunDog \
  -import analysis/regions/rea-library22-char9-captured.bin -overwrite -processor 6502:LE:16:default \
  -loader BinaryLoader -loader-baseAddr a934 -scriptPath ghidra/scripts \
  -postScript ExportBoot.java ghidra/exports/library22-glyph.txt a934 \
  -postScript AnnotateGlyph.java analysis/graphics-call-chain.json analysis/local/ghidra-glyph-annotations.json \
  > analysis/local/ghidra-glyph.log 2>&1
python3 - <<'PYCODE'
from pathlib import Path
import json
log=Path('analysis/local/ghidra-glyph.log').read_text()
if 'Persisted six bounded glyph annotations with readback.' not in log or 'REPORT: Save succeeded' not in log:
    raise SystemExit('Ghidra annotations/project save failed; inspect the local log')
rows=json.loads(Path('analysis/local/ghidra-glyph-annotations.json').read_text())
if len(rows)!=6 or not all(r['comment_readback_matches'] for r in rows):raise SystemExit('Annotation readback incomplete')
report=json.loads(Path('analysis/graphics-call-chain.json').read_text())
Path('analysis/ghidra-glyph-annotations.json').write_text(json.dumps(dict(program='rea-library22-char9-captured.bin',source_sha256=report['captured_mapping']['captured_slice_sha256'],project_save_verified=True,annotations=rows),indent=2)+'\n')
print('Six glyph annotations persisted in Ghidra project.')
PYCODE
