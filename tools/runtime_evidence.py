#!/usr/bin/env python3
"""Catalogue native dispatch evidence. Does not decode any game p-code."""
import json,pathlib
from boot_regions import pages
from disk_analysis import digest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def u16(data,offset):
    return int.from_bytes(data[offset:offset+2],'little')

def catalogue(bank1,bank2):
    if len(bank1)!=0x1000 or len(bank2)!=0x3000:raise ValueError('incorrect bank sizes')
    common=bank2[0x1000:];view=bank1+common
    def at(address,n):return view[address-0xd000:address-0xd000+n]
    # These complete instructions establish how the tables are indexed.
    if at(0xd293,13)!=bytes.fromhex('a000b15810ef0a8d9ed26c00d0'):
        raise ValueError('primary fetch/dispatch signature changed')
    if at(0xe67f,11)!=bytes.fromhex('a001b1580a8d88e66c00d1'):
        raise ValueError('secondary dispatch signature changed')
    primary=[dict(opcode=0x80+i,table_address=0xd000+2*i,handler=u16(bank1,2*i)) for i in range(128)]
    # 41 word-shaped cells precede executable D152. Zero cells are reserved/unknown,
    # not executable handlers. Valid selector range is still unproved.
    secondary=[dict(selector=i,table_address=0xd100+2*i,handler=u16(bank1,0x100+2*i),status='zero/unknown' if u16(bank1,0x100+2*i)==0 else 'candidate handler') for i in range(41)]
    wrappers=[]
    for n in range(21):
        wrapper=0xff00+3*n;trampoline=wrapper+0x5c
        if at(wrapper,3)!=bytes.fromhex('209eff') or at(trampoline,1)!=b'\x4c':raise ValueError('BIOS wrapper shape changed')
        wrappers.append(dict(wrapper=wrapper,return_address=wrapper+2,added_to_return=0x5a,trampoline=trampoline,bank2_handler=u16(view,trampoline-0xd000+1)))
    return dict(primary=primary,secondary=secondary,bios_wrappers=wrappers,fetch_address=0xd293,instruction_pointer=[0x58,0x59],primary_patch=0xd29e,secondary_patch=0xe688,secondary_dispatch_opcode=next(x['opcode'] for x in primary if x['handler']==0xe67f),confidence='high for native instructions and table values; bytecode archive format and full opcode semantics not established')

def provenance(address):
    block=243 if address<0xe000 else 219
    base=0xd000
    _,sectors=pages(block,16 if block==243 else 48)
    p=sectors[(address-base)//256]
    return dict(side='utility',**p,byte_in_sector=address%256,image_offset=p['offset']+address%256,bank='bank1' if address<0xe000 else 'common')

def main():
    b1,_=pages(243,16);b2,_=pages(219,48)
    report=catalogue(b1,b2)
    for group in ('primary','secondary'):
        for x in report[group]:
            x['table_source']=provenance(x['table_address'])
            if x['handler']>=0xd152:x['handler_source']=provenance(x['handler'])
    for x in report['bios_wrappers']:
        # BIOS low-bank handlers use bank 2, not interpreter bank 1.
        _,sectors=pages(219,48);p=sectors[(x['bank2_handler']-0xd000)//256]
        x['handler_source']=dict(side='utility',**p,byte_in_sector=x['bank2_handler']%256)
    report['source_hashes']=dict(bank1=digest(b1),bank2=digest(b2))
    (ROOT/'analysis/runtime-dispatch.json').write_text(json.dumps(report,indent=2)+'\n')
    seeds={0xfef2,0xd27b,0xd155,0xe67f,0xd293}
    for group in ('primary','secondary'):
        seeds.update(x['handler'] for x in report[group] if x['handler']>=0xd152)
    (ROOT/'analysis/local/runtime-seeds.txt').write_text(','.join(format(n,'x') for n in sorted(seeds)))
    bios={0xdaa9,0xd83d,0xd00e,0xf69a}
    bios.update(x['bank2_handler'] for x in report['bios_wrappers'])
    (ROOT/'analysis/local/bios-seeds.txt').write_text(','.join(format(n,'x') for n in sorted(bios)))
    print(json.dumps(dict(primary=len(report['primary']),secondary_cells=len(report['secondary']),bios_wrappers=len(report['bios_wrappers']))))
if __name__=='__main__':main()
