#!/usr/bin/env python3
"""Compare the Swift HGR decoder with retained reference frames; emit metadata only."""
import argparse
import json
from pathlib import Path
import subprocess
from reference_runtime import ROOT, sha


def compare(captures, inspector):
    rows = []
    for directory in captures:
        manifest = json.loads((directory/'manifest.json').read_text())
        for record in manifest.get('checkpoints', manifest.get('events', [])):
            frame = record.get('frame', {})
            label = record.get('label', Path(frame.get('pixels', '')).stem)
            row = dict(capture=str(directory.relative_to(ROOT)), label=label,
                       memory_sha256=record.get('main_sha256'), frame_sha256=frame.get('sha256'))
            if frame.get('wire_format') != 'argb8888-bgra-little-endian':
                row.update(status='excluded', reason='legacy channel conversion not verified')
            else:
                expected = directory/frame['pixels']
                if sha(expected.read_bytes()) != frame['sha256']:
                    raise ValueError('reference frame hash mismatch: '+str(expected))
                run = subprocess.run([str(inspector), '--capture', str(directory), '--label', label,
                                      '--compare', str(expected)], capture_output=True, text=True)
                result = json.loads(run.stdout) if run.stdout.strip() else dict(error=run.stderr.strip())
                row.update(status=('matched' if result.get('matches_reference') else
                                   'mismatch' if run.returncode == 2 else 'unsupported_or_error'),
                           exit_code=run.returncode, result=result)
            rows.append(row)
    return dict(method='Swift CPU HGR decode of hashed captured main RAM versus a2m captured RGBA',
                inspector_sha256=sha(inspector.read_bytes()), preset='a2m-hgr-colour-v1',
                limitations=['Same digital colour preset, not analog NTSC/hardware validation',
                             'Reference frontend frames may lag the paused machine RAM',
                             'GPU and display colour conversion are not tested by this comparison'],
                counts={s:sum(r['status']==s for r in rows) for s in
                        ('matched','mismatch','excluded','unsupported_or_error')}, records=rows)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('captures',nargs='+',type=Path)
    p.add_argument('--inspector',type=Path,default=ROOT/'analysis/local/native-build/SunDogInspect')
    p.add_argument('--output',type=Path,default=ROOT/'analysis/video-comparison.json')
    a=p.parse_args();r=compare([c.resolve() for c in a.captures],a.inspector.resolve())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['counts']))
