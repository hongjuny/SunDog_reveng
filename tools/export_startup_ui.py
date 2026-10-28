#!/usr/bin/env python3
"""Export source-bound startup text and disk marker data, never captured screens."""
import hashlib
import json
from pathlib import Path
from boot_regions import pages
from initial_game_flow import load_segment
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()

def main():
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive=next(a for a in inventory['archives'] if a['name']=='SYSTEM.LIBRARY')
    source=next(s for s in archive['segments'] if s['segment_number']==26)
    raw=(ROOT/source['path']).read_bytes()
    if SHA(raw)!=source['sha256']:raise ValueError('Startup source changed')
    pcode=json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-05.json').read_text())
    proc=next(p for p in pcode if p['procedure']['number']==6)
    nodes={r['address']:r for r in proc['instructions']}
    proofs=[]
    def text(address):
        row=nodes[address]
        if row['opcode']!=0xa6:raise ValueError('Expected original inline string')
        value=raw[address+2:address+2+row['operands']['payload_length']]
        if SHA(value)!=row['operands']['payload_sha256']:raise ValueError('String digest changed')
        proofs.append(dict(segment=26,procedure=6,address=address,length=len(value),sha256=SHA(value)))
        return list(value)
    addresses={'tooBad':0x04e3,'wellDone':0x04f9,'hello':0x050b,'died':0x0539,
        'succeeded':0x054d,'gameOver':0x055d,'damaged':0x057f,'can':0x059b,
        'start':0x05b5,'continueGame':0x05c1,'yourGame':0x05cf,'options':0x05e1}
    messages={key:text(address) for key,address in addresses.items()}
    labels=[dict(id=identifier,bytes=text(address)) for identifier,address in [(2,0x0627),(1,0x0645),(3,0x0665)]]
    play_source,play_raw,play_procs=load_segment(7)
    flip=[]
    for address in (0x0041,0x0077,0x0087):
        row=next(r for r in play_procs[3]['instructions'] if r['address']==address)
        value=play_raw[address+2:address+2+row['operands']['payload_length']]
        if SHA(value)!=row['operands']['payload_sha256']:raise ValueError('Flip message changed')
        flip.append(list(value));proofs.append(dict(segment=7,procedure=3,address=address,length=len(value),sha256=SHA(value)))
    output=ROOT/'analysis/local/native-assets';output.mkdir(parents=True,exist_ok=True)
    data=dict(greeting=messages,labels=labels,playFlip=flip)
    asset=output/'sundog-startup-ui.json';asset.write_text(json.dumps(data,indent=2)+'\n')
    play=(ROOT/'extracted/play.do').read_bytes();boot,sectors=pages(0,2,play)
    if boot[252]!=9:raise ValueError('Supplied Play side marker changed')
    (output/'sundog-play-boot.bin').write_bytes(boot)
    report=dict(method='Original decoded string identities and Play boot block; no reference-screen data',
        source_sha256=source['sha256'],ui_asset_sha256=SHA(asset.read_bytes()),strings=proofs,
        play_boot_sha256=SHA(boot),play_marker=boot[252],play_boot_sectors=sectors,
        limitations=['Text extraction alone does not prove UI layout; renderer evidence is separate.',
                     'A marker check is the original gate, not complete filesystem or game validity.'])
    (ROOT/'analysis/startup-ui-assets.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(strings=len(proofs),play_marker=boot[252])))

if __name__=='__main__':main()
