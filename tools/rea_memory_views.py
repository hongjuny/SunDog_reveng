#!/usr/bin/env python3
"""Prepare bounded views and verify retained actual REA Evidence; no target execution."""
import argparse
import hashlib
import json
from pathlib import Path
from verify_memory_views import compare_views

ROOT = Path(__file__).resolve().parents[1]
SPECS = (
    ('bank1-entry', 'runtime-bank1', 0xd000, 0xd152, 0xd155, 'JMP'),
    ('bank2-entry', 'lc-bank2', 0xd000, 0xd152, 0xd155, 'JSR'),
    ('common-before', 'runtime-bank1', 0xd000, 0xf1ca, 0xfe7c, 'RTS'),
    ('common-after', 'interpreter-ready', 0xd000, 0xf1ca, 0xfe7c, 'RTS'),
    ('copy-routine', 'runtime-bank1', 0xd000, 0xf269, 0xf290, 'LDA'),
    ('relocated-init', 'relocated-6800', 0x6800, 0x6800, 0x6d00, 'CLD'),
)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def evidence(record, operation, target):
    if not record.get('evidence_id') or record.get('provider', {}).get('id') != 'ghidra':
        raise ValueError('Ghidra REA Evidence identity required')
    if record.get('operation') != operation:
        raise ValueError('wrong Evidence operation')
    if record.get('subject', {}).get('digest', {}).get('sha256') != target:
        raise ValueError('Evidence belongs to a different target')
    return record['normalized_result']

def verify_read(record, target, address, raw):
    result = evidence(record, 'read_bytes', target)
    if (result.get('address') != hex(address) or result.get('complete') is not True
            or result.get('requested_bytes') != len(raw)
            or result.get('returned_bytes') != len(raw)):
        raise ValueError('incomplete or differently addressed REA read')
    if bytes.fromhex(result['bytes_hex']) != raw:
        raise ValueError('REA memory differs from bounded source')
    return True

def prepare():
    directory = ROOT / 'analysis/regions'
    raw = {n: (directory/(n+'.bin')).read_bytes() for n in
           ('lc-bank1', 'lc-bank2', 'runtime-bank1', 'interpreter-ready', 'relocated-6800')}
    segment = (directory/'archives/SYSTEM.PASCAL-slot-00.bin').read_bytes()
    composition = compare_views(*(raw[n] for n in ('lc-bank1', 'lc-bank2',
                               'runtime-bank1', 'interpreter-ready')), segment)
    boot = json.loads((ROOT/'analysis/boot-regions.json').read_text())
    handoff = json.loads((ROOT/'analysis/boot-handoff.json').read_text())
    disk = (ROOT/'extracted/utility.do').read_bytes()
    rows = []
    for name, source, base, start, end, mnemonic in SPECS:
        payload = raw[source][start-base:end-base]
        if len(payload) != end-start:
            raise ValueError('slice outside snapshot')
        sources = []
        for address in range(start, end):
            origin = address if source != 'relocated-6800' else address-0x6800+0xf290
            if source == 'interpreter-ready' and 0xf248 <= origin < 0xfe7c:
                offset, sectors, kind = origin-0xf248, handoff['segment0']['sectors'], 'segment0'
            else:
                kind = 'lc-bank2' if source == 'lc-bank2' else 'runtime-bank1'
                offset = origin-0xd000
                sectors = next(r for r in boot if r['name'] == kind)['sectors']
            sector = sectors[offset//256]
            disk_offset = sector['offset'] + offset % 256
            if disk[disk_offset] != payload[address-start]:
                raise ValueError('Utility source-sector mismatch')
            if (sources and sources[-1]['source_kind'] == kind
                    and sources[-1]['disk_offset']+sources[-1]['length'] == disk_offset
                    and sources[-1]['sector'] == sector['sector']
                    and sources[-1]['track'] == sector['track']):
                sources[-1]['length'] += 1
            else:
                sources.append(dict(source_kind=kind, side='utility', track=sector['track'],
                                    sector=sector['sector'], physical_sector=sector['physical_sector'],
                                    disk_offset=disk_offset, memory_address=hex(address), length=1))
        if mnemonic == 'RTS' and payload[0] != 0x60:
            raise ValueError('expected existing RTS boundary before data')
        path = directory/('rea-memory-'+name+'.bin')
        path.write_bytes(payload)
        rows.append(dict(name=name, path=str(path.relative_to(ROOT)), base_and_entry=hex(start),
                         end_exclusive=hex(end), length=len(payload), sha256=sha(payload),
                         source_snapshot='analysis/regions/'+source+'.bin',
                         source_snapshot_sha256=sha(raw[source]), source_snapshot_offset=start-base,
                         expected_entry_mnemonic=mnemonic, sectors=sources,
                         entry_scope=('Existing native RTS selected to stop flow before data; '
                                      'not a boot entry' if mnemonic == 'RTS' else 'Bounded native entry')))
    result = dict(method='Static disk-derived views; no Language Card emulation',
                  composition=composition, views=rows)
    (ROOT/'analysis/rea-memory-inputs.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps([dict(name=r['name'], length=r['length'], entry=r['base_and_entry']) for r in rows]))

def verify(directory):
    manifest = json.loads((ROOT/'analysis/rea-memory-inputs.json').read_text())
    summaries = []
    for row in manifest['views']:
        raw = (ROOT/row['path']).read_bytes()
        if sha(raw) != row['sha256']:
            raise ValueError('prepared source changed')
        records = {k: json.loads((directory/row['name']/(k+'.json')).read_text())
                   for k in ('load', 'bytes', 'entry')}
        result = evidence(records['load'], 'inspect_native_load_image', row['sha256'])
        if (result.get('status') != 'verified' or result.get('format') != 'raw-binary'
                or result.get('architecture') != '6502'
                or result.get('language_id') != '6502:LE:16:default'
                or result.get('base_address') != row['base_and_entry']
                or result.get('file_bytes') != len(raw)
                or not result.get('checks') or not all(c['matched'] for c in result['checks'])):
            raise ValueError('REA load mapping did not verify')
        uninitialized = result['observations']['mappings']
        for name in ('ZERO_PAGE', 'STACK'):
            block = next(b for b in uninitialized if b['block'] == name)
            if block['initialized'] or block['sha256'] is not None:
                raise ValueError('language-defined scratch RAM was treated as observed bytes')
        verify_read(records['bytes'], row['sha256'], int(row['base_and_entry'], 16), raw)
        ins = evidence(records['entry'], 'inspect_native_instruction', row['sha256'])
        if (ins.get('status') != 'decoded' or ins.get('address') != row['base_and_entry']
                or ins.get('mnemonic') != row['expected_entry_mnemonic']
                or not isinstance(ins.get('length'), int) or ins['length'] <= 0
                or bytes.fromhex(ins.get('bytes') or '') != raw[:ins['length']]):
            raise ValueError('REA entry instruction differs')
        summaries.append(dict(name=row['name'], sha256=row['sha256'], complete_bytes_verified=len(raw),
                              load_checks=len(result['checks']), entry_address=ins['address'],
                              entry_mnemonic=ins['mnemonic'],
                              evidence_ids={k:r['evidence_id'] for k,r in records.items()}))
    before, after = (next(r for r in manifest['views'] if r['name'] == n)
                     for n in ('common-before', 'common-after'))
    a, b = ((ROOT/r['path']).read_bytes() for r in (before, after))
    boundary = 0xf248-int(before['base_and_entry'], 16)
    segment = (ROOT/'analysis/regions/archives/SYSTEM.PASCAL-slot-00.bin').read_bytes()
    if a[:boundary] != b[:boundary] or b[boundary:] != segment:
        raise ValueError('overlay differs from archived segment')
    pointer_offset = 0xf267-int(before['base_and_entry'], 16)
    copy_source = int.from_bytes(a[pointer_offset:pointer_offset+2], 'little')
    relocated = next(r for r in manifest['views'] if r['name'] == 'relocated-init')
    bank2 = (ROOT/'analysis/regions/lc-bank2.bin').read_bytes()
    if copy_source != 0xf290 or (ROOT/relocated['path']).read_bytes() != bank2[copy_source-0xd000:copy_source-0xd000+1280]:
        raise ValueError('relocated bytes differ from the common-memory copy source')
    guard_record = json.loads((directory/'common-after/pcode-start.json').read_text())
    guard = evidence(guard_record, 'inspect_native_instruction', after['sha256'])
    if (guard.get('address') != '0xf248' or guard.get('status') not in ('data', 'undecodable')
            or guard.get('mnemonic') is not None):
        raise ValueError('p-code entry was classified as a native instruction')
    report = dict(status='verified_bounded_memory_views', provider='ghidra', views=summaries,
                  overlay_length=len(segment), overlay_changed_byte_values=sum(x != y for x,y in zip(a,b)),
                  relocation=dict(source=hex(copy_source), destination='0x6800', length=1280,
                                  scope='Static source-pointer and payload equality, not executed copy'),
                  rea_pcode_entry=dict(address='0xf248', status=guard['status'],
                                       evidence_id=guard_record['evidence_id'],
                                       scope='Single address; full-range array classification is direct Ghidra evidence'),
                  scope='Actual REA byte reads compared with disk-derived snapshots and direct Ghidra',
                  limitations=['Static imports do not emulate bank hardware or boot execution.',
                               'Low-bank REA probes cover D152..D154, not the entire low bank.',
                               'Persistent array typing is checked in direct Ghidra, not imported into REA.',
                               'Both analysis routes use Ghidra, not independent decoders.'])
    direct = json.loads((ROOT/'analysis/memory-view-validation.json').read_text())
    if (direct['snapshot_sha256'] != sha((ROOT/'analysis/regions/interpreter-ready.bin').read_bytes())
            or not direct['checks']['ghidra_data_classification_matches']
            or not direct['checks']['ghidra_memory_hash_matches']):
        raise ValueError('direct Ghidra view validation is missing or stale')
    report['direct_ghidra'] = dict(report='analysis/memory-view-validation.json',
                                   snapshot_sha256=direct['snapshot_sha256'],
                                   region_classifications=direct['region_classifications'])
    report['assembly_evidence_ids'] = {
        name: json.loads((directory/name/'assembly.json').read_text())['evidence_id']
        for name in ('copy-routine', 'relocated-init')}
    (ROOT/'analysis/rea-memory-crosscheck.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], views=len(summaries),
                          bytes=sum(r['complete_bytes_verified'] for r in summaries))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', type=Path, metavar='EVIDENCE_DIRECTORY')
    args = parser.parse_args()
    verify(args.verify) if args.verify else prepare()
