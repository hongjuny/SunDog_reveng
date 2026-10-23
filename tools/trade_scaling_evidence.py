#!/usr/bin/env python3
"""Reconstruct one original arithmetic helper, preserving its integer rounding order."""
import hashlib,itertools,json
from pathlib import Path
from native_probe import CPU
ROOT=Path(__file__).resolve().parents[1]

def signed16(n):
    n &= 65535
    return n if n<32768 else n-65536

def scale_selected(x,y,divisor):
    """Verified nonnegative input domain only; original operations wrap to signed16."""
    if x==0 or divisor==0:raise ZeroDivisionError('original signed division error boundary')
    if not (0<x<=32767 and 0<=y<=32767 and 0<divisor<=32767):raise ValueError('outside selected verified input domain')
    if 32767//x<=y:
        return signed16(x*(y//divisor)),'divide-before-multiply'
    product=signed16(x*y)
    quotient=abs(product)//divisor
    return (-quotient if product<0 else quotient),'multiply-before-divide'

def probe(raw,snapshot,x,y,divisor):
    cpu=CPU();cpu.memory[0xd000:]=snapshot;cpu.memory[0x4800:0x4800+len(raw)]=raw
    def word(p,v):cpu.memory[p:p+2]=(v&65535).to_bytes(2,'little')
    word(0x58,0x4800);word(0x52,0x6000)
    for index,value in enumerate((0,0,divisor,y,x),start=1):word(0x6000+10+2*index,value)
    steps=[]
    for _ in range(30):
        pc=cpu.word(0x58)
        if cpu.read(pc)==0xad:
            return dict(result=signed16(cpu.word(0x600c)),stack_restored=cpu.sp==255,
                        visited=cpu.visited,bytecode_offsets=steps,error=None)
        if not 0x4800<=pc<0x4800+len(raw):raise ValueError('helper escaped supplied bytecode')
        steps.append(pc-0x4800);cpu.pc=0xd293
        cpu.run({0xd293,0xd20a},max_steps=5000)
        if cpu.pc==0xd20a:return dict(error=cpu.word(0xbdde),visited=cpu.visited,bytecode_offsets=steps)
    raise ValueError('helper did not reach its return boundary')

def run():
    inv=json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())
    source=next(s for s in inv['segments'] if s['segment_number']==20)
    archive=(ROOT/source['path']).read_bytes()
    if hashlib.sha256(archive).hexdigest()!=source['sha256']:raise ValueError('game source identity differs')
    decoded=json.loads((ROOT/'analysis/local/pcode/SYSTEM.STARTUP-slot-14-play.json').read_text())
    procedure=next(p for p in decoded if p['procedure']['number']==18)
    p=procedure['procedure'];raw=archive[p['entry_address']:p['attribute_address']]
    if procedure['boundaries'] or any(i['calls'] for i in procedure['instructions']):raise ValueError('arithmetic helper has unresolved effects')
    # Short loads map to local[1..], with two reserved result words preceding three inputs.
    expected=[(0xa73,5),(0xa75,4),(0xa79,5),(0xa7a,4),(0xa7b,3),(0xa82,5),(0xa83,4),(0xa85,3)]
    actual={i['address']:i['operands'].get('index') for i in procedure['instructions'] if i['operation']=='load_local_short'}
    if any(actual.get(address)!=index for address,index in expected):raise ValueError('helper frame interpretation differs')
    attrs=p['attribute_address']
    if int.from_bytes(archive[attrs+2:attrs+4],'little')!=10:raise ValueError('helper parameter byte count differs')
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    defined={int(line[:4],16) for line in (ROOT/'ghidra/exports/interpreter-ready.txt').read_text().splitlines() if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    cases=[];visited=set();paths={}
    values=(1,2,7,8,9,127,255,1024,32767)
    inputs=list(itertools.product(values,(0,1,7,8,9,127,255,1024,32767),values))
    inputs += [(8,4094,8),(8,4095,8),(8,5000,3),(8,4096,8)]
    for x,y,d in inputs:
        expected,branch=scale_selected(x,y,d);actual=probe(raw,snapshot,x,y,d)
        if actual['error'] is not None or actual['result']!=expected or not actual['stack_restored']:raise AssertionError('native helper differs from reconstructed arithmetic')
        if not actual['visited']<=defined:raise AssertionError('helper native instructions left Ghidra listing')
        visited.update(actual['visited']);paths[branch]=actual['bytecode_offsets']
        cases.append(dict(x=x,y=y,divisor=d,result=expected,branch=branch))
    errors=[]
    for x,y,d in ((0,1,1),(1,1,0),(0,0,0)):
        result=probe(raw,snapshot,x,y,d)
        if result['error']!=106:raise AssertionError('zero divisor error differs')
        if not result['visited']<=defined:raise AssertionError('error path left Ghidra listing')
        visited.update(result['visited'])
        errors.append(dict(x=x,y=y,divisor=d,error=106))
    def provenance(offset):
        sector=source['sectors'][offset//256]
        return dict(side='play',**sector,byte_in_sector=offset%256,image_offset=sector['offset']+offset%256)
    result=dict(method='Original segment-20 procedure-18 p-code through bounded original native handlers on synthetic frame; independent arithmetic expression comparison; no game VM/backend',
                source_sha256=source['sha256'],segment=20,procedure=18,entry_offset=p['entry_address'],source=provenance(p['entry_address']),
                input_frame={'local1':'result slot','local2':'reserved result word','local3':'divisor','local4':'y','local5':'x','parameter_bytes':10},
                verified_domain='x in 1..32767, y in 0..32767, divisor in 1..32767; selected cases, not exhaustive',
                expression='if floor(32767/x) <= y: signed16(x * floor(y/divisor)); else: trunc_zero(signed16(x*y)/divisor)',
                cases=len(cases),zero_error_cases=errors,branch_bytecode_offsets=paths,ghidra_boundaries_match=True,
                native_instruction_addresses=[hex(p) for p in sorted(visited)],
                remaining=['Negative input behavior outside the selected contract','Semantic meaning and provenance of caller values','Caller balance/inventory side effects'])
    (ROOT/'analysis/trade-scaling-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'analysis/local/trade-scaling-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),zero_errors=len(errors),branches=list(paths),examples=[c for c in cases[-4:]])))
if __name__=='__main__':run()
