#!/usr/bin/env python3
"""Analyze only known text procedures' decoded CFG; never an application VM.

No decoder, loader, device, graphics raster or general external calls. Every
instruction must be in source-verified procedures 11,12,45,47,48. Native P9 is
an explicit placement hook with independently checked x advance; P44/P57 stop.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda b: hashlib.sha256(b).hexdigest()


class Boundary(ValueError):
    pass


def signed(n):
    return n if n < 32768 else n - 65536


class TextCFG:
    ARGS = {11: 1, 12: 2, 45: 0, 47: 1, 48: 1}

    def __init__(self, procedures, state):
        self.procedures = procedures
        self.table = {11: state['bottom'], 14: state['left'], 17: state['right'],
                      18: state['y'], 19: state['x'], 366: 0}
        self.memory = bytearray(65536)
        self.stack = []
        self.placements = []
        self.steps = 0
        self.visited = set()

    def word(self, p):
        return int.from_bytes(self.memory[p:p+2], 'little')

    def put(self, p, value):
        self.memory[p:p+2] = (value & 65535).to_bytes(2, 'little')

    def pop(self):
        if not self.stack:
            raise AssertionError('stack underflow')
        return self.stack.pop()

    def call(self, number, depth=0):
        if number == 44:
            raise Boundary('bottom_P44')
        if number == 57:
            raise Boundary('positioning_line_P57')
        if number == 9:
            value = self.pop()
            self.placements.append(dict(character=value & 255, x=self.table[365], y=self.table[364]))
            self.table[365] = (self.table[365] + 6) & 65535
            return
        if number not in self.ARGS or depth > 8:
            raise Boundary('call outside text whitelist')
        rows = self.procedures[number]
        base = 0x7000 + depth * 256
        for index in range(1, self.ARGS[number]+1):
            self.put(base+2*index, self.pop())
        pc = rows['procedure']['entry_address']
        nodes = {r['address']: r for r in rows['instructions']}
        while True:
            self.steps += 1
            if self.steps > 30000:
                raise Boundary('instruction budget')
            row = nodes[pc]
            self.visited.add((number, pc))
            op = row['opcode']; operands = row['operands']; next_pc = row['successors'][0] if row['successors'] else None
            if op < 128:
                self.stack.append(op)
            elif 0xd8 <= op <= 0xe7 or op == 0xca:
                self.stack.append(self.word(base+2*operands['index']))
            elif op == 0xcc:
                self.put(base+2*operands['index'], self.pop())
            elif op == 0xc6:
                self.stack.append(base+2*operands['index'])
            elif op == 0xc7:
                self.stack.append(operands['word'])
            elif op == 0x9d:
                if operands['selector_or_depth'] != 29: raise Boundary('other table')
                self.stack.append(self.table.get(operands['index'], 0))
            elif op == 0xd1:
                if operands['selector_or_depth'] != 29: raise Boundary('other table')
                self.table[operands['index']] = self.pop()
            elif op == 0xaa:
                source = self.pop(); destination = self.pop()
                if source < 256: raise Boundary('character-string assignment not modeled')
                length = self.memory[source]
                if length > operands['count']: raise Boundary('string_error_113')
                self.memory[destination:destination+length+1] = self.memory[source:source+length+1]
            elif op == 0xbe:
                index = self.pop(); address = self.pop(); self.stack.append(self.memory[address+index])
            elif op == 0xbf:
                value = self.pop(); index = self.pop(); address = self.pop(); self.memory[address+index] = value & 255
            elif op in (0x82, 0x95, 0x8f, 0x84, 0x8d, 0xc3, 0xc5, 0xc8):
                b = self.pop(); a = self.pop()
                if op == 0x82: value = a+b
                elif op == 0x95: value = a-b
                elif op == 0x8f: value = a*b
                elif op == 0x84: value = a&b
                elif op == 0x8d: value = a|b
                elif op == 0xc3: value = int(a == b)
                elif op == 0xc5: value = int(signed(a) > signed(b))
                else: value = int(signed(a) <= signed(b))
                self.stack.append(value & 65535)
            elif op == 0x93:
                self.stack.append(self.pop() ^ 65535)
            elif op == 0xa1:
                next_pc = row['successors'][int(bool(self.pop() & 1))]
            elif op == 0xb9:
                pass
            elif op == 0xcf:
                self.call(operands['procedure'], depth+1)
            elif op == 0xad:
                if operands['result_words'] != 0: raise Boundary('unexpected return result')
                return
            else:
                raise Boundary(f'unsupported opcode {op:02x}')
            pc = next_pc

    def run(self, text):
        data = text.encode('ascii')
        self.memory[0x6000:0x6001+len(data)] = bytes([len(data)])+data
        self.stack.append(0x6000)
        boundary = None
        try:
            self.call(48)
        except Boundary as error:
            boundary = str(error)
        return dict(placements=self.placements, x=self.table[19], y=self.table[18],
                    mask=self.table.get(357), mode=self.table.get(367), boundary=boundary)


def build_cases(procedures):
    cases = []
    texts = ['', 'A', ' A', '   A', '|A', '||A', '\\A', '\\\\A', 'A\\B', 'A\\\\B',
             'A B', 'A|B', 'AB CD', 'A  B', 'A|\\B', 'A\\|B', 'ABCDEFGHIJKLMNOPQRST',
             'AB\\CD EF', 'A\nB', '    ', '|||', '\\\\']
    for text in texts:
        for right in (32, 80):
            state = dict(left=0, right=right, bottom=100, x=2, y=15)
            cfg = TextCFG(procedures, state)
            cases.append(dict(text=text, **state, expected=cfg.run(text)))
    for state, text in [
        (dict(left=10,right=50,bottom=100,x=45,y=15),'A'),
        (dict(left=10,right=50,bottom=100,x=44,y=15),'A'),
        (dict(left=0,right=20,bottom=100,x=2,y=15),'ABC'),
        (dict(left=0,right=14,bottom=100,x=2,y=15),'AB'),
        (dict(left=0,right=80,bottom=15,x=2,y=15),'A\\B'),
        (dict(left=0,right=14,bottom=15,x=2,y=15),'AB'),
    ]:
        cases.append(dict(text=text, **state, expected=TextCFG(procedures,state).run(text)))
    return cases


def main():
    from native_archive_disassembly import apply_relocations
    from native_probe import CPU
    from pcode_analysis import mixed_directory, decode_one, Space
    inventory = json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive = next(a for a in inventory['archives'] if a['name']=='SYSTEM.LIBRARY')
    segment = next(s for s in archive['segments'] if s['slot']==1)
    raw = (ROOT/segment['path']).read_bytes()
    if SHA(raw) != segment['sha256']: raise ValueError('source archive changed')
    all_rows = json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-01.json').read_text())
    procedures = {r['procedure']['number']:r for r in all_rows if r['procedure']['number'] in TextCFG.ARGS}
    if set(procedures) != set(TextCFG.ARGS) or any(r['boundaries'] for r in procedures.values()): raise ValueError('missing original decoded text procedure')
    catalogue=json.loads((ROOT/'analysis/opcode-evidence.json').read_text())
    opcodes={r['opcode']:r for r in catalogue['primary']}
    space=Space([(0,raw)])
    for proc in procedures.values():
        for row in proc['instructions']:
            checked=decode_one(space,row['address'],proc['procedure']['trailer_address'],opcodes)
            if any(checked[key] != row[key] for key in ('opcode','length','operands','successors','calls')):
                raise ValueError('decoded source differs')
    normalized = apply_relocations(raw, mixed_directory(raw))
    native = json.loads((ROOT/'analysis/native-archive-disassembly.json').read_text())
    native_segment=next(s for s in native['archive_segments'] if s['segment_number']==22)
    if SHA(normalized)!=native_segment['normalized_sha256']:raise ValueError('normalized native identity differs')
    native_starts={0x4000+r['offset'] for p in native_segment['ghidra']['procedures'] for r in p['instruction_spans']}
    helper_instructions = set()
    for x in range(273):
        cpu = CPU();cpu.memory[0x4000:0x4000+len(raw)] = normalized
        cpu.memory[0x30]=x&255;cpu.memory[0x31]=x>>8;cpu.push_word(0x6fff);cpu.pc=0x5607
        cpu.run({0x7000},max_steps=200)
        if (cpu.memory[0x32],cpu.memory[0x34]) != (x//7,x%7): raise AssertionError('native coordinate helper differs')
        if not cpu.visited<=native_starts:raise AssertionError('coordinate probe left Ghidra instruction boundaries')
        helper_instructions.update(cpu.visited)
    cases = build_cases(procedures)
    output = ROOT/'analysis/local/text-layout';output.mkdir(parents=True,exist_ok=True)
    (output/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    references = []
    for number, proc in sorted(procedures.items()):
        entry=proc['procedure']['entry_address'];sector=segment['sectors'][entry//256]
        references.append(dict(procedure=number,entry=entry,source=dict(side='utility',**sector,byte_in_sector=entry%256),
                               instruction_count=len(proc['instructions'])))
    report = dict(method='Source-bound original decoded CFG evaluation of only text procedures, with explicit native drawing hook; no general VM or raster execution',
                  source_sha256=SHA(raw),native_report_sha256=SHA((ROOT/'analysis/native-archive-disassembly.json').read_bytes()),
                  procedures=references,fixture_count=len(cases),fixtures='analysis/local/text-layout/cases.json',fixtures_sha256=SHA((output/'cases.json').read_bytes()),
                  coordinate_helper=dict(source_offset=0x1607,normalized_entry=0x5607,cases=273,x_range=[0,272],formula='column=x//7; shift=x%7',
                                         method='Bounded original relocated 6502 helper; all native operands relocated using loader-derived tables',
                                         native_addresses=[hex(a) for a in sorted(helper_instructions)]),
                  rules=dict(capacity=80,over_capacity='error113, not truncation',leading_space='ignored unless x > left+2',
                             vertical_bar='always draw space',backslash='new line only if x > left+2',
                             word_pre_wrap='x+6*word_length > right',glyph_pre_and_post_wrap='x > right-5',
                             newline='x=left+2; y+=8; if y>bottom call P44',
                             setup='P11(3): table29[367]=3; table29[357]=63',
                             positioning='P12 stores x at365 and y at364; when table366>0 first calls P57 line routine'),
                  supported_native_contract=dict(text_bytes_max=80,consecutive_nondelimiter_bytes_max=20,positioning_mode366=0,
                                                 bottom_policy='stop before P44',raster_x_range=[0,272],raster_baseline_range=[7,191]),
                  confidence='high for selected CFG and native coordinate arithmetic; named geometry roles inferred from dataflow',
                  limitations=['P9 hook records placement and independently established x+6; it does not execute raster in CFG evaluator.',
                               'P44/P57 are stop boundaries, not silently implemented.',
                               'Scratch local49 overlaps scalar local59 after20bytes; longer words excluded from first native contract.',
                               'ASCII LF is an ordinary character in P48, not a newline.',
                               'Host fixture sampling is not original hardware execution.'])
    (ROOT/'analysis/text-layout-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(fixtures=len(cases),native_coordinate_cases=273,bottom_boundaries=sum(c['expected']['boundary']=='bottom_P44' for c in cases))))


if __name__=='__main__':main()
