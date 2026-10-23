#!/usr/bin/env python3
"""A2M/13 local-process reference capture. No game/ROM bytes are versioned.

Uses the existing emulator's inherited-fd control transport, not a network listener.
All disk mounts are private copies. Protocol implemented from the local a2m wire
documentation; no Ultima game behavior is reused.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import time
import zlib

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_EMULATOR=ROOT.parent/'UltimaI_reveng/build/emulator/a2m-socketpair-build/a2m'

def sha(raw):return hashlib.sha256(raw).hexdigest()

class Control:
    def __init__(self,connection):
        self.connection=connection;self.connection.settimeout(25)
        self.buffer=b'';self.serial=0;self.events=[];self.log=[]

    def line(self):
        while b'\n' not in self.buffer:
            chunk=self.connection.recv(65536)
            if not chunk:raise EOFError('reference process disconnected')
            self.buffer+=chunk
            if len(self.buffer)>1024*1024:raise ValueError('oversized protocol header')
        raw,self.buffer=self.buffer.split(b'\n',1)
        return raw.decode('latin1')

    def binary(self,length):
        if not 0<=length<=16*1024*1024:raise ValueError('invalid binary response length')
        while len(self.buffer)<length+1:
            chunk=self.connection.recv(65536)
            if not chunk:raise EOFError('incomplete reference data')
            self.buffer+=chunk
        raw=self.buffer[:length]
        if self.buffer[length:length+1]!=b'\n':raise ValueError('missing binary delimiter')
        self.buffer=self.buffer[length+1:]
        return raw

    def command(self,command):
        if '\n' in command or '\r' in command:raise ValueError('multiline command rejected')
        self.serial+=1
        self.connection.sendall(f'{self.serial} {command}\n'.encode())
        while True:
            line=self.line();parts=line.split(' ',4)
            if len(parts)<2:raise ValueError('malformed reference reply')
            if parts[0]=='0' and parts[1]=='event':self.events.append(line);continue
            if int(parts[0])!=self.serial:raise ValueError('reference reply ID mismatch')
            kind=parts[1]
            if kind=='data':
                if len(parts)<4:raise ValueError('short data header')
                raw=self.binary(int(parts[3]));meta=parts[4] if len(parts)>4 else ''
                result=dict(kind=kind,type=parts[2],metadata=meta,data=raw)
                self.log.append(dict(command=command,reply=line,length=len(raw),sha256=sha(raw)))
            else:
                result=dict(kind=kind,text=' '.join(parts[2:]))
                self.log.append(dict(command=command,reply=line))
            if kind=='error':raise RuntimeError(f'{command}: {result["text"]}')
            if kind not in ('ok','data'):raise ValueError('unexpected reference response')
            return result

    def memory(self,address,length,mode='map'):
        result=self.command(f'get-memory ${address:04X} {length} {mode}')
        if result['kind']!='data' or len(result['data'])!=length:raise ValueError('incomplete memory read')
        return result['data']

def png_rgba(path,width,height,rgba):
    if len(rgba)!=width*height*4:raise ValueError('wrong RGBA size')
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    scan=b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')
    Path(path).write_bytes(raw)

def metadata(text):return dict(re.findall(r'(\S+)=([^ ]+)',text))

def capture_frame(control,directory,label):
    frame=control.command('get-frame');m=metadata(frame.get('metadata',''))
    width,height,stride=(int(m.get(k,'0'),0) for k in ('width','height','stride'))
    raw=frame.get('data',b'')
    if m.get('format')!='argb8888' or stride!=width*4 or len(raw)!=stride*height:raise ValueError('unsupported reference frame')
    # Wire pixels are uint32 0xAARRGGBB in LE memory: B,G,R,A, not A,R,G,B.
    rgba=bytearray(len(raw));rgba[0::4]=raw[2::4];rgba[1::4]=raw[1::4];rgba[2::4]=raw[0::4];rgba[3::4]=raw[3::4]
    (directory/(label+'.bgra')).write_bytes(raw)
    png_rgba(directory/(label+'.png'),width,height,rgba)
    (directory/(label+'.rgba')).write_bytes(rgba)
    return dict(width=width,height=height,format='rgba8888',wire_format='argb8888-bgra-little-endian',sha256=sha(rgba),png=label+'.png',pixels=label+'.rgba')

def run_until(control,address,timeout=20000):
    control.command('break-clear-all')
    control.command(f'break-exec ${address:04X}')
    control.command('run')
    control.command(f'wait-paused {timeout}')
    cpu=control.command('get-cpu')['text'];state=control.command('get-state')['text']
    match=re.search(r'\bpc=([0-9a-fA-F]{4})\b',cpu)
    if not match or int(match[1],16)!=address:raise RuntimeError(f'expected {address:04X}; {cpu}; {state}')
    return cpu,state

def capture(executable,model,output,sector_image=False):
    if output.exists():raise ValueError('capture output already exists; preserve earlier evidence')
    output.mkdir(parents=True)
    original=ROOT/('extracted/utility.do' if sector_image else 'disk/Sundog Frozen Legacy v2.0 - Utility Side (boot).woz')
    original_hash=sha(original.read_bytes())
    media=output/('utility.do' if sector_image else 'utility.woz');shutil.copyfile(original,media)
    parent,child=socket.socketpair()
    env=os.environ.copy();env.update(A2M_CONTROL_FD=str(child.fileno()),SDL_AUDIODRIVER='dummy')
    command=[str(executable.resolve()),'--headless','--control-port=6510','--noini','--nosaveini',
             '--model='+model,'--mb-slot=0','--history-memory=0','--disk='+str(media.resolve()),'--log-level=warn']
    report=dict(method=('Observed execution of validated logical Utility sectors re-encoded by a2m; not original WOZ bit timing' if sector_image else 'Observed execution of copied original WOZ in pinned a2m reference; not real Apple II hardware'),
                media_file=media.name,source_media=str(original),
                model=model,executable=dict(path=str(executable.resolve()),sha256=sha(executable.read_bytes())),
                original_media_sha256=original_hash,command=command,checkpoints=[],status='in_progress')
    process=None;control=None
    try:
        with (output/'emulator.log').open('wb') as log:
            process=subprocess.Popen(command,cwd=output,env=env,pass_fds=(child.fileno(),),stdout=log,stderr=subprocess.STDOUT)
        child.close();control=Control(parent)
        report['hello']=control.command('hello')['text']
        report['version']=control.command('version')['text']
        control.command('pause');control.command('wait-paused 2000')
        control.command('set-disk-writable 6 0 0')
        control.command('set-turbo max')
        for address in (0x0801,0x08ff,0x4000,0xfef2,0x6800,0xd293,0xff06):
            cpu,state=run_until(control,address)
            label=f'pc-{address:04x}'
            entry=dict(pc=hex(address),cpu=cpu,state=state,softswitches=control.command('get-softswitches')['text'])
            ram=control.memory(0,65536,'main');(output/(label+'-main.bin')).write_bytes(ram)
            entry['main_sha256']=sha(ram)
            for mode in ('lc1','lc2'):
                bank=control.memory(0xd000,12288,mode);(output/(label+'-'+mode+'.bin')).write_bytes(bank)
                entry[mode+'_sha256']=sha(bank)
            entry['frame']=capture_frame(control,output,label)
            control.command('save-state '+str((output/(label+'.a2state')).resolve()))
            if address==0x0801:
                expected=(ROOT/'analysis/regions/boot-stage.bin').read_bytes()[:256]
                if ram[0x800:0x900]!=expected:raise ValueError('ROM-loaded first sector differs')
                entry['boot_sector_matches']=True
                rom=control.memory(0xd000,12288,'rom');(output/'system-rom.bin').write_bytes(rom)
                slotrom=control.memory(0xc600,256);(output/'slot6-rom.bin').write_bytes(slotrom)
                report['rom_hashes']=dict(system=sha(rom),slot6=sha(slotrom))
            if address==0x6800:
                expected=(ROOT/'analysis/regions/relocated-6800.bin').read_bytes()
                if ram[0x6800:0x6800+len(expected)]!=expected:raise ValueError('relocated init differs')
                entry['relocation_matches']=True
            if address==0xd293:
                entry['pcode_pc']=hex(int.from_bytes(ram[0x58:0x5a],'little'))
                if entry['pcode_pc']!='0xf248':raise ValueError('first p-code PC differs from static reconstruction')
                mapped=control.memory(0xf248,3124)
                if mapped!=(ROOT/'analysis/regions/archives/SYSTEM.PASCAL-slot-00.bin').read_bytes():raise ValueError('loaded p-code differs')
                entry['segment0_matches']=True
            report['checkpoints'].append(entry)
            print(json.dumps(dict(reached=label,pcode_pc=entry.get('pcode_pc'),frame=entry['frame']['png'])),flush=True)
            (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        report['status']='boot_to_first_bios_observed'
    except Exception as error:
        report.update(status='capture_stopped',error=str(error))
        if control is not None:
            for name in ('get-cpu','get-state','get-softswitches'):
                try:report[name]=control.command(name)
                except Exception:pass
        raise
    finally:
        if control is not None:(output/'control-log.json').write_text(json.dumps(control.log,indent=2)+'\n')
        parent.close();child.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        report['original_unchanged']=sha(original.read_bytes())==original_hash
        report['private_copy_unchanged']=sha(media.read_bytes())==original_hash
        (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--emulator',type=Path,default=DEFAULT_EMULATOR)
    p.add_argument('--model',choices=('plus','enh'),default='plus')
    p.add_argument('--sector-image',action='store_true',help='separate logical-sector reference; does not establish WOZ bit timing')
    p.add_argument('--output',type=Path,default=ROOT/'analysis/local/reference'/time.strftime('%Y%m%d-%H%M%S'))
    args=p.parse_args();capture(args.emulator,args.model,args.output.resolve(),args.sector_image)
