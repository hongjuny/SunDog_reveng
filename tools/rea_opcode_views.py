#!/usr/bin/env python3
"""Bounded native opcode probes and verification of retained actual REA Evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from rea_memory_views import evidence, verify_read

ROOT = Path(__file__).resolve().parents[1]
SPECS = (
    ('a1', 0xd2a0, 0xd2a8, (0xa1,)),
    ('b9', 0xd2a8, 0xd2d7, (0xb9,)),
    ('9d', 0xd442, 0xd467, (0x9d,)),
    ('d1', 0xd467, 0xd48c, (0xd1,)),
    ('a7', 0xd48c, 0xd4a8, (0xa7,)),
    ('9a', 0xd4bc, 0xd4d6, (0x9a,)),
    ('be', 0xd567, 0xd581, (0xbe,)),
    ('bf', 0xd581, 0xd59b, (0xbf,)),
    ('multiply-helper', 0xd75f, 0xd786, (0x8f, 0x98)),
    ('8f', 0xd786, 0xd7cd, (0x8f,)),
    ('98', 0xd7cd, 0xd7d9, (0x98,)),
)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def prepare():
    snapshot = (ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    dispatch = json.loads((ROOT/'analysis/runtime-dispatch.json').read_text())
    boot = json.loads((ROOT/'analysis/boot-regions.json').read_text())
    sectors = next(r for r in boot if r['name'] == 'runtime-bank1')['sectors']
    disk = (ROOT/'extracted/utility.do').read_bytes()
    rows = []
    for name, start, end, ops in SPECS:
        if name != 'multiply-helper':
            for op in ops:
                if next(r for r in dispatch['primary'] if r['opcode'] == op)['handler'] != start:
                    raise ValueError('native dispatch target changed')
        raw = snapshot[start-0xd000:end-0xd000]
        sources = []
        for p in range(start, end):
            sector = sectors[(p-0xd000)//256]
            offset = sector['offset'] + p % 256
            if disk[offset] != raw[p-start]:
                raise ValueError('native slice differs from Utility sector')
            if sources and sources[-1]['disk_offset']+sources[-1]['length'] == offset:
                sources[-1]['length'] += 1
            else:
                sources.append(dict(side='utility', track=sector['track'], sector=sector['sector'],
                                    physical_sector=sector['physical_sector'], disk_offset=offset,
                                    memory_address=hex(p), length=1))
        path = ROOT/'analysis/regions'/('rea-opcode-'+name+'.bin')
        path.write_bytes(raw)
        rows.append(dict(name=name, path=str(path.relative_to(ROOT)), base_and_entry=hex(start),
                         end_exclusive=hex(end), length=len(raw), sha256=sha(raw), opcodes=list(ops),
                         sources=sources))
    result = dict(snapshot_sha256=sha(snapshot), views=rows,
                  scope='Native-only bounded slices; calls/jumps outside slices remain unresolved in REA')
    (ROOT/'analysis/rea-opcode-inputs.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(rows))

def compare_assembly(assembly, listing, raw, base):
    direct = {int(a, 16): text.strip() for a, text in re.findall(r'^([0-9a-f]{4})  (.+)$', listing, re.M)}
    rows = re.findall(r'^0x([0-9a-f]+): (.+)$', assembly, re.M)
    if not rows:
        raise ValueError('REA assembly has no instruction observations')
    expected = {a for a in direct if base <= a < base+len(raw)}
    observed = [int(a, 16) for a, _ in rows]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError('REA assembly is incomplete or contains duplicate instructions')
    for address, text in rows:
        address = int(address, 16)
        if not base <= address < base+len(raw) or direct.get(address) != text.strip():
            raise ValueError('REA assembly differs from bounded direct Ghidra listing')
    return len(rows)

def verify(directory):
    manifest = json.loads((ROOT/'analysis/rea-opcode-inputs.json').read_text())
    if manifest['snapshot_sha256'] != sha((ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()):
        raise ValueError('interpreter snapshot changed')
    listing = (ROOT/'ghidra/exports/interpreter-ready.txt').read_text()
    rows = []
    for target in manifest['views']:
        raw = (ROOT/target['path']).read_bytes()
        if sha(raw) != target['sha256']:
            raise ValueError('native source changed')
        records = {k: json.loads((directory/target['name']/(k+'.json')).read_text())
                   for k in ('load', 'bytes', 'entry', 'assembly')}
        loaded = evidence(records['load'], 'inspect_native_load_image', target['sha256'])
        if (loaded.get('status') != 'verified' or loaded.get('architecture') != '6502'
                or loaded.get('format') != 'raw-binary' or loaded.get('language_id') != '6502:LE:16:default'
                or loaded.get('base_address') != target['base_and_entry']
                or loaded.get('file_bytes') != len(raw) or not loaded.get('checks')
                or not all(c['matched'] for c in loaded['checks'])):
            raise ValueError('REA native load did not verify')
        start = int(target['base_and_entry'], 16)
        verify_read(records['bytes'], target['sha256'], start, raw)
        ins = evidence(records['entry'], 'inspect_native_instruction', target['sha256'])
        if (ins.get('status') != 'decoded' or ins.get('address') != target['base_and_entry']
                or not ins.get('length') or bytes.fromhex(ins.get('bytes') or '') != raw[:ins['length']]):
            raise ValueError('native entry not decoded from source bytes')
        assembly = evidence(records['assembly'], 'procedure_assembly', target['sha256'])
        count = compare_assembly(assembly, listing, raw, start)
        rows.append(dict(name=target['name'], opcodes=target['opcodes'], sha256=target['sha256'],
                         complete_bytes_verified=len(raw), load_checks=len(loaded['checks']),
                         native_instructions_compared=count,
                         evidence_ids={k:r['evidence_id'] for k,r in records.items()}))
    report = dict(status='verified_bounded_native_handlers', snapshot_sha256=manifest['snapshot_sha256'],
                  views=rows, limitations=['REA and direct analysis both use Ghidra.',
                  'Static bounded views do not prove runtime bank state, stack contents or all indirect targets.',
                  'Selected semantics are established separately by synthetic native-handler replay.'])
    (ROOT/'analysis/rea-opcode-crosscheck.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], views=len(rows),
                         instructions=sum(r['native_instructions_compared'] for r in rows))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    verify(args.verify) if args.verify else prepare()
