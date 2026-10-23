#!/usr/bin/env python3
"""Suggest review targets from decoded inline strings plus procedure/call context.
Roles remain candidates until state changes and I/O contracts are reconstructed.
No original strings or instruction bytes are published in the summary.
"""
import hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TERMS={'trade':['buy','sell','price','lots','storing cargo'],
       'ship_navigation':['planetary','city-city','out of fuel','refuel','planet:'],
       'ship_inventory':['cargo','locker','stores','guns'],
       'location_display':['city:','planet:']}
def main():
    inventory=json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())
    rows=[]
    for segment in inventory['segments']:
        raw=(ROOT/segment['path']).read_bytes()
        decoded=json.loads((ROOT/f"analysis/local/pcode/SYSTEM.STARTUP-slot-{segment['slot']:02}-play.json").read_text())
        for procedure in decoded:
            hits=[]
            for instruction in procedure['instructions']:
                if instruction['opcode'] not in (0xa6,0xd0):continue
                address=instruction['address'];n=instruction['operands']['payload_length'];payload=raw[address+2:address+2+n]
                text=payload.decode('ascii',errors='replace').lower()
                matches={group:[term for term in terms if re.search(r'\b'+re.escape(term),text)] for group,terms in TERMS.items()}
                matches={key:value for key,value in matches.items() if value}
                if not matches:continue
                source=segment['sectors'][address//256]
                hits.append(dict(pcode_offset=address,payload_length=n,payload_sha256=hashlib.sha256(payload).hexdigest(),
                                 matched_terms=matches,source=dict(side='play',**source,byte_in_sector=address%256)))
            if not hits:continue
            operations=Counter(i['operation'] for i in procedure['instructions'])
            accesses=Counter((i['operation'],i['operands'].get('selector_or_depth'),i['operands'].get('index'))
                             for i in procedure['instructions'] if i['operation'] in ('load_table_indexed','store_table_indexed','address_table_indexed'))
            rows.append(dict(segment_number=segment['segment_number'],procedure=procedure['procedure']['number'],
                             entry_offset=procedure['procedure']['entry_address'],confidence='candidate from decoded inline text and static procedure context; not verified subsystem semantics',
                             hints=hits,operation_counts=dict(operations),
                             table_accesses=[dict(operation=op,selector=selector,index=index,occurrences=count) for (op,selector,index),count in sorted(accesses.items())],
                             static_calls=[dict(pcode_offset=i['address'],**c) for i in procedure['instructions'] for c in i['calls']],
                             boundaries=procedure['boundaries']))
    report=dict(method='Review prioritization from decoded original Play p-code; labels are hypotheses, not a native implementation specification',candidates=rows)
    (ROOT/'analysis/subsystem-candidates.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(candidate_procedures=len(rows),by_segment=dict(Counter(r['segment_number'] for r in rows)))))
if __name__=='__main__':main()
