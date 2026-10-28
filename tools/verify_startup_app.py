#!/usr/bin/env python3
"""Drive actual native bundle state transitions and verify source-bound frames."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    binary=ROOT/'Build/SunDog.app/Contents/MacOS/SunDog'
    out=ROOT/'analysis/local/native-build'
    expected={'gate':('awaitingBegin','4bcf4c0178d3c8dc719c6e2a57f5e79c595a9108d3f11fd4a2b90f064e001ac5'),
              'choices':('choices',None),'play-disk':('playDisk',None),
              'ship':('ship',json.loads((ROOT/'analysis/initial-ship-asset.json').read_text())['decoded_sha256'])}
    records=[]
    for name,(screen,digest) in expected.items():
        result=json.loads(subprocess.check_output([str(binary),'--diagnose','--startup-screen',name,
            '--export-startup',str(out/f'startup-{name}.png')],text=True))
        if result['error'] or result['screen']!=screen:raise ValueError(f'Native startup failed at {name}: {result}')
        if digest is not None and result['page_sha256']!=digest:raise ValueError(f'Original frame differs at {name}')
        if result['player']!='Bowie' or result['original_state']!=2:raise ValueError('Disk-backed startup profile changed')
        records.append(dict(stage=name,screen=screen,history=result['history'],page_sha256=result['page_sha256']))
    if records[-1]['history']!=['title','awaitingBegin','choices','playDisk','ship']:
        raise ValueError('Startup transition path is incomplete')
    report=dict(method='Actual native bundle title-to-ship script using button edges, original choices and Play marker check',
        executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),stages=records,all_matched=True,
        source_profile='analysis/post-title-flow.json',gui_verified=False,
        limitations=['Initial SHIP graphics are source-decoded; status/cursor overlays and ship interaction are not yet ported.',
                     'Mouse/keyboard bindings and wall-clock gate sampling are host policy.',
                     'Utility and demo program routes are identified but not implemented.'])
    (ROOT/'analysis/startup-app-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stages=len(records),all_matched=True,initial_ship=True)))

if __name__=='__main__':main()
