#!/usr/bin/env python3
"""Advance a retained reference snapshot without patches; preserve full evidence."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from reference_runtime import ROOT, DEFAULT_EMULATOR, Control, capture_frame, sha


def advance(source, label, output, frames=720):
    if output.exists(): raise ValueError('preserve existing evidence')
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        raise ValueError('invalid checkpoint')
    if not 1 <= frames <= 3600: raise ValueError('bounded frame count required')
    media = list(source.glob('utility.do')) + list(source.glob('utility.woz'))
    if len(media) != 1: raise ValueError('expected one Utility medium')
    lineage = source
    model = None
    for _ in range(8):
        metadata = json.loads((lineage/'manifest.json').read_text())
        model = metadata.get('model')
        if model: break
        lineage = Path(metadata['source_capture'])
    if model not in ('plus', 'enh'): raise ValueError('unknown source model')
    snapshot = source / (label + '.a2state')
    output.mkdir(parents=True)
    disk = output / media[0].name
    shutil.copyfile(media[0], disk)
    parent, child = socket.socketpair()
    env = dict(os.environ, A2M_CONTROL_FD=str(child.fileno()), SDL_AUDIODRIVER='dummy')
    command = [str(DEFAULT_EMULATOR.resolve()), '--headless', '--control-port=6510', '--noini',
               '--nosaveini', '--model='+model, '--mb-slot=0', '--history-memory=0',
               '--disk=' + str(disk), '--sna=' + str(snapshot), '--log-level=warn']
    report = dict(method='Bounded reference continuation; no game memory patches', model=model, executable_sha256=sha(DEFAULT_EMULATOR.read_bytes()),
                  source_capture=str(source), source_label=label, frames=frames,
                  source_snapshot_sha256=sha(snapshot.read_bytes()), events=[], status='in_progress')
    process = None
    control = None
    try:
        with (output / 'emulator.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=output, env=env, pass_fds=(child.fileno(),),
                                       stdout=log, stderr=subprocess.STDOUT)
        child.close()
        control = Control(parent)
        control.command('hello'); control.command('pause'); control.command('wait-paused 2000')
        control.command('set-disk-writable 6 0 0'); control.command('break-clear-all')
        control.command('set-turbo max'); control.command('run')
        control.command(f'wait-frame {frames} 30000')
        control.command('pause'); control.command('wait-paused 2000')
        name = 'advanced'
        ram = control.memory(0, 65536, 'main')
        (output / (name + '-main.bin')).write_bytes(ram)
        for mode in ('lc1', 'lc2'):
            (output / (name + '-' + mode + '.bin')).write_bytes(control.memory(0xd000, 12288, mode))
        report['events'].append(dict(label=name, main_sha256=sha(ram),
            cpu=control.command('get-cpu')['text'], state=control.command('get-state')['text'],
            softswitches=control.command('get-softswitches')['text'],
            pcode_pc=hex(int.from_bytes(ram[0x58:0x5a], 'little')),
            frame=capture_frame(control, output, name)))
        control.command('save-state ' + str(output / (name + '.a2state')))
        report['status'] = 'continuation_observed'
    except Exception as error:
        report.update(status='capture_stopped', error=str(error))
        raise
    finally:
        if control: (output / 'control-log.json').write_text(json.dumps(control.log, indent=2)+'\n')
        parent.close(); child.close()
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        report['mounted_copy_unchanged'] = sha(disk.read_bytes()) == sha(media[0].read_bytes())
        (output / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path); parser.add_argument('--label', required=True)
    parser.add_argument('--frames', type=int, default=720)
    parser.add_argument('--output', type=Path, default=ROOT/'analysis/local/reference'/('advance-'+time.strftime('%Y%m%d-%H%M%S')))
    args = parser.parse_args()
    advance(args.source.resolve(), args.label, args.output.resolve(), args.frames)
