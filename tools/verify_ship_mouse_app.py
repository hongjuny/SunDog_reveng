#!/usr/bin/env python3
"""Exercise actual native model mouse path; does not claim OS event delivery."""
import json
import subprocess
from initial_game_flow import ROOT,SHA

def main():
    binary=ROOT/'Build/SunDog.app/Contents/MacOS/SunDog'
    records=[]
    for flag in (None,'--ship-mouse-check','--ship-action-check'):
        cmd=[str(binary),'--diagnose','--startup-screen','ship']
        if flag:cmd.append(flag)
        record=json.loads(subprocess.check_output(cmd,text=True))
        if record['error'] or record['screen']!='ship' or record['left_held']:
            raise ValueError(record)
        records.append(record)
    initial,moved,selected=records
    if initial['actor']!=[42,103] or moved['actor']!=[77,103] or moved['pointer']!=[80,100]:
        raise ValueError('Host pointer/held movement route differs')
    if selected['actor']!=initial['actor'] or selected['selected_action']!=1 or not selected['notice']:
        raise ValueError('Release did not select original cockpit target')
    report=dict(executable_sha256=SHA(binary.read_bytes()),all_matched=True,
        initial_actor=initial['actor'],moved_actor=moved['actor'],stationary_release_action=selected['selected_action'],
        scope='Native model used by AppKit mouse callbacks; actual OS event delivery not observed',
        host_policy='33ms per two movement stages; no Apple II timing equivalence',
        limitations=['Facility selection shows a notice; target scenes are not yet implemented','No world simulation/save path'])
    (ROOT/'analysis/ship-mouse-app-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native mouse movement/release action checks passed')
if __name__=='__main__':main()
