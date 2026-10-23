#!/usr/bin/env python3
"""Compare the Swift text planner with original, narrowly evaluated decoded CFGs."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, str(ROOT / 'tools/text_layout_evidence.py')], cwd=ROOT, check=True)
    output = ROOT / 'analysis/local/text-layout'
    compiler = subprocess.check_output(['xcrun', '--find', 'swiftc'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    sources = [ROOT / 'native/SunDogLogic/WindowTextLayout.swift', ROOT / 'tests/native/VerifyWindowTextLayout.swift']
    binary = output / 'verify-text-layout'
    subprocess.run([compiler, '-swift-version', '6', '-O', '-parse-as-library', '-sdk', sdk,
                    '-target', platform.machine() + '-apple-macosx14.0',
                    '-module-cache-path', str(output / 'module-cache'), *map(str, sources), '-o', str(binary)], check=True)
    cases = output / 'cases.json'
    report = json.loads(subprocess.check_output([str(binary), str(cases)], text=True))
    report.update(method='Swift planner versus bounded original P48/P47/P45/P11/P12 decoded control flow; no full-game execution',
                  evidence='analysis/text-layout-evidence.json',
                  cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
                  source_files={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  limitations=['P44 scrolling and P12 line drawing are not ported.',
                               'Only 80-byte strings, words up to 20 bytes and declared coordinate ranges are supported.',
                               'Unsupported-path partial side effects are not reproduced.'])
    (ROOT / 'analysis/native-text-layout-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
