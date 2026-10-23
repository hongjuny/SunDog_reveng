#!/usr/bin/env python3
"""Continue a captured original execution; bounded reference frames, no game patches."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from reference_runtime import ROOT,DEFAULT_EMULATOR,Control,capture_frame,run_until,sha

def follow(capture,output,executable=DEFAULT_EMULATOR):
    if output.exists():raise ValueError('preserve existing output')
    source=json.loads((capture/'manifest.json').read_text())
    if source['status']!='boot_to_first_bios_observed':raise ValueError('need completed boot reference')
    output.mkdir(parents=True)
    media_name=source.get('media_file','utility.woz')
    media=output/media_name;shutil.copyfile(capture/media_name,media)
    left,right=socket.socketpair()
    env=os.environ.copy();env.update(A2M_CONTROL_FD=str(right.fileno()),SDL_AUDIODRIVER='dummy')
    command=[str(executable.resolve()),'--headless','--control-port=6510','--noini','--nosaveini',
             '--model='+source['model'],'--mb-slot=0','--history-memory=0','--disk='+str(media.resolve()),
             '--sna='+str((capture/'pc-ff06.a2state').resolve()),'--log-level=warn']
    report=dict(method='Observed continuation of captured original game execution in a2m; no game memory patches',
                source_capture=str(capture),source_snapshot_sha256=sha((capture/'pc-ff06.a2state').read_bytes()),
                executable_sha256=sha(executable.read_bytes()),model=source['model'],events=[],status='in_progress')
    process=None;c=None
    def record(label):
        ram=c.memory(0,65536,'main');(output/(label+'-main.bin')).write_bytes(ram)
        event=dict(label=label,cpu=c.command('get-cpu')['text'],state=c.command('get-state')['text'],
                   softswitches=c.command('get-softswitches')['text'],pcode_pc=hex(int.from_bytes(ram[0x58:0x5a],'little')),
                   main_sha256=sha(ram),frame=capture_frame(c,output,label))
        for mode in ('lc1','lc2'):(output/(label+'-'+mode+'.bin')).write_bytes(c.memory(0xd000,12288,mode))
        c.command('save-state '+str((output/(label+'.a2state')).resolve()))
        report['events'].append(event);print(json.dumps({k:event[k] for k in ('label','cpu','pcode_pc')}),flush=True)
        (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        return event
    try:
        with (output/'emulator.log').open('wb') as log:
            process=subprocess.Popen(command,cwd=output,env=env,pass_fds=(right.fileno(),),stdout=log,stderr=subprocess.STDOUT)
        right.close();c=Control(left);c.command('hello');c.command('pause');c.command('wait-paused 2000')
        c.command('set-disk-writable 6 0 0');c.command('set-turbo max')
        run_until(c,0xd7ef);e=record('bios-bank2')
        expected=(ROOT/'analysis/regions/lc-bank2.bin').read_bytes()[0x7ef:0x7ff]
        if c.memory(0xd7ef,16)!=expected:raise ValueError('BIOS mapping is not the expected bank2 bytes')
        run_until(c,0xd293);e=record('first-bios-return')
        if e['pcode_pc']!='0xf24e':raise ValueError('first service returned to unexpected p-code PC')
        c.command('break-clear-all')
        for label,frames in (('after-120-frames',120),('after-720-frames',600)):
            c.command('run');c.command(f'wait-frame {frames} 15000');c.command('pause');c.command('wait-paused 2000')
            record(label)
        report['status']='reference_continuation_captured'
    except Exception as error:
        report.update(status='capture_stopped',error=str(error));raise
    finally:
        if c is not None:(output/'control-log.json').write_text(json.dumps(c.log,indent=2)+'\n')
        left.close();right.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        report['mounted_copy_unchanged']=sha(media.read_bytes())==source['original_media_sha256']
        (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'analysis/local/reference'/('follow-'+time.strftime('%Y%m%d-%H%M%S')))
    args=p.parse_args();follow(args.capture.resolve(),args.output.resolve())
