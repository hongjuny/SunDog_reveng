#!/usr/bin/env python3
"""Refresh listings and require the independent structural coverage audit.

Requires original media-derived regions, saved REA evidence, and native Ghidra
exports. Native export rebuild commands are documented in native-disassembly.md.
Complete instruction listings remain private under analysis/local/.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ('service_instruction_formats.py', 'pcode_analysis.py', 'disassembly_coverage.py'):
        subprocess.run([sys.executable, str(ROOT / 'tools' / name)], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    coverage = json.loads((ROOT / 'analysis/disassembly-coverage.json').read_text())
    if not coverage['full_disassembly_accepted']:
        raise SystemExit('Structural disassembly audit rejected completion; inspect coverage report.')
    files = []
    for pattern in ('analysis/local/pcode/*.txt', 'analysis/local/native-complete/*.txt',
                    'analysis/local/native-stages/*.txt'):
        for path in sorted(ROOT.glob(pattern)):
            files.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    reports = {}
    for name in ('disassembly-coverage', 'pcode-callgraph', 'native-archive-disassembly',
                 'native-stage-disassembly', 'service-instruction-formats'):
        path = ROOT / 'analysis' / (name + '.json')
        reports[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = dict(accepted=True, scope=coverage['acceptance_scope'], totals=coverage['totals'],
                  reports=reports, private_listings=files,
                  limitations=['Unreadable Play track 34 remains unknown.',
                               'Gameplay semantics and unknown-role bytes require further research.',
                               'Native exports and REA evidence must first be regenerated if source inputs change.'])
    (ROOT / 'analysis/disassembly-index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(accepted=True, private_listings=len(files), totals=coverage['totals'])))


if __name__ == '__main__':
    main()
