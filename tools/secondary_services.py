#!/usr/bin/env python3
"""Verify bounded 9E service interfaces, separately from full disk/loader semantics."""
import hashlib,json
from pathlib import Path
from native_probe import handler_probe
from runtime_evidence import provenance
ROOT=Path(__file__).resolve().parents[1]
SPECS=((0x15,0xe66b,0xe675,'acquire_segment'),(0x16,0xe675,0xe67f,'release_segment'),
       (0x20,0xd6af,0xd6c6,'snapshot_allocation_cursor'),(0x21,0xd6c6,0xd6e4,'restore_allocation_cursor'),
       (0x22,0xeed1,0xeedc,'read_io_result'))

def prepare():
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes();rows=[]
    for selector,start,end,name in SPECS:
        raw=snapshot[start-0xd000:end-0xd000];path=ROOT/f'analysis/regions/rea-service-{selector:02x}.bin';path.write_bytes(raw)
        rows.append(dict(selector=selector,name=name,entry=start,end_exclusive=end,path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),source=provenance(start)))
    (ROOT/'analysis/local/secondary-service-inputs.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

def verify():
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    inputs=json.loads((ROOT/'analysis/local/secondary-service-inputs.json').read_text())
    listing={int(line.split(' ',1)[0],16) for line in (ROOT/'ghidra/exports/interpreter-ready.txt').read_text().splitlines() if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    cases=[];visited=set()
    def check(selector,stack,words,check_result,condition,stop=0xd293):
        cpu,sp=handler_probe(snapshot,bytes([0x9e,selector]),stack=stack,pc=0x40ff,words=words,stop=stop,max_steps=2000)
        check_result(cpu,sp)
        if stop==0xd293 and cpu.word(0x58)!=0x4101:raise AssertionError('service continuation is not fixed two bytes')
        if not cpu.visited<=listing:raise AssertionError('service probe left Ghidra instruction boundaries')
        visited.update(cpu.visited);cases.append(dict(selector=selector,condition=condition,stop=stop))
        return cpu
    def require(condition):
        if not condition:raise AssertionError('secondary service effect differs')
    for selector in (0x15,0x16):
        for slot in (1,7,22,30):
            for count in (1,2,255,256,65534):
                table=0xbd1e+2*slot;expected=count+(1 if selector==0x15 else -1)
                check(selector,(slot,),((table,count),(0x5c,0x7600),(0xbd5e+2*slot,0x7200)),
                    lambda c,sp,t=table,n=expected,s=selector:require(c.word(t)==n and c.sp==(sp+2)&255 and c.word(0x5c)==(0x7200 if s==0x16 and n==0 else 0x7600)),
                    f'resident slot={slot}, count={count}')
    for slot in (1,7,22,30):
        check(0x15,(slot,),((0xbd1e+2*slot,0),),lambda c,sp,s=slot:require(c.read(0x90)==s and c.word(0x58)==0x40ff),
              f'nonresident slot={slot}; stop before allocation/load',stop=0xe502)
    for cursor in (0,0x5000,0x7fff,0xffff):
        for pending in (0,0x3456):
            for destination in (0x4000,0x41ff):
                check(0x20,(destination,),((0x5a,cursor),(0xbde6,pending)),
                    lambda c,sp,d=destination,v=cursor,p=pending:require(c.word(d)==(p or v) and c.word(0x5a)==(p or v) and c.word(0xbde6)==0 and c.sp==(sp+2)&255),
                    f'cursor={cursor}, pending={pending}, destination={destination}')
    for value in (0,0x4000,0x7fff,0xffff):
        for address in (0x4000,0x41ff):
            check(0x21,(address,),((address,value),(0x5a,0x6000),(0xbde6,0x1234)),
                lambda c,sp,v=value:require(c.word(0x5a)==v and c.word(0xbde6)==0 and c.sp==(sp+2)&255),
                f'restore value={value}, address={address}')
    for value in (0,1,0x1234,0xffff):
        check(0x22,(),((0xbdde,value),),lambda c,sp,v=value:require(c.sp==(sp-2)&255 and c.pop_word()==v),f'I/O result={value}')
    rows=[]
    for source in inputs:
        selector=source['selector'];record=dict(source,pcode_length=2,continuation='conditional on normal service return; PC+2',
            probe_cases=sum(c['selector']==selector for c in cases),
            tested_scope=('resident reference counts and explicit nonresident loader boundary' if selector==0x15 else
                          'resident decrement and saved allocation-top restore' if selector==0x16 else
                          'declared RAM/stack values; direct memory effects'),
            selected_memory_effects_verified=True,complete_runtime_semantics=False)
        evidence_path=ROOT/f'analysis/local/rea/service-{selector:02x}.json'
        if not evidence_path.exists():raise ValueError('actual REA service evidence is required')
        evidence=json.loads(evidence_path.read_text())
        if evidence['subject']['digest']['sha256']!=record['sha256'] or evidence['provider']['id']!='ghidra':raise ValueError('REA source/provider mismatch')
        record['rea_evidence_id']=evidence['evidence_id'];rows.append(record)
    result=dict(method='Actual Apple II service instructions in bounded synthetic native probes; not game execution or an application VM',
                snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),services=rows,cases=len(cases),probe_conditions=cases,
                native_instruction_addresses=[hex(p) for p in sorted(visited)],ghidra_boundaries_match=True,
                remaining=['Nonresident loader I/O and bank switches','Validity of arbitrary pointer/count inputs','Game ownership and lifetime of each allocation'])
    (ROOT/'analysis/secondary-services.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(services=len(rows),cases=len(cases),native_instructions=len(visited))))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args();prepare() if a.prepare else verify()
