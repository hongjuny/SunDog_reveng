#!/usr/bin/env python3
"""Record a keyboard event at a real input-read boundary of the reference machine."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import time
from reference_runtime import ROOT,DEFAULT_EMULATOR,Control,capture_frame,sha

def input_trace(source,output,key=0x15,checkpoint="after-720-frames",turbo="1"):
    if not checkpoint or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in checkpoint):raise ValueError("invalid checkpoint")
    if not 1 <= key <= 0x7f:raise ValueError('key must be nonzero 7-bit ASCII')
    if output.exists():raise ValueError('existing evidence must be preserved')
    output.mkdir(parents=True)
    manifest=json.loads((source/'manifest.json').read_text())
    boot=json.loads((Path(manifest['source_capture'])/'manifest.json').read_text())
    name=boot.get('media_file','utility.woz');disk=output/name;shutil.copyfile(source/name,disk)
    parent,child=socket.socketpair();env=os.environ.copy()
    env.update(A2M_CONTROL_FD=str(child.fileno()),SDL_AUDIODRIVER='dummy')
    command=[str(DEFAULT_EMULATOR.resolve()),'--headless','--control-port=6510','--noini','--nosaveini',
             '--model='+boot['model'],'--mb-slot=0','--history-memory=0','--disk='+str(disk.resolve()),
             '--sna='+str((source/(checkpoint+'.a2state')).resolve()),'--log-level=warn']
    report=dict(method='Observed keyboard event against original game in reference emulator',
                source_capture=str(source),source_snapshot_sha256=sha((source/(checkpoint+'.a2state')).read_bytes()),
                key=key,checkpoint=checkpoint,turbo=turbo,model=boot['model'],
                executable_sha256=sha(DEFAULT_EMULATOR.read_bytes()),events=[],status='in_progress')
    process=None;c=None
    def record(label):
        ram=c.memory(0,65536,'main');(output/(label+'-main.bin')).write_bytes(ram)
        event=dict(label=label,cpu=c.command('get-cpu')['text'],state=c.command('get-state')['text'],
                   softswitches=c.command('get-softswitches')['text'],main_sha256=sha(ram),
                   pcode_pc=hex(int.from_bytes(ram[0x58:0x5a],'little')),frame=capture_frame(c,output,label))
        c.command('save-state '+str((output/(label+'.a2state')).resolve()))
        report['events'].append(event);print(json.dumps(dict(label=label,cpu=event['cpu'],pcode_pc=event['pcode_pc'])),flush=True)
    try:
        with (output/'emulator.log').open('wb') as log:
            process=subprocess.Popen(command,cwd=output,env=env,pass_fds=(child.fileno(),),stdout=log,stderr=subprocess.STDOUT)
        child.close();c=Control(parent);c.command('hello');c.command('pause');c.command('wait-paused 2000')
        c.command('set-disk-writable 6 0 0');c.command('set-turbo '+turbo)
        c.command('break-clear-all');c.command('break-create exec $D6E0 actions=break d000=lc2')
        c.command('run');c.command('wait-paused 5000')
        record('keyboard-read')
        c.command('break-clear-all');c.command('break-create exec $D6E3 actions=break d000=lc2')
        # a2m paste/key resumes execution: arm the next boundary before injection.
        c.command(f'key ${key:02X}');c.command('wait-paused 5000');record('keyboard-loaded')
        cpu=report['events'][-1]['cpu'];match=re.search(r'\ba=([0-9A-Fa-f]{2})\b',cpu)
        if not match or int(match[1],16)!=(key|0x80):raise ValueError('keyboard latch did not contain the requested key')
        report['keyboard_latch_verified']=True
        c.command('break-clear-all');c.command('run');c.command('wait-frame 60 10000')
        c.command('pause');c.command('wait-paused 2000');record('after-key')
        report['status']='input_boundary_observed'
    except Exception as error:
        report.update(status='capture_stopped',error=str(error))
        if c is not None:
            try:
                c.command('pause');c.command('wait-paused 2000');record('stopped-diagnostic')
            except Exception as diagnostic:report['diagnostic_error']=str(diagnostic)
        raise
    finally:
        if c is not None:(output/'control-log.json').write_text(json.dumps(c.log,indent=2)+'\n')
        parent.close();child.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        report['private_copy_unchanged']=sha(disk.read_bytes())==boot['original_media_sha256']
        (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--key',type=lambda x:int(x,0),default=0x15)
    p.add_argument('--output',type=Path,default=ROOT/'analysis/local/reference'/('input-'+time.strftime('%Y%m%d-%H%M%S')))
    p.add_argument('--checkpoint',default='after-720-frames');p.add_argument('--turbo',choices=['1','max'],default='1')
    a=p.parse_args();input_trace(a.source.resolve(),a.output.resolve(),a.key,a.checkpoint,a.turbo)
