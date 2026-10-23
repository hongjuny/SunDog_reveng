#!/usr/bin/env python3
"""Extract the game's actual packed-state dispatcher, preserving unresolved roles."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def paths_to_join(rows,start,join):
    nodes={r['address']:r for r in rows};pending=[start];seen=set();calls=[]
    while pending:
        pc=pending.pop()
        if pc==join or pc in seen:continue
        seen.add(pc)
        if pc not in nodes:raise ValueError('route reaches unanalysed instruction')
        row=nodes[pc]
        calls.extend(dict(address=pc,**call) for call in row['calls'])
        pending.extend(row['successors'])
    return sorted(calls,key=lambda row:row['address'])

def main():
    inventory=json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())
    source=next(s for s in inventory['segments'] if s['segment_number']==1)
    raw=(ROOT/source['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('startup source changed')
    procedures=json.loads((ROOT/'analysis/local/pcode/SYSTEM.STARTUP-slot-00-play.json').read_text())
    by_number={r['procedure']['number']:r for r in procedures}
    if any(r['boundaries'] for r in procedures):raise ValueError('startup dispatcher still has an unresolved decode boundary')
    def provenance(offset):
        sector=source['sectors'][offset//256]
        return dict(side='play',**sector,byte_in_sector=offset%256,image_offset=sector['offset']+offset%256)
    initial=by_number[1];nodes={r['address']:r for r in initial['instructions']};pc=initial['procedure']['entry_address'];seen=set();events=[];previous=None
    while pc not in seen:
        seen.add(pc);row=nodes[pc]
        if row['calls']:events.extend(dict(address=pc,**call) for call in row['calls'])
        if row['opcode']==0x9e:
            if previous is None or previous['opcode']>=128:raise ValueError('service argument not directly proven constant')
            events.append(dict(address=pc,service=row['service_name'],argument=previous['opcode']))
        if row.get('return'):break
        if len(row['successors'])!=1:raise ValueError('initialization order is not a simple path')
        previous=row;pc=row['successors'][0]
    routes=[]
    for number,join in ((3,0x5c),(4,0x160)):
        p=by_number[number];case=next(r for r in p['instructions'] if r['opcode']==0xac)
        entries=[]
        for value,target in zip(range(case['operands']['lower'],case['operands']['upper']+1),case['successors'][1:]):
            entries.append(dict(state=value,target_offset=target,calls_before_join=paths_to_join(p['instructions'],target,join)))
        routes.append(dict(procedure=number,case_offset=case['address'],case_source=provenance(case['address']),join_offset=join,
                           default_target=case['successors'][0],entries=entries))
    state=dict(table_selector=29,word_index=45,width=4,shift=8,formula='(word(table[29] + 2*45) >> 8) & 15',
               note='table[29] is the BD9E-indexed pointer; native assembler data base may be table[29]+2')
    result=dict(method='Original Play segment-1 CFG and verified native operand/packed-field rules; static normal-return conditions',
                source_sha256=source['sha256'],state_field=state,initialization_events=events,dispatchers=routes,
                master_loop=dict(procedure=6,loop_offset=0x1b0,loop_source=provenance(0x1b0),
                    low_state_predicate='state <= 2',low_state_call=3,other_state_call=4,exit_predicate='state >= 11',back_edge_offset=0x1c8),
                nested_dispatch=dict(procedure=5,predicate='state == 8',true_segment=14,false_segment=8),
                subordinate_loop_exits={'3':'state >= 11 or state == 3 or state == 4','4':'state <= 2 or state >= 11'},
                conditional_routes={'procedure4_state5':'local[2] == 255 selects segment 17, otherwise segment 18',
                                    'procedure4_state6':'signed local[2] <= 3 selects segment 19, otherwise segment 20'},
                remaining=['Meaning and ownership of every state value','Input event structure returned by segment 21','Runtime disk selection','Nested scene/transaction state changes'])
    (ROOT/'analysis/startup-control-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(startup_procedures=6,all_static_paths_decoded=True,state_bits='8..11 of table29 word45',initialization_events=len(events))))
if __name__=='__main__':main()
