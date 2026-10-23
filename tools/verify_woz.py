#!/usr/bin/env python3
"""Read-only CiderPress2 spot-check of image provenance and failed sectors."""
import argparse,json,pathlib,re,subprocess
from disk_analysis import load,offset,digest
ap=argparse.ArgumentParser();ap.add_argument('--cp2',default='/Users/ay5/Projects/CiderPress2/cp2/bin/Release/net10.0/osx-arm64/cp2');args=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];records=[]
for side in ('utility','play'):
    path=next((root/'disk').glob('*'+('Utility' if side=='utility' else 'Play')+'*.woz'));data=load(root/'extracted'/f'{side}.do')
    samples=[(0,0),(0,13),(0,14),(13,0),(17,15),(33,15)]+([(34,s) for s in range(16)] if side=='play' else [(34,15)])
    for t,s in samples:
        r=subprocess.run([args.cp2,'read-sector',str(path),str(t),str(s)],capture_output=True,text=True)
        raw=b''.join(bytes.fromhex(m.group(1)) for m in re.finditer(r'^\s*[0-9a-fA-F]{6}: ((?:[0-9a-fA-F]{2} ){15}[0-9a-fA-F]{2})',r.stdout,re.M))
        rec=dict(side=side,track=t,sector=s,returncode=r.returncode,decoded_bytes=len(raw),matches=len(raw)==256 and raw==data[offset(t,s):offset(t,s)+256],stderr=r.stderr.strip())
        if len(raw)==256:rec['sha256']=digest(raw)
        records.append(rec)
(root/'analysis/woz-checks.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(dict(samples=len(records),matches=sum(r['matches'] for r in records),failed=sum(r['decoded_bytes']!=256 for r in records))))
