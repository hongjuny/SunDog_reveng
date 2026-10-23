#!/usr/bin/env python3
"""Bounded original native display replay versus an independent reveal plan.

The replay is an analysis tool. The native application uses reconstructed drawing
operations, never this CPU, a ROM, a disk controller, or a p-code executor.
"""
import hashlib
import json
from pathlib import Path
import re
from native_probe import CPU, UnsupportedInstruction

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda b: hashlib.sha256(b).hexdigest()
REGION_SHA = '1b9dfd8bbaa973ea73bc650e1c9161f3991d00d6a071bc2403d59582fdc6f29d'
BASE_CYCLES = {0xa9:2,0x85:3,0xa2:2,0x20:6,0xa5:3,0x18:2,0x69:2,0xa0:2,
    0xb1:5,0x91:6,0xc8:2,0xa6:3,0xe6:5,0x38:2,0xe5:3,0xa4:3,0xa1:6,
    0x81:6,0xf6:6,0xe8:2,0xe0:2,0xd0:2,0x88:2,0xc0:2,0xc5:3,0x90:2,
    0xf0:2,0xc6:5,0xd6:6,0xb0:2,0xe9:2,0xc9:2,0x4c:3,0x60:6,0xbd:4,0x65:3}


def row_offset(row):
    if not 0 <= row < 192: raise ValueError('row outside HGR')
    return (row & 7)*1024 + ((row >> 3)&7)*128 + (row >> 6)*40


def reveal_offsets():
    """Data-independent native write order, including repeated edge writes."""
    out = [row_offset(y)+x for y in (95,96) for x in (19,20)]
    milestones = [dict(stage='seed',iteration=-1,write_count=len(out))]
    for i in range(19):
        left,right,top,bottom = 18-i,21+i,90-5*i,101+5*i
        out += [row_offset(y)+x for x in range(left,right+1) for y in range(top,top+5)]
        out += [row_offset(y)+right for y in range(top,bottom+1)]
        out += [row_offset(y)+x for x in range(right,left-1,-1) for y in range(bottom,bottom-5,-1)]
        out += [row_offset(y)+left for y in range(bottom,top,-1)]
        milestones.append(dict(stage='ring',iteration=i,left=left,right=right,top=top,bottom=bottom,write_count=len(out)))
    return out,milestones


class RevealProbe(CPU):
    def __init__(self):
        super().__init__();self.cycles=0;self.instruction_end=0;self.events=[];self.milestones=[]
    def write(self,p,value):
        super().write(p,value)
        if 0x2000 <= p < 0x4000:
            self.events.append(dict(offset=p-0x2000,value=value&255,cycles=self.instruction_end))
    def cost(self):
        pc=self.pc;op=self.read(pc)
        if op not in BASE_CYCLES:raise UnsupportedInstruction(f'unattested timing opcode {op:02x}')
        cost=BASE_CYCLES[op]
        if op in (0xd0,0xf0,0x90,0xb0):
            take={0xd0:not self.z,0xf0:bool(self.z),0x90:not self.c,0xb0:bool(self.c)}[op]
            if take:
                displacement=self.read(pc+1);displacement-=256 if displacement>=128 else 0
                target=(pc+2+displacement)&65535
                cost+=1+int((pc+2)&0xff00 != target&0xff00)
        elif op==0xbd:
            base=self.word(pc+1);cost+=int(base&0xff00 != (base+self.x)&0xff00)
        elif op==0xb1:
            base=self.zpword(self.read(pc+1));cost+=int(base&0xff00 != (base+self.y)&0xff00)
        return cost
    def step(self):
        self.instruction_end=self.cycles+self.cost()
        pc=self.pc;op=self.read(pc)
        if op in (0xa1,0x81,0xf6,0xd6):
            self.fetch();self.steps+=1;self.visited.add(pc);operand=(self.fetch()+self.x)&255
            if op==0xa1:self.a=self.nz(self.read(self.zpword(operand)))
            elif op==0x81:self.write(self.zpword(operand),self.a)
            else:self.write(operand,self.nz(self.read(operand)+(1 if op==0xf6 else -1)))
        else:super().step()
        self.cycles=self.instruction_end
        if self.pc==0x405e and not self.milestones:
            self.milestones.append(dict(stage='seed',iteration=-1,write_count=len(self.events),cycles=self.cycles))
        if self.pc==0x41f6:
            self.milestones.append(dict(stage='ring',iteration=self.read(0x23)-1,write_count=len(self.events),cycles=self.cycles))


def attest_timing_source(cp2=Path('/Users/ay5/Projects/CiderPress2')):
    cpu=cp2/'FileConv/Asm65/CpuDef.cs';ops=cp2/'FileConv/Asm65/OpDef.cs'
    text=cpu.read_text(encoding='utf-8-sig');text=text[text.index('private static CpuDef Cpu6502 {'):]
    text=text[text.index('mOpDefs = new OpDef[] {'):];text=text[:text.index('};')]
    names=re.findall(r'OpDef\.(Op\w+)(?:\s*[,)]|\s*$)',text,re.M)
    if len(names)!=256:raise ValueError('NMOS opcode reference shape changed')
    definitions={}
    for m in re.finditer(r'public static readonly OpDef\s+(Op\w+)\s*=\s*new OpDef\([^)]*\)\s*\{(.*?)\};',ops.read_text(encoding='utf-8-sig'),re.S):
        cycle=re.search(r'CycDef\s*=\s*(\d+)',m[2])
        if cycle:definitions[m[1]]=int(cycle[1])
    for op,cost in BASE_CYCLES.items():
        if definitions[names[op]]!=cost:raise ValueError(f'timing fact differs for opcode {op:02x}')
    return dict(method='Base NMOS timing facts independently checked against installed CiderPress2 Cpu6502/OpDef; relevant index-page and branch penalties applied per original execution',
                cpu_definition_sha256=SHA(cpu.read_bytes()),opcode_definition_sha256=SHA(ops.read_bytes()),
                base_cycles={f'{op:02X}':cost for op,cost in sorted(BASE_CYCLES.items())})


def main():
    raw=(ROOT/'analysis/regions/initial-4000.bin').read_bytes()
    if SHA(raw)!=REGION_SHA:raise ValueError('graphics source changed')
    for y in range(192):
        if raw[0x210+y] | (raw[0x2d0+y]<<8) != 0x2000+row_offset(y):raise ValueError('native HGR row tables differ')
    region=next(r for r in json.loads((ROOT/'analysis/boot-regions.json').read_text()) if r['name']=='initial-4000')
    def provenance(address):
        offset=address-0x4000;sector=region['sectors'][offset//256]
        return dict(side='utility',**sector,byte_in_sector=offset%256,image_offset=sector['offset']+offset%256)
    evidence=[];defined=set()
    for name in ('splash-display-4000','splash-row-helper-4200'):
        e=json.loads((ROOT/'analysis/local/rea'/f'{name}.json').read_text())
        if e['provider']['id']!='ghidra':raise ValueError('not actual Ghidra evidence')
        source=Path(e['subject']['local_path']).read_bytes()
        if SHA(source)!=e['subject']['digest']['sha256'] or source!=raw:raise ValueError('REA import identity changed')
        evidence.append(e['evidence_id'])
        defined.update(int(m,16) for m in re.findall(r'^0x([0-9a-f]+):',e['normalized_result'],re.M))
    c=RevealProbe();c.memory[0x4000:0x6400]=raw;c.push_word(0x05ff);c.writes.clear();c.pc=0x4000
    c.run({0x0600},max_steps=200000)
    if not c.visited <= defined:raise ValueError('native execution left actual REA-defined instruction boundaries')
    if c.sp!=255 or any(not (p<=0x23 or 0x100<=p<0x200 or 0x2000<=p<0x4000) for p,v in c.writes):raise ValueError('native replay escaped declared stack/zero-page/HGR effects')
    offsets,milestones=reveal_offsets()
    expected=[dict(offset=p,value=raw[0x400+p]) for p in offsets]
    if [(r['offset'],r['value']) for r in c.events] != [(r['offset'],r['value']) for r in expected]:raise AssertionError('high-level reveal write order differs')
    if [(r['iteration'],r['write_count']) for r in c.milestones]!=[(r['iteration'],r['write_count']) for r in milestones]:raise AssertionError('native iteration boundaries differ')
    expected_page=bytearray(8192)
    for r in expected:expected_page[r['offset']]=r['value']
    if c.memory[0x2000:0x4000]!=expected_page:raise AssertionError('final page mismatch')
    if SHA(expected_page)!='623c8808ab8653a9d20bcbc26ce5cf4058a458764915a9b0c0071d9e35508c37':raise AssertionError('not full original splash')
    for native,model in zip(c.milestones,milestones):native.update({k:v for k,v in model.items() if k not in native})
    out=ROOT/'analysis/local/splash-reveal';out.mkdir(parents=True,exist_ok=True)
    fixture=dict(source=list(expected_page),final_page=list(expected_page),writes=c.events,write_cycles=[r['cycles'] for r in c.events],milestones=c.milestones,total_cycles=c.cycles,
                 source_sha256=SHA(raw),final_page_sha256=SHA(expected_page))
    (out/'writes.json').write_text(json.dumps(fixture,separators=(',',':'))+'\n')
    (out/'final.hgr').write_bytes(expected_page)
    result=dict(method='Bounded original 4000..420F native execution versus independent geometric write-order reconstruction; no ROM/MMIO/runtime or app emulator',
                source_side='utility',region='initial-4000',region_sha256=SHA(raw),routine_entry=0x4000,routine_return=0x41ff,row_helper=0x4200,
                entry_source=provenance(0x4000),return_source=provenance(0x41ff),helper_source=provenance(0x4200),
                rea_evidence_ids=evidence,native_instruction_count=len(c.visited),native_steps=c.steps,
                ordered_write_count=len(c.events),unique_visible_bytes=len(set(offsets)),final_page_sha256=SHA(expected_page),
                ordered_writes_match=True,iteration_boundaries_match=True,total_cycles=c.cycles,
                cycle_origin='First cycle of LDA at4000; caller JSR excluded; final RTS included. HGR STA commit is recorded at its final instruction cycle.',
                timing_reference=attest_timing_source(),milestones=c.milestones,
                fixture='analysis/local/splash-reveal/writes.json',fixture_sha256=SHA((out/'writes.json').read_bytes()),
                confidence='high for byte order and instruction-cycle count under declared binary-mode NMOS execution',
                limitations=['No analog RGB/NTSC fidelity claim.','Cycle count assumes binary-mode NMOS6502, no interrupts or memory wait states.',
                             'Wall-clock presentation depends on selected machine clock and macOS scheduling; native clock/refresh synchronization is not observed here.',
                             'Disk read duration, boot clear/resident branches and later game initialization are outside this isolated routine.'])
    (ROOT/'analysis/splash-reveal-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('ordered_write_count','unique_visible_bytes','native_steps','total_cycles','ordered_writes_match')}))


if __name__=='__main__':main()
