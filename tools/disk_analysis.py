#!/usr/bin/env python3
"""Deterministic inventory. DOS logical slots; unreadable sectors never become data."""
import argparse, collections, hashlib, json, math, pathlib, re, struct, zlib
TRACKS, SECTORS, SIZE = 35, 16, 256
DOS_TO_PHYSICAL = (0,13,11,9,7,5,3,1,14,12,10,8,6,4,2,15)
def offset(track, sector):
    if not 0 <= track < TRACKS or not 0 <= sector < SECTORS:
        raise ValueError('track/sector out of range')
    return (track * SECTORS + sector) * SIZE
def digest(data): return hashlib.sha256(data).hexdigest()
def stats(data):
    c = collections.Counter(data)
    return dict(sha256=digest(data), entropy=-sum(n/len(data)*math.log2(n/len(data)) for n in c.values()), distinct=len(c), zeros=c[0], ff=c[255], printable=sum(c[n] for n in range(32,127)), histogram=[c[n] for n in range(256)])
def load(path):
    data = pathlib.Path(path).read_bytes()
    if len(data) != TRACKS*SECTORS*SIZE: raise ValueError('expected 143360 bytes')
    return data
def analyze(root):
    root = pathlib.Path(root)
    out = root/'analysis'; out.mkdir(exist_ok=True)
    regions = out/'regions'; regions.mkdir(exist_ok=True)
    disks = {}; allhash = collections.defaultdict(list); inventories = []
    for side in ('utility','play'):
        data = load(root/'extracted'/f'{side}.do'); valid = {}
        records=[]; strings=[]; signatures=[]; candidates=[]
        for t in range(TRACKS):
            for s in range(SECTORS):
                pos=offset(t,s); rec=dict(side=side,track=t,sector=s,offset=pos,status='unknown' if side=='play' and t==34 else 'readable')
                if rec['status']=='readable':
                    block=data[pos:pos+SIZE]; valid[t,s]=block; rec.update(stats(block)); allhash[digest(block)].append([side,t,s])
                records.append(rec)
        # Scan only contiguous known bytes; never scan the failed track.
        known=data[:34*4096] if side=='play' else data
        for encoding, buf in [('ascii',known),('high-bit-masked',bytes(x&127 for x in known))]:
            for m in re.finditer(rb'[ -~]{6,}',buf):
                strings.append(dict(offset=m.start(),track=m.start()//4096,sector=m.start()//256%16,encoding=encoding,text=m.group().decode('ascii')))
        for sig in (b'SYSTEM',b'PASCAL',b'UCSD',b'SUNDOG',b'APPLE',b'FTL'):
            for m in re.finditer(re.escape(sig),known.upper()): signatures.append(dict(signature=sig.decode(),offset=m.start()))
        # Heuristic only: Pascal short names and plausible little-endian block extents.
        for p in range(0,len(known)-26,2):
            start,end,kind=struct.unpack_from('<HHH',known,p); n=known[p+6]
            if 0<=start<end<=280 and kind<=8 and 1<=n<=15 and re.fullmatch(rb'[A-Z0-9. _-]+',known[p+7:p+7+n]):
                candidates.append(dict(offset=p,start_block=start,end_block=end,kind=kind,name=known[p+7:p+7+n].decode(),confidence='low; unvalidated directory-entry heuristic'))
        disks[side]=valid
        (out/f'{side}-sectors.json').write_text(json.dumps(records,indent=2)+'\n')
        (out/f'{side}-search.json').write_text(json.dumps(dict(strings=strings,signatures=signatures,pascal_entry_candidates=candidates),indent=2)+'\n')
        # Each known track is a reproducible region, without guessed runtime identity.
        for t in range(TRACKS):
            if (t,0) not in valid: continue
            block=b''.join(valid[t,s] for s in range(16)); name=f'{side}-track-{t:02}.bin'; (regions/name).write_bytes(block)
            inventories.append(dict(path='analysis/regions/'+name,side=side,offset=t*4096,length=4096,sha256=digest(block),identity='unclassified track',confidence='high for byte provenance only'))
    corresponding=[]; similarity=[]
    for key,a in disks['utility'].items():
        if key not in disks['play']: continue
        b=disks['play'][key]; equal=sum(x==y for x,y in zip(a,b)); similarity.append(dict(track=key[0],sector=key[1],equal_bytes=equal))
        if a==b: corresponding.append(list(key))
    shared_tracks=[t for t in range(34) if all([t,s] in corresponding for s in range(16))]
    summary=dict(geometry=dict(tracks=35,sectors=16,bytes_per_sector=256,ordering='DOS logical, supplied provenance; not independently decoded from WOZ',dos_slot_to_physical=DOS_TO_PHYSICAL),unknown_sectors=[dict(side='play',track=34,sector=s,reason='supplied extraction failure') for s in range(16)],corresponding_identical=corresponding,identical_tracks=shared_tracks,repeated_sectors=[dict(sha256=h,locations=v) for h,v in sorted(allhash.items()) if len(v)>1],similarity=similarity)
    (out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'regions.json').write_text(json.dumps(inventories,indent=2)+'\n')
    media=[]
    for p in sorted((root/'disk').glob('*.woz')):
        b=p.read_bytes(); chunks=[]; cursor=12; info={}
        while cursor+8<=len(b):
            tag=b[cursor:cursor+4].decode('ascii'); length=struct.unpack_from('<I',b,cursor+4)[0]
            if cursor+8+length>len(b): raise ValueError('truncated WOZ chunk')
            chunks.append(dict(id=tag,offset=cursor,length=length))
            if tag=='INFO':
                payload=b[cursor+8:cursor+8+length]
                info=dict(version=payload[0],disk_type=payload[1],creator=payload[5:37].decode('ascii').strip())
            cursor+=8+length
        media.append(dict(path=str(p.relative_to(root)),size=len(b),sha256=digest(b),magic=b[:4].decode('ascii'),crc_stored=struct.unpack_from('<I',b,8)[0],crc_computed=zlib.crc32(b[12:])&0xffffffff,chunks=chunks,info=info))
    (out/'media.json').write_text(json.dumps(media,indent=2)+'\n')
    print(json.dumps(dict(identical_sectors=len(corresponding),identical_tracks=shared_tracks,regions=len(inventories))))
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); analyze(ap.parse_args().root)
