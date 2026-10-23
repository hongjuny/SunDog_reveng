#!/usr/bin/env python3
"""Static handoff reconstruction from native load arithmetic and procedure pointers.
No CPU emulation and no bytecode instruction decoding are performed.
"""
import json,pathlib
from boot_regions import pages
from runtime_evidence import u16
from disk_analysis import digest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def procedure_directory(segment,base,extra_regions=()):
    regions=[(base,segment),*extra_regions]
    def read(address,count):
        for start,raw in regions:
            p=address-start
            if p>=0 and p+count<=len(raw):return raw[p:p+count]
        raise ValueError(f'procedure metadata outside known loaded regions: {address:04x}')
    count=segment[-1];result=[]
    if not count or 2+2*count>len(segment):raise ValueError('invalid procedure count')
    for number in range(1,count+1):
        cell=base+len(segment)-2-2*number
        trailer=cell-u16(read(cell,2),0)
        tag=read(trailer,2)
        if tag[0]!=number:raise ValueError('procedure trailer number mismatch')
        attr=trailer-8
        entry=attr+6-u16(read(attr+6,2),0)
        read(entry,1)
        result.append(dict(number=number,directory_cell=cell,trailer_address=trailer,attribute_address=attr,lexical_level=tag[1] if tag[1]<128 else tag[1]-256,entry_address=entry,outside_main_segment=not base<=entry<base+len(segment)))
    return result

def main():
    header,hprov=pages(251,2);b1,_=pages(243,16);b2,bprov=pages(219,48)
    segment_length=u16(header,2);helper_length=u16(header,62)
    initial_top=u16(b2,0xf1f3-0xd000)
    helper_base=initial_top-helper_length
    relocated=(ROOT/'analysis/regions/relocated-6800.bin').read_bytes()
    if relocated[0x3a1:0x3a9]!=bytes.fromhex('a9fe855da97c855c'):raise ValueError('segment-zero load top changed')
    if relocated[0x30f:0x31b]!=bytes.fromhex('a003b180c68129e0c9a0f017'):
        raise ValueError('native codefile version-test signature changed')
    segment_top=0xfe7c;segment_base=segment_top-segment_length
    seg,segprov=pages(251+u16(header,0),2*((segment_length+511)//512));seg=seg[:segment_length]
    helper,hprov2=pages(251+u16(header,60),2*((helper_length+511)//512));helper=helper[:helper_length]
    procedures=procedure_directory(seg,segment_base,[(helper_base,helper)])
    view=bytearray(b1+b2[4096:]);view[segment_base-0xd000:segment_top-0xd000]=seg
    (ROOT/'analysis/regions/interpreter-ready.bin').write_bytes(view)
    (ROOT/'analysis/regions/initial-helper.bin').write_bytes(helper)
    report=dict(method='static reconstruction, conditional on successful reads and the observed native branches; not an emulator trace',directory_block=79,system_pascal_block=251,descriptor_sources=hprov,segment0=dict(source_block=252,length=segment_length,load_top=segment_top,load_address=segment_base,sectors=segprov,sha256=digest(seg)),helper=dict(source_block=259,length=helper_length,initial_top=initial_top,load_address=helper_base,sectors=hprov2,sha256=digest(helper)),native_copy_region_overwritten=[0xf290,0xf790],first_fetch=dict(native_address=0xd293,pointer_low=0x58,pointer_high=0x59,pcode_address=procedures[0]['entry_address'],first_opcode=seg[procedures[0]['entry_address']-segment_base]),procedure_count=len(procedures),procedures=procedures,cleanup=dict(start=0x6000,end_inclusive=0x6c30,preserved_final_jump=0x6c43),snapshot=dict(path='analysis/regions/interpreter-ready.bin',base=0xd000,length=len(view),sha256=digest(view)))
    (ROOT/'analysis/boot-handoff.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(first_pcode=hex(report['first_fetch']['pcode_address']),procedures=len(procedures),helper=hex(helper_base),cross_region_procedures=[p['number'] for p in procedures if p['outside_main_segment']])) )
if __name__=='__main__':main()
