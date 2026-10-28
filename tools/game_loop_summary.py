#!/usr/bin/env python3
"""Reproduce evidence index and bounded periodic-call observations."""
import hashlib
import json
from pathlib import Path
from initial_game_flow import require, span
ROOT = Path(__file__).resolve().parents[1]

def main():
    inventory = json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive = next(a for a in inventory['archives'] if a['name']=='SYSTEM.LIBRARY')
    source = next(s for s in archive['segments'] if s.get('segment_number')==24)
    raw = (ROOT/source['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:
        raise ValueError('Shared runtime source changed')
    p = next(p for p in json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-03.json').read_text()) if p['procedure']['number']==9)
    if p['boundaries']: raise ValueError('Unresolved decoder boundary')
    for row in p['instructions']:
        if raw[row['address']]!=row['opcode']: raise ValueError('Opcode mismatch')
    require(p,0xE0A,'store_local',index=1)
    require(p,0xE11,'remainder_magnitude16')
    require(p,0xE12,'store_table_indexed',index=352)
    require(p,0xE1E,'call_external_segment',segment_operand=22,procedure=29)
    require(p,0xE27,'store_table_indexed',index=352)
    for address,proc in ((0xE2D,12),(0xE31,15),(0xE3D,13),(0xE4E,7)):
        require(p,address,'call_current_global_link',procedure=proc)
    require(p,0xE40,'store_table_indexed',index=227)
    result = dict(evidence_documents=['ship-main-loop.json','joystick-pointer.json','ship-actions.json','ghidra-gameplay-annotations.json'],
        periodic=dict(source=span(source,raw,9,0xE06,0xE52), confidence='high-static',
        operations=['Copy global227 into local1','global352 %= 4; when zero call22P29; then increment global352',
                    'Call24P12 and24P15 with local1 reference; optionally24P13 when flag40 set',
                    'Write local1 back toglobal227; call24P7 with global323 address and values227/8/10'],
        limitations=['24P9 itself does not store loop counter354; indirect callees not resolved here',
                     'No conversion of loop count15 into seconds or frames is justified',
                     'Names and effects of nested periodic subsystems need further analysis']))
    (ROOT/'analysis/game-loop-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Game-loop evidence index and periodic source guards checked')

if __name__=='__main__': main()
