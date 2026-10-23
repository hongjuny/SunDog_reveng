#!/usr/bin/env python3
"""Check genuine REA inspect_native_instruction Evidence after reconnection.
The validator does not manufacture REA output or count direct Ghidra as REA.
"""
import argparse,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]

def validate(evidence):
    if evidence.get('provider',{}).get('id')!='ghidra':raise ValueError('expected genuine Ghidra-provider Evidence')
    if not evidence.get('evidence_id'):raise ValueError('REA evidence_id is required')
    r=evidence.get('normalized_result',{})
    if r.get('status')!='decoded' or r.get('address')!='0xd293':raise ValueError('expected a decoded instruction at D293')
    raw=re.sub(r'\s+','',r.get('bytes') or '').lower().removeprefix('0x')
    if raw!='a000' or r.get('mnemonic')!='LDY' or r.get('length')!=2:raise ValueError('REA instruction disagrees with sector bytes and direct Ghidra')
    return dict(status='verified',evidence_id=evidence['evidence_id'],provider='ghidra',address='0xd293',bytes='a000',mnemonic='LDY',length=2,scope='one native instruction in the bounded 37-byte fetch-loop target')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('evidence',type=pathlib.Path);args=p.parse_args()
    result=validate(json.loads(args.evidence.read_text()))
    (ROOT/'analysis/rea-crosscheck.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
