#!/usr/bin/env python3
"""Compare Swift reveal order with bounded original 6502 execution and export timing."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]

def main():
    subprocess.run([sys.executable, str(ROOT/'tools/splash_reveal_evidence.py')], cwd=ROOT, check=True)
    out = ROOT/'analysis/local/splash-reveal'
    cases = out/'writes.json'
    fixture = json.loads(cases.read_text())
    compiler = subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources = [ROOT/'native/SunDogLogic/SplashReveal.swift',ROOT/'tests/native/VerifySplashReveal.swift']
    binary = out/'verify-native-splash'
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,
        '-target',platform.machine()+'-apple-macosx14.0','-module-cache-path',str(out/'module-cache'),
        *map(str,sources),'-o',str(binary)],check=True)
    report = json.loads(subprocess.check_output([str(binary),str(cases)],text=True))
    report.update(method='Swift native algorithm versus complete ordered original $4000 HGR writes; bounded analysis-only replay',
        evidence='analysis/splash-reveal-evidence.json',
        source_files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        fixture_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
        limitations=['Nominal 1.023MHz host clock is a declared approximation, not a measured original machine clock.',
                     'Host display samples the original write schedule; no original scanout/raster synchronization is claimed.'])
    (ROOT/'analysis/native-splash-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    timing=dict(write_cycles=[r['cycles'] for r in fixture['writes']],total_cycles=fixture['total_cycles'],
                method='Original binary-mode NMOS6502 routine instruction cycles, ending with RTS; caller JSR excluded')
    (ROOT/'analysis/local/native-assets/sundog-splash-timing.json').write_text(json.dumps(timing,separators=(',',':'))+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
