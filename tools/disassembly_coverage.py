#!/usr/bin/env python3
"""Independent byte-accounting audit; never treats undecoded bytes as proved data.

Public output contains structural coordinates/counts/hashes only. Original
instructions, operands, text and byte values stay in ignored local artifacts.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from pcode_analysis import Space
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda raw:hashlib.sha256(raw).hexdigest()


def ranges(values):
    result=[]
    for value in sorted(set(values)):
        if result and value==result[-1][1]:result[-1][1]+=1
        else:result.append([value,value+1])
    return result


def classify_pcode(space,procedure,instructions):
    """Disjoint byte roles for decoded records, with narrow padding evidence."""
    roles={};conflicts=[];flow_targets={t for i in instructions for t in i.get('successors',[])}
    def mark(a,b,role):
        if a>b:raise ValueError('reversed range')
        space.read(a,b-a)
        for p in range(a,b):roles.setdefault(p,set()).add(role)
    for row in instructions:
        pc=row['address'];end=pc+row['length'];inline=set()
        for a,b in row.get('data_ranges',[]):
            role='case_table' if row['opcode']==0xac else 'inline_payload'
            mark(a,b,role);inline.update(range(a,b))
        ignored=set()
        if row['opcode']==0xac and pc%2==0:ignored.add(pc+1)
        if row['opcode']==0xb3 and pc%2:ignored.add(pc+2)
        for p in ignored:mark(p,p+1,'instruction_alignment')
        for p in range(pc,end):
            if p not in inline and p not in ignored:mark(p,p+1,'pcode_encoding')
        cell=row.get('operands',{}).get('branch_cell')
        if cell is not None:mark(cell,cell+2,'backward_branch_cell')
    mark(procedure['attribute_address'],procedure['trailer_address'],'procedure_attributes')
    mark(procedure['trailer_address'],procedure['trailer_address']+2,'procedure_tag')
    start=procedure['entry_address'];end=procedure['attribute_address']
    unknown=set(range(start,end))-set(roles)
    padding=[]
    for a,b in ranges(unknown):
        # This inference cannot certify long runs, an even-address zero, a flow
        # target, or a zero with no following structurally known word boundary.
        before=next((r for r in instructions if r['address']+r['length']==a),None)
        following=roles.get(b,set())
        if (b-a==1 and a%2==1 and space.byte(a)==0 and a not in flow_targets
                and before is not None and a not in before.get('successors',[])
                and following & {'backward_branch_cell','procedure_attributes'}):
            mark(a,b,'unreferenced_zero_alignment')
            padding.append(dict(start=a,end_exclusive=b,confidence='alignment-supported inference',
                evidence='odd unreferenced zero after a non-fallthrough instruction and before known even word structure'))
    unknown=set(range(start,end))-set(roles)
    for address,labels in roles.items():
        if 'pcode_encoding'in labels and labels & {'inline_payload','case_table','backward_branch_cell','procedure_attributes','procedure_tag'}:
            conflicts.append(dict(address=address,roles=sorted(labels)))
    return roles,padding,ranges(unknown),conflicts


def cp2_opcode_lengths(cp2):
    """Read only ISA length facts from the installed independent CiderPress2 source."""
    cpu=cp2/'FileConv/Asm65/CpuDef.cs';op=cp2/'FileConv/Asm65/OpDef.cs'
    text=cpu.read_text(encoding='utf-8-sig')
    start=text.index('private static CpuDef Cpu6502 {')
    tail=text[start:];array=tail[tail.index('mOpDefs = new OpDef[] {'):]
    array=array[:array.index('};')]
    names=[]
    for line in array.splitlines()[1:]:
        m=re.search(r'OpDef\.(Op\w+)(?:\s*[,)]|\s*$)',line)
        if m:names.append(m[1])
    if len(names)!=256:raise ValueError('independent NMOS opcode table does not have 256 entries')
    definitions={}
    for m in re.finditer(r'public static readonly OpDef\s+(Op\w+)\s*=\s*new OpDef\([^)]*\)\s*\{(.*?)\};',op.read_text(encoding='utf-8-sig'),re.S):
        mode=re.search(r'AddrMode\s*=\s*AddressMode\.(\w+)',m[2])
        if mode:definitions[m[1]]=mode[1]
    one={'Unknown','Acc','Implied','StackPull','StackPush','StackRTI','StackRTL','StackRTS'}
    two={'DP','DPIndexX','DPIndexY','DPIndexXInd','DPInd','DPIndLong','DPIndIndexY','DPIndIndexYLong','Imm','ImmLongA','ImmLongXY','PCRel','StackInt','StackDPInd','StackRel','StackRelIndIndexY'}
    three={'Abs','AbsIndexX','AbsIndexY','AbsInd','AbsIndexXInd','AbsIndLong','PCRelLong','BlockMove','StackAbs','StackPCRelLong'}
    result=[]
    for name in names:
        mode=definitions[name]
        if mode in one:length=1
        elif mode in two:length=2
        elif mode in three:length=3
        else:raise ValueError('unclassified independent addressing mode '+mode)
        result.append(length)
    return result,dict(method='NMOS 6502 length facts read from independent installed CiderPress2 source',
                       cpu_definition_sha256=SHA(cpu.read_bytes()),opcode_definition_sha256=SHA(op.read_bytes()))


def baseline_regions(lengths):
    specs=[('boot-stage',0x800,'boot.txt'),('initial-4000',0x4000,'initial-4000.txt'),
           ('lc-bank2',0xd000,'lc-bank2.txt'),('runtime-bank1',0xd000,'runtime-bank1.txt'),
           ('relocated-6800',0x6800,'relocated-6800.txt'),('interpreter-ready',0xd000,'interpreter-ready.txt'),
           ('play-bootstrap-code',0x801,None)]
    result=[]
    for name,base,listing_name in specs:
        path=ROOT/'analysis/regions'/(name+'.bin')
        if not path.exists():continue
        raw=path.read_bytes();starts={};references=[];functions=[]
        listing=ROOT/'ghidra/exports'/listing_name if listing_name else None
        if listing is not None and listing.exists():
            current=None;function_part=False
            for line in listing.read_text().splitlines():
                if line=='FUNCTIONS':function_part=True;continue
                m=re.match(r'^([0-9a-f]{4})  (.*)',line)
                if m:
                    current=int(m[1],16)
                    if base<=current<base+len(raw):starts[current]=lengths[raw[current-base]]
                elif current is not None and (m:=re.match(r'^  -> ([0-9a-f]+) ([A-Z_]+)',line)):
                    if any(word in m[2] for word in ('CALL','JUMP')):references.append(dict(source=current,target=int(m[1],16),kind=m[2]))
                elif function_part and (m:=re.match(r'^([0-9a-f]{4})\s+(\S+)\s+',line)):
                    functions.append(dict(address=int(m[1],16),name=m[2]))
        else:
            # The Play bootstrap's actual REA Evidence is retained separately.
            evidence_path=ROOT/'analysis/local/rea/play-boot-evidence.json'
            if name=='play-bootstrap-code' and evidence_path.exists():
                evidence=json.loads(evidence_path.read_text())
                if evidence['subject']['digest']['sha256']!=SHA(raw):raise ValueError('Play REA evidence identity differs')
                for line in evidence['normalized_result'].splitlines():
                    m=re.match(r'^0x([0-9a-f]+): ',line)
                    if m:
                        address=int(m[1],16);starts[address]=lengths[raw[address-base]]
                functions=[dict(address=0x801,name='play_bootstrap')]
        covered=set();bad=[]
        for address,size in starts.items():
            if address+size>base+len(raw):bad.append(dict(address=address,reason='instruction crosses region boundary'))
            covered.update(range(address,min(address+size,base+len(raw))))
        missing=[f for f in functions if f['address'] not in starts]
        internal=[r for r in references if base<=r['target']<base+len(raw) and r['target'] not in starts]
        indirect=[]
        if listing is not None and listing.exists():
            indirect=[dict(address=int(m[1],16),expression=m[2]) for line in listing.read_text().splitlines()
                      if (m:=re.match(r'^([0-9a-f]{4})  (JMP \(.*\))',line))]
        alternatives=[]
        if name=='lc-bank2':
            contexts=[(0xd5d3,1,'CLC',0xd5d4,0xd5d2,2,bytes.fromhex('18 68'),'0xd5d3: CLC','0xd5d4: PLA'),
                      (0xd029,2,'LDY immediate',0xd02b,0xd028,3,bytes.fromhex('a0 01'),'0xd029: LDY','0xd02b: STY')]
            for address,size,operation,nxt,canonical,canonical_size,expected,first,second in contexts:
                if raw[address-base:address-base+len(expected)]!=expected:raise ValueError('alternate context source differs')
                proof=None
                for path in (ROOT/'analysis/local/rea').glob('*overlap*.json'):
                    try:evidence=json.loads(path.read_text())
                    except (ValueError,KeyError):continue
                    assembly=evidence.get('normalized_result','')
                    if first not in assembly or second not in assembly:continue
                    source=Path(evidence['subject']['local_path'])
                    if not source.is_file() or SHA(source.read_bytes())!=evidence['subject']['digest']['sha256']:continue
                    if source.read_bytes()!=raw[address-base:address-base+source.stat().st_size]:continue
                    proof=evidence['evidence_id'];break
                alternatives.append(dict(address=address,length=size,operation=operation,next_address=nxt,
                    canonical_context=dict(address=canonical,length=canonical_size,operation='BIT'),
                    evidence='Exact source sequence, recovered alternate entry and independent REA alternate import',
                    rea_evidence_id=proof,verified=bool(proof)))
                if proof:
                    internal=[r for r in internal if r['target']!=address]
                    missing=[r for r in missing if r['address']!=address]
        result.append(dict(name=name,base=base,length=len(raw),sha256=SHA(raw),listing=str(listing.relative_to(ROOT)) if listing and listing.exists() else None,
            recovered_entries=functions,instruction_starts=len(starts),instruction_encoding_bytes=len(covered),
            unreferenced_db_ranges=[dict(start=a,end_exclusive=b,length=b-a) for a,b in ranges(set(range(base,base+len(raw)))-covered)],
            classification_limit='Unreferenced DB is role-unknown, not certified data; includes tables/graphics/pools and possibly unrecovered code.',
            missing_entry_instructions=missing,internal_transfer_targets_not_disassembled=internal,
            external_transfers=[r for r in references if not base<=r['target']<base+len(raw)],
            indirect_transfers=indirect,alternate_instruction_contexts=alternatives,invalid_spans=bad))
    return result


def audit(cp2):
    graph=json.loads((ROOT/'analysis/pcode-callgraph.json').read_text())
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives']
    play=json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())['segments']
    handoff=json.loads((ROOT/'analysis/boot-handoff.json').read_text())
    result=dict(method='Independent per-byte disassembly audit; DB means explicit unreferenced/unknown-role bytes, not proved data',
                procedure_inventories=[],native_pending=True,blocking_findings=[],limitations=[
                    'Structural instruction coverage is distinct from complete gameplay semantics or runtime reachability.',
                    'No failed Play track-34 byte is supplied as data.',
                    'Zero-alignment classification is a narrow structural inference, not an entropy-based data guess.'])
    total=Counter()
    native_path=ROOT/'analysis/native-archive-disassembly.json'
    native_report=json.loads(native_path.read_text()) if native_path.exists() else None
    native_segments={(a['archive'],a['slot']):a for a in native_report['archive_segments']} if native_report else {}
    native_blockers=[]
    for arc in graph['archives']:
        record=next(s for a in inventory if a['name']==arc['name'] for s in a['segments'] if s['slot']==arc['slot']) if arc['side']=='utility' else next(s for s in play if s['slot']==arc['slot'])
        raw=(ROOT/record['path']).read_bytes()
        if SHA(raw)!=arc['source_sha256']:raise ValueError('archive source identity differs')
        base=arc['load_base'];regions=[(base,raw)]
        if arc['name']=='SYSTEM.PASCAL' and arc['slot']==0:
            helper=(ROOT/'analysis/regions/initial-helper.bin').read_bytes()
            if SHA(helper)!=handoff['helper']['sha256']:raise ValueError('helper identity differs')
            regions.append((handoff['helper']['load_address'],helper))
        space=Space(regions);name=f"{arc['name']}-slot-{arc['slot']:02}"+('-play' if arc['side']=='play' else '')
        detailed=json.loads((ROOT/'analysis/local/pcode'/(name+'.json')).read_text())
        summaries=[];all_roles={}
        for decoded in detailed:
            p=decoded['procedure'];entry=p['entry_address'];attr=p['attribute_address'];trailer=p['trailer_address']
            if p.get('kind')=='native-6502':
                total['native_procedures']+=1
                source=native_segments.get((arc['name'],arc['slot']))
                if source is None:
                    summaries.append(dict(number=p['number'],kind='native-6502',entry=entry,body_end=attr,status='pending native archive audit'))
                    native_blockers.append(dict(archive=arc['name'],slot=arc['slot'],procedure=p['number'],reason='missing native report'))
                    continue
                if source['source_sha256']!=SHA(raw):raise ValueError('native report archive identity differs')
                metadata=next(r for r in source['procedures'] if r['number']==p['number'])
                listing=next(r for r in source['ghidra']['procedures'] if r['number']==p['number'])
                native_roles={};conflicts=[]
                def mark_native(a,b,role):
                    space.read(a,b-a)
                    for address in range(a,b):native_roles.setdefault(address,set()).add(role)
                for row in listing['instruction_spans']:
                    mark_native(base+row['offset'],base+row['offset']+row['length'],'native_encoding')
                for row in listing['inline_data']:
                    mark_native(base+row['start_offset'],base+row['end_exclusive'],'native_inline_data')
                for row in metadata['relocation_groups']:
                    mark_native(base+row['start_offset'],base+row['end_exclusive'],'native_relocation')
                mark_native(trailer-2,trailer,'native_entry_pointer')
                mark_native(trailer,trailer+2,'procedure_tag')
                mark_native(p['directory_cell'],p['directory_cell']+2,'procedure_directory')
                for address,labels in native_roles.items():
                    if 'native_encoding'in labels and labels & {'native_inline_data','native_relocation','native_entry_pointer','procedure_tag'}:
                        conflicts.append(dict(address=address,roles=sorted(labels)))
                    all_roles.setdefault(address,set()).update(labels)
                unknown=ranges(set(range(entry,trailer+2))-set(native_roles))
                summary=dict(number=p['number'],kind='native-6502',entry=entry,body_end=base+metadata['body_end_exclusive'],
                    instruction_count=len(listing['instruction_spans']),byte_roles=dict(Counter(role for labels in native_roles.values() for role in labels)),
                    unclassified_native_envelope=[dict(start=a,end_exclusive=b,length=b-a) for a,b in unknown],
                    role_conflicts=conflicts,ghidra_unclassified_ranges=listing['unclassified_ranges'],
                    native_report_complete=metadata.get('native_complete',False))
                summaries.append(summary);total['native_instructions']+=len(listing['instruction_spans'])
                total['unclassified_native_envelope_bytes']+=sum(b-a for a,b in unknown)
                if unknown or conflicts or listing['unclassified_ranges'] or not metadata.get('native_complete',False):
                    native_blockers.append(dict(archive=arc['name'],slot=arc['slot'],procedure=p['number'],reason='native code/data coverage incomplete',details=summary))
                continue
            roles,padding,unknown,conflicts=classify_pcode(space,p,decoded['instructions'])
            for address,labels in roles.items():all_roles.setdefault(address,set()).update(labels)
            for address in range(p['directory_cell'],p['directory_cell']+2):all_roles.setdefault(address,set()).add('procedure_directory')
            boundaries=[b for b in decoded['boundaries'] if b['reason'] not in ('generated reset stub',)]
            summary=dict(number=p['number'],kind='pcode',entry=entry,attribute_address=attr,
                         instruction_count=len(decoded['instructions']),byte_roles=dict(Counter(role for labels in roles.values() for role in labels)),
                         unclassified_code_envelope=[dict(start=a,end_exclusive=b,length=b-a) for a,b in unknown],
                         inferred_alignment=padding,role_conflicts=conflicts,decoder_boundaries=boundaries)
            summaries.append(summary);total['pcode_procedures']+=1;total['pcode_instructions']+=len(decoded['instructions'])
            total['unclassified_pcode_envelope_bytes']+=sum(b-a for a,b in unknown)
            total['inferred_zero_alignment_bytes']+=len(padding)
            if unknown or conflicts or boundaries:result['blocking_findings'].append(dict(archive=arc['name'],side=arc['side'],slot=arc['slot'],procedure=p['number'],
                code_envelope_ranges=summary['unclassified_code_envelope'],role_conflicts=conflicts,boundaries=boundaries))
        all_roles.setdefault(base+len(raw)-2,set()).add('segment_tag')
        all_roles.setdefault(base+len(raw)-1,set()).add('procedure_count')
        result['procedure_inventories'].append(dict(archive=arc['name'],side=arc['side'],slot=arc['slot'],segment_number=arc['segment_number'],source_sha256=arc['source_sha256'],procedures=summaries,
            payload_regions=[dict(base=b,length=len(data),sha256=SHA(data),unreferenced_db_ranges=[dict(start=a,end_exclusive=z,length=z-a) for a,z in ranges(set(range(b,b+len(data)))-set(all_roles))]) for b,data in regions]))
    lengths,reference=cp2_opcode_lengths(cp2);result['native_length_reference']=reference
    result['recovered_native_regions']=baseline_regions(lengths)
    result['native_pending']=bool(native_blockers) or native_report is None
    result['native_blocking_findings']=native_blockers
    if native_report:result['native_archive_report_sha256']=SHA(native_path.read_bytes())
    stage_path=ROOT/'analysis/native-stage-disassembly.json'
    if stage_path.exists():
        staged=json.loads(stage_path.read_text());result['native_stage_report_sha256']=SHA(stage_path.read_bytes())
        result['staged_classification_summary']=[dict(program=v['program'],base=v['base'],length=v['length'],source_sha256=v['source_sha256'],instruction_count=len(v['instruction_spans']),classification_bytes=dict(Counter({kind:sum(r['end_exclusive']-r['start'] for r in v['classification_ranges'] if r['kind']==kind) for kind in ('decoded_instruction','defined_data','unreferenced_DB_untyped')})),alternate_instructions=v['alternate_instructions']) for v in staged['views']]
        stage_blockers=[]
        if len(staged['views'])!=7:stage_blockers.append('Expected seven recovered native views')
        for view in staged['views']:
            raw=(ROOT/view['source_path']).read_bytes()
            if SHA(raw)!=view['source_sha256'] or len(raw)!=view['length']:
                stage_blockers.append(dict(program=view['program'],reason='source identity differs'))
                continue
            lo=view['base'];hi=lo+len(raw);covered=set();code=set();invalid=False
            for row in view['classification_ranges']:
                a,b=row['start'],row['end_exclusive']
                if a<lo or b>hi or a>=b or covered.intersection(range(a,b)):invalid=True
                covered.update(range(a,b))
                if row['kind']=='decoded_instruction':code.update(range(a,b))
                elif row['kind'] not in ('defined_data','unreferenced_DB_untyped'):invalid=True
            spans=set();starts=set()
            for row in view['instruction_spans']:
                a=row['address'];b=a+row['length'];starts.add(a)
                if row['length']!=lengths[raw[a-lo]] or a<lo or b>hi or spans.intersection(range(a,b)):invalid=True
                spans.update(range(a,b))
            if covered!=set(range(lo,hi)) or spans!=code:invalid=True
            alternate_starts={r['address'] for r in view['alternate_instructions']}
            if invalid or any(seed not in starts|alternate_starts for seed in view['seeds']):
                stage_blockers.append(dict(program=view['program'],reason='partition, encoding length, or entry coverage failed'))
        result['native_stage_blocking_findings']=stage_blockers
    from native_probe import handler_probe
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    cpu,_=handler_probe(snapshot,b'\xd6',stop=0)
    expected=bytes.fromhex('ad 8a c0 6c fc ff')
    if bytes(cpu.memory[:6])!=expected:raise ValueError('generated reset stub differs')
    result['generated_native_contexts']=[dict(name='primary_D6_reset_stub',source_entry=0xd6e4,generated_base=0,length=6,
        generated_sha256=SHA(expected),instruction_spans=[dict(address=0,length=3,operation='read_softswitch',target=0xc08a),
        dict(address=3,length=3,operation='indirect_reset_jump',pointer_address=0xfffc)],
        method='Exact native constant writes through existing bounded handler probe; stop before executing MMIO/ROM')]
    result['totals']=dict(total)
    result['archive_pcode_byte_complete']=not result['blocking_findings']
    staged_ready=stage_path.exists() and not result.get('native_stage_blocking_findings',[])
    baseline_blockers=[dict(name=r['name'],missing_entries=r['missing_entry_instructions'],missing_internal_targets=r['internal_transfer_targets_not_disassembled'],invalid_spans=r['invalid_spans'])
        for r in result['recovered_native_regions'] if r['missing_entry_instructions'] or r['internal_transfer_targets_not_disassembled'] or r['invalid_spans']
        or not r['instruction_starts'] or any(not a['verified'] for a in r['alternate_instruction_contexts'])]
    result['baseline_blocking_findings']=baseline_blockers
    result['full_disassembly_accepted']=result['archive_pcode_byte_complete'] and not result['native_pending'] and not baseline_blockers and staged_ready
    result['acceptance_scope']='All format-defined archive procedures and recovered boot/runtime executable paths. Unknown-role unreferenced DB is explicit; gameplay semantics/undiscovered code are not asserted complete.'
    result['helper_scope']=dict(path='analysis/regions/initial-helper.bin',source_archive='SYSTEM.PASCAL slot15, machine_type0',
                               ownership='Already referenced and decoded as segment0 procedure38; not a missing additional native procedure',
                               length=handoff['helper']['length'],sha256=handoff['helper']['sha256'])
    (ROOT/'analysis/disassembly-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(totals=result['totals'],blocking_procedures=len(result['blocking_findings']),native_regions=len(result['recovered_native_regions']),full_disassembly_accepted=result['full_disassembly_accepted'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cp2-source',type=Path,default=Path('/Users/ay5/Projects/CiderPress2'));a=p.parse_args();audit(a.cp2_source)
