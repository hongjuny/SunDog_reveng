#!/usr/bin/env python3
"""Compare the Swift glyph rewrite with 420 bounded original-native fixtures.

Original bytecode is used solely in the offline analysis probe. The application
contains the reconstructed expression, not this probe or the original bytes.
Full-page synthetic fixtures and the verification report remain local.
"""
import hashlib
import json
import platform
import subprocess
from pathlib import Path

from glyph_evidence import hgr_row
from native_probe import CPU
from pcode_analysis import mixed_directory

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'analysis/local/native-glyph'
    output.mkdir(parents=True, exist_ok=True)
    raw = (ROOT / 'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes()
    proc = next(p for p in mixed_directory(raw) if p['number'] == 9)
    body = raw[proc['entry_address']:proc['attribute_address']]
    proof = json.loads((ROOT / 'analysis/glyph-compositor-evidence.json').read_text())
    rea = json.loads((ROOT / 'analysis/local/rea/library22-glyph-raw.json').read_text())
    digest = hashlib.sha256(body).hexdigest()
    if (proc['entry_address'] != 0x1376 or proc['kind'] != 'native-6502' or
            hashlib.sha256(raw).hexdigest() != proof['source_sha256'] or
            digest != proof['native_slice_sha256'] or
            digest != rea['subject']['digest']['sha256']):
        raise ValueError('Original glyph body or retained REA identity differs')
    defined = {int(line.split(':', 1)[0], 16) for line in rea['normalized_result'].splitlines()
               if line.startswith('0x')}
    glyph = bytes([0x15, 0x2a, 0x01, 0, 0x7f, 0x40, 0x03, 0x10])
    fixtures = []
    for shift in range(7):
        for mask_low in (0, 0x3f, 0x7f, 0x55, 0xff):
            for mask_high in (0, 0x0f, 0x7f):
                for baseline in (7, 31, 127, 191):
                    cpu = CPU()
                    cpu.memory[0x1376:0x1376 + len(body)] = body
                    initial = bytes(0x80 | ((i * 13 + 19) & 0x7f) for i in range(8192))
                    cpu.memory[0x2000:0x4000] = initial

                    def word(address, value):
                        cpu.memory[address:address + 2] = value.to_bytes(2, 'little')

                    word(0x2c6, 0x5000)
                    word(0x2d8, 35 + shift)
                    cpu.memory[0x2c8] = mask_low
                    cpu.memory[0x2dc] = 0
                    cpu.memory[0x2c] = baseline
                    cpu.memory[0x32] = 5
                    cpu.memory[0x34] = shift
                    cpu.memory[4] = mask_low
                    cpu.memory[5] = mask_high
                    cpu.memory[0x12] = 65
                    cpu.memory[0x13] = 0
                    cpu.memory[0x5000 + 65 * 8:0x5000 + 66 * 8] = glyph
                    for y in range(192):
                        address = hgr_row(y)
                        cpu.memory[0xdc0 + y] = address & 255
                        cpu.memory[0xe80 + y] = address >> 8
                    cpu.pc = 0x13d0
                    cpu.run({0x14bf}, max_steps=5000)
                    if not cpu.visited <= defined:
                        raise ValueError('Native probe left retained REA instruction boundaries')
                    fixtures.append(dict(glyph=list(glyph), x=35 + shift, baseline=baseline,
                                         maskLow=mask_low, maskHigh=mask_high,
                                         initialPage=list(initial), expectedPage=list(cpu.memory[0x2000:0x4000]),
                                         nextX=cpu.word(0x2d8)))
    cases = output / 'cases.json'
    cases.write_text(json.dumps(fixtures, separators=(',', ':')) + '\n')
    compiler = subprocess.check_output(['xcrun', '--find', 'swiftc'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    sources = [ROOT / 'native/SunDogLogic/GlyphCompositor.swift', ROOT / 'tests/native/VerifyGlyphCompositor.swift']
    binary = output / 'verify-glyph'
    subprocess.run([compiler, '-swift-version', '6', '-O', '-parse-as-library', '-sdk', sdk,
                    '-target', platform.machine() + '-apple-macosx14.0', '-module-cache-path', str(output / 'module-cache'),
                    *map(str, sources), '-o', str(binary)], check=True)
    report = json.loads(subprocess.check_output([str(binary), str(cases)], text=True))
    report.update(method='Compiled Swift rewrite versus full HGR pages produced by bounded original native P9 body',
                  source_files={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  original_archive_sha256=proof['source_sha256'], native_slice_sha256=digest,
                  retained_rea_evidence_id=rea['evidence_id'], cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
                  limitations=proof['not_checked'])
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'analysis/native-glyph-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
