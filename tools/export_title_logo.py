#!/usr/bin/env python3
"""Extract six original eight-frame logo sprites from verified Utility sectors.

The early boot bitmap has no SUN DOG logo. This is the later segment26 resource,
not a crop or a pixel reconstruction from a captured screenshot.
"""
import hashlib
import json
from pathlib import Path
from boot_regions import pages
from disk_analysis import load

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()
ASSET_SHA = 'c49ef7d757ac42f03b2d33ef8fd95c9c83faf02a0d29ac27ad9af1a756d9c2a2'
FINAL_HGR_SHA = '7e4f8f739f8b9d40a411f462036f740e1b518ce547184d03c5f4c746d0cc317d'


def row_offset(row):
    if not 0 <= row < 192: raise ValueError('Invalid HGR row')
    return (row & 7)*1024 + ((row >> 3) & 7)*128 + (row >> 6)*40


def compose_final(background, glyphs):
    """Independent final-state contract; moving-letter order is verified separately."""
    if len(background) != 8192 or len(glyphs) != 6144:
        raise ValueError('Expected8192-byte background and6144-byte logo resource')
    page = bytearray(background)
    for column in range(30):
        pattern = (0xaa if column % 2 == 0 else 0xd5) if column != 29 else 0
        for row in range(32,80):
            page[row_offset(row)+column] = pattern if 36 <= row < 40 or 72 <= row < 76 else 0
    for character in range(6):
        for row in range(24):
            for column in range(4):
                page[row_offset(44+row)+character*5+column] = glyphs[character*1024+7*128+row*4+column] | 0x80
    return bytes(page)


def main():
    disk_path = ROOT/'extracted/utility.do'
    disk = load(disk_path)
    resource, sectors = pages(67,24,disk)
    if len(resource) != 6144 or SHA(resource) != ASSET_SHA:
        raise ValueError('Logo resource differs from source-bound original')
    verification_path = ROOT/'analysis/woz-full-checks.json'
    checks = json.loads(verification_path.read_text())
    verified = {(r['track'],r['sector']):r for r in checks['sectors'] if r['side']=='utility'}
    sources=[]
    for index,sector in enumerate(sectors):
        raw=resource[index*256:(index+1)*256];proof=verified[sector['track'],sector['sector']]
        if proof['returncode']!=0 or not proof['matches'] or proof['decoded_bytes']!=256 or proof['sha256']!=SHA(raw):
            raise ValueError('Logo source sector is not verified against original WOZ')
        sources.append(dict(side='utility',**sector,destination_offset=index*256,load_address=0x4000+index*256,length=256,sha256=SHA(raw)))
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive=next(a for a in inventory['archives'] if a['name']=='SYSTEM.LIBRARY')
    segment=next(s for s in archive['segments'] if s['slot']==5)
    code=(ROOT/segment['path']).read_bytes()
    if SHA(code)!=segment['sha256']:raise ValueError('Segment26 source identity changed')
    procedures=json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-05.json').read_text())
    p14=next(p for p in procedures if p['procedure']['number']==14)
    rows={r['address']:r for r in p14['instructions']}
    if [rows[a]['operands'].get('word',rows[a]['opcode']) for a in (0x68,0x6b,0x6c,0x6d)] != [16384,12,64,1]:
        raise ValueError('Original loader call arguments changed')
    if rows[0x6e]['calls']!=[dict(kind='external-segment-operand',segment_operand=22,procedure=53)]:
        raise ValueError('Original P14 read call changed')
    captures=[]
    capture_dir=ROOT/'analysis/local/reference/logo-write-20261023-151127'
    capture_path=capture_dir/'first-logo-write-main.bin'
    if capture_path.exists():
        manifest=json.loads((capture_dir/'manifest.json').read_text())
        memory=capture_path.read_bytes()
        event=next(e for e in manifest['events'] if e['label']=='first-logo-write')
        # The source-equality claim is separate from any screenshot pixels.
        if SHA(memory)!=event['main_sha256'] or memory[0x4000:0x5800]!=resource:raise ValueError('Captured loaded sprite resource differs')
        captures.append(dict(path=str(capture_path.relative_to(ROOT)),memory_sha256=SHA(memory),loaded_address=0x4000,loaded_length=6144,resource_equal=True,role='Runtime corroboration; never extraction source'))
    background=(ROOT/'analysis/local/native-assets/sundog-splash.hgr').read_bytes()
    final=compose_final(background,resource)
    if SHA(final)!=FINAL_HGR_SHA:raise ValueError('Independent final logo composition changed')
    ref_dir=ROOT/'analysis/local/reference/follow-20261023-115323'
    ref_path=ref_dir/'after-720-frames-main.bin'
    if ref_path.exists():
        manifest=json.loads((ref_dir/'manifest.json').read_text())
        event=next(e for e in manifest['events'] if e['label']=='after-720-frames')
        memory=ref_path.read_bytes()
        if SHA(memory)!=event['main_sha256'] or memory[0x2000:0x4000]!=final:raise ValueError('Final logo composition differs from original reference')
        captures.append(dict(path=str(ref_path.relative_to(ROOT)),memory_sha256=SHA(memory),full_page_equal=True,page_sha256=SHA(final),role='Full final-page corroboration; never bitmap source'))
    output=ROOT/'analysis/local/native-assets/sundog-logo.bin';output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(resource)
    report=dict(artifact=str(output.relative_to(ROOT)),length=len(resource),sha256=SHA(resource),
        identity='Original separate SUN DOG animated logo sprites, added after the native spaceship/planet reveal',
        method='Direct original loader-order extraction; P14 read arguments and verified original WOZ sector hashes',
        source_side='utility',source_image=str(disk_path.relative_to(ROOT)),source_image_sha256=SHA(disk),
        loader=dict(archive='SYSTEM.LIBRARY',slot=5,segment_number=26,procedure=14,call_offset=0x6e,
                    call_segment=22,call_procedure=53,buffer=0x4000,requested_block=64,unit=4,block_bias=3,
                    actual_start_block=67,end_block_exclusive=79,block_count=12,pages=24,source_sha256=SHA(code)),
        layout=dict(glyph_count=6,frame_count=8,glyph_stride=1024,frame_stride=128,rows=24,bytes_per_row=4,
                    displayed_frame_bytes=96,padding_bytes_per_frame=32,phase_policy='Original native P11 ORs each copied byte with0x80'),
        final_layout=dict(glyph_frame=7,baseline_row_start=44,target_byte_columns=[0,5,10,15,20,25],
                    modified_rows=[32,79],modified_byte_columns=[0,29],page_sha256=SHA(final)),
        woz_verification_sha256=SHA(verification_path.read_bytes()),sources=sources,corroboration=captures,
        confidence='High for original resource bytes, loader mapping, and independent final HGR equality',
        limitations=['This asset is separate from the earlier boot bitmap; its extraction alone does not implement the animation.',
                     'Physical display timing and input behavior remain outside asset identity.'])
    (ROOT/'analysis/title-logo-asset.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('artifact','length','sha256')}))

if __name__=='__main__':main()
