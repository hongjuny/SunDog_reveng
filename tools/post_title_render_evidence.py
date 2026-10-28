#!/usr/bin/env python3
"""Source-derived post-title window/text composition; no screenshot app asset."""
import hashlib
import json
from pathlib import Path
from native_probe import CPU
from native_archive_disassembly import apply_relocations
from pcode_analysis import mixed_directory
from glyph_evidence import compose_row, hgr_row
from text_layout_evidence import TextCFG

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda b: hashlib.sha256(b).hexdigest()


class WindowProbe(CPU):
    def step(self):
        op = self.read(self.pc)
        if op == 0xb8:
            self.visited.add(self.pc); self.pc += 1; self.steps += 1; return
        if op == 0x50:
            if self.read(self.pc - 1) != 0xb8: raise ValueError('BVC outside explicit CLV path')
            self.visited.add(self.pc); self.pc += 1; self.steps += 1
            b = self.fetch(); self.pc = (self.pc + (b if b < 128 else b - 256)) & 65535; return
        if op == 0xbe:
            self.visited.add(self.pc); self.pc += 1; self.steps += 1
            self.x = self.nz(self.read(self.fetch_word() + self.y)); return
        super().step()


def rectangle(page, left, right, top, bottom, white=False, mode=None):
    if len(page) != 8192 or not 0 <= left <= right < 280 or not 0 <= top <= bottom < 192:
        raise ValueError('Rectangle outside selected HGR page')
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            p = hgr_row(y) - 0x2000 + x // 7
            bit = 1 << (x % 7)
            pattern = (0xd5 if x // 7 % 2 == 0 else 0xaa) if mode == 10 else 0xff if white else 0x80
            page[p] = (page[p] & ~bit) | (pattern & bit) | 128


def compose(background, font, messages, procedures):
    if len(background) != 8192 or len(font) != 1024: raise ValueError('Invalid selected media size')
    page = bytearray(background)
    rectangle(page, 133, 272, 88, 183, True)
    rectangle(page, 135, 270, 89, 182)
    rectangle(page, 135, 270, 90, 181)
    cfg = TextCFG(procedures, dict(left=135, right=270, bottom=181, x=137, y=100))
    placements = []
    for text in messages:
        result = cfg.run(bytes(text).decode('ascii'))
        if result['boundary']: raise ValueError('Prompt reached unimplemented text boundary')
        placements.extend(result['placements'])
        for g in result['placements']:
            for row in range(8):
                p = hgr_row(g['y'] - 7 + row) - 0x2000 + g['x'] // 7
                page[p], page[p + 1] = compose_row(page[p], page[p + 1],
                    font[g['character'] * 8 + 7 - row], g['x'] % 7, 63, 0)
        cfg.placements = []
    return bytes(page), placements


def draw_character(page, font, character, x, baseline, mask=63):
    for row in range(8):
        p = hgr_row(baseline - 7 + row) - 0x2000 + x // 7
        page[p], page[p+1] = compose_row(page[p], page[p+1],
            font[character * 8 + 7 - row], x % 7, mask, 0)


def compose_choices(background, font, messages, labels, procedures, cursor=None):
    if len(labels)>3 or any(len(label)>15 for label in labels): raise ValueError('Selected button labels differ')
    page = bytearray(compose(background, font, messages, procedures)[0])
    for index, label in enumerate(labels):
        top = 139 + index * 15; bottom = top + 10
        rectangle(page,137,268,top-2,bottom+2,mode=10)
        rectangle(page,139,266,top,bottom)
        x = 139 + (128 - 6 * len(label)) // 2; baseline = 148 + index * 15
        for character in label:
            draw_character(page,font,character,x,baseline);x += 6
    if cursor:
        draw_character(page,font,1,cursor[0]-3,cursor[1]+3,mask=0)
    return bytes(page)


def main():
    inventory = json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    library = next(a for a in inventory['archives'] if a['name'] == 'SYSTEM.LIBRARY')
    segments = {s['segment_number']: s for s in library['segments']}
    raw = {n: (ROOT/segments[n]['path']).read_bytes() for n in (22, 25, 26)}
    for n in raw:
        if SHA(raw[n]) != segments[n]['sha256']: raise ValueError('Source library differs')
    rows26 = json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-05.json').read_text())
    p6 = next(r for r in rows26 if r['procedure']['number'] == 6)
    by_address = {r['address']: r for r in p6['instructions']}
    strings = [r for r in p6['instructions'] if r['opcode'] == 0xa6 and 0x3af <= r['address'] <= 0x463]
    if [r['address'] for r in strings] != [0x3af,0x3c5,0x3dd,0x3f5,0x40f,0x429,0x447,0x463]:
        raise ValueError('Startup prompt string locations differ')
    messages = []
    sources = []
    for row in strings:
        p = row['address']; value = raw[26][p + 2:p + row['length']]
        if SHA(value) != row['operands']['payload_sha256']: raise ValueError('Prompt bytes differ')
        messages.append(list(value)); sector = segments[26]['sectors'][p // 256]
        sources.append(dict(address=p, length=len(value), sha256=SHA(value),
            source=dict(side='utility', **sector, byte_in_sector=p % 256)))
    capture_dir = ROOT/'analysis/local/reference/follow-20261023-120102'
    capture = capture_dir/'after-720-frames-main.bin'; memory = capture.read_bytes()
    manifest = json.loads((capture_dir/'manifest.json').read_text())
    event = next(r for r in manifest['events'] if r['label'] == 'after-720-frames')
    if SHA(memory) != event['main_sha256']: raise ValueError('Prompt reference RAM differs')
    table = int.from_bytes(memory[0xbdd8:0xbdda], 'little')
    def word(index): return int.from_bytes(memory[table+2*index:table+2*index+2], 'little')
    if [word(i) for i in (3,4,5,6,11,12,13,14)] != [95,0,139,0,181,90,270,135]:
        raise ValueError('Observed window bounds differ')
    normalized = apply_relocations(raw[22], mixed_directory(raw[22]), segment_base=0x95be, global_base=table + 2)
    if normalized[0x11c4:0x1346] != memory[0xa782:0xa904]: raise ValueError('Native P7 relocation differs')
    # Independent primitive checks against original native code on synthetic RAM.
    native_checks = []; native_addresses = set()
    for mode, bounds in [(8,(135,270,90,181)), (11,(133,272,88,183)), (10,(137,268,137,151))]:
        c = WindowProbe(memory)
        for offset, value in [(0x2cc,0),(0x2ce,bounds[2]),(0x2d0,bounds[3]),(0x2d2,bounds[1]),(0x2d4,bounds[0])]:
            p = table + 2 + offset; c.memory[p:p+2] = value.to_bytes(2, 'little')
        initial = bytes((i * 13 + 19) & 255 for i in range(8192))
        c.memory[0x2000:0x4000] = initial
        c.push_word(mode); c.push_word(0x6fff); c.pc = 0xa782; c.run({0x7000}, max_steps=100000)
        expected = bytearray(initial); rectangle(expected, *bounds, white=(mode == 11),mode=mode)
        if c.sp != 255 or c.memory[0x2000:0x4000] != expected: raise ValueError('Original native rectangle differs')
        native_addresses.update(c.visited)
        native_checks.append(dict(mode=mode, bounds=list(bounds), instructions=c.steps, matched=True))
    native_report = json.loads((ROOT/'analysis/native-archive-disassembly.json').read_text())
    segment22 = next(s for s in native_report['archive_segments'] if s['segment_number'] == 22)
    defined = {0x95be + r['offset'] for p in segment22['ghidra']['procedures'] for r in p['instruction_spans']}
    if not native_addresses <= defined: raise ValueError('Native rectangle left saved Ghidra boundaries')
    rea = json.loads((ROOT/'analysis/local/rea/post-title-window7.json').read_text())
    if rea['provider']['id'] != 'ghidra' or rea['subject']['digest']['sha256'] != SHA(memory[0xa782:0xa904]):
        raise ValueError('Fresh REA window primitive identity differs')
    rea_starts = {int(line.split(':',1)[0],16) for line in rea['normalized_result'].splitlines() if line.startswith('0x')}
    if not {a for a in native_addresses if 0xa782 <= a < 0xa904} <= rea_starts:
        raise ValueError('Window probe left actual REA P7 boundaries')
    font = (ROOT/'analysis/local/native-assets/sundog-font.bin').read_bytes()
    font_proof = json.loads((ROOT/'analysis/native-font-asset.json').read_text())
    if SHA(font) != font_proof['sha256']: raise ValueError('Font asset differs')
    title_path = ROOT/'analysis/local/reference/follow-20261023-115323/after-720-frames-main.bin'
    title_memory = title_path.read_bytes()
    background = title_memory[0x2000:0x4000]
    if SHA(background) != '7e4f8f739f8b9d40a411f462036f740e1b518ce547184d03c5f4c746d0cc317d':
        raise ValueError('Original completed logo reference differs')
    rows22 = json.loads((ROOT/'analysis/local/pcode/SYSTEM.LIBRARY-slot-01.json').read_text())
    procedures = {r['procedure']['number']: r for r in rows22 if r['procedure']['number'] in TextCFG.ARGS}
    page, placements = compose(background, font, messages, procedures)
    if page != memory[0x2000:0x4000]: raise ValueError('Prompt composite differs from complete original frame')
    def inline(address):
        row = by_address[address]
        if row['opcode'] != 0xa6: raise ValueError('Expected original inline string')
        value=raw[26][address+2:address+row['length']]
        if SHA(value)!=row['operands']['payload_sha256']:raise ValueError('Inline menu source changed')
        return list(value)
    labels = [inline(a) for a in (0x627,0x645,0x665)]
    menu_capture=ROOT/'analysis/local/reference/advance-20261023-122315/advanced-main.bin'
    menu_memory=menu_capture.read_bytes()
    menu_manifest=json.loads((menu_capture.parent/'manifest.json').read_text())
    menu_event=next(r for r in menu_manifest['events'] if r['label']=='advanced')
    if SHA(menu_memory)!=menu_event['main_sha256']:raise ValueError('Menu RAM differs')
    menu_table=int.from_bytes(menu_memory[0xbdd8:0xbdda],'little')
    name_address=menu_table+2*255
    name=list(menu_memory[name_address+1:name_address+1+menu_memory[name_address]])
    menu_messages=[inline(0x50b),name,inline(0x59b),inline(0x5c1),inline(0x5cf),inline(0x5e1)]
    button_table=int.from_bytes(menu_memory[0xbdda:0xbddc],'little')
    button_records=[]
    for i,identity in enumerate((2,1,3)):
        record=button_table+2*(67+i*5)
        values=[int.from_bytes(menu_memory[record+2*k:record+2*k+2],'little') for k in range(5)]
        if values[0]&255!=identity or values[1:] != [59+15*i,49+15*i,131,4]:
            raise ValueError('Retained button records differ from original P6/P3 geometry')
        button_records.append(dict(id=identity,word_index=67+i*5,relative_bottom=values[1],relative_top=values[2],
            relative_right=values[3],relative_left=values[4],button_flag=(values[0]>>8)&1,label_index=(values[0]>>9)&15))
    menu_page=compose_choices(background,font,menu_messages,labels,procedures,cursor=(199,137))
    if menu_page!=menu_memory[0x2000:0x4000]:raise ValueError('Startup menu differs from complete original HGR')
    private = ROOT/'analysis/local/post-title'; private.mkdir(parents=True, exist_ok=True)
    (private/'render-cases.json').write_text(json.dumps(dict(background=list(background), font=list(font), messages=messages, expected=list(page)))+'\n')
    (private/'menu-render-case.json').write_text(json.dumps(dict(background=list(background),font=list(font),
        messages=menu_messages,labels=labels,cursor=[199,137],expected=list(menu_page)))+'\n')
    assets = ROOT/'analysis/local/native-assets'; assets.mkdir(parents=True,exist_ok=True)
    (assets/'startup-text.json').write_text(json.dumps(dict(gate_messages=messages,
        choice_labels=labels, menu_fragments={hex(a):inline(a) for a in (0x50b,0x59b,0x5b5,0x5c1,0x5cf,0x5e1)},
        font_sha256=SHA(font), prompt_page_sha256=SHA(page)), indent=2)+'\n')
    report = dict(method='Original P51/P44 geometry, bounded native P7 rectangle checks and P48 CFG placements, compared with full retained prompt HGR',
        source_libraries={str(n): SHA(raw[n]) for n in raw}, messages=sources,
        window=dict(outer=[133,272,88,183], inner=[135,270,89,182], text=[135,270,90,181], cursor=[137,100], right=270),
        template_bounds=[word(i) for i in (6,5,4,3)], native_rectangle_checks=native_checks,
        rea_evidence_id=rea['evidence_id'], rea_slice_sha256=rea['subject']['digest']['sha256'],
        native_instruction_addresses=len(native_addresses), placements=len(placements),
        font_proof='analysis/native-font-asset.json', font_sha256=SHA(font),
        full_page_equal=True, final_page_sha256=SHA(page), reference_capture=str(capture.relative_to(ROOT)),
        reference_memory_sha256=SHA(memory), original_text_asset='analysis/local/native-assets/startup-text.json',
        confidence='High for selected original startup prompt window and message path',
        menu=dict(full_page_equal=True,page_sha256=SHA(menu_page),reference=str(menu_capture.relative_to(ROOT)),
            reference_memory_sha256=SHA(menu_memory),cursor=dict(character=1,raw=[199,137],glyph=[196,140],mode=1,mask=0),
            label_sources=[dict(address=a,length=len(inline(a)),sha256=SHA(bytes(inline(a))),
                source=dict(side='utility',**segments[26]['sectors'][a//256],byte_in_sector=a%256)) for a in (0x627,0x645,0x665)],
            renderer_sources=[dict(segment=25,procedure=n,entry=a,
                source=dict(side='utility',**segments[25]['sectors'][a//256],byte_in_sector=a%256))
                for n,a in ((3,0x14),(6,0x17a),(9,0xc6),(7,0x210))],
            buttons=[dict(index=i,left=139,right=266,top=139+15*i,bottom=149+15*i,
                hit_top=137+15*i,hit_bottom=151+15*i,label_baseline=148+15*i) for i in range(3)],
            mode10_pattern=dict(even_byte=213,odd_byte=170),
            original_records=button_records,
            greeting='Selected retained healthy continuation branch; player name is fixture input, not an app asset copied from RAM'),
        limitations=['Original window-opening/sound timing is not reconstructed.',
                    'The current contract selects the original P51(40,24) window; it is not a general game window engine.',
                    'Reference RAM is corroboration only; app inputs are original font/messages and rewritten pixel operations.'])
    (ROOT/'analysis/post-title-render.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(messages=len(messages), placements=len(placements), full_page_equal=True, sha256=SHA(page))))

if __name__ == '__main__': main()
