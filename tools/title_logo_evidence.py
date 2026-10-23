#!/usr/bin/env python3
"""Source-bound logo CFG + bounded native primitives; analysis only, never app VM."""
import hashlib,json
from pathlib import Path
from native_probe import CPU
from pcode_analysis import mixed_directory
from native_archive_disassembly import apply_relocations,relocations
from export_title_logo import compose_final
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()
BASE=0x7e8e
CAPTURE=ROOT/'analysis/local/reference/logo-write-20261023-151127'
def rowoff(y):return (y&7)*1024+((y>>3)&7)*128+(y>>6)*40
def signed(n):return n if n<32768 else n-65536

class LogoProbe(CPU):
    def step(self):
        op=self.read(self.pc)
        if op not in (0xa1,0x81):return super().step()
        address=self.pc;self.pc+=1;self.steps+=1;self.visited.add(address)
        zp=(self.fetch()+self.x)&255;p=self.zpword(zp)
        if op==0xa1:self.a=self.nz(self.read(p))
        else:self.write(p,self.a)

class LogoCFG:
    ARGS={13:0,14:0,15:3,16:0}
    NATIVE_ARGS={9:3,10:5,11:4,12:6}
    def __init__(self,procedures,cpu):
        self.procedures=procedures;self.cpu=cpu;self.stack=[];self.memory=bytearray(65536)
        self.steps=[dict(glyph=-1,iteration=0,writes=[])];self.visited=set();self.operations=0;self.sound_calls=[]
        self.native_calls=[]
    def word(self,p):return int.from_bytes(self.memory[p:p+2],'little')
    def put(self,p,v):self.memory[p:p+2]=(v&65535).to_bytes(2,'little')
    def popargs(self,n):
        args=self.stack[-n:];del self.stack[-n:];return args
    def native(self,number):
        args=self.popargs(self.NATIVE_ARGS[number]);c=self.cpu
        c.writes.clear()
        for v in args:c.push_word(v)
        c.push_word(0x5fff);c.pc=BASE+{9:0x800,10:0x8ae,11:0x942,12:0x9d4}[number]
        c.run({0x6000},max_steps=20000)
        if c.sp!=255:raise AssertionError('Native argument stack did not restore')
        writes=[dict(offset=p-0x2000,value=v) for p,v in c.writes if 0x2000<=p<0x4000]
        self.steps[-1]['writes'].extend(writes)
        self.native_calls.append(dict(procedure=number,args=args,writes=len(writes)))
    def call(self,number,depth=0):
        if number in self.NATIVE_ARGS:return self.native(number)
        if number not in self.ARGS or depth>2:raise ValueError('Call outside logo whitelist')
        base=0x7000+depth*256
        for i in range(1,self.ARGS[number]+1):self.put(base+2*i,self.stack.pop())
        proc=self.procedures[number];nodes={r['address']:r for r in proc['instructions']};pc=proc['procedure']['entry_address']
        while True:
            self.operations+=1
            if self.operations>100000:raise ValueError('Logo CFG budget')
            r=nodes[pc];op=r['opcode'];o=r['operands'];self.visited.add((number,pc));nextpc=r['successors'][0] if r['successors'] else None
            if op<128:self.stack.append(op)
            elif op==0xc7:self.stack.append(o['word'])
            elif 0xd8<=op<=0xe7 or op==0xca:self.stack.append(self.word(base+2*o['index']))
            elif op==0xcc:self.put(base+2*o['index'],self.stack.pop())
            elif op in (0xb6,0xb2):
                p=0x7000+(depth-o['selector_or_depth'])*256+2*o['index']
                self.stack.append(p if op==0xb2 else self.word(p))
            elif op==0xb8:self.put(0x7000+(depth-o['selector_or_depth'])*256+2*o['index'],self.stack.pop())
            elif op==0xa4:
                index=self.stack.pop();p=self.stack.pop();self.stack.append((p+index*o['index']*2)&65535)
            elif op==0xa2:self.stack.append((self.stack.pop()+2*o['index'])&65535)
            elif 0xf8<=op<=0xff:self.stack.append(self.word(self.stack.pop()+2*o['word_offset']))
            elif op==0x9a:
                value=self.stack.pop();self.put(self.stack.pop(),value)
            elif op in (0x82,0x95,0x8f,0x8d,0x84,0xc3,0xc5,0xc8,0xc9):
                b=self.stack.pop();a=self.stack.pop()
                value={0x82:lambda:a+b,0x95:lambda:a-b,0x8f:lambda:a*b,0x8d:lambda:a|b,0x84:lambda:a&b,
                       0xc3:lambda:int(a==b),0xc5:lambda:int(signed(a)>signed(b)),0xc8:lambda:int(signed(a)<=signed(b)),0xc9:lambda:int(signed(a)<signed(b))}[op]()
                self.stack.append(value&65535)
            elif op==0xa1:
                truth=self.stack.pop()&1;nextpc=r['successors'][1 if truth else 0]
            elif op==0xb9:pass
            elif op in (0xce,0xcf):
                target=o['procedure'];self.call(target,self.procedures[target]['procedure'].get('lexical_level',1)-1 if target in self.ARGS else depth)
            elif op==0xcd:
                if o['segment_operand']!=22:raise ValueError('External call outside logo contract')
                if o['procedure']==53:
                    if self.popargs(4)!=[0x4000,12,64,1]:raise AssertionError('Logo read contract changed')
                elif o['procedure']==4:
                    args=self.popargs(7);self.sound_calls.append(args)
                    self.steps.append(dict(glyph=self.word(base+14),iteration=self.word(base+6),writes=[]))
                else:raise ValueError('External call outside logo contract')
            elif op==0xad:return
            else:raise ValueError(f'Unknown logo opcode {op:02x} at {pc:x}')
            pc=nextpc

def main():
    archive=(ROOT/'analysis/regions/archives/SYSTEM.LIBRARY-slot-05.bin').read_bytes()
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    source=next(s for a in inventory['archives'] if a['name']=='SYSTEM.LIBRARY' for s in a['segments'] if s['segment_number']==26)
    if SHA(archive)!=source['sha256']:raise ValueError('Source archive changed')
    memory=(CAPTURE/'first-logo-write-main.bin').read_bytes();manifest=json.loads((CAPTURE/'manifest.json').read_text())
    if SHA(memory)!=manifest['events'][0]['main_sha256']:raise ValueError('Observed capture changed')
    procedures=mixed_directory(archive);normalized=apply_relocations(archive,procedures,segment_base=BASE)
    for p in procedures:
        if p['number'] not in (9,10,11,12,18):continue
        info=relocations(archive,p);lo=p['entry_address'];hi=info['body_end_exclusive']
        if memory[BASE+lo:BASE+hi]!=normalized[lo:hi]:raise ValueError('Native runtime relocation differs')
    background=(ROOT/'analysis/local/native-assets/sundog-splash.hgr').read_bytes()
    glyphs=(ROOT/'analysis/local/native-assets/sundog-logo.bin').read_bytes()
    if memory[0x4000:0x5800]!=glyphs:raise ValueError('Observed original logo read differs from disk asset')
    cpu=LogoProbe(memory);cpu.memory[0x2000:0x4000]=background;cpu.sp=255
    rows=json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-05.json').read_text())
    cfg=LogoCFG({r['procedure']['number']:r for r in rows},cpu);cfg.call(13)
    final=bytes(cpu.memory[0x2000:0x4000])
    if cfg.stack or final!=compose_final(background,glyphs):raise AssertionError('Logo CFG/native result differs from independent final model')
    expected_sha='7e4f8f739f8b9d40a411f462036f740e1b518ce547184d03c5f4c746d0cc317d'
    if SHA(final)!=expected_sha:raise AssertionError('Final logo differs from retained original title')
    listing=(ROOT/'analysis/local/native-complete/library-26-normalized.txt').read_text().splitlines()
    defined={BASE+int(line[:4],16)-0x4000 for line in listing if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    if not cpu.visited<=defined:raise AssertionError('Native primitive left persisted Ghidra instruction boundaries')
    rea=json.loads((ROOT/'analysis/local/rea/title-logo-glyph11.json').read_text())
    if rea['subject']['digest']['sha256']!=SHA(memory[BASE+0x942:BASE+0x9c2]):raise ValueError('Actual REA glyph slice differs')
    out=ROOT/'analysis/local/title-logo';out.mkdir(parents=True,exist_ok=True)
    fixture=dict(background=list(background),glyphs=list(glyphs),steps=cfg.steps,final_page=list(final))
    path=out/'cases.json';path.write_text(json.dumps(fixture,separators=(',',':'))+'\n')
    report=dict(method='Original P13/P14/P15/P16 decoded CFG with bounded original relocated native P9/P10/P11/P12; disk read bound to original asset and sound call recorded only',
        archive='SYSTEM.LIBRARY',segment=26,source_sha256=SHA(archive),runtime_base=BASE,
        observed_write_breakpoint=dict(path=str(CAPTURE.relative_to(ROOT)),pc=0x86da,pcode_pc=0x7f33,source_offset=0x84c,caller_procedure=16,caller_call_offset=0xa3),
        rea_evidence_id=rea['evidence_id'],native_calls=len(cfg.native_calls),native_instruction_addresses=len(cpu.visited),
        pcode_instruction_addresses=len(cfg.visited),cfg_operations=cfg.operations,animation_steps=len(cfg.steps),
        ordered_hgr_writes=sum(len(s['writes']) for s in cfg.steps),final_page_sha256=SHA(final),
        glyph_resource=dict(length=6144,shape=[6,8,128],visible_frame_shape=[24,4],source_relative_block=64,unit_read_absolute_block=67),
        fixture_sha256=SHA(path.read_bytes()),sound_calls=len(cfg.sound_calls),
        limitations=['Sound-generator delays and physical timing are not reproduced by this visual contract.',
                     'P14 disk-load transition timing and the rest of the startup menu are outside this comparison.'])
    (ROOT/'analysis/title-logo-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
