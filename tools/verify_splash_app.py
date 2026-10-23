#!/usr/bin/env python3
"""Verify the real app bundle at original routine cycle boundaries without GUI."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()

def main():
    binary = ROOT/'Build/SunDog.app/Contents/MacOS/SunDog'
    path = ROOT/'analysis/local/splash-reveal/writes.json'
    proof = json.loads((ROOT/'analysis/native-splash-verification.json').read_text())
    if SHA(path.read_bytes()) != proof['fixture_sha256']:raise ValueError('Original write fixture changed')
    fixture = json.loads(path.read_text())
    out = ROOT/'analysis/local/native-build'
    records = []
    for cycle in (0,104,105,10000,50000,125000,250000,400000,515593):
        page = bytearray(8192);count = 0
        for row in fixture['writes']:
            if row['cycles'] > cycle:break
            page[row['offset']] = row['value'];count += 1
        actual = json.loads(subprocess.check_output([str(binary),'--diagnose','--at-cycle',str(cycle),
            '--export-startup',str(out/f'splash-cycle-{cycle}.png')],text=True))
        if actual['page_sha256'] != SHA(page) or actual['applied_writes'] != count:
            raise ValueError(f'App differs from original HGR writes at cycle {cycle}')
        records.append(dict(cycle=cycle,writes=count,page_sha256=SHA(page)))
    expected_rgba = '80d5864f3e444bc5dd96f8839e5a02e4b04e25e6246598ffdfc092a514d0ff4a'
    if actual['rgba_sha256'] != expected_rgba:raise ValueError('Final rendered frame differs from retained original reference')
    report = dict(method='Actual macOS bundle headless startup model versus original native HGR write fixture',
        snapshots=records,all_matched=True,final_rgba_sha256=expected_rgba,
        final_reference='Retained original pc-FEF2 Apple II Plus execution; bitmap itself comes directly from Utility disk',
        executable_sha256=SHA(binary.read_bytes()),gui_verified=False,
        limitations=['This verifies model, timing lookup and frame production; window presentation remains unverified in the restricted session.',
                     'Nominal host clock and sampled presentation do not establish exact physical Apple II scanout.'])
    (ROOT/'analysis/splash-app-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(snapshots=len(records),all_matched=True,gui_verified=False)))

if __name__=='__main__':main()
