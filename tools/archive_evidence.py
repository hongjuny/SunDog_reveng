#!/usr/bin/env python3
"""Inventory runtime-supported Pascal dictionaries; never guess bytecode instructions."""
import json,math,pathlib
from boot_regions import pages
from disk_analysis import load,digest
from runtime_evidence import u16
ROOT=pathlib.Path(__file__).resolve().parents[1]

def directory(data):
    if len(data)<512:raise ValueError('directory block must be complete')
    n=u16(data,16)
    if not 0<n<=18:raise ValueError('entry count not contained in supplied directory block')
    entries=[]
    for i in range(1,n+1):
        p=i*26;start=u16(data,p);end=u16(data,p+2);size=data[p+6]
        if not 0<=start<end<=280 or not 1<=size<=15:raise ValueError('invalid directory entry')
        entries.append(dict(record_offset=p,start_block=start,end_block=end,kind=u16(data,p+4),name=data[p+7:p+7+size].decode('ascii'),last_block_bytes=u16(data,p+22)))
    return entries

def dictionary(data,file_blocks):
    if len(data)<512:raise ValueError('dictionary block must be complete')
    records=[]
    for slot in range(16):
        addr=u16(data,4*slot);length=u16(data,4*slot+2)
        if addr==length==0:continue
        if length==0:raise ValueError('zero segment length in occupied slot')
        info=u16(data,0x100+slot*2)
        status='allocation_only' if addr==0 and u16(data,0xc0+slot*2)==7 else 'outside_directory_extent' if addr+math.ceil(length/512)>file_blocks else 'stored'
        records.append(dict(status=status,slot=slot,relative_block=addr,length=length,storage_blocks=math.ceil(length/512),segment_number=info&255,machine_type=(info>>8)&15,reserved=(info>>12)&1,version_bits=(info>>13)&7,kind=u16(data,0xc0+slot*2),name_bytes_zero=not any(data[0x40+slot*8:0x48+slot*8])))
    return records

def main():
    media={side:load(ROOT/'extracted'/f'{side}.do') for side in ('utility','play')}
    d,dir_source=pages(79,2,media['utility']);entries=directory(d)
    out=ROOT/'analysis/regions/archives';out.mkdir(parents=True,exist_ok=True)
    archives=[]
    for entry in entries:
        if entry['name'] not in ('SUNDOG.LIBRARY','SYSTEM.LIBRARY','SYSTEM.STARTUP','SYSTEM.PASCAL'):continue
        start=entry['start_block'];end=entry['end_block'];data,source=pages(start,(end-start)*2,media['utility'])
        records=dictionary(data[:512],end-start);covered={0}
        for rec in records:
            if rec['status']!='stored':continue
            block=start+rec['relative_block'];rec['absolute_block']=block
            raw,prov=pages(block,rec['storage_blocks']*2,media['utility']);raw=raw[:rec['length']]
            rec['sha256']=digest(raw);rec['side']='utility';rec['sectors']=prov
            rec['source_byte_count_last_sector']=(rec['length']-1)%256+1
            rec['path']=f"analysis/regions/archives/{entry['name']}-slot-{rec['slot']:02}.bin"
            (ROOT/rec['path']).write_bytes(raw)
            covered.update(range(rec['relative_block'],rec['relative_block']+rec['storage_blocks']))
            # Compare only known Play sectors; no unknown bytes may participate.
            if block+rec['storage_blocks']<=272:
                other,_=pages(block,rec['storage_blocks']*2,media['play'])
                rec['identical_on_play']=raw==other[:rec['length']]
            else:rec['identical_on_play']=None
        other_identical=None
        if end<=272:
            other,_=pages(start,(end-start)*2,media['play']);other_identical=data==other
        archives.append(dict(**entry,side='utility',extent_sha256=digest(data),extent_identical_on_play=other_identical,header_sources=source[:2],dictionary_sha256=digest(data[:512]),segments=records,uncovered_relative_blocks=[n for n in range(end-start) if n not in covered],confidence='high for block/length descriptors used by native bootstrap; info fields cross-checked with CiderPress2 ApplePascal_Code.cs, not ST layouts'))
    system_header,_=pages(251,2,media['utility'])
    report=dict(directory_block=79,directory_source=dir_source,directory_entries=entries,archives=archives,version_check=dict(native_address=0x6b0f,test_address=0x6103,mask=0xe0,expected=0xa0,observed_byte=system_header[0x103],observed_version_bits=system_header[0x103]>>5,message_address=0xf23e,interpretation='bootstrap accepts version field 5, rejected input prints SYSTEM.PASCAL is not version 1.2; not proof of unmodified stock runtime'))
    for archive in archives:
        expected={r.get('path') for r in archive['segments']}
        for slot in range(16):
            candidate=out/f"{archive['name']}-slot-{slot:02}.bin"
            if str(candidate.relative_to(ROOT)) not in expected and candidate.exists():candidate.unlink()
    (ROOT/'analysis/archive-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({a['name']:dict(segments=len(a['segments']),uncovered_blocks=a['uncovered_relative_blocks']) for a in archives}))
if __name__=='__main__':main()
