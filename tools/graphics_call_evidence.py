#!/usr/bin/env python3
"""Join p-code calls, mixed native tags, source sectors and retained RAM evidence."""
import hashlib,json
from collections import Counter
from pathlib import Path
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())['archives']
    archive=next(a for a in inventory if a['name']=='SYSTEM.LIBRARY')
    segment=next(s for s in archive['segments'] if s['segment_number']==22)
    raw=(ROOT/segment['path']).read_bytes();procs=mixed_directory(raw)
    if sha(raw)!=segment['sha256']:raise ValueError('library bytes differ')
    graph=json.loads((ROOT/'analysis/pcode-callgraph.json').read_text())
    sundog=next(a for a in graph['archives'] if a['name']=='SUNDOG.LIBRARY')
    decoded=json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-01.json').read_text())
    capture=ROOT/'analysis/local/reference/advance-20261023-122315/advanced-main.bin'
    memory=capture.read_bytes()
    manifest=json.loads((capture.parent/'manifest.json').read_text())
    expected=next(r['main_sha256'] for r in manifest['events'] if r['label']=='advanced')
    if sha(memory)!=expected:raise ValueError('retained capture memory identity differs')
    p9=next(p for p in procs if p['number']==9)
    prefix=raw[p9['entry_address']:p9['entry_address']+13]
    addresses=[p for p in range(len(memory)-len(prefix)+1) if memory[p:p+len(prefix)]==prefix]
    if len(addresses)!=1:raise ValueError('glyph prefix mapping ambiguous')
    loaded=addresses[0];base=loaded-p9['entry_address'];word=lambda p:int.from_bytes(memory[p:p+2],'little')
    directory=word(0xbd9e+22*2)
    if directory!=base+len(raw)-2 or memory[directory:directory+2]!=raw[-2:]:raise ValueError('segment-22 table binding differs')
    data_base=word(0xbd9e+29*2)+2
    (ROOT/'analysis/regions/rea-library22-coordinate-captured.bin').write_bytes(memory[base+0x1607:base+0x163e])
    captured=memory[loaded:loaded+p9['attribute_address']-p9['entry_address']]
    original=raw[p9['entry_address']:p9['attribute_address']]
    (ROOT/'analysis/regions/rea-library22-char9.bin').write_bytes(original)
    (ROOT/'analysis/regions/rea-library22-char9-captured.bin').write_bytes(captured)
    (ROOT/'analysis/regions/rea-library22-coordinate-helper.bin').write_bytes(raw[0x1607:0x163e])
    deltas=Counter();covered=set();patches=[]
    # Differences are exact little-endian operand word changes. All remaining bytes must agree.
    i=0
    while i<len(original):
        if original[i]==captured[i]:i+=1;continue
        if i+1>=len(original):raise ValueError('incomplete relocated word')
        delta=(int.from_bytes(captured[i:i+2],'little')-int.from_bytes(original[i:i+2],'little'))&65535
        if delta not in (base,data_base,loaded):raise ValueError('unexplained native operand change')
        deltas[hex(delta)]+=1;patches.append(dict(offset=i,delta=delta));covered.update((i,i+1));i+=2
    if any(a!=b for n,(a,b) in enumerate(zip(original,captured)) if n not in covered):raise ValueError('unexplained source difference')
    rows=[memory[0xdc0+y]|memory[0xe80+y]<<8 for y in range(192)]
    expected=[0x2000+(y&7)*0x400+((y>>3)&7)*0x80+(y>>6)*0x28 for y in range(192)]
    if rows!=expected:raise ValueError('captured row table is not full page-1 HGR addressing')
    def source(offset):
        s=segment['sectors'][offset//256]
        return dict(side='utility',**s,byte_in_sector=offset%256,image_offset=s['offset']+offset%256)
    procedures=[]
    for n in (9,11,12,45,47,48,49):
        p=next(p for p in procs if p['number']==n);r=next(r for r in decoded if r['procedure']['number']==n)
        procedures.append(dict(number=n,kind=p['kind'],entry_offset=p['entry_address'],entry_source=source(p['entry_address']),
            static_callees=[c for i in r['instructions'] for c in i['calls']],boundaries=r['boundaries']))
    counts=Counter(c['procedure'] for c in sundog['calls'] if c.get('segment_operand')==22)
    result=dict(method='Static source/callgraph analysis, REA/Ghidra native disassembly, bounded synthetic row checks, and pre-existing reference-memory corroboration; no new emulator execution',
        source_archive_sha256=sha(raw),source_segment_number=22,source_payload_bytes=len(raw),
        mixed_procedures=dict(total=len(procs),native=sum(p['kind']=='native-6502' for p in procs),pcode=sum(p['kind']=='pcode' for p in procs)),
        procedures=procedures,sundog_calls_to_segment22=dict(sorted(counts.items())),
        captured_mapping=dict(capture=str(capture.relative_to(ROOT)),memory_sha256=sha(memory),segment_base=base,
            segment_directory_cell=0xbd9e+22*2,segment_directory_pointer=directory,data29_base=data_base,
            native9_address=loaded,native_slice_length=len(original),source_slice_sha256=sha(original),captured_slice_sha256=sha(captured),
            changed_bytes=sum(a!=b for a,b in zip(original,captured)),operand_word_deltas=dict(deltas),
            note='22 operand-word changes explained by segment, data-29 and procedure bases; relocation parser still to be reconstructed'),
        hgr_row_table=dict(low=0xdc0,high=0xe80,rows=192,formula_matches=True),
        rea_evidence_ids={name:json.loads((ROOT/path).read_text())['evidence_id'] for name,path in
            [('native_source','analysis/local/rea/library22-glyph-raw.json'),('captured_native','analysis/local/rea/library22-glyph-captured.json'),('coordinate_helper','analysis/local/rea/library22-coordinate-helper.json'),('frame_branch_base','analysis/local/rea/restart-frame-evidence.json')]},
        confidence=dict(call_operands='high static',segment22_binding='observed in retained snapshot only',
            native_row_composition='420 synthetic cases; see glyph-compositor-evidence.json',
            string_layout_role='strong static inference; exact wrapping/API contract still under analysis'),
        remaining=['Native relocation table format','Mode-2 query/collision semantics','String wrapping and clipping boundary cases','Original glyph asset provenance','Input/event loop and actual game-state owners'])
    (ROOT/'analysis/graphics-call-chain.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(segment22_base=hex(base),native9=hex(loaded),data29=hex(data_base),calls_to_string48=counts[48],native_operand_deltas=dict(deltas))))
if __name__=='__main__':main()
