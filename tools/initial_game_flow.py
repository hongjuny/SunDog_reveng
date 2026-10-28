#!/usr/bin/env python3
"""Source-bound Play startup initialization and first disk-side gate.

This extracts control/data contracts from already decoded procedures; it does not
run a game VM and does not assign scene names to unclassified packed state.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()


def signed16(value):
    value &= 65535
    return value if value < 32768 else value - 65536


def disk_side_gate(block, want_utility, io_result=0):
    """Selected segment7 P2 outcomes; no inferred filesystem identification."""
    if len(block) != 512:
        raise ValueError('Original gate reads exactly one 512-byte block')
    if signed16(io_result) > 0:
        return 'nonlocal_exit'
    return 'accepted' if block[252] == (0 if want_utility else 9) else 'wrong_side'


def button_ready(first, second):
    """P3 OR followed by native low-bit branch truth, not generic nonzero."""
    return bool((first | second) & 1)


def load_segment(number):
    inventory = json.loads((ROOT / 'analysis/play-startup-inventory.json').read_text())
    source = next(s for s in inventory['segments'] if s['segment_number'] == number)
    raw = (ROOT / source['path']).read_bytes()
    if SHA(raw) != source['sha256']:
        raise ValueError('Original Play segment identity changed')
    path = ROOT / f"analysis/local/pcode/SYSTEM.STARTUP-slot-{source['slot']:02}-play.json"
    records = json.loads(path.read_text())
    procedures = {r['procedure']['number']: r for r in records}
    for proc in records:
        if proc['boundaries']:
            raise ValueError('Startup proof crosses an unresolved decoder boundary')
        for row in proc['instructions']:
            if raw[row['address']] != row['opcode']:
                raise ValueError('Decoded instruction/source mismatch')
    return source, raw, procedures


def require(proc, address, operation, **operands):
    row = next(r for r in proc['instructions'] if r['address'] == address)
    if row['operation'] != operation or any(row['operands'].get(k) != v for k, v in operands.items()):
        raise ValueError(f'Original startup expression differs at {address:04X}')
    return row


def coordinate(source, address):
    sector = source['sectors'][address // 256]
    return dict(side='play', **sector, byte_in_sector=address % 256,
                image_offset=sector['offset'] + address % 256)


def span(source, raw, procedure, start, end):
    return dict(segment=source['segment_number'], procedure=procedure, start=start,
                end_exclusive=end, sha256=SHA(raw[start:end]), source=coordinate(source, start))


def main():
    source, raw, p = load_segment(7)
    ship_source, ship_raw, ship = load_segment(13)
    # Entry boolean really chooses startup initialization versus later save/exit.
    require(p[1], 0x070D, 'load_local_short', index=1)
    require(p[1], 0x070E, 'branch_even_word')
    startup_calls = [(r['address'], r['calls'][0]['procedure']) for r in p[1]['instructions']
                     if 0x0710 <= r['address'] <= 0x071A and r['calls']]
    if startup_calls != [(0x0710, 4), (0x0712, 5), (0x0714, 6), (0x0716, 7), (0x071A, 8)]:
        raise ValueError('Original startup call order changed')
    # P2 reads a whole boot block and chooses exact original marker byte.
    for address, value in ((0x0003, 4), (0x000A, 0), (0x0010, 0), (0x0014, 7),
                           (0x0015, 2), (0x0021, 0), (0x002D, 9)):
        require(p[2], address, 'push_short_constant', value=value)
    require(p[2], 0x0007, 'literal_word', word=512)
    require(p[2], 0x000C, 'secondary_dispatch', effective_selector=5)
    require(p[2], 0x000E, 'secondary_dispatch', effective_selector=34)
    require(p[2], 0x0011, 'compare_signed_greater16')
    require(p[2], 0x0016, 'secondary_dispatch', effective_selector=4)
    require(p[2], 0x0018, 'load_local_short', index=3)
    for address in (0x001D, 0x0029): require(p[2], address, 'literal_word', word=252)
    # Both buttons are actual original rising-edge selectors, followed by OR.
    for address in (0x00BE, 0x00C4):
        require(p[3], address, 'call_external_segment', segment_operand=22, procedure=2)
    require(p[3], 0x00C7, 'bitwise_or16')
    wait = require(p[3], 0x00C8, 'branch_even_word')
    retry = require(p[3], 0x00CF, 'branch_even_word')
    if wait['successors'] != [0x00BB, 0x00CA] or retry['successors'] != [0x003E, 0x00D1]:
        raise ValueError('Wrong-side retry or button-loop target changed')
    require(p[5], 0x01C6, 'push_short_constant', value=1)
    require(p[5], 0x01C7, 'call_external_segment', segment_operand=26, procedure=6)
    require(p[5], 0x01CA, 'push_short_constant', value=0)
    require(p[5], 0x01CB, 'call_current_lexical_link', procedure=3)
    # Extract the selected constant table initialization rather than naming it.
    initial = []
    rows = p[4]['instructions']
    for before, row in zip(rows, rows[1:]):
        if before['operation'] == 'push_short_constant' and row['operation'] == 'store_table_indexed':
            initial.append(dict(word_index=row['operands']['index'], value=before['operands']['value'],
                                address=row['address'], source=coordinate(source, row['address'])))
    # Resource bases are a deterministic addition chain in P5.
    require(p[5], 0x0142, 'push_short_constant', value=26)
    require(p[5], 0x0143, 'store_table_indexed', selector_or_depth=29, index=32)
    resource_bases = {32: 26}
    for previous, add_address, amount, store_address, index in (
        (32, 0x0149, 16, 0x014B, 30), (30, 0x0151, 10, 0x0153, 29),
        (29, 0x0159, 9, 0x015B, 28), (28, 0x0161, 15, 0x0163, 27),
        (27, 0x0169, 9, 0x016B, 26)):
        require(p[5], add_address, 'push_short_constant', value=amount)
        require(p[5], store_address, 'store_table_indexed', selector_or_depth=29, index=index)
        resource_bases[index] = resource_bases[previous] + amount
    require(ship[1], 0x25EA, 'literal_word', word=2048)
    require(ship[1], 0x25EE, 'load_table_indexed', selector_or_depth=29, index=27)
    require(ship[1], 0x25F4, 'call_external_segment', segment_operand=22, procedure=53)
    # Supplied media corroboration is metadata only; unknown Play track34 unused.
    from boot_regions import pages
    media = []
    verified = json.loads((ROOT / 'analysis/woz-full-checks.json').read_text())
    decoded = {(r['side'], r['track'], r['sector']): r for r in verified['sectors']}
    for side in ('utility', 'play'):
        disk = (ROOT / f'extracted/{side}.do').read_bytes()
        block, sectors = pages(0, 2, disk)
        for index, sector in enumerate(sectors):
            proof = decoded[side, sector['track'], sector['sector']]
            if proof['returncode'] != 0 or not proof['matches'] or proof['sha256'] != SHA(block[index * 256:(index + 1) * 256]):
                raise ValueError('Startup side-marker block is not verified readable original media')
        media.append(dict(side=side, block=0, length=512, marker_offset=252,
                          marker=block[252], sha256=SHA(block), sectors=sectors,
                          outcome_for_play=disk_side_gate(block, False)))
    result = dict(method='Source-bound Play segment7/13 decoded CFG and operand checks; static normal-return contracts',
        source_sha256=source['sha256'], ship_segment_sha256=ship_source['sha256'],
        initialization=dict(procedure=1, argument_true_calls=[4, 5, 6, 7], argument_false_call=8,
            evidence=span(source, raw, 1, 0x0706, 0x071C)),
        initial_table_constants=initial, relative_resource_bases=resource_bases,
        title_to_play_gate=dict(title_call=span(source, raw, 5, 0x01C6, 0x01CA),
            title_callee=dict(segment=26, procedure=6, argument=1),
            gate_call=span(source, raw, 5, 0x01CA, 0x01CD), desired_utility=False,
            note='Segment26 P6 performs more than the logo; its menu/result contract must be traced separately.'),
        side_gate=dict(procedure=2, unit=4, block=0, bytes=512, marker_offset=252,
            utility_marker=0, play_marker=9, utility_test=0x0018,
            io_predicate='signed16(IORESULT)>0 invokes nonlocal EXIT service with preceding constants7,2',
            evidence=span(source, raw, 2, 0, 0x0033)),
        side_prompt=dict(procedure=3, button_selectors=[0, 1], predicate='(edge0 OR edge1) bit0',
            no_button_target=0x00BB, wrong_side_target=0x003E, accepted_return=0x00D1,
            evidence=span(source, raw, 3, 0x003E, 0x00D3)),
        supplied_boot_blocks=media,
        first_scene=dict(root_state_field='(table29.word45 >> 8) &15',
            root_routes={'0,1':'segment13 P1', '2':'segment15 P1'},
            segment13_entry=span(ship_source, ship_raw, 1, 0x2586, 0x2590),
            initial_resource_read=dict(destination=0x0800, blocks=2, relative_block='table29.word27 + 2',
                absolute_block_if_P5_bases_unchanged=resource_bases[27] + 2 + 3,
                call=span(ship_source, ship_raw, 1, 0x25EA, 0x25F7)),
            note='No new-game state value is assumed. Word45 is not initialized by the selected constant-init stores; preceding menu/data side effects remain material.'),
        confidence='High for identified source operands, selected branches and supplied disk markers; no full game start execution claimed',
        remaining=['Segment26 P6 choice/data initialization and state ownership',
            'Complete Play-side writes and initial saved/new-game data construction',
            'First interactive scene render/input loop and physical control mapping',
            'Original window clear/scroll and resource lifetimes across scene transitions'])
    (ROOT / 'analysis/initial-game-flow.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(initialization_calls=[4, 5, 6, 7], play_marker=9,
        supplied_markers={r['side']:r['marker'] for r in media}, first_scene_state_not_assumed=True)))

if __name__ == '__main__':
    main()
