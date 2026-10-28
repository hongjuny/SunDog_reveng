#!/usr/bin/env python3
"""Source-bound initial title gate and startup choice contracts; no runtime VM."""
import hashlib
import json
from pathlib import Path
from archive_evidence import directory
from boot_regions import pages
from native_probe import CPU

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def signed16(value):
    return ((value + 32768) & 65535) - 32768


def begin_gate_step(remaining, first_edge, second_edge):
    """One original loop's decrement/predicate; iterations are not seconds."""
    remaining = signed16(remaining - 1)
    return remaining, bool(first_edge or second_edge or remaining <= 0)


def menu_contract(play_mode, slot_index, state_word, damaged=False):
    state = (state_word >> 8) & 15
    blocked = bool(state in (12, 13) or damaged or slot_index >= 4)
    return dict(mode=bool(play_mode), state=state, play_allowed=not blocked,
                choices=([2] if not blocked else []) + [1, 3],
                reboot_choice=1 if play_mode else 2,
                reboot_template_block=81 if play_mode else 80)


def choice_route(play_mode, choice, play_allowed=True):
    if choice not in (1, 2, 3) or choice == 2 and not play_allowed:
        raise ValueError('choice is not in the presented original menu')
    if choice == 3:
        return dict(action='replace_directory_then_boot_slot6', target='demo', template_block=82,
                    set_skip_title_marker=False)
    if choice == (1 if play_mode else 2):
        return dict(action='replace_directory_then_boot_slot6', target='utility' if play_mode else 'play',
                    template_block=81 if play_mode else 80, set_skip_title_marker=True)
    return dict(action='return_to_caller', target='play' if play_mode else 'utility')


def save_checksum(data):
    if len(data) != 5120:raise ValueError('selected game checksum requires ten512-byte blocks')
    return ((sum(data[1::2]) & 255) << 8) | (sum(data[::2]) & 255)


def cold_utility_profile(disk, library_raw):
    metadata, metadata_sectors=pages(83,2,disk)
    slot=metadata[1]
    if slot>=4:raise ValueError('selected original cold Utility fixture has no readable game record')
    relative=10*slot+24;absolute=relative+3
    game,sectors=pages(absolute,20,disk)
    catalog,catalog_sectors=pages(26,2,disk)
    expected=int.from_bytes(catalog[30+64*slot:32+64*slot],'little')
    actual=save_checksum(game)
    # Original native26P3 adds low/high byte columns independently. Run its body
    # on the actual disk data with a declared RAM/stack fixture, no devices.
    cpu=CPU();code=library_raw[0x7ba:0x7f4]
    cpu.memory[0x4000:0x4000+len(code)]=code;cpu.memory[0x6000:0x7400]=game
    for value in (0x6000,10,0,0):cpu.push_word(value)
    cpu.push_word(0x2fff);cpu.pc=0x4000;cpu.run({0x3000},max_steps=60000)
    if cpu.pop_word()!=actual or cpu.sp!=255:raise ValueError('Original native checksum differs')
    natives=json.loads((ROOT/'analysis/native-archive-disassembly.json').read_text())
    segment=next(s for s in natives['archive_segments'] if s['segment_number']==26)
    procedure=next(p for p in segment['ghidra']['procedures'] if p['number']==3)
    defined={r['offset'] for r in procedure['instruction_spans']}
    if not {address-0x4000+0x7ba for address in cpu.visited}<=defined:
        raise ValueError('Checksum probe left persisted Ghidra instruction boundaries')
    def word(index):return int.from_bytes(game[(index-36)*2:(index-36)*2+2],'little')
    nameoffset=(255-36)*2;namebytes=game[nameoffset+1:nameoffset+1+game[nameoffset]]
    if not 0<game[nameoffset]<=15:raise ValueError('Unsupported original selected name length')
    name=namebytes.decode('ascii')
    state=word(45);can_start=(word(43)&0x3fff)==0 and word(42)>>8==0 and word(42)&0x3f==0
    profile=dict(mode='utility',name=name,skipIntro=metadata[0]!=0,slotIndex=slot,
                 stateWord=state,word42=word(42),word43=word(43),damaged=actual!=expected,
                 state=(state>>8)&15,playAllowed=((state>>8)&15) not in (12,13) and actual==expected,
                 newGame=can_start,computedChecksum=actual,expectedChecksum=expected,
                 sourceGameBlock=absolute,sourceGameSHA256=SHA(game),
                 sourceMetadataSHA256=SHA(metadata),
                 scope='Supplied immutable Utility cold-start profile; not a generic/newly created game')
    proof=dict(source_side='utility',metadata_block=83,metadata_sha256=SHA(metadata),metadata_sectors=metadata_sectors,
               selected_slot=slot,game_relative_block=relative,game_loader_block=absolute,game_blocks=10,
               game_sha256=SHA(game),game_sectors=sectors,catalog_loader_block=26,catalog_sha256=SHA(catalog),
               catalog_sectors=catalog_sectors,stored_checksum_offset=30+64*slot,
               checksum_expected=expected,checksum_actual=actual,native_checksum_agrees=True,
               native_checksum_ghidra_boundaries_agree=True,
               native_checksum_entry=0x7ba,native_checksum_body_sha256=SHA(code),
               name_source_offset=nameoffset,name_length=len(namebytes),name_sha256=SHA(namebytes),
               table_load='P24 preserves pointer(table29.word36); P53 reads first512bytes of selected game into word36 onward',
               state_word_index=45,state_source_byte_offset=18,state_word=state,state=(state>>8)&15,
               word42=word(42),word43=word(43),play_allowed=profile['playAllowed'],new_game=can_start)
    return profile,proof


def source_segment(archive_name, segment_number, play=False):
    if play:
        inventory = json.loads((ROOT/'analysis/play-startup-inventory.json').read_text())
        rec = next(r for r in inventory['segments'] if r['segment_number'] == segment_number)
        listing = ROOT/f"analysis/local/pcode/SYSTEM.STARTUP-slot-{rec['slot']:02}-play.json"
    else:
        inventory = json.loads((ROOT/'analysis/archive-inventory.json').read_text())
        archive = next(a for a in inventory['archives'] if a['name'] == archive_name)
        rec = next(r for r in archive['segments'] if r['segment_number'] == segment_number)
        listing = ROOT/f"analysis/local/pcode/{archive_name}-slot-{rec['slot']:02}.json"
    raw = (ROOT/rec['path']).read_bytes()
    if SHA(raw) != rec['sha256']:
        raise ValueError('original archive differs')
    rows = json.loads(listing.read_text())
    return rec, raw, {r['procedure']['number']: r for r in rows}


def main():
    record, raw, procedures = source_segment('SYSTEM.LIBRARY', 26)
    p6 = {r['address']: r for r in procedures[6]['instructions']}
    def row(address, opcode, **operands):
        value = p6[address]
        if value['opcode'] != opcode or raw[address] != opcode or any(value['operands'].get(k) != v for k, v in operands.items()):
            raise ValueError(f'Original startup proof changed at {address:04x}')
        return value
    for address, op, args in [
        (0x2d9,0xcd,dict(segment_operand=22,procedure=53)),
        (0x325,0xcf,dict(procedure=13)), (0x3a7,0xca,dict(index=21)),
        (0x47c,0xc7,dict(word=11400)), (0x488,0xdf,dict(index=8)),
        (0x489,1,dict(value=1)), (0x48a,0x95,{}), (0x490,0xcd,dict(segment_operand=22,procedure=2)),
        (0x493,1,dict(value=1)), (0x496,0xcd,dict(segment_operand=22,procedure=2)),
        (0x49c,0xc8,{}), (0x49e,0xa1,{}),
        (0x63c,0xcd,dict(segment_operand=25,procedure=3)),
        (0x65b,0xcd,dict(segment_operand=25,procedure=3)),
        (0x675,0xcd,dict(segment_operand=25,procedure=3)),
        (0x67b,0xcf,dict(procedure=5)), (0x684,0xc3,{}),
        (0x68c,3,dict(value=3)), (0x6c0,0xcf,dict(procedure=2))]:
        row(address,op,**args)
    if raw[0x7a8:0x7ae] != bytes.fromhex('ad8ac04c00c6'):
        raise ValueError('Native slot6 boot handoff differs')
    def provenance(address):
        sector = record['sectors'][address//256]
        return dict(side='utility',**sector,byte_in_sector=address%256,image_offset=sector['offset']+address%256)
    # These are actual source strings for local rendering, not public copied assets.
    strings = []
    for item in procedures[6]['instructions']:
        if item['opcode'] == 0xa6 and 0x3af <= item['address'] < 0x47c:
            start=item['address']+2;count=item['operands']['payload_length']
            payload=raw[start:start+count]
            strings.append(dict(address=item['address'],text=payload.decode('ascii'),
                                length=count,sha256=SHA(payload)))
    local=ROOT/'analysis/local/post-title-flow';local.mkdir(parents=True,exist_ok=True)
    (local/'intro-strings.json').write_text(json.dumps(strings,indent=2)+'\n')
    utility_record, utility_raw, utility = source_segment('SUNDOG.LIBRARY', 1)
    play_record, play_raw, play = source_segment('SYSTEM.STARTUP', 7, True)
    for program, number, address, parameter in [(utility,8,0x57,0),(play,5,0x1c7,1)]:
        instructions={r['address']:r for r in program[number]['instructions']}
        if instructions[address-1]['opcode'] != parameter or instructions[address]['calls'][0].get('segment_operand') != 26:
            raise ValueError('Caller mode binding changed')
    disk=(ROOT/'extracted/utility.do').read_bytes()
    metadata, metadata_sectors=pages(83,2,disk)
    profile,profile_proof=cold_utility_profile(disk,raw)
    asset=ROOT/'analysis/local/native-assets/sundog-startup-profile.json'
    asset.parent.mkdir(parents=True,exist_ok=True)
    asset.write_text(json.dumps(profile,indent=2)+'\n')
    templates=[]
    for block in (79,80,81,82):
        content,sectors=pages(block,2,disk)
        templates.append(dict(block=block,sha256=SHA(content),sectors=sectors,
            directory_entries=directory(content)))
    reference=[]
    for capture,label in [('follow-20261023-120102','after-720-frames'),('advance-20261023-122315','advanced')]:
        folder=ROOT/'analysis/local/reference'/capture
        manifest=json.loads((folder/'manifest.json').read_text())
        entry=next(r for r in manifest['events'] if r['label']==label)
        memory=(folder/(label+'-main.bin')).read_bytes()
        if SHA(memory)!=entry['main_sha256']:raise ValueError('Existing reference RAM differs')
        word=lambda address:int.from_bytes(memory[address:address+2],'little')
        table=word(0xbd9e+29*2)
        reference.append(dict(capture=str(folder.relative_to(ROOT)),label=label,main_sha256=SHA(memory),
            frame_rgba_sha256=entry['frame']['sha256'],table29=table,
            text_fields={str(i):word(table+2*i) for i in (11,12,13,14,17,18,19,357,364,365,366,367)},
            interpretation='Original intro/button prompt' if label.startswith('after') else 'Original subsequent three-choice startup menu'))
    report=dict(method='Original decoded static CFG, exact source instruction checks and hash-bound existing reference observations',
        source=dict(archive='SYSTEM.LIBRARY',segment=26,slot=5,sha256=SHA(raw)),
        caller_modes=[dict(archive='SUNDOG.LIBRARY',segment=1,procedure=8,call_offset=0x57,parameter=0,
                           source_sha256=SHA(utility_raw),meaning='Utility mode'),
                      dict(archive='Play SYSTEM.STARTUP',segment=7,procedure=5,call_offset=0x1c7,parameter=1,
                           source_sha256=SHA(play_raw),meaning='Play mode')],
        metadata=dict(relative_block=80,absolute_loader_block=83,destination=0x1400,length=512,
                      sha256=SHA(metadata),sectors=metadata_sectors,
                      fields={'0':'nonzero skips logo, intro and menu; clear marker, write header and return to caller',
                              '1':'selected game/save index; indices>=4 block Play choice',
                              '2..5':'four copied game words corresponding table29 words21..22',
                              '7':'directory replacement target block; source read uses value-3 before P53 adds3'},
                      observed_prefix=list(metadata[:8]),side='utility',
                      limitation='The same absolute block on Play is not interchangeable metadata; disk context matters'),
        flow=[dict(stage='optional_logo',procedure=6,span=[0x320,0x327],source=provenance(0x320),predicate='metadata[0] == 0',call='segment26 P13'),
              dict(stage='skip_startup_ui',procedure=6,span=[0x3a7,0x3ac],source=provenance(0x3a7),
                   predicate='metadata[0] != 0',branch_target=0x6cd,
                   behavior='Set header byte0 to0, write relative block80, return; no intro, gate or choices'),
              dict(stage='intro_and_button_prompt',procedure=6,span=[0x3a7,0x47c],source=provenance(0x3a7),predicate='metadata[0] == 0',
                   renderer='segment22 P44 then P48 strings',strings=[{k:v for k,v in r.items() if k!='text'} for r in strings]),
              dict(stage='begin_gate',procedure=6,span=[0x47c,0x4a0],source=provenance(0x47c),
                   initial_iterations=11400,predicate='edge(channel0) OR edge(channel1) OR signed16(--remaining)<=0',
                   channel_selectors=[0,1],native_input='segment22 native P2',
                   other_call='segment22 native P3 updates pseudo-random state; it is not keyboard input',
                   timing='Iteration budget, not milliseconds or frames; original execution timing unresolved'),
              dict(stage='startup_choices',procedure=6,span=[0x4a0,0x68b],source=provenance(0x4a0),
                   choice_ids={'1':'Use utilities','2':'Play SunDog','3':'Run demo'},
                   play_blocked='state nibble12/13 OR checksum_mismatch OR metadata[1]>=4',
                   new_game_predicate='table29.word43 bits0..13==0 AND word42 bits8..15==0 AND word42 bits0..5==0'),
              dict(stage='return_or_reboot',procedure=6,span=[0x682,0x6da],source=provenance(0x682),
                   same_mode='Utility1 or Play2 returns to its caller',
                   cross_mode='Utility2 selects directory block80; Play1 selects block81; both write marker83[0]=255',
                   demo='Both modes choice3 selects directory block82 without writing the skip-title marker',
                   native_handoff='segment26 P2("MUST") then native P8: LDA C08A; JMP C600')],
        directory_templates=templates,reference_observations=reference,
        cold_utility_profile=dict(**profile_proof,artifact=str(asset.relative_to(ROOT)),artifact_sha256=SHA(asset.read_bytes())),
        next_play_steps=dict(segment=7,procedure=5,after_call_offsets=[0x1ca,0x1cd],
                             behavior='P3(false) requests/verifies Play side, then segment22 P52; remaining initialization precedes gameplay dispatcher'),
        confidence='High for the source-specific flow and existing observed screens; not every disk/event path was executed',
        limitations=['No app-side writes to original disks are authorized by this analysis; model the selected transition natively.',
                     'Ctrl-U is not a direct predicate of this P6 button loop; the earlier BIOS keyboard route is separate.',
                     'Physical joystick mapping, countdown duration, media timing and full scene initialization remain unresolved.'])
    (ROOT/'analysis/post-title-flow.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stages=len(report['flow']),intro_strings=len(strings),input_channels=[0,1],countdown_iterations=11400)))

if __name__=='__main__':main()
