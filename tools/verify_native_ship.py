#!/usr/bin/env python3
"""Swift image decoding versus bounded original native segment24 P5 execution."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from export_initial_ship import decode_image, verified_pages
from native_probe import CPU
from native_archive_disassembly import apply_relocations
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda data:hashlib.sha256(data).hexdigest()


class ImageProbe(CPU):
    def step(self):
        pc=self.pc;op=self.read(pc)
        if op in (0xa1,0x81):
            self.fetch();self.steps+=1;self.visited.add(pc)
            pointer=self.zpword((self.fetch()+self.x)&255)
            if op==0xa1:self.a=self.nz(self.read(pointer))
            else:self.write(pointer,self.a)
        else:super().step()


def synthetic(stride, variant):
    source=bytearray([stride])
    for column in range(stride):
        count=len(range(column,8192,stride))
        if variant:
            source.append(0x82)
            source.extend(((column*13+5)&255,(column*17+67)&255,(column*29+128)&255))
            count-=3
        while count:
            amount=min(count,128)
            source.extend((amount-1,(column*7+variant*31)&255));count-=amount
    return bytes(source)


def main():
    subprocess.run([sys.executable,str(ROOT/'tools/export_initial_ship.py')],cwd=ROOT,check=True)
    out=ROOT/'analysis/local/native-ship';out.mkdir(parents=True,exist_ok=True)
    inv=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive=next(a for a in inv['archives'] if a['name']=='SYSTEM.LIBRARY')
    segment=next(s for s in archive['segments'] if s['segment_number']==24)
    raw=(ROOT/segment['path']).read_bytes()
    if SHA(raw)!=segment['sha256']:raise ValueError('Original decoder archive changed')
    procedures=mixed_directory(raw);normalized=apply_relocations(raw,procedures)
    p=next(p for p in procedures if p['number']==5)
    if p['entry_address']!=0x1010 or p['kind']!='native-6502':raise ValueError('Image procedure differs')
    defined={int(line[:4],16) for line in (ROOT/'analysis/local/native-complete/library-24-normalized.txt').read_text().splitlines()
             if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    cases=[verified_pages('play',block,8)[0] for block in (29,33)]
    cases.extend(synthetic(stride,variant) for stride in (1,2,3,7,40,64,127,128,255) for variant in (0,1))
    fixtures=[];visited=set();steps=0
    for source in cases:
        expected,consumed=decode_image(source)
        if len(source)>0x1010:raise ValueError('Declared source overlaps bounded native code')
        cpu=ImageProbe();cpu.memory[0x4000:0x4000+len(normalized)]=normalized
        cpu.memory[0x4000:0x4000+len(source)]=source
        cpu.push_word(0x2fff);cpu.pc=0x5010
        cpu.run({0x3000},max_steps=300000)
        if bytes(cpu.memory[0x2000:0x4000])!=expected or cpu.word(2)-0x4000!=consumed:
            raise AssertionError('Original decoder output or input cursor differs')
        if cpu.sp!=255 or not cpu.visited<=defined:raise AssertionError('Native probe stack/Ghidra boundary differs')
        writes=[p for p,v in cpu.writes if 0x2000<=p<0x4000]
        if len(writes)!=8192 or len(set(writes))!=8192:raise AssertionError('Original page coverage differs')
        visited.update(cpu.visited);steps+=cpu.steps
        fixtures.append(dict(encoded=list(source),page=list(expected),consumed=consumed))
    casepath=out/'cases.json';casepath.write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic/ShipScreenDecoder.swift',ROOT/'tests/native/VerifyShipScreen.swift']
    binary=out/'verify-ship-screen'
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,
        '-target',platform.machine()+'-apple-macosx14.0','-module-cache-path',str(out/'module-cache'),
        *map(str,sources),'-o',str(binary)],check=True)
    report=json.loads(subprocess.check_output([str(binary),str(casepath)],text=True))
    report.update(method='Compiled Swift decoder versus bounded original native segment24P5 on original and synthetic resources',
        original_source_sha256=segment['sha256'],native_entry=0x1010,declared_native_view_base=0x4000,
        original_resource_blocks=[29,33],native_instruction_count=len(visited),native_steps=steps,
        native_ghidra_boundaries_match=True,cases_sha256=SHA(casepath.read_bytes()),
        source_files={str(p.relative_to(ROOT)):SHA(p.read_bytes()) for p in sources},
        limitations=['Base SHIP image decoding is not the subsequent interactive scene or status overlays.',
            'No machine, p-code interpreter, ROM or device execution backend is included in the product.'])
    (ROOT/'analysis/native-ship-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
