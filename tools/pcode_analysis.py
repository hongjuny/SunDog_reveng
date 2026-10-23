#!/usr/bin/env python3
"""Bounded static Apple II p-code analysis from this repository's native evidence.

Not a VM. Never assumes ST opcodes, guesses across unsupported services, or
exports listings/game bytes into versioned reports.
"""
import hashlib
import json
from collections import Counter, deque
from pathlib import Path
from boot_handoff import procedure_directory
ROOT=Path(__file__).resolve().parents[1]

class DecodeBoundary(ValueError):pass
class Space:
    def __init__(self,regions):self.regions=regions
    def read(self,address,count):
        if count<0:raise DecodeBoundary('negative read')
        for base,raw in self.regions:
            p=address-base
            if p>=0 and p+count<=len(raw):return raw[p:p+count]
        raise DecodeBoundary(f'bytes outside known regions at {address:04x}+{count}')
    def byte(self,p):return self.read(p,1)[0]
    def word(self,p):return int.from_bytes(self.read(p,2),'little')
    def index(self,p):
        first=self.byte(p)
        return (first,1) if first<128 else (((first&127)<<8)|self.byte(p+1),2)

def decode_one(space,pc,branch_base,catalogue,services=None):
    services=services or {}
    op=space.byte(pc);row=dict(address=pc,opcode=op,length=1,operands={},successors=[],calls=[],data_ranges=[])
    if op<128:row['operation']='push_short_constant';row['operands']['value']=op
    else:
        evidence=catalogue[op];row['operation']=evidence['rule'];row['native_handler']=evidence['handler']
        row['native_evidence_ids']=evidence.get('rea_static_evidence_ids',[])
        if evidence['rule']=='shared_error_111':
            row.update(terminal_transfer='shared_error_111');return row
        if op==0xd6:row.update(terminal_transfer='generated_reset_stub',generated_target=0);return row
        if op==0x9e:
            selector=space.byte(pc+1);row['length']=2;row['operands']['selector']=selector
            effective=selector&127
            if effective not in services:

                row['boundary']='secondary service operand/continuation not verified';return row
            service=services[effective]
            row['operands']['effective_selector']=effective
            row['length']=service if isinstance(service,int) else service['pcode_length']
            if isinstance(service,dict):
                row['service_name']=service['name'];row['service_evidence_id']=service.get('rea_evidence_id')
                flow=service.get('flow','fallthrough')
                if flow!='fallthrough':
                    row['terminal_transfer']=flow
                    if flow=='nonlocal_exit':row['target_expression']='(target_procedure_trailer-4)-word(target_procedure_trailer-4); may unwind caller frames'
                    return row
            row['service_continuation']='conditional on normal service return'
        elif op in (0xa1,0xb9):
            b=space.byte(pc+1);row['length']=2
            if b<128:target=(pc+2+b)&65535
            else:
                cell=(branch_base+b-256)&65535;target=(cell-space.word(cell))&65535
                row['operands']['branch_cell']=cell
            row['operands']['branch_encoding']=b
            row['successors']=[target]+([pc+2] if op==0xa1 else [])
            return row
        elif op in (0xa2,0xa3,0xa4,0xa5,0xa8,0xa9,0xab,0xc6,0xca,0xcc,0xd5):
            value,width=space.index(pc+1);row['length']=1+width;row['operands']['index']=value
        elif op in (0x9d,0xa7,0xb2,0xb6,0xb8,0xd1):
            row['operands']['selector_or_depth']=space.byte(pc+1)
            value,width=space.index(pc+2);row['length']=2+width;row['operands']['index']=value
        elif op in (0xa6,0xd0):
            n=space.byte(pc+1);payload=space.read(pc+2,n);row['length']=n+2
            row['operands'].update(payload_length=n,payload_sha256=hashlib.sha256(payload).hexdigest())
            row['data_ranges']=[(pc+2,pc+2+n)] if n else []
        elif op==0xc7:row['length']=3;row['operands']['word']=space.word(pc+1)
        elif op in (0xaa,0xbc,0xbd):row['length']=2;row['operands']['count']=space.byte(pc+1)
        elif op==0xc0:
            row['length']=3;row['operands'].update(elements_per_word=space.byte(pc+1),bits=space.byte(pc+2))
        elif op in (0xaf,0xb0,0xb1,0xb4,0xb5,0xb7):
            kind=space.byte(pc+1);row['length']=2;row['operands']['kind']=kind
            if kind not in (2,4,6,8):
                n,width=space.index(pc+2);row['length']+=width;row['operands']['comparison_count']=n
        elif op==0xb3:
            n=space.byte(pc+1)
            if not 1<=n<=126:raise DecodeBoundary('inline-word raw u8-wrap count; legal program encoding unestablished')
            row['length']=2+2*n+(pc&1);space.read(pc,row['length'])
            row['operands']['word_count']=n;row['data_ranges']=[(pc+2+(pc&1),pc+row['length'])]
        elif op==0xac:
            aligned=pc|1
            signed=lambda n:n if n<32768 else n-65536
            lower=signed(space.word(aligned+1));upper=signed(space.word(aligned+3))
            if upper<lower or upper-lower>4096:raise DecodeBoundary('unbounded/invalid case table')
            first=aligned+7;end=first+2*(upper-lower+1);space.read(first,end-first)
            row['length']=aligned+5-pc
            row['operands'].update(lower=lower,upper=upper)
            row['data_ranges']=[(first,end)]
            row['successors']=[aligned+5]+[cell-space.word(cell) for cell in range(first,end,2)]
            return row
        elif op in (0xad,0xc1):
            row['length']=2;row['operands']['result_words']=space.byte(pc+1);row['return']=True;return row
        elif op in (0xae,0xc2,0xce,0xcf):
            row['length']=2;proc=space.byte(pc+1);row['operands']['procedure']=proc
            row['calls']=[dict(kind='current-segment',procedure=proc)]
        elif op==0xcd:
            row['length']=3;segment=space.byte(pc+1);proc=space.byte(pc+2)
            row['operands'].update(segment_operand=segment,procedure=proc)
            row['calls']=[dict(kind='external-segment-operand',segment_operand=segment,procedure=proc)]
        elif 0xd8<=op<=0xe7:row['operands']['index']=op-0xd8+1
        elif 0xe8<=op<=0xf7:row['operands']['index']=op-0xe8+1
        elif 0xf8<=op<=0xff:row['operands']['word_offset']=op-0xf8
        elif evidence.get('operands')!='none':
            raise DecodeBoundary('operand shape not explicitly supported: '+str(evidence.get('operands')))
    space.read(pc,row['length'])
    row['successors']=[pc+row['length']]
    return row

def walk(space,procedure,catalogue,services=None):
    entry=procedure['entry_address'];end=procedure['attribute_address'];pending=deque([entry]+([procedure['exit_address']] if 'exit_address' in procedure else []));rows={};stops=[]
    while pending:
        pc=pending.popleft()
        if pc in rows:continue
        if not entry<=pc<end:
            stops.append(dict(address=pc,reason='target outside this procedure code envelope'));continue
        overlap=next((p for p,r in rows.items() if p<pc<p+r['length'] or any(a<=pc<b for a,b in r['data_ranges'])),None)
        if overlap is not None:
            stops.append(dict(address=pc,reason='target overlaps decoded instruction/data',owner=overlap));continue
        try:
            row=decode_one(space,pc,procedure['trailer_address'],catalogue,services)
            if pc+row['length']>end:raise DecodeBoundary('instruction crosses procedure metadata')
            # Check overlap in both directions; never silently bless contradictory layouts.
            if any(pc<p<pc+row['length'] or any(a<=p<b for a,b in row['data_ranges']) for p in rows):
                raise DecodeBoundary('decoded span conflicts with an existing instruction')
            rows[pc]=row
            if 'boundary' in row:stops.append(dict(address=pc,reason=row['boundary'],selector=row['operands'].get('selector')))
            pending.extend(row['successors'])
        except DecodeBoundary as error:stops.append(dict(address=pc,reason=str(error)))
    # Some structured branches leave an unreachable unconditional jump immediately
    # after EXIT/return. Decode it only when both neighbouring instruction boundaries
    # and its destination independently agree; do not force arbitrary gaps to code.
    occupied=set()
    predecessors={}
    for address,row in rows.items():
        occupied.update(range(address,address+row['length']))
        for a,b in row['data_ranges']:occupied.update(range(a,b))
        cell=row['operands'].get('branch_cell')
        if cell is not None:occupied.update(range(cell,cell+2))
        predecessors[address+row['length']]=row
    for pc in range(entry,end-1):
        if pc in occupied or pc+1 in occupied or pc+2 not in rows:continue
        previous=predecessors.get(pc)
        if previous is None or pc in previous['successors'] or space.byte(pc)!=0xb9:continue
        candidate=decode_one(space,pc,procedure['trailer_address'],catalogue,services)
        if candidate['length']==2 and candidate['successors'][0] in rows:
            candidate.update(discovery='unreferenced_compiled_jump',reachable_from_entry=False,
                             classification_proof='Adjacent decoded boundaries, no predecessor fallthrough, encoded jump target is an existing instruction start')
            rows[pc]=candidate;occupied.update((pc,pc+1))
    return dict(procedure=procedure,instructions=[rows[p] for p in sorted(rows)],boundaries=stops,
                complete_within_static_model=not stops)

def mixed_directory(raw):
    count=raw[-1]
    if not count or 2+count*2>len(raw):raise ValueError('invalid procedure directory')
    result=[]
    for number in range(1,count+1):
        cell=len(raw)-2-number*2
        tag=cell-int.from_bytes(raw[cell:cell+2],'little')
        if not 2<=tag<len(raw)-2-count*2:raise ValueError('procedure tag outside payload')
        marker=raw[tag]
        if marker not in (0,number):raise ValueError('procedure ordinal mismatch')
        entry=tag-2-int.from_bytes(raw[tag-2:tag],'little')
        end=tag-8 if marker else tag-2
        if not 0<=entry<end:raise ValueError('procedure entry outside code envelope')
        result.append(dict(number=number,directory_cell=cell,trailer_address=tag,attribute_address=end,
                           entry_address=entry,kind='native-6502' if marker==0 else 'pcode',
                           metadata_second_byte=raw[tag+1],
                           lexical_level=None if marker==0 else raw[tag+1] if raw[tag+1]<128 else raw[tag+1]-256))
    return result

def analyse():
    catalogue=json.loads((ROOT/'analysis/opcode-evidence.json').read_text())
    opcodes={r['opcode']:r for r in catalogue['primary']}
    verified_services={}
    service_file=ROOT/'analysis/secondary-services.json'
    if service_file.exists():
        service_report=json.loads(service_file.read_text())
        if service_report['snapshot_sha256']!=catalogue['snapshot_sha256']:raise ValueError('service catalogue snapshot differs')
        for row in service_report['services']:
            if row['pcode_length']!=2 or not row['probe_cases'] or not row['rea_evidence_id']:raise ValueError('service lacks bounded evidence')
            verified_services[row['selector']]=row
    archives=json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives']
    out=ROOT/'analysis/local/pcode';out.mkdir(parents=True,exist_ok=True)
    report=dict(method='Static recursive p-code decoding using Apple II native-backed operand rules; no runtime execution or subsystem-name guessing',
                limitations=['External segment operands are not globally resolved module names.',
                             'Unverified 9E services stop a path; calls/services are conditional on normal return.',
                             'Relative archive analysis assumes an even load address for aligned inline data.',
                             'SYSTEM.STARTUP uses structurally validated Play payloads; runtime side selection remains open.'],archives=[])
    if service_file.exists():report['secondary_service_catalogue_sha256']=hashlib.sha256(service_file.read_bytes()).hexdigest()
    selected=[(a,s) for a in archives if a['name'] in ('SUNDOG.LIBRARY','SYSTEM.PASCAL','SYSTEM.LIBRARY') for s in a['segments'] if s.get('machine_type') in (2,7) and s['status']=='stored']
    play_startup=ROOT/'analysis/play-startup-inventory.json'
    if play_startup.exists():
        startup=json.loads(play_startup.read_text())
        selected.extend((dict(name='SYSTEM.STARTUP'),s) for s in startup['segments'])
    handoff=json.loads((ROOT/'analysis/boot-handoff.json').read_text())
    format_file=ROOT/'analysis/service-instruction-formats.json'
    if format_file.exists():
        formats=json.loads(format_file.read_text())
        if formats['snapshot_sha256']!=catalogue['snapshot_sha256']:raise ValueError('service instruction formats snapshot differs')
        for row in formats['services']:
            if not row['format_verified'] or row['pcode_length']!=2:raise ValueError('unverified instruction format')
            verified_services[row['selector']]=row
        report['service_format_catalogue_sha256']=hashlib.sha256(format_file.read_bytes()).hexdigest()
    native_rows={}
    native_file=ROOT/'analysis/native-archive-disassembly.json'
    if native_file.exists():
        native_report=json.loads(native_file.read_text())
        for archive_view in native_report['archive_segments']:
            for proc in archive_view['procedures']:
                native_rows[tuple(proc['key'])]=dict(proc,private_listing=archive_view['private_listing'],
                                                   source_sha256=archive_view['source_sha256'],view=archive_view['declared_view'])
        report['native_archive_catalogue_sha256']=hashlib.sha256(native_file.read_bytes()).hexdigest()
    report['method']='Static recursive p-code disassembly from entry and explicit EXIT-IC metadata; native-backed formats, terminal/dynamic transfers kept explicit'
    for archive,segment in selected:
        raw=(ROOT/segment['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=segment['sha256']:raise ValueError('payload hash mismatch')
        if archive['name']=='SYSTEM.PASCAL' and segment['slot']==0:
            base=handoff['segment0']['load_address'];helper=(ROOT/'analysis/regions/initial-helper.bin').read_bytes()
            space=Space([(base,raw),(handoff['helper']['load_address'],helper)])
            procedures=handoff['procedures'];services=dict(verified_services)
            if 0x26 not in services:services[0x26]=2
        else:
            base=0;space=Space([(0,raw)]);procedures=mixed_directory(raw);services=dict(verified_services)
        procedures=[dict(p) for p in procedures]
        for p in procedures:
            if p.get('kind')=='native-6502':continue
            cell=p['trailer_address']-4;target=(cell-space.word(cell))&65535
            if not p['entry_address']<=target<p['attribute_address']:raise ValueError('EXIT-IC outside known procedure code')
            p.update(exit_ic_cell=cell,exit_address=target)
        results=[]
        for p in procedures:
            if p.get('kind')!='native-6502':results.append(walk(space,p,opcodes,services));continue
            native=native_rows.get((archive['name'],segment['slot'],p['number']))
            if native and (native['source_sha256']!=segment['sha256'] or native['entry_offset']!=p['entry_address']):raise ValueError('native disassembly/source mismatch')
            complete=bool(native and native['native_complete'] and native['unresolved_decoding_count']==0)
            results.append(dict(procedure=p,instructions=[],native_disassembly=native,
                                boundaries=[] if complete else [dict(address=p['entry_address'],reason='native 6502 disassembly incomplete')],
                                complete_within_static_model=complete))
        name=f"{archive['name']}-slot-{segment['slot']:02}"+("-play" if segment.get('side')=='play' else '')
        (out/(name+'.json')).write_text(json.dumps(results,indent=2)+'\n')
        lines=[];summaries=[];edges=[]
        for result in results:
            p=result['procedure'];number=p['number'];lines.append(f'\nprocedure {number}: entry={p["entry_address"]:04X} trailer={p["trailer_address"]:04X}')
            if result.get('native_disassembly'):lines.append('NATIVE LISTING '+result['native_disassembly']['private_listing'])
            for row in result['instructions']:
                raw_instruction=space.read(row['address'],row['length'])
                lines.append(f'{row["address"]:04X}  {raw_instruction.hex(" "):30} {row["operation"]} {row["operands"]}')
                for call in row['calls']:
                    offset=row['address']-base;source=segment['sectors'][offset//256] if 0<=offset<len(raw) else None
                    edges.append(dict(caller_procedure=number,call_address=row['address'],source=(dict(side=segment.get('side','utility'),**source,byte_in_sector=offset%256) if source else dict(region='initial-helper',address=row['address'])),**call))
            lines.extend('BOUNDARY '+str(b) for b in result['boundaries'])
            summaries.append(dict(number=number,kind=p.get('kind','pcode'),entry=p['entry_address'],trailer=p['trailer_address'],
                                  decoded_instructions=(result['native_disassembly']['instruction_count'] if result.get('native_disassembly') else len(result['instructions'])),
                                  native_listing=result['native_disassembly']['private_listing'] if result.get('native_disassembly') else None,boundaries=result['boundaries'],
                                  complete_within_static_model=result['complete_within_static_model'],
                                  terminal_transfers=[dict(address=i['address'],kind=i['terminal_transfer']) for i in result['instructions'] if 'terminal_transfer' in i]))
        (out/(name+'.txt')).write_text('\n'.join(lines)+'\n')
        report['archives'].append(dict(name=archive['name'],side=segment.get('side','utility'),slot=segment['slot'],segment_number=segment['segment_number'],source_sha256=segment['sha256'],
            load_base=base,address_kind='verified initial loaded address' if base else 'segment-relative; even-base condition',
            procedures=summaries,calls=edges,counts=dict(procedures=len(results),instructions=sum(len(r['instructions']) for r in results),
            complete_procedures=sum(r['complete_within_static_model'] for r in results),calls=len(edges),
            native_instructions=sum(r['native_disassembly']['instruction_count'] for r in results if r.get('native_disassembly')),
            boundary_reasons=dict(Counter(b['reason'] for r in results for b in r['boundaries'])))))
    (ROOT/'analysis/pcode-callgraph.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(name=a['name'],slot=a['slot'],**a['counts']) for a in report['archives']],indent=2))
if __name__=='__main__':analyse()
