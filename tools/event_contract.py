#!/usr/bin/env python3
"""Reproduce segment21 shared-reference/selection evidence; no game interpreter."""
import hashlib
import json
from pathlib import Path
from native_probe import CPU
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()


def root_reference(procedure,row):
    """Identify a load of one of P1's eight reference words, respecting depth."""
    level=procedure['lexical_level'];op=row['operation'];d=row['operands']
    if procedure['number']==1 and op in ('load_local','load_local_short'):
        index=d['index']
    elif op=='load_nonlocal' and d['selector_or_depth']==level-1:
        index=d['index']
    else:return None
    return index if 1<=index<=8 else None


def source_point(segment,offset):
    sector=segment['sectors'][offset//256]
    return dict(side='play',**sector,byte_in_sector=offset%256,image_offset=sector['offset']+offset%256)


def load_inputs():
    inv=json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())
    sources={s['segment_number']:s for s in inv['segments']}
    out={}
    for number in (1,21):
        s=sources[number];raw=(ROOT/s['path']).read_bytes()
        if SHA(raw)!=s['sha256']:raise ValueError('Archive source changed')
        path=ROOT/f"analysis/local/pcode/SYSTEM.STARTUP-slot-{s['slot']:02}-play.json"
        decoded=json.loads(path.read_text())
        if any(r['boundaries'] for r in decoded):raise ValueError('Unresolved procedure boundary')
        out[number]=(s,raw,{r['procedure']['number']:r for r in decoded})
    return out


def run():
    sources=load_inputs();source,raw,procedures=sources[21]
    caller,caller_raw,caller_procedures=sources[1]
    p1=procedures[1]['procedure'];parameter_bytes=int.from_bytes(raw[p1['trailer_address']-6:p1['trailer_address']-4],'little')
    if parameter_bytes!=16:raise ValueError('P1 no longer takes eight word arguments')
    rows=caller_procedures[4]['instructions'];pushes=[r for r in rows if 0xf8<=r['address']<0x108]
    order=[r['operands']['index'] for r in pushes if r['operation']=='address_local']
    if order!=[8,7,6,5,4,3,2,9] or len(pushes)!=8:raise ValueError('Caller argument preparation differs')
    call=next(r for r in rows if r['address']==0x108)
    if call['calls']!=[dict(kind='external',segment_operand=21,procedure=1)]:
        # Catalogue call records may carry additional descriptive fields.
        if not any(c.get('segment_operand')==21 and c.get('procedure')==1 for c in call['calls']):raise ValueError('Caller target differs')
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    if SHA(snapshot)!='fbb9094b9dd0e11eadcc91351cc2ebdb9c65739762072b2cf14e291b99907f7b':raise ValueError('Native snapshot changed')
    defined={int(line[:4],16) for line in (ROOT/'ghidra/exports/interpreter-ready.txt').read_text().splitlines() if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    argument_cases=[]
    for base in (0x2000,0x8000,0xff00):
        c=CPU();c.memory[0xd000:]=snapshot
        def word(p,v):c.memory[p:p+2]=(v&65535).to_bytes(2,'little')
        word(0x86,0x6000);word(0x88,0x4000);word(0x6002,parameter_bytes)
        for index in order:c.push_word(base+2*index)
        c.pc=0xe1f8;c.run({0xe216},500)
        actual=[c.word(0x400c+2*i) for i in range(8)]
        if actual!=[base+2*i for i in (9,2,3,4,5,6,7,8)] or c.sp!=255 or not c.visited<=defined:raise AssertionError('Native argument copier disagrees')
        argument_cases.append(dict(pointer_base=base,callee_local_to_caller_local=[9,2,3,4,5,6,7,8]))
    refs={i:[] for i in range(1,9)}
    for r in procedures.values():
        rows=r['instructions']
        for i,row in enumerate(rows):
            index=root_reference(r['procedure'],row)
            if index is None:continue
            following=rows[i+1] if i+1<len(rows) else None
            usage='word_read' if following and following['operation']=='load_indirect_short' and following['operands']['word_offset']==0 else 'pointer_use; effect requires following dataflow'
            refs[index].append(dict(procedure=r['procedure']['number'],offset=row['address'],source=source_point(source,row['address']),usage=usage))
    spans=[(21,0xaea,0xb18,'40-by-24 byte-map selection into reference2'),
           (40,0x1b9c,0x1bce,'same lookup, then reference2 magnitude remainder16'),
           (12,0x555,0x56b,'reference4=(root26+3)/7; reference3=(root25-3)/8'),
           (30,0x1563,0x156d,'clear reference1 and reference2'),
           (1,0x1e7f,0x1e82,'set reference1 to1'),
           (40,0x1de9,0x1df0,'set reference2 to255')]
    evidence=[]
    for number,start,end,meaning in spans:
        rows=[r for r in procedures[number]['instructions'] if start<=r['address']<end]
        if not rows or rows[0]['address']!=start or rows[-1]['address']+rows[-1]['length']!=end:raise ValueError('Evidence span boundaries differ')
        evidence.append(dict(procedure=number,start_offset=start,end_exclusive=end,meaning=meaning,
                             source=source_point(source,start),sha256=SHA(raw[start:end]),instruction_count=len(rows)))
    # Verify the exact fields/scale and operations that give the portable formula.
    p21={r['address']:r for r in procedures[21]['instructions']}
    expected={0xaea:('load_nonlocal',{'selector_or_depth':1,'index':6}),0xaee:('load_nonlocal',{'selector_or_depth':1,'index':26}),
              0xaf3:('push_short_constant',{'value':28}),0xaf6:('push_short_constant',{'value':40}),
              0xafa:('load_nonlocal',{'selector_or_depth':1,'index':5}),0xafe:('load_nonlocal',{'selector_or_depth':1,'index':25}),
              0xb03:('load_nonlocal',{'selector_or_depth':1,'index':21}),0xb08:('push_short_constant',{'value':24}),
              0xb0c:('load_nonlocal',{'selector_or_depth':1,'index':2}),0xb0f:('load_nonlocal',{'selector_or_depth':1,'index':55}),
              0xb13:('scaled_indexed_address',{'index':20}),0xb16:('load_indexed_byte',{}),0xb17:('store_indirect_word',{})}
    for a,(op,d) in expected.items():
        if p21[a]['operation']!=op or p21[a]['operands']!=d:raise ValueError('Selected field or encoding changed')
    result=dict(method='Original decoded p-code dataflow, source-digest checks and actual native argument-copy probe; static effects, not an observed game event trace',
                source_sha256=source['sha256'],segment=21,procedure=1,parameter_bytes=parameter_bytes,
                caller=dict(segment=1,procedure=4,call_offset=0x108,source=source_point(caller,0x108),source_sha256=caller['sha256'],push_order=order),
                native_argument_copy=dict(start=0xe1f8,stop_before=0xe216,snapshot_sha256=SHA(snapshot),slice_sha256=SHA(snapshot[0xe1f8-0xd000:0xe216-0xd000]),cases=argument_cases,ghidra_boundaries_match=True),
                references=[dict(callee_local=i,caller_local=(9 if i==1 else i),accesses=refs[i]) for i in range(1,9)],
                selected_effects=evidence,
                selection=dict(row_bytes=40,rows=24,total_bytes=960,map_pointer='P1 local55',
                    column='magnitude_remainder16(add16(*ref6, divide_signed16(add16(P1.local26,3),28)),40)',
                    row='magnitude_remainder16(add16(*ref5, divide_signed16(subtract16(P1.local25,3),P1.local21)),24)',
                    byte_address='P1.local55 + 40*row + column',output='*ref2',
                    P40_followup='*ref2 = magnitude_remainder16(*ref2,16)'),
                return_control=dict(root_flag_reference=1,caller_local=9,
                    P1_loop_exit='state(bits8..11) differs from saved nibble(bits4..7), or table29.word347 bit0, or *ref1 bit0',
                    consumer='Startup segment1 P4 state5 compares local2 to255 for segments17/18; state6 signed local2<=3 selects19, else20'),
                confidence='high for exact source fields, pointer ordering and selected arithmetic/dataflow; semantic names remain partial',
                remaining=['Full scene initialization and ownership of map/local55','Meaning of every selected byte and nibble','Joystick/keyboard event timing and cursor conversion before these expressions',
                           'Every caller-owned reference lifetime and all indirect callee side effects','Original map graphics/tile resources and clipping'])
    (ROOT/'analysis/event-contract.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(segment=21,reference_words=8,argument_copy_cases=len(argument_cases),root_reference_load_sites=sum(map(len,refs.values())),selected_evidence_spans=len(evidence))))

if __name__=='__main__':run()
