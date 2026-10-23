#!/usr/bin/env python3
"""Catch original post-background logo writes in an isolated reference process.

Analysis only: this is never an application execution backend. Original media
and snapshot are immutable; all mounted media and results are private copies.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from reference_runtime import ROOT, DEFAULT_EMULATOR, Control, capture_frame, sha

def main():
    source=ROOT/'analysis/local/reference/follow-20261023-120102'
    snapshot=source/'first-bios-return.a2state'
    output=ROOT/'analysis/local/reference'/('logo-write-'+time.strftime('%Y%m%d-%H%M%S'))
    output.mkdir()
    media=output/'utility.do';shutil.copyfile(source/'utility.do',media)
    parent,child=socket.socketpair()
    env=dict(os.environ,A2M_CONTROL_FD=str(child.fileno()),SDL_AUDIODRIVER='dummy')
    command=[str(DEFAULT_EMULATOR.resolve()),'--headless','--control-port=6510','--noini','--nosaveini',
        '--model=plus','--mb-slot=0','--history-memory=0','--disk='+str(media),
        '--sna='+str(snapshot),'--log-level=warn']
    report=dict(method='Original reference data-write breakpoint; no game patches; analysis only',
        source_snapshot_sha256=sha(snapshot.read_bytes()),executable_sha256=sha(DEFAULT_EMULATOR.read_bytes()),
        source_capture=str(source.relative_to(ROOT)),events=[])
    process=None;c=None
    try:
        with (output/'emulator.log').open('wb') as log:
            process=subprocess.Popen(command,cwd=output,env=env,pass_fds=(child.fileno(),),stdout=log,stderr=subprocess.STDOUT)
        child.close();c=Control(parent)
        c.command('hello');c.command('pause');c.command('wait-paused 2000')
        c.command('set-disk-writable 6 0 0');c.command('break-clear-all');c.command('set-turbo max')
        c.command('break-create write $2201 actions=break')
        c.command('run')
        try:c.command('wait-paused 5000')
        except RuntimeError as failure:
            report['wait_error']=str(failure)
            c.command('pause');c.command('wait-paused 2000')
        label='timeout-stop' if 'wait_error' in report else 'first-logo-write'
        for label in (label,):
            memory=c.memory(0,65536,'main');(output/(label+'-main.bin')).write_bytes(memory)
            for bank in ('lc1','lc2'):(output/(label+'-'+bank+'.bin')).write_bytes(c.memory(0xd000,12288,bank))
            event=dict(label=label,cpu=c.command('get-cpu')['text'],state=c.command('get-state')['text'],
                switches=c.command('get-softswitches')['text'],pcode_pc=hex(int.from_bytes(memory[0x58:0x5a],'little')),
                main_sha256=sha(memory),frame=capture_frame(c,output,label))
            report['events'].append(event)
            c.command('save-state '+str(output/(label+'.a2state')))
        report['status']='timeout_snapshot' if 'wait_error' in report else 'watchpoint_observed'
        print(json.dumps(dict(output=str(output.relative_to(ROOT)),events=[{k:v for k,v in e.items() if k!='frame'} for e in report['events']]),indent=2))
    finally:
        if c:(output/'control-log.json').write_text(json.dumps(c.log,indent=2)+'\n')
        parent.close();child.close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        report['mounted_copy_unchanged']=sha(media.read_bytes())==sha((source/'utility.do').read_bytes())
        (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
