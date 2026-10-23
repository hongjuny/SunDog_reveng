#!/usr/bin/env python3
"""Recover 6502 relocation tables and run bounded Ghidra archive disassembly.

Original payloads are immutable. Normalized views use declared synthetic bases;
all assembly and game bytes remain private. Undecoded body bytes stay unresolved
until supported code/data evidence is supplied.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]
BASE=0x4000
GLOBAL=0x9000

def sha(data):return hashlib.sha256(data).hexdigest()
def u16(data,offset):
    if offset<0 or offset+2>len(data):raise ValueError('word outside source')
    return int.from_bytes(data[offset:offset+2],'little')

def relocations(data,procedure):
    """Loader E5C7..E630 calls E3FD four times, scanning counts/cells backwards."""
    entry=procedure['entry_address'];tag=procedure['trailer_address'];count_cell=tag-4;groups=[]
    for kind in ('data_or_global_base','segment_base','procedure_entry','kernel_D1AD_word'):
        count=u16(data,count_cell)
        if count>len(data)//2:raise ValueError('unbounded relocation count')
        cells=[count_cell-2-2*i for i in range(count)]
        targets=[cell-u16(data,cell) for cell in cells]
        groups.append(dict(kind=kind,count_cell=count_cell,count=count,entries=[dict(cell=c,target=t) for c,t in zip(cells,targets)]))
        count_cell-=2*(count+1)
    body_end=count_cell+2
    if not entry<body_end<=tag-2:raise ValueError('relocation tables overlap entry or trailer')
    all_targets=[e['target'] for g in groups for e in g['entries']]
    if any(not entry<=t<body_end-1 for t in all_targets):raise ValueError('relocation target outside native body')
    if any(b-a<2 for a,b in zip(sorted(all_targets),sorted(all_targets)[1:])):raise ValueError('overlapping relocation target words')
    return dict(body_start=entry,body_end_exclusive=body_end,relocation_start=body_end,relocation_end_exclusive=tag-2,groups=groups)

def apply_relocations(data,procedures,segment_base=BASE,global_base=GLOBAL,kernel_base=0xd1af):
    result=bytearray(data)
    for procedure in procedures:
        if procedure['kind']!='native-6502':continue
        info=relocations(data,procedure)
        values=(global_base,segment_base,segment_base+procedure['entry_address'],kernel_base)
        for group,base in zip(info['groups'],values):
            for entry in group['entries']:
                p=entry['target'];result[p:p+2]=((u16(data,p)+base)&65535).to_bytes(2,'little')
    return bytes(result)

def inline_data(data,segment,procedure,info):
    """Explicit table/state evidence; unrecognized gaps remain unclassified."""
    ranges=[]
    def add(a,b,kind,proof):
        if not info['body_start']<=a<b<=info['body_end_exclusive']:raise ValueError('data outside native body')
        ranges.append(dict(start_offset=a,end_exclusive=b,kind=kind,evidence=proof))
    n=procedure['number']
    if (segment,n)==(22,2):
        add(0xcd2,0xcd4,'relocated_code_pointer','Procedure-relative relocation at CD2; value resolves to CDD input hook. Installation copies pointer into D004.')
        add(0xcd4,0xcd8,'pending_input_bytes','Indexed OR/read/write at C89/C99/CA0 with selector&3; hook ORs first two channels.')
        add(0xcd8,0xcdc,'previous_input_bytes','Indexed edge-state reads/writes at CA9/CB5 with selector&3.')
        add(0xcdc,0xcdd,'installed_flag','Absolute read/write at procedure entry and hook-install prefix.')
    if (segment,n)==(22,4):add(0xd8f,0xd91,'mutable_generator_state','Absolute INC/read/write uses both bytes; immediately follows terminating RTS.')
    if (segment,n)==(22,7):
        arrays=[bytes((1<<i)-1 for i in range(7)),bytes((~((1<<i)-1))&255 for i in range(7)),bytes((0x7f<<(i+1))&0x7f for i in range(7)),bytes((~((0x7f<<(i+1))&0x7f))&255 for i in range(7))]
        for i,expected in enumerate(arrays):
            a=0x132a+7*i
            if data[a:a+7]!=expected:raise ValueError('pixel mask table changed')
            add(a,a+7,'pixel_mask_table','Four indexed LDA/AND bases 132A/1331/1338/133F; exact seven-position HGR mask formulas.')
    if (segment,n)==(22,8):
        if data[0x10f0:0x10f7]!=bytes(1<<i for i in range(7)):raise ValueError('single-pixel masks changed')
        add(0x10f0,0x10f7,'single_pixel_masks','Indexed LDA/EOR base 10F0; exact 1<<bit table for seven HGR positions.')
        add(0x10f7,0x10fb,'pixel_operation_descriptor','Indexed base 10F7; X is masked with 3 at 1060.')
        add(0x10fb,0x10ff,'pixel_operation_descriptor','Indexed base 10FB; X is masked with 3 at 1060.')
    if (segment,n)==(22,55):
        add(0x163e,0x164a,'even_odd_colour_masks','Indexed reads at 125C/13CA; table base 163E, companion base 164A, each twelve entries.')
        add(0x164a,0x1656,'even_odd_colour_masks','Indexed reads at 1257/13C4; table ends at referenced coordinate table base 1656.')
        expected=bytes(((i//7)*8+i%7)&255 for i in range(266))
        if data[0x1656:0x1760]!=expected:raise ValueError('packed horizontal coordinate table changed')
        add(0x1656,0x1760,'packed_x_coordinate_lookup','Native helper 1612 indexed read; all 266 stored entries satisfy (8*(x//7)+x%7)&FF. Final ten are table continuation, not asserted reachable by X alone.')
    if (segment,n)==(23,2):
        if data[0x6b:0x6f]!=bytes(3<<(2*i) for i in range(4)):raise ValueError('two-bit masks changed')
        add(0x6b,0x6f,'unreferenced_two_bit_masks','After RTS at 006A and before referenced transition table; exact 3<<(2*i) constants, not legal entry-flow instructions.')
        add(0x6f,0xa7,'two_bit_state_transition_lookup','Indexed read at 004F; four-column state transition matrix, values0..13 and current-state*4+symbol index.')
    if (segment,n)==(24,3):
        for a in (0xf23,0xf2f,0xf3b):add(a,a+12,'bounded_shape_parameter_lookup','Three indexed reads at 0EA7/0EAF/0EB4; Y loop exits at12 via CPY#0C.')
    if (segment,n)==(24,4):add(0xfdd,0xffe,'bounded_waveform_lookup','Indexed LDA at0FA1; AND#3F, compare33 and mirror transform constrain X to0..32.')
    if (segment,n)==(26,18):
        if data[0xa94:0xbac]!=bytes(i//7 for i in range(280)):raise ValueError('horizontal quotient table changed')
        add(0xa94,0xbac,'x_div_7_lookup','Both page-indexed reads at0A8C/0A90; complete280 entries equal floor(x/7), followed by separately reached code at0BAC.')
    covered={i for r in ranges for i in range(r['start_offset'],r['end_exclusive'])}
    end=info['body_end_exclusive']
    # Word-aligning byte after a terminator, or after a declared data block. Ghidra validates the predecessor below.
    if end-1 not in covered and data[end-1]==0:
        if end-2 in covered:add(end-1,end,'word_alignment_after_data','Single zero aligns the explicitly bounded inline table/state data to next relocation word.')
        elif data[end-2]==0x60:add(end-1,end,'word_alignment_after_RTS','Zero byte after one-byte RTS; Ghidra must confirm RTS instruction and no control-flow edge to padding.')
        elif data[end-4]==0x4c:add(end-1,end,'word_alignment_after_JMP','Zero byte after absolute JMP; Ghidra confirms the terminating instruction.')
    return ranges

def prepare():
    inv=json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives']
    output=ROOT/'analysis/local/native-complete';output.mkdir(parents=True,exist_ok=True)
    specs=[]
    for archive in inv:
        if archive['name']!='SYSTEM.LIBRARY':continue
        for segment in archive['segments']:
            if segment.get('machine_type')!=7 or segment['status']!='stored':continue
            data=(ROOT/segment['path']).read_bytes()
            if sha(data)!=segment['sha256']:raise ValueError('native source identity mismatch')
            procedures=mixed_directory(data);native=[p for p in procedures if p['kind']=='native-6502']
            records=[]
            for p in native:
                info=relocations(data,p);sector=segment['sectors'][p['entry_address']//256]
                records.append(dict(**p,**info,inline_data=inline_data(data,segment['segment_number'],p,info),extra_code_entries=([0xcdd] if segment['segment_number']==22 and p['number']==2 else []),source=dict(side='utility',**sector,byte_in_sector=p['entry_address']%256)))
            name=f"library-{segment['segment_number']:02}-normalized";path=output/(name+'.bin')
            normalized=apply_relocations(data,procedures);path.write_bytes(normalized)
            spec=dict(segment_number=segment['segment_number'],slot=segment['slot'],path=str(path.relative_to(ROOT)),
                source_path=segment['path'],source_sha256=sha(data),normalized_sha256=sha(normalized),length=len(data),
                declared_view=dict(segment_base=BASE,global_data_base=GLOBAL,kernel_base=0xd1af,
                    meaning='synthetic disassembly normalization; not an observed runtime placement'),procedures=records)
            (output/(name+'.json')).write_text(json.dumps(spec,indent=2)+'\n');specs.append(spec)
    (output/'inputs.json').write_text(json.dumps(specs,indent=2)+'\n')
    return specs

def captured_check():
    source=(ROOT/'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes();procedures=mixed_directory(source)
    normalized=apply_relocations(source,procedures,0x95be,0xadbc)
    memory=(ROOT/'analysis/local/reference/advance-20261023-122315/advanced-main.bin').read_bytes()
    records=[]
    for p in procedures:
        if p['kind']!='native-6502':continue
        info=relocations(source,p);a=p['entry_address'];b=info['body_end_exclusive'];captured=memory[0x95be+a:0x95be+b]
        differing=[i+a for i,(x,y) in enumerate(zip(normalized[a:b],captured)) if x!=y]
        records.append(dict(procedure=p['number'],normalized_body_sha256=sha(normalized[a:b]),captured_body_sha256=sha(captured),
                            differing_offsets=differing,exact_match=not differing))
    if not next(r for r in records if r['procedure']==9)['exact_match']:raise ValueError('known glyph relocation does not reproduce capture')
    return dict(method='Apply four source relocation groups with captured segment/global bases; compare all native bodies',
                segment_base=0x95be,global_base=0xadbc,procedures=records,
                exact_matches=sum(r['exact_match'] for r in records),note='Remaining changes can include mutable data and self-modifying operands; they are not silently ignored')

def run_ghidra(specs):
    install=Path(os.environ.get('GHIDRA_INSTALL_DIR','/Users/ay5/Applications/ghidra_12.1.4_PUBLIC'))
    env=dict(os.environ,JAVA_HOME=os.environ.get('JAVA_HOME','/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home'),
        JAVA_TOOL_OPTIONS=f'-Duser.home={ROOT}/analysis/local/home -Djava.io.tmpdir={ROOT}/analysis/local/tmp')
    out=ROOT/'analysis/local/native-complete'
    for spec in specs:
        name=Path(spec['path']).stem;log=out/(name+'.log')
        command=[str(install/'support/analyzeHeadless'),str(ROOT/'ghidra/projects'),'SunDogNativeComplete',
            '-import',str(ROOT/spec['path']),'-overwrite','-noanalysis','-processor','6502:LE:16:default',
            '-loader','BinaryLoader','-loader-baseAddr',hex(BASE)[2:],'-scriptPath',str(ROOT/'ghidra/scripts'),
            '-postScript','ExportNativeArchive.java',str(out/(name+'.json')),str(out/(name+'-ghidra.json')),str(out/(name+'.txt'))]
        with log.open('w') as f:subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        text=log.read_text()
        if 'NATIVE_ARCHIVE_EXPORT_OK' not in text or 'REPORT: Save succeeded' not in text:raise ValueError('Ghidra export/save failed: '+name)

def report(specs):
    rows=[]
    for spec in specs:
        path=ROOT/'analysis/local/native-complete'/(Path(spec['path']).stem+'-ghidra.json')
        ghidra=json.loads(path.read_text()) if path.exists() else None
        rows.append(dict(archive='SYSTEM.LIBRARY',slot=spec['slot'],private_listing=str(Path(spec['path']).with_suffix('.txt')),private_ghidra_json=str(path.relative_to(ROOT)),segment_number=spec['segment_number'],source_sha256=spec['source_sha256'],payload_length=spec['length'],
            normalized_sha256=spec['normalized_sha256'],declared_view=spec['declared_view'],
            procedures=[dict(number=p['number'],entry_offset=p['entry_address'],body_end_exclusive=p['body_end_exclusive'],
                extra_code_entries=p['extra_code_entries'],source=p['source'],trailer_address=p['trailer_address'],directory_cell=p['directory_cell'],relocation_start=p['relocation_start'],relocation_end_exclusive=p['relocation_end_exclusive'],inline_data=p['inline_data'],relocation_groups=[dict(kind=g['kind'],count=g['count'],count_cell=g['count_cell'],start_offset=g['count_cell']-2*g['count'],end_exclusive=g['count_cell']+2) for g in p['groups']]) for p in spec['procedures']],
            ghidra=ghidra))
    for row in rows:
        by_number={p['number']:p for p in row['ghidra']['procedures']} if row['ghidra'] else {}
        for p in row['procedures']:
            decoded=by_number.get(p['number'])
            p['key']=['SYSTEM.LIBRARY',row['slot'],p['number']]
            if decoded is not None:
                starts={i['offset'] for i in decoded['instruction_spans']}
                if not {p['entry_offset'],*p['extra_code_entries']}<=starts:raise ValueError('native entry was not disassembled')
                p.update(instruction_count=len(decoded['instruction_spans']),code_bytes=sum(i['length'] for i in decoded['instruction_spans']),data_bytes=sum(r['end_exclusive']-r['start_offset'] for r in p['inline_data']),relocation_bytes=p['relocation_end_exclusive']-p['relocation_start'],relocation_word_targets=sum(g['count'] for g in p['relocation_groups']),unresolved_decoding_count=sum(r['end_exclusive']-r['start_offset'] for r in decoded['unclassified_ranges']),native_complete=not decoded['unclassified_ranges'])
    dynamic=[dict(segment=22,procedure=2,instruction_offset=0xcf3,target_expression='Original pcode ADD dispatcher saved from D004, then patched into JMP operand CF4/CF5; captured target D71D',evidence='Installer writes CF4/CF5 and sets CDC flag; only3captured body differences are CDC/CF4/CF5'),dict(segment=22,procedure=25,instruction_offset=0xf58,target_expression='16-bit destination popped from native argument stack into JMP operand F59/F5A',evidence='STA F59 at F4B and STA F5A at F4F; captured body differences confined to those operands')]
    result=dict(dynamic_target_expressions=dynamic,method='Original native loader relocation tables + normalized Ghidra 6502 listing/function/reference export; no target execution',
        relocation_loader_addresses=['E3FD..E43C','E5C7..E630'],archive_segments=rows,captured_verification=captured_check(),
        scope='All 31 native procedure bodies in the 4 mixed SYSTEM.LIBRARY archive segments; code/data coverage explicit',
        remaining=[])
    for row in rows:
        if row['ghidra'] is None:result['remaining'].append(dict(segment=row['segment_number'],reason='Ghidra export pending'))
        else:
            for p in row['ghidra']['procedures']:
                if p['unclassified_ranges']:result['remaining'].append(dict(segment=row['segment_number'],procedure=p['number'],unclassified_ranges=p['unclassified_ranges']))
    (ROOT/'analysis/native-archive-disassembly.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(native_procedures=sum(len(s['procedures']) for s in specs),remaining=len(result['remaining']),captured_exact_matches=result['captured_verification']['exact_matches'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ghidra',action='store_true');a=parser.parse_args()
    specs=prepare()
    if a.ghidra:run_ghidra(specs)
    report(specs)
