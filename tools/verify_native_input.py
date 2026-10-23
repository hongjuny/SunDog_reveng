#!/usr/bin/env python3
"""Compare pure Swift input state against actual original native probe results."""
import hashlib
import itertools
import json
import platform
from pathlib import Path
import subprocess

from native_probe import CPU
from pcode_analysis import mixed_directory

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    output = ROOT / 'analysis/local/native-input'
    output.mkdir(parents=True, exist_ok=True)
    report = json.loads((ROOT / 'analysis/button-input-evidence.json').read_text())
    memory = (ROOT / report['capture']).read_bytes()
    if SHA(memory) != report['capture_main_sha256']:
        raise ValueError('Retained RAM digest differs')
    archive = (ROOT / 'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes()
    if SHA(archive) != report['source_archive_sha256']:
        raise ValueError('Source archive digest differs')
    proc = next(p for p in mixed_directory(archive) if p['number'] == 2)
    entry = report['captured_entry']
    end = entry + proc['attribute_address'] - proc['entry_address']
    code = memory[entry:end]
    if SHA(code) != report['captured_function_sha256']:
        raise ValueError('Native function digest differs')
    evidence = json.loads((ROOT / 'analysis/local/rea/input2-captured.json').read_text())
    hook = json.loads((ROOT / 'analysis/local/rea/input-hook-full.json').read_text())
    if evidence['subject']['digest']['sha256'] != SHA(code):
        raise ValueError('REA function digest differs')
    hook_address = report['installed_hook']['address']
    if hook['subject']['digest']['sha256'] != SHA(memory[hook_address:0xa2b4]):
        raise ValueError('REA hook digest differs')
    defined = {int(line.split(':', 1)[0], 16) for e in (evidence, hook)
               for line in e['normalized_result'].splitlines() if line.startswith('0x')}
    pending_base = report['memory_fields']['pending']
    history_base = report['memory_fields']['previous']
    filters = []
    for channel, level, sample, pending, previous, carry in itertools.product(
            range(4), (False, True), (0, 0x7f, 0x80, 0xff), (0, 0x7f, 0x80, 0xff), (0, 1), (0, 1)):
        selector = channel | (4 if level else 0)
        c = CPU(); c.memory[entry:end] = code
        c.memory[report['memory_fields']['installed']] = 1
        for value in (selector, 0, 0): c.push_word(value)
        c.push_word(0x3fff); c.pc = entry; c.c = carry
        c.memory[0xc061 + channel] = sample
        c.memory[pending_base + channel] = pending
        c.memory[history_base + channel] = previous
        c.run({0x4000}, max_steps=500)
        result = c.pop_word()
        if not c.visited <= defined or c.sp != 255 or result not in (0, 1):
            raise AssertionError('Native filter left verified instructions or result contract')
        filters.append(dict(selector=selector, sample=sample, pending=pending, previous=bool(previous),
                            result=bool(result), remaining=c.read(pending_base + channel),
                            history=bool(c.read(history_base + channel))))
    latches = []
    for first, second, p0, p1 in itertools.product((0, 0x7f, 0x80, 0xff), repeat=4):
        c = CPU(); c.memory[entry:end] = code
        c.memory[0xc061] = first; c.memory[0xc062] = second
        c.memory[pending_base:pending_base + 4] = bytes([p0, p1, 17, 19])
        c.pc = 0xa29d; c.run({0xa2af}, max_steps=10)
        if not c.visited <= defined:
            raise AssertionError('Native latch left verified instructions')
        latches.append(dict(first=first, second=second, pending=[p0, p1, 17, 19],
                            expected=list(c.memory[pending_base:pending_base + 4])))
    cases = output / 'cases.json'
    cases.write_text(json.dumps(dict(filters=filters, latches=latches), indent=2) + '\n')
    compiler = subprocess.check_output(['xcrun', '--find', 'swiftc'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    sources = [ROOT / 'native/SunDogLogic/ButtonInput.swift', ROOT / 'tests/native/VerifyButtonInput.swift']
    binary = output / 'verify-button-input'
    subprocess.run([compiler, '-swift-version', '6', '-O', '-parse-as-library', '-sdk', sdk,
                    '-target', platform.machine() + '-apple-macosx14.0', '-module-cache-path', str(output / 'module-cache'),
                    *map(str, sources), '-o', str(binary)], check=True)
    result = json.loads(subprocess.check_output([str(binary), str(cases)], text=True))
    result.update(method='Swift state transitions versus bounded original native instructions; raw MMIO samples supplied as test RAM',
                  original_evidence='analysis/button-input-evidence.json', rea_evidence_ids=report['rea_evidence_ids'],
                  source_files={str(p.relative_to(ROOT)): SHA(p.read_bytes()) for p in sources},
                  cases_sha256=SHA(cases.read_bytes()),
                  limitations=['No physical device timing or macOS mapping inferred.',
                               'Selector 8 emits a restore signal; native product does not patch p-code dispatch.',
                               'Only verified selectors 0 through 8 and boolean edge history are supported.'])
    (ROOT / 'analysis/native-input-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
