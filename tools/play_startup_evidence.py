#!/usr/bin/env python3
"""Validate the shared startup dictionary against readable Play-side payloads.

Structure is evidence of payload identity, not proof of runtime disk selection.
Unreadable track 34 is never included, hashed as data, or exported.
"""
import hashlib,json
from pathlib import Path
from boot_regions import pages
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    inventory=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    old=next(a for a in inventory['archives'] if a['name']=='SYSTEM.STARTUP')
    media={s:(ROOT/'extracted'/f'{s}.do').read_bytes() for s in ('utility','play')}
    header,sources=pages(old['start_block'],2,media['play']);other,_=pages(old['start_block'],2,media['utility'])
    if header!=other or sha(header)!=old['dictionary_sha256']:raise ValueError('shared dictionary identity differs')
    verified=json.loads((ROOT/'analysis/woz-full-checks.json').read_text())['sectors']
    known={(r['track'],r['sector']):r['sha256'] for r in verified if r['side']=='play' and r['decoded_bytes']==256 and r['matches']}
    out=ROOT/'analysis/regions/play-startup';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for record in old['segments']:
        first=old['start_block']+record['relative_block'];count=record['storage_blocks']*2
        if first*2+count>34*16:raise ValueError("Play payload reaches unreadable track 34")
        raw,provenance=pages(first,count,media['play'])
        for i,p in enumerate(provenance):
            expected=known.get((p['track'],p['sector']))
            if expected is None or sha(raw[i*256:(i+1)*256])!=expected:raise ValueError('payload includes unknown or unverified sector')
        raw=raw[:record['length']];procedures=mixed_directory(raw)
        if raw[-2]!=record['segment_number']:raise ValueError('segment number does not match descriptor')
        target=out/f"segment-{record['segment_number']:02}.bin";target.write_bytes(raw)
        utility,_=pages(first,count,media['utility']);utility=utility[:record['length']]
        try:
            up=mixed_directory(utility)
            utility_validation=dict(valid=True,procedures=len(up),segment_number=utility[-2])
        except ValueError as error:utility_validation=dict(valid=False,reason=str(error))
        rows.append(dict(**{k:v for k,v in record.items() if k not in ('path','side','sha256','sectors','absolute_block','status')},
                         status='structurally_validated_on_play',side='play',absolute_block=first,end_block_exclusive=first+record['storage_blocks'],
                         path=str(target.relative_to(ROOT)),sha256=sha(raw),sectors=provenance,
                         procedures=len(procedures),procedure_kinds={k:sum(p['kind']==k for p in procedures) for k in ('pcode','native-6502')},
                         identical_utility_payload=utility==raw,utility_structure=utility_validation))
    report=dict(method='Shared block-140 dictionary, independently verified readable Play sectors, all procedure ordinal/self-relative entry checks; no execution',
                dictionary_block=old['start_block'],dictionary_sha256=sha(header),dictionary_identical_both_sides=True,dictionary_sources=sources,
                utility_directory_extent=[old['start_block'],old['end_block']],
                play_payload_storage_end_exclusive=max(r['end_block_exclusive'] for r in rows),segments=rows,
                confidence='High structural correspondence of dictionary and Play payloads; runtime side-selection/loader branches still unverified',
                limitations=['A valid Pascal procedure directory does not identify gameplay responsibilities.',
                             'The Utility filesystem extent cannot bound the Play application payloads.',
                             'Play track 34 remains unknown; none of its bytes participate.'])
    (ROOT/'analysis/play-startup-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(segments=len(rows),procedures=sum(r['procedures'] for r in rows),storage_end=report['play_payload_storage_end_exclusive'],track34_used=False)))
if __name__=='__main__':main()
