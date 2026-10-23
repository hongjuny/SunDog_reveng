#!/usr/bin/env python3
"""Read-only CiderPress2 sector decoding, comparison, and optional known-track export."""
import argparse,json,pathlib,re,subprocess
from disk_analysis import load,offset,digest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def parse_sector_dump(output):
    lines=re.findall(r'^\s*([0-9a-fA-F]{6}): ((?:[0-9a-fA-F]{2} ){15}[0-9a-fA-F]{2})',output,re.M)
    if [int(p,16) for p,_ in lines]!=list(range(0,256,16)):
        return None
    return b''.join(bytes.fromhex(raw) for _,raw in lines)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cp2',default='/Users/ay5/Projects/CiderPress2/cp2/bin/Release/net10.0/osx-arm64/cp2')
    ap.add_argument('--full',action='store_true',help='decode all 1120 sector slots; export only complete readable tracks')
    args=ap.parse_args();records=[];track_records=[]
    for side in ('utility','play'):
        path=next((ROOT/'disk').glob('*'+('Utility' if side=='utility' else 'Play')+'*.woz'))
        data=load(ROOT/'extracted'/f'{side}.do')
        samples=[(t,s) for t in range(35) for s in range(16)] if args.full else [(0,0),(0,13),(0,14),(13,0),(17,15),(33,15)]+([(34,s) for s in range(16)] if side=='play' else [(34,15)])
        decoded={}
        for t,s in samples:
            r=subprocess.run([args.cp2,'read-sector',str(path),str(t),str(s)],capture_output=True,text=True)
            raw=parse_sector_dump(r.stdout) if r.returncode==0 else None
            rec=dict(side=side,track=t,sector=s,returncode=r.returncode,decoded_bytes=0 if raw is None else len(raw),matches=raw is not None and raw==data[offset(t,s):offset(t,s)+256],stderr=r.stderr.strip())
            if raw is not None:
                rec['sha256']=digest(raw);decoded[t,s]=raw
            records.append(rec)
            if args.full and s==15 and (t%5==4 or t==34):print(f'{side}: decoded through track {t}',flush=True)
        if args.full:
            dest=ROOT/'analysis/regions/woz-read'/side;dest.mkdir(parents=True,exist_ok=True)
            for t in range(35):
                target=dest/f'track-{t:02}.bin'
                if not all((t,s) in decoded for s in range(16)):
                    target.unlink(missing_ok=True)
                    continue
                block=b''.join(decoded[t,s] for s in range(16))
                target.write_bytes(block)
                track_records.append(dict(side=side,track=t,path=str(target.relative_to(ROOT)),sha256=digest(block),length=len(block)))
    if args.full:
        cp=pathlib.Path(args.cp2)
        identities=[dict(path=str(p),sha256=digest(p.read_bytes())) for p in (cp,cp.with_suffix('.dll'),cp.parent/'DiskArc.dll') if p.is_file()]
        output=dict(method='cp2 read-sector WOZ track DOS-sector; strict complete hex-dump parsing; nonzero exit is unknown',decoder_files=identities,sectors=records,known_tracks=track_records)
        target=ROOT/'analysis/woz-full-checks.json'
    else:output=records;target=ROOT/'analysis/woz-checks.json'
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(samples=len(records),matches=sum(r['matches'] for r in records),failed=sum(r['decoded_bytes']!=256 for r in records))))
if __name__=='__main__':main()
