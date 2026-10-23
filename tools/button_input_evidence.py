#!/usr/bin/env python3
"""Reconstruct native button polling/latching; MMIO samples are declared test RAM."""
import hashlib,itertools,json
from pathlib import Path
from native_probe import CPU
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def filter_sample(sample,pending,previous,level_mode):
    down=((sample|pending)>>7)&1
    remaining=0 if down and pending else pending
    if level_mode:return down,remaining,previous
    return down&(~previous&255),remaining,down

def run():
    mapping=json.loads((ROOT/'analysis/graphics-call-chain.json').read_text())
    capture=ROOT/mapping['captured_mapping']['capture'];memory=capture.read_bytes()
    if sha(memory)!=mapping['captured_mapping']['memory_sha256']:raise ValueError('retained RAM identity differs')
    archive=(ROOT/'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes()
    if sha(archive)!=mapping['source_archive_sha256']:raise ValueError('library identity differs')
    p=next(p for p in mixed_directory(archive) if p['number']==2)
    base=mapping['captured_mapping']['segment_base'];entry=base+p['entry_address'];end=base+p['attribute_address']
    if entry!=0xa208:raise ValueError('captured mapping differs from selected analysis')
    code=memory[entry:end];hook_address=int.from_bytes(memory[0xa290:0xa292],'little')
    hook=memory[hook_address:0xa2b4]
    for name,data in [('rea-library22-input2-source',archive[p['entry_address']:p['attribute_address']]),
                      ('rea-library22-input2-captured',code),('rea-library22-input-hook-full',hook)]:
        (ROOT/'analysis/regions'/(name+'.bin')).write_bytes(data)
    evidence=json.loads((ROOT/'analysis/local/rea/input2-captured.json').read_text())
    hook_evidence=json.loads((ROOT/'analysis/local/rea/input-hook-full.json').read_text())
    if evidence['subject']['digest']['sha256']!=sha(code) or hook_evidence['subject']['digest']['sha256']!=sha(hook):raise ValueError('REA identity differs')
    defined={int(line.split(':',1)[0],16) for e in (evidence,hook_evidence) for line in e['normalized_result'].splitlines() if line.startswith('0x')}
    visited=set();cases=0
    def fixture(selector,installed=1,install_enabled=0):
        c=CPU();c.memory[entry:end]=code;c.memory[0xa29a]=installed;c.memory[0xbf22]=install_enabled;c.memory[1]=install_enabled
        c.memory[0xd004:0xd006]=(0xd71d).to_bytes(2,'little')
        for value in (selector,0,0):c.push_word(value)
        c.push_word(0x3fff);c.pc=entry
        return c
    for index,level,sample,pending,previous,carry in itertools.product(range(4),(False,True),(0,0x7f,0x80,0xff),(0,0x7f,0x80,0xff),(0,1),(0,1)):
        selector=index|(4 if level else 0);c=fixture(selector);c.c=carry
        c.memory[0xc061+index]=sample;c.memory[0xa292+index]=pending;c.memory[0xa296+index]=previous
        expected=filter_sample(sample,pending,previous,level)
        c.run({0x4000},max_steps=500)
        result=c.pop_word()
        if (result,c.read(0xa292+index),c.read(0xa296+index))!=expected or c.sp!=255:raise AssertionError('native filter/latch/edge result differs')
        if not c.visited<=defined:raise AssertionError('input probe left REA-defined instructions')
        visited.update(c.visited);cases+=1
    hook_cases=0
    for current0,current1,pending0,pending1 in itertools.product((0,0x7f,0x80,0xff),repeat=4):
        c=CPU();c.memory[entry:end]=code;c.memory[0xc061]=current0;c.memory[0xc062]=current1
        c.memory[0xa292]=pending0;c.memory[0xa293]=pending1;c.pc=0xa29d
        c.run({0xa2af},max_steps=10)
        if (c.read(0xa292),c.read(0xa293))!=(current0|pending0,current1|pending1):raise AssertionError('hook latching differs')
        if not c.visited<=defined:raise AssertionError('hook body left REA-defined instructions')
        visited.update(c.visited);hook_cases+=1
    c=fixture(0,installed=0,install_enabled=1);c.run({0x4000},max_steps=500)
    if c.word(0xd004)!=hook_address or c.word(0xa2b2)!=0xd71d or c.read(0xa29a)!=1:raise AssertionError('dispatch hook installation differs')
    if not c.visited<=defined:raise AssertionError('installation left REA-defined instructions')
    visited.update(c.visited)
    c=fixture(8);c.memory[0xd004:0xd006]=hook_address.to_bytes(2,'little');c.run({0x4000},max_steps=500)
    if c.word(0xd004)!=0xd71d or c.pop_word()!=0:raise AssertionError('selector-8 dispatch restore differs')
    if not c.visited<=defined:raise AssertionError('restore left REA-defined instructions')
    visited.update(c.visited)
    lc_path=capture.with_name('advanced-lc1.bin');lc=lc_path.read_bytes()
    original=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    if int.from_bytes(lc[4:6],'little')!=hook_address or int.from_bytes(original[4:6],'little')!=0xd71d:raise ValueError('captured/original dispatch cell differs')
    segment=next(s for a in json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives'] if a['name']=='SYSTEM.LIBRARY' for s in a['segments'] if s['segment_number']==22)
    s=segment['sectors'][p['entry_address']//256]
    report=dict(method='Actual REA/Ghidra native function, retained bank-1 mapping, bounded native probes with explicit RAM values standing for hardware samples; no live MMIO execution',
        capture=str(capture.relative_to(ROOT)),capture_main_sha256=sha(memory),retained_stage='Utility Ctrl-U menu; not a new Play execution observation',
        source=dict(side='utility',**s,byte_in_sector=p['entry_address']%256),procedure=2,segment=22,
        source_archive_sha256=sha(archive),native_source_entry=p['entry_address'],captured_entry=entry,captured_function_sha256=sha(code),
        filter_cases=cases,hook_body_cases=hook_cases,dispatch_install_restore_cases=2,
        selector_contract={'0..3':'channel = selector & 3; rising-edge mode','4..7':'same channels; level mode, edge history unchanged','8':'restore saved D004 dispatch word; return false'},
        memory_fields=dict(pending=0xa292,previous=0xa296,installed=0xa29a,saved_dispatch_operand=0xa2b2),
        installed_hook=dict(address=hook_address,original_dispatch=0xd71d,dispatch_cell=0xd004,primary_opcode=0x82,
                            hardware_reads=[0xc061,0xc062],body='OR raw channel samples into pending bytes, preserve A/status, jump to saved original ADD16 handler',
                            captured_lc1_sha256=sha(lc),captured_dispatch_matches=True),
        native_instruction_addresses=[hex(p) for p in sorted(visited)],rea_evidence_ids=[evidence['evidence_id'],hook_evidence['evidence_id']],
        remaining=['Meaning/timing of initial BF22 & zero-page-1 hook gate','Physical input sampling and call timing','Full UI event object returned by segment 21','Keyboard and gamepad-to-host mapping','Full flag preservation outside tested hook middle'])
    (ROOT/'analysis/button-input-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(filter_cases=cases,hook_cases=hook_cases,installed_in_add16_dispatch=True)))
if __name__=='__main__':run()
