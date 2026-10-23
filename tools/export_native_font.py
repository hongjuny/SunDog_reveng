#!/usr/bin/env python3
"""Export only the source-verified 128-slot font prefix for local native rendering.

Original glyph bytes stay in ignored analysis/local/native-assets/. The complete
256-character addressable bank size and original font loader are not asserted.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()
DOS_TO_PHYSICAL = (0, 13, 11, 9, 7, 5, 3, 1, 14, 12, 10, 8, 6, 4, 2, 15)


def main():
    capture = ROOT / 'analysis/local/reference/advance-20261023-122315/advanced-main.bin'
    memory = capture.read_bytes()
    manifest = json.loads((capture.parent / 'manifest.json').read_text())
    expected = next(r['main_sha256'] for r in manifest['events'] if r['label'] == 'advanced')
    if len(memory) != 65536 or SHA(memory) != expected:
        raise ValueError('retained memory identity differs')
    mapping = json.loads((ROOT / 'analysis/graphics-call-chain.json').read_text())['captured_mapping']
    if SHA(memory) != mapping['memory_sha256']:
        raise ValueError('graphics mapping identity differs')
    evidence = json.loads((ROOT / 'analysis/local/rea/library22-glyph-captured.json').read_text())
    text = evidence['normalized_result'].lower()
    native_start = mapping['native9_address']
    native_bytes = memory[native_start:native_start + mapping['native_slice_length']]
    if SHA(native_bytes) != evidence['subject']['digest']['sha256']:
        raise ValueError('REA source digest differs from captured procedure')
    if evidence['provider']['id'] != 'ghidra' or '0xa9a9: lda 0xb082' not in text or '0xa9b0: lda 0xb083' not in text:
        raise ValueError('captured glyph pointer reads differ')
    pointer_cell = mapping['data29_base'] + 0x2c6
    if pointer_cell != 0xb082 or int.from_bytes(memory[pointer_cell:pointer_cell + 2], 'little') != 0x1000:
        raise ValueError('font pointer differs from retained baseline')
    disk = (ROOT / 'extracted/utility.do').read_bytes()
    if len(disk) != 143360:
        raise ValueError('unexpected logical disk size')
    sector_inventory = json.loads((ROOT / 'analysis/utility-sectors.json').read_text())
    records = []
    chunks = []
    for index, sector in enumerate((9, 8, 7, 6)):
        offset = sector * 256
        data = disk[offset:offset + 256]
        row = next(r for r in sector_inventory if r['track'] == 0 and r['sector'] == sector)
        address = 0x1000 + index * 256
        if row['status'] != 'readable' or SHA(data) != row['sha256'] or data != memory[address:address + 256]:
            raise ValueError('font bytes do not match verified disk sectors and retained RAM')
        chunks.append(data)
        records.append(dict(side='utility', track=0, sector=sector, physical_sector=DOS_TO_PHYSICAL[sector],
                            image_offset=offset, memory_address=address, length=256, sha256=SHA(data)))
    font = b''.join(chunks)
    output = ROOT / 'analysis/local/native-assets/sundog-font.bin'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(font)
    report = dict(method='Actual REA/Ghidra pointer reads, retained RAM binding, and exact verified disk-sector correspondence',
                  artifact=str(output.relative_to(ROOT)), sha256=SHA(font), length=len(font),
                  glyph_slots=128, character_range=[0, 127], bytes_per_glyph=8,
                  storage='bottom row first; normal compositor masks each row with 0x7f',
                  font_pointer_cell=pointer_cell, captured_font_base=0x1000,
                  capture=str(capture.relative_to(ROOT)), capture_sha256=SHA(memory),
                  rea_evidence_id=evidence['evidence_id'], sectors=records,
                  character_mapping=dict(method='String byte passed unchanged to P47, then native P9 uses low byte times eight',
                                         pcode_addresses=[0x09b7, 0x09b8, 0x08bf, 0x08c0],
                                         native_multiply_range=[0xa99f, 0xa9a8],
                                         note='Selected 7-bit character slots; no Unicode or alternate character remapping inferred'),
                  confidence='high for selected bytes and retained pointer binding',
                  limitations=['This is a verified 128-slot prefix, not proof that the full font bank ends at 0x1400.',
                               'Font loading and later pointer swaps are not reconstructed.',
                               'Capture is existing Utility-menu evidence, not a new game execution.',
                               'No original glyph bytes are included in the public report.'])
    (ROOT / 'analysis/native-font-asset.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(artifact=report['artifact'], length=len(font), sha256=SHA(font))))


if __name__ == '__main__':
    main()
