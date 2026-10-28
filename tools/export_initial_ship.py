#!/usr/bin/env python3
"""Extract the initial profile-selected Play SHIP image resource from original disk."""
import hashlib
import json
from pathlib import Path
from boot_regions import pages
from initial_game_flow import load_segment, require, coordinate

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()


def decode_image(encoded):
    if not encoded or encoded[0] == 0:
        raise ValueError('Invalid image stride')
    stride = encoded[0]; source = 1; page = bytearray(8192)
    def next_byte():
        nonlocal source
        if source >= len(encoded): raise ValueError('Truncated image source')
        value = encoded[source]; source += 1; return value
    for column in range(stride):
        destination = column
        while destination < 8192:
            token = next_byte(); count = (token & 127) + 1
            if token < 128:
                value = next_byte()
                for _ in range(count):
                    page[destination] = value; destination += stride
                    if destination >= 8192: break
            else:
                for _ in range(count):
                    page[destination] = next_byte(); destination += stride
                    if destination >= 8192: break
    return bytes(page), source


def verified_pages(side, block, count):
    disk = (ROOT/f'extracted/{side}.do').read_bytes()
    value, sectors = pages(block, count, disk)
    proof = json.loads((ROOT/'analysis/woz-full-checks.json').read_text())
    lookup = {(r['side'],r['track'],r['sector']):r for r in proof['sectors']}
    result=[]
    for index,sector in enumerate(sectors):
        raw=value[256*index:256*(index+1)]; row=lookup[side,sector['track'],sector['sector']]
        if row['returncode']!=0 or not row['matches'] or row['sha256']!=SHA(raw):
            raise ValueError('Image resource contains an unverified sector')
        result.append(dict(side=side,**sector,resource_offset=index*256,sha256=SHA(raw)))
    return value,result


def main():
    source, raw, p = load_segment(15)
    require(p[8],0x02FA,'load_nonlocal',selector_or_depth=1,index=26)
    require(p[8],0x02FD,'push_short_constant',value=4)
    require(p[8],0x0315,'address_table_indexed',selector_or_depth=29,index=82)
    require(p[8],0x0318,'push_short_constant',value=7)
    require(p[8],0x031F,'load_table_indexed',selector_or_depth=29,index=32)
    require(p[8],0x0329,'push_short_constant',value=4)
    require(p[8],0x0333,'call_external_segment',segment_operand=22,procedure=53)
    require(p[8],0x033C,'call_external_segment',segment_operand=24,procedure=5)
    metadata,_ = verified_pages('utility',83,2)
    profile_number = metadata[1]
    relative_profile = 24 + 10*profile_number
    profile,profile_sources = verified_pages('utility',relative_profile+3,2)
    state = int.from_bytes(profile[18:20],'little')
    flags82 = int.from_bytes(profile[92:94],'little')
    flag7 = bool(flags82 & 128)
    # Segment7 P5 initializes table29.word32 to26. P8 selects +0 or +4.
    relative = 26 + (0 if flag7 else 4)
    absolute = relative + 3
    encoded,sectors = verified_pages('play',absolute,8)
    page,consumed = decode_image(encoded)
    out=ROOT/'analysis/local/native-assets';out.mkdir(parents=True,exist_ok=True)
    artifact=out/'sundog-initial-ship.bin';artifact.write_bytes(encoded)
    (out/'sundog-initial-ship.hgr').write_bytes(page)
    result=dict(method='Original Play segment15 resource selection from Utility profile flags; direct verified disk extraction',
        artifact=str(artifact.relative_to(ROOT)),length=len(encoded),sha256=SHA(encoded),
        decoded_length=8192,decoded_sha256=SHA(page),consumed_bytes=consumed,stride=encoded[0],
        source_segment_sha256=source['sha256'],selection_source=coordinate(source,0x0315),
        resource=dict(side='play',relative_block=relative,absolute_block=absolute,blocks=4,sectors=sectors),
        profile=dict(side='utility',selector_metadata_block=83,profile_index=profile_number,
            absolute_block=relative_profile+3,record_sha256=SHA(profile),sectors=profile_sources,
            state_word45=state,state_hex=f'{state:04x}',mode=(state>>8)&15,
            word82=flags82,flag7=flag7,note='State0x32BB means mode2, not3; high nibble3 is not the dispatcher field.'),
        decoder=dict(archive='SYSTEM.LIBRARY',segment=24,procedure=5,entry_offset=0x1010,
            rule='Header stride; low token repeats next byte(token+1), high token copies(token&127)+1 literal bytes; column-major strided destination covers8192 bytes'),
        confidence='High for original source/data selection and native decoding contract; full first-scene behavior is separate',
        limitations=['This is the base SHIP bitmap before subsequent cursor/status overlays.',
            'Conditional early-return/resource cache paths are not a complete scene emulator.',
            'No interactive movement or gameplay rules are implemented by decoding the image.'])
    (ROOT/'analysis/initial-ship-asset.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('artifact','length','sha256','decoded_sha256','consumed_bytes')}))

if __name__=='__main__':main()
