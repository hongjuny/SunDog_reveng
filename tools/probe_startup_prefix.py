#!/usr/bin/env python3
"""Replay only the verified initial native interpreter paths on synthetic state.
Stops before the BIOS wrapper; never claims an Apple II boot.
"""
import hashlib,json,pathlib,re
from native_probe import CPU
from boot_handoff import procedure_directory
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    handoff=json.loads((ROOT/'analysis/boot-handoff.json').read_text())
    dispatch=json.loads((ROOT/'analysis/runtime-dispatch.json').read_text())
    entry=handoff['first_fetch']['pcode_address']
    cpu=CPU();cpu.memory[0xd000:]=snapshot
    for p,v in ((0x58,entry),(0x52,0x6000),(0x50,0x7000),(0x6014,0xabcd)):
        cpu.memory[p]=v&255;cpu.memory[p+1]=v>>8
    cpu.memory[0xa1]=0x55;cpu.memory[0xa2]=0xaa
    cpu.pc=0xd293;events=[]
    for expected,rule in ((0x9f,'push_zero'),(0xcc,'store_local_index_5'),(1,'push_short_immediate')):
        pcode=cpu.word(0x58)
        if cpu.read(pcode)!=expected:raise ValueError('initial p-code prefix changed')
        initial_sp=cpu.sp;cpu.run({0xd293})
        events.append(dict(pcode_address=pcode,opcode=expected,selected_semantic=rule,next_pcode_address=cpu.word(0x58),native_stack_pointer_before=initial_sp,native_stack_pointer_after=cpu.sp))
    if cpu.word(0x6014)!=0 or cpu.sp!=253:raise ValueError('prefix memory/stack effect differs')
    boundary=cpu.word(0x58)
    if cpu.read(boundary)!=0x9e:raise ValueError('expected secondary dispatch after prefix')
    selector=cpu.read(boundary+1)
    target=next(r['handler'] for r in dispatch['secondary'] if r['selector']==selector)
    cpu.run({target})
    top=cpu.read(0x100+((cpu.sp+1)&255))|(cpu.read(0x100+((cpu.sp+2)&255))<<8)
    if top!=1:raise ValueError('unexpected system-handler stack argument')
    cpu.run({0xff06})
    if cpu.read(0xa1)!=0 or cpu.read(0xa2)!=0:raise ValueError('system-handler preparation differs')
    route=next(r for r in dispatch['bios_wrappers'] if r['wrapper']==0xff06)
    def stack_word(offset):
        return cpu.read(0x100+((cpu.sp+offset)&255))|(cpu.read(0x100+((cpu.sp+offset+1)&255))<<8)
    params=[stack_word(5),stack_word(3)]
    if params!=[cpu.word(0xee82),cpu.word(0xf1f7)]:raise ValueError('native stack arguments disagree with source words')
    defined={int(a,16) for a in re.findall(r'^([0-9a-f]{4})  ',(ROOT/'ghidra/exports/interpreter-ready.txt').read_text(),re.M)}
    if not cpu.visited<=defined:raise ValueError('startup native replay left Ghidra-defined instructions')
    resume=boundary+2
    if cpu.read(resume)!=0xcd or snapshot[0xe306-0xd000:0xe312-0xd000]!=bytes.fromhex('a002b1588582a001b1588590'):raise ValueError('conditional call operand evidence changed')
    segment_number=cpu.read(resume+1);procedure_number=cpu.read(resume+2)
    archives=json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives']
    archive=next(a for a in archives if a['name']=='SYSTEM.PASCAL')
    descriptor=next(r for r in archive['segments'] if r['slot']==segment_number)
    payload=(ROOT/descriptor['path']).read_bytes()
    if hashlib.sha256(payload).hexdigest()!=descriptor['sha256']:raise ValueError('conditional target segment differs from archive inventory')
    procedures=procedure_directory(payload,0)
    procedure=next(r for r in procedures if r['number']==procedure_number)
    source=descriptor['sectors'][procedure['entry_address']//256]
    conditional=dict(condition='BIOS path returns normally through F008/D27B; not executed',pcode_address=resume,opcode=0xcd,native_operand_reader=0xe306,segment_slot=segment_number,procedure_number=procedure_number,segment_absolute_block=descriptor['absolute_block'],segment_bytes=len(payload),procedure_count=len(procedures),entry_offset_in_segment=procedure['entry_address'],entry_disk_source=dict(side='utility',**source,byte_in_sector=procedure['entry_address']%256),runtime_load_address='unresolved; depends on allocation state')
    report=dict(conditional_next_call=conditional,native_instruction_addresses=[f'0x{a:04x}' for a in sorted(cpu.visited)],ghidra_instruction_boundaries_match=True,method='bounded replay of actual native interpreter and original p-code bytes on explicitly synthetic frame/stack state; not an observed boot and not REA Evidence',snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),synthetic_assumptions=dict(local_frame=0x6000,global_frame=0x7000,initial_stack_pointer=255,initial_local_index_5=0xabcd,initial_a1=0x55,initial_a2=0xaa),events=events,local_index_5_after=0,next_boundary=dict(pcode_address=boundary,opcode=0x9e,selector=selector,native_handler=target,top_word_on_entry=1,executed_until=0xff06,bios_wrapper=0xff06,bank2_destination_from_trampoline=route['bank2_handler'],pushed_parameter_words=params,bios_executed=False,reason='Handler followed only until entry to BIOS wrapper FF06; no bank switch or device access is executed.'),confidence='derived from verified native bytes, limited 6502 model and synthetic state; actual startup frame values unobserved')
    (ROOT/'analysis/startup-prefix-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(verified_prefix_operations=len(events),next_native_handler=hex(target),selector=hex(selector),stopped_before_bios=True)))
if __name__=='__main__':main()
