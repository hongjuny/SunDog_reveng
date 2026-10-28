#!/usr/bin/env python3
"""Source-guarded pointer analysis; isolated binary-mode probes, no device emulation."""
import hashlib
import json
from pathlib import Path
from native_probe import CPU

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = '7d52f0e6959d0a8b9ac3f08bc78ced7e7af44ed87a00d80d4d82025ab7735f49'


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def correct_counters(c064, c065):
    """Counter values, not analog voltages or host-device coordinates."""
    if not 0 <= c064 <= 255 or not 0 <= c065 <= 255:
        raise ValueError('expected two 8-bit counters')
    half = c065 // 2
    return clamp(c064 - 3, 0, 139), clamp(half + (half + 1) // 2 - 5, 0, 95)


def axis_setup(lower, upper, nominal):
    span = upper - lower
    scale = 2 if span > nominal else 1
    return scale, lower - ((scale * nominal - span) >> 1)


def pointer_position(raw_x, raw_y, rectangle):
    """Rectangle is left,right,top,bottom; source rectangle words use reverse order."""
    left, right, top, bottom = rectangle
    if right - left < 8 or bottom - top < 8:
        raise ValueError('inverted inset pointer bounds')
    xmin, xmax, ymin, ymax = left + 3, right - 5, top + 5, bottom - 3
    sx, ox = axis_setup(xmin, xmax, 140)
    sy, oy = axis_setup(ymin, ymax, 96)
    return clamp(sx * raw_x + ox, xmin, xmax), clamp(sy * raw_y + oy, ymin, ymax)


def cursor_operations(old, new):
    return [] if old == new else [('xor', old), ('store', new), ('xor', new)]


class ProbeCPU(CPU):
    """Adds only BIT zp and PHP/PLP needed by the isolated selected bodies."""
    def step(self):
        op = self.read(self.pc)
        if op not in (0x24, 0x08, 0x28):
            return super().step()
        self.visited.add(self.pc)
        self.steps += 1
        self.pc += 1
        if op == 0x24:
            value = self.read(self.fetch())
            self.z = int(not (self.a & value))
            self.n = value >> 7
        elif op == 0x08:
            self.push(0x30 | self.c | (self.z << 1) | (self.n << 7))
        else:
            value = self.pop()
            self.c, self.z, self.n = value & 1, (value >> 1) & 1, value >> 7


def native_shift(archive, number, value, count):
    start, end = {30: (0xFA8, 0xFD4), 31: (0xF6C, 0xF9C)}[number]
    c = ProbeCPU()
    c.memory[start:end] = archive[start:end]
    for word in (value & 65535, count, 0, 0):
        c.push_word(word)
    c.push_word(0x3FFF)
    c.pc = start
    c.run({0x4000}, max_steps=3000)
    result = c.pop_word()
    if c.sp != 255:
        raise AssertionError('shift stack not balanced')
    return result


class PulseCPU(ProbeCPU):
    """Declared finite high-read counts; this is not analog paddle timing."""
    def __init__(self, pulse_counts):
        super().__init__()
        self.pulse_counts = dict(zip((0xC064, 0xC065), pulse_counts))
        self.read_counts = {0xC064: 0, 0xC065: 0}
        self.strobes = 0

    def read(self, address):
        if address == 0xC070:
            self.strobes += 1
            return 0
        if address in self.read_counts:
            index = self.read_counts[address]
            self.read_counts[address] += 1
            return 0x80 if index < self.pulse_counts[address] else 0
        return super().read(address)


def run():
    archive = (ROOT / 'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes()
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA:
        raise ValueError('original archive identity differs')
    rea = json.loads((ROOT / 'analysis/local/rea/joystick-native5.json').read_text())
    code = archive[0xDAA:0xE20]
    # The one absolute JMP operand is a relocation cell in the stored body.
    if code[0x2C:0x2F] != bytes.fromhex('4c1d00'):
        raise ValueError('original P5 loop relocation cell differs')
    captured_code = bytearray(code)
    captured_code[0x2D:0x2F] = (0xA385).to_bytes(2, 'little')
    if hashlib.sha256(captured_code).hexdigest() != rea['subject']['digest']['sha256']:
        raise ValueError('REA input does not match original native P5')
    if rea['provider']['id'] != 'ghidra':
        raise ValueError('expected actual Ghidra provider evidence')
    defined = {int(line.split(':', 1)[0], 16) for line in rea['normalized_result'].splitlines() if line.startswith('0x')}
    c = ProbeCPU()
    c.memory[0xDAA:0xE20] = code
    c.memory[2:4] = (0x7000).to_bytes(2, 'little')
    visited = set()
    for c064 in range(256):
        for c065 in range(256):
            c.pc, c.sp, c.x, c.y = 0xDE0, 255, c065, c064
            c.c = (c064 ^ c065) & 1
            c.visited.clear()
            c.writes.clear()
            c.push_word(0x3FFF)
            c.run({0x4000}, max_steps=80)
            got = c.word(0x7000), c.word(0x7002)
            if got != correct_counters(c064, c065) or c.sp != 255:
                raise AssertionError((c064, c065, got))
            visited.update(c.visited)
    if not {pc + 0x95BE for pc in visited} <= defined:
        raise AssertionError('tail left fresh REA-defined instruction starts')
    sampling_cases = 0
    for px in (0, 1, 2, 3, 4, 7, 127, 255, 256, 257):
        for py in (0, 1, 2, 3, 4, 7, 127, 255, 256, 257):
            pulse = PulseCPU((px, py))
            pulse.memory[0xA368:0xA3DE] = captured_code
            pulse.push_word(0x7000)
            pulse.push_word(0x3FFF)
            pulse.pc = 0xA368
            pulse.run({0x4000}, max_steps=10000)
            if (pulse.word(0x7000), pulse.word(0x7002)) != correct_counters(px & 255, py & 255) or pulse.sp != 255 or pulse.strobes != 1:
                raise AssertionError(('declared pulse sequence', px, py))
            if not pulse.visited <= defined:
                raise AssertionError('sampling probe left fresh REA instruction starts')
            sampling_cases += 1
    shift_cases = 0
    for number in (30, 31):
        for value in (0, 1, 2, 3, 5, 13, 127, 140, 183, 192, 271, 280, 32767, 32768, 65533, 65535):
            for count in range(18):
                signed = value if value < 32768 else value - 65536
                expected = (value << count) & 65535 if number == 30 else (signed >> count) & 65535
                if native_shift(archive, number, value, count) != expected:
                    raise AssertionError(('native shift', number, value, count))
                shift_cases += 1
    listing = json.loads((ROOT / 'analysis/local/pcode/SYSTEM.LIBRARY-slot-01.json').read_text())
    inventory = json.loads((ROOT / 'analysis/archive-inventory.json').read_text())
    segment = next(s for a in inventory['archives'] if a['name'] == 'SYSTEM.LIBRARY' for s in a['segments'] if s.get('segment_number') == 22)
    procedures = []
    for number, role in [(5, 'paddle timer sampling and counter correction'), (30, '16-bit left shift'), (31, 'signed arithmetic right shift'), (37, 'signed coordinate clamp'), (41, 'XOR pointer glyph'), (42, 'pointer bounds and initial draw'), (43, 'sample and redraw only changed pointer'), (61, 'scale offset clamp and output'), (62, 'axis scale and centering setup')]:
        row = next(p for p in listing if p['procedure']['number'] == number)
        p = row['procedure']
        for instruction in row['instructions']:
            if archive[instruction['address']] != instruction['opcode']:
                raise ValueError('cached p-code listing differs from original instruction opcode')
        source = dict(segment['sectors'][p['entry_address'] // 256])
        source.update(side='utility', byte_in_sector=p['entry_address'] % 256)
        procedures.append(dict(number=number, role=role, segment_offset=p['entry_address'], captured_address=0x95BE + p['entry_address'], source=source, body_to_attribute_sha256=hashlib.sha256(archive[p['entry_address']:p['attribute_address']]).hexdigest(), confidence='high; source control-flow reconstruction, native transformations independently replayed'))
    report = dict(schema_version=1, archive_sha256=ARCHIVE_SHA, segment=22,
        rea=dict(evidence_id=rea['evidence_id'], provider=rea['provider'], subject_sha256=rea['subject']['digest']['sha256'], original_body_sha256=hashlib.sha256(code).hexdigest(), captured_base=0x95BE, source_body=[0xDAA, 0xE20], relocation=dict(source_operand_offset=0xDD7, stored_word=0x1D, captured_word=0xA385)),
        validation=dict(counter_tail_cases=65536, declared_pulse_sequence_cases=sampling_cases, shift_cases=shift_cases, rea_defined_tail_instruction_starts=len(visited), binary_mode=True, physical_device_execution=False),
        native_correction=dict(x='clamp(c064_counter-3,0,139)', y='q=c065_counter//2; clamp(q+(q+1)//2-5,0,95)', carry='Second LSR replaces CLC carry before ADC; rounding term is ceil(q/2).'),
        axis_mapping=dict(x_counter_register='Y', y_counter_register='X', x_mmio='C064', y_mmio='C065', timer_strobe='C070', nominal_spans=[140,96], inset_bounds=['left+3','right-5','top+5','bottom-3'], scale='2 iff inset span > nominal; otherwise 1', offset='lower - arithmetic_shift_right(scale*nominal - inset_span,1)'),
        examples=[dict(rectangle=[0,279,0,191], x_scale_offset=axis_setup(3,274,140), y_scale_offset=axis_setup(5,188,96)),dict(rectangle=[135,270,90,181], x_scale_offset=axis_setup(138,265,140), y_scale_offset=axis_setup(95,178,96))],
        redraw=dict(procedure=43, changed=['P41 XOR erase old','store new coordinates','P41 XOR draw new'], unchanged=[], glyph_table_word=374, glyph_position=['x-3','y+3'], mode='P41 sets P11(1), draws via native P9, then P11(0)'),
        procedures=procedures,
        uncertainties=['No real joystick acquisition or electrical timing was measured.', 'Eight-bit counters wrap; native loop has no observed timeout. Stuck-high input can loop indefinitely.', 'No center deadzone or velocity accumulation in this chain; other configuration paths are not excluded.', 'P-code pointer procedures were reconstructed statically, not executed end to end in a live original gameplay session.'])
    path = ROOT / 'analysis/joystick-pointer.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = run()
    print(json.dumps(report['validation'], indent=2))
