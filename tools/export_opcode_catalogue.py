#!/usr/bin/env python3
"""Export primary opcode identification, explicitly separated from runtime completeness."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def coverage(catalogue):
    rows=catalogue['primary']
    if len(rows)!=128 or {r['opcode'] for r in rows}!=set(range(128,256)):
        raise ValueError('primary catalogue must contain each high opcode exactly once')
    unresolved=[r['opcode'] for r in rows if r['status']!='verified_selected_semantics' or not r.get('probe_cases')]
    special={0x9e:'secondary-dispatch-only',0xd6:'generated-reset-stub-boundary'}
    calls={0xae,0xce,0xcf,0xcd,0xc2,0xc1,0xad}
    levels=[]
    for r in rows:
        level=('shared-error-prefix' if r.get('rule')=='shared_error_111' else special.get(r['opcode'])
               or ('controlled-call-return-and-service-boundaries' if r['opcode'] in calls else 'selected-data-control-semantics'))
        levels.append(dict(opcode=f'{r["opcode"]:02X}',rule=r.get('rule'),coverage=level,
                           checked_cases=r.get('probe_cases',0),native_handler=f'{r["handler"]:04X}',
                           rea_evidence_ids=r.get('rea_static_evidence_ids',[])))
    return dict(primary_entries=256,short_constant_values=128,high_entries=128,
                all_primary_entries_identified=not unresolved,unresolved_high_opcodes=unresolved,
                exhaustive_runtime_verified=False,coverage_by_high_opcode=levels,
                limitations=['Identification and selected native-model checks do not prove all inputs or Apple II execution.',
                             '18 shared-error slots are checked only to the exception machinery boundary.',
                             '9E is verified as a dispatcher; its target services are not thereby semantically verified.',
                             'ROM/MMIO, nonresident segment reads and release services remain explicit boundaries.',
                             'Legal Pascal type/operand combinations and complete modified p-system version remain open.'])

def main():
    catalogue=json.loads((ROOT/'analysis/opcode-evidence.json').read_text())
    low=catalogue['low_immediate_family']
    if (low['opcode_first'],low['opcode_last'],low['cases'])!=(0,127,128):
        raise ValueError('short constant family lacks complete value coverage')
    if sum(r.get('probe_cases',0) for r in catalogue['primary'])+128!=catalogue['total_probe_cases']:
        raise ValueError('per-opcode case accounting differs')
    if any(not r['native_instruction_addresses'] for r in catalogue['primary']):
        raise ValueError('identified opcode lacks visited native evidence')
    result=coverage(catalogue)
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    if hashlib.sha256(snapshot).hexdigest()!=catalogue['snapshot_sha256']:
        raise ValueError('catalogue snapshot changed')
    boot=json.loads((ROOT/'analysis/boot-regions.json').read_text())
    sectors=next(r for r in boot if r['name']=='runtime-bank1')['sectors']
    layouts=[]
    for address,size,name in ((0xddd6,34,'packed-field-masks'),(0xe189,2,'native-return-minus-one'),(0xe18b,1,'native-return-segment-marker')):
        raw=snapshot[address-0xd000:address-0xd000+size]
        p=sectors[(address-0xd000)//256]
        layouts.append(dict(name=name,address=hex(address),length=size,sha256=hashlib.sha256(raw).hexdigest(),
                            source=dict(side='utility',**p,byte_in_sector=address%256,image_offset=p['offset']+address%256),
                            method='native data-flow, source-byte checks and persistent Ghidra data classification',confidence='high static'))
    masks=snapshot[0xddd6-0xd000:0xddf8-0xd000]
    if [int.from_bytes(masks[n:n+2],'little') for n in range(0,34,2)]!=[(1<<n)-1 for n in range(17)]:
        raise ValueError('packed mask table differs')
    if int.from_bytes(snapshot[0xe189-0xd000:0xe18b-0xd000],'little')!=0xe17d:
        raise ValueError('native synthetic return data changed')
    result.update(snapshot_sha256=catalogue['snapshot_sha256'],total_controlled_cases=catalogue['total_probe_cases'],layouts=layouts)
    rea=json.loads((ROOT/'analysis/rea-opcode-crosscheck.json').read_text())
    if rea['status']!='verified_bounded_native_handlers' or rea['snapshot_sha256']!=catalogue['snapshot_sha256']:
        raise ValueError('REA native cross-check is absent or for another snapshot')
    result['rea_native_crosscheck']=dict(report='analysis/rea-opcode-crosscheck.json',views=len(rea['views']),
        native_instructions=sum(r['native_instructions_compared'] for r in rea['views']),
        source_bytes=sum(r['complete_bytes_verified'] for r in rea['views']),
        high_opcodes_linked=sum(bool(r.get('rea_static_evidence_ids')) for r in catalogue['primary']))
    (ROOT/'analysis/opcode-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Apple II primary p-code reference','',
           'Generated by `python3 tools/export_opcode_catalogue.py` from the native-backed catalogue.',
           'All 256 primary values are identified; coverage levels and remaining runtime limits are in',
           '`analysis/opcode-coverage.json`. This is selected semantics, not exhaustive execution proof.',
           'Low values 00–7F push their own unsigned value as a word and advance by one byte.','',
           '| Opcode | Native entry | Selected operation | Operands | Stack words | Continuation | Cases |',
           '|---|---|---|---|---|---|---:|']
    def cell(value):return str(value if value is not None else 'dynamic/boundary').replace('|','\\|').replace('\n',' ')
    for r in catalogue['primary']:
        lines.append('| '+ ' | '.join(cell(v) for v in (f'{r["opcode"]:02X}',f'{r["handler"]:04X}',r['rule'],r['operands'],r['stack_word_delta'],r['advance'],r['probe_cases']))+' |')
    lines+=['','See [semantics and experiments](opcode-semantics.md) for interpretation, fixture assumptions,',
            'error/dispatch boundaries, invalid operand edge behavior and actual REA Evidence.','']
    (ROOT/'docs/opcode-reference.md').write_text('\n'.join(lines))
    print(json.dumps(dict(all_primary_entries_identified=result['all_primary_entries_identified'],unresolved=result['unresolved_high_opcodes'],cases=result['total_controlled_cases'])))

if __name__=='__main__':main()
