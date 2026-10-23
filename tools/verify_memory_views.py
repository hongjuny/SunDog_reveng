#!/usr/bin/env python3
"""Check bank composition, p-code overlay, and Ghidra listing classification."""
import argparse,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]

def compare_views(bank1,bank2,runtime,ready,segment0):
    if (len(bank1),len(bank2),len(runtime),len(ready),len(segment0))!=(0x1000,0x3000,0x3000,0x3000,3124):raise ValueError('unexpected bounded view sizes')
    if runtime[:4096]!=bank1:raise ValueError('bank 1 view uses the wrong low bank')
    if runtime[4096:]!=bank2[4096:]:raise ValueError('bank 1 view has wrong common upper RAM')
    start=0xf248-0xd000;end=0xfe7c-0xd000
    if ready[start:end]!=segment0:raise ValueError('initial p-code overlay differs from archive payload')
    if ready[:start]!=runtime[:start] or ready[end:]!=runtime[end:]:raise ValueError('overlay modified bytes outside its load range')
    return dict(low_bank_matches=True,common_upper_matches=True,segment0_overlay_matches=True,outside_overlay_unchanged=True,changed_bytes=sum(a!=b for a,b in zip(runtime,ready)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=pathlib.Path,default=ROOT/'analysis/ghidra-interpreter-memory.json');ap.add_argument('--annotations',type=pathlib.Path,default=ROOT/'analysis/ghidra-opcode-annotations.json');args=ap.parse_args()
    directory=ROOT/'analysis/regions'
    def raw(name):return (directory/(name+'.bin')).read_bytes()
    payload=raw('archives/SYSTEM.PASCAL-slot-00')
    checks=compare_views(raw('lc-bank1'),raw('lc-bank2'),raw('runtime-bank1'),raw('interpreter-ready'),payload)
    b2=raw('lc-bank2');relocation=json.loads((ROOT/'analysis/relocation.json').read_text())
    p=relocation['source_address']-0xd000
    if raw('relocated-6800')!=b2[p:p+relocation['length']]:raise ValueError('relocation snapshot differs from common-bank source')
    checks['relocation_matches']=True
    state=json.loads(args.state.read_text())
    expected=[('d000',256),('d100',82),('ddd6',34),('e189',2),('e18b',1),('f248',3124)]
    for address,length in expected:
        region=next(r for r in state['regions'] if r['start']==address)
        if region.get('data_length')!=length or region['native_instruction_count']!=0:raise ValueError('Ghidra table/p-code data classification failed: '+address)
    digest=hashlib.sha256(raw('interpreter-ready')).hexdigest()
    initialized=[b for b in state['blocks'] if b['initialized']]
    if len(initialized)!=1 or initialized[0]['sha256']!=digest:raise ValueError('Ghidra loaded bytes differ from bounded snapshot')
    checks['ghidra_data_classification_matches']=True;checks['ghidra_memory_hash_matches']=True
    catalogue=json.loads((ROOT/'analysis/opcode-evidence.json').read_text())
    visited={int(a,16) for r in catalogue['primary'] for a in r['native_instruction_addresses']}
    listing=(ROOT/'ghidra/exports/interpreter-ready.txt').read_text()
    defined={int(a,16) for a in re.findall(r'^([0-9a-f]{4})  ',listing,re.M)}
    if not visited<=defined:raise ValueError('replayed native PC is not a Ghidra-defined instruction: '+str(sorted(visited-defined)))
    checks['native_probe_addresses_match_ghidra']=True;checks['distinct_replayed_native_addresses']=len(visited)
    annotations=json.loads(args.annotations.read_text())
    expected_aliases={r['opcode'] for r in catalogue['primary'] if r['status']=='verified_selected_semantics'}
    saved_aliases={op for r in annotations for op in r['opcodes']}
    if saved_aliases!=expected_aliases or not all(r['comment_readback_matches'] for r in annotations):raise ValueError('Ghidra annotation readback differs from verified catalogue')
    checks['annotated_native_entries']=len(annotations);checks['annotation_aliases_match']=True
    linked={r['handler']:r['rea_static_evidence_ids'] for r in catalogue['primary'] if r.get('rea_static_evidence_ids')}
    for row in annotations:
        if row['handler'] in linked and row.get('rea_static_evidence_ids')!=linked[row['handler']]:raise ValueError('Ghidra annotation lost actual REA Evidence links')
    checks['rea_linked_native_entries']=len(linked)
    report=dict(scope='direct Ghidra and source-byte composition verification; separate bounded REA acceptance in analysis/rea-memory-crosscheck.json',checks=checks,ghidra_program=state['program'],snapshot_sha256=digest,region_classifications=state['regions'],uninitialized_blocks=[b for b in state['blocks'] if not b['initialized']],relocation_source='analysis/relocation.json',overlay_source='analysis/boot-handoff.json')
    (ROOT/'analysis/memory-view-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(checks))
if __name__=='__main__':main()
