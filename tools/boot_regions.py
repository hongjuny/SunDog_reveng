#!/usr/bin/env python3
"""Reconstruct regions using the loader's own sector table, not ST formats."""
import json,pathlib
from disk_analysis import load,offset,DOS_TO_PHYSICAL,digest
root=pathlib.Path(__file__).resolve().parents[1]
skew=tuple(range(0,16,2))+tuple(range(1,16,2))
def pages(block,count,data=None):
    if not 0<=block<280 or count<0 or block*2+count>560:raise ValueError('load outside known geometry')
    if data is None:data=load(root/'extracted/utility.do')
    result=[]; provenance=[]
    for n in range(block*2,block*2+count):
        t=n//16; physical=skew[n%16]; s=DOS_TO_PHYSICAL.index(physical); p=offset(t,s)
        result.append(data[p:p+256]); provenance.append(dict(track=t,sector=s,physical_sector=physical,offset=p))
    return b''.join(result),provenance
if __name__=='__main__':
    records=[]
    for name,start,count,addr in [('initial-4000',201,36,0x4000),('lc-bank2',219,48,0xd000),('lc-bank1',243,16,0xd000)]:
        b,provenance=pages(start,count); path=root/'analysis/regions'/f'{name}.bin';path.write_bytes(b)
        records.append(dict(name=name,start_block=start,pages=count,address=addr,sha256=digest(b),side='utility',sectors=provenance,confidence='high static reconstruction; execution and controller success unobserved'))
        print(name,b[:16].hex())
    (root/'analysis/boot-regions.json').write_text(json.dumps(records,indent=2)+'\n')
    b,_=pages(219,48); bank1,_=pages(243,16)
    (root/'analysis/regions/runtime-bank1.bin').write_bytes(bank1+b[4096:])
    combined=bank1+b[4096:]
    _,p2=pages(219,48); _,p1=pages(243,16)
    records.append(dict(name='runtime-bank1',address=0xd000,length=0x3000,sha256=digest(combined),side='utility',sectors=p1+p2[16:],confidence='static view after FEF2 reads C08B'))
    (root/'analysis/boot-regions.json').write_text(json.dumps(records,indent=2)+'\n')
    source=int.from_bytes(combined[0x2267:0x2269],'little')
    relocated=combined[source-0xd000:source-0xd000+0x500]
    (root/'analysis/regions/relocated-6800.bin').write_bytes(relocated)
    (root/'analysis/relocation.json').write_text(json.dumps(dict(source_address=source,destination_address=0x6800,length=0x500,sha256=digest(relocated),source_region='lc-bank2',source_region_offset=source-0xd000,copy_routine=0xf269,entry=0x6800,confidence='high static copy loop; runtime unobserved'),indent=2)+'\n')
    print('FFf8 vector:',hex(int.from_bytes(b[0x2ff8:0x2ffa],'little')))
