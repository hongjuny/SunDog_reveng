#!/usr/bin/env python3
"""Source-bound SHIP action classifier and controlled native movement probes.

The collision oracle is explicitly synthetic. No game VM or runtime trajectory
is claimed. Original bodies remain private; public output contains provenance.
"""
import json
from initial_game_flow import ROOT, SHA, load_segment, require, span, signed16
from native_archive_disassembly import apply_relocations
from pcode_analysis import mixed_directory
from native_probe import CPU


def truncdiv(a, b):
    return abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)


def action_at(x, y, word38=0, word39=0):
    """Translated seg15 P14; actor anchor, not pointer coordinates."""
    col = truncdiv(signed16(x + 3), 7)
    row = truncdiv(signed16(y - 3), 8)
    top = truncdiv(signed16(y - 5), 8)
    equipped = (word38 & 63) + (word39 & 31) > 0
    if col == 6: return 1 if row == 12 else 0
    if col == 8: return 4 if row == 14 and equipped else 6 if row == 10 else 0
    if col == 12: return 5 if row == 13 else 0
    if col == 14: return 3 if row == 14 and equipped else 0
    if col == 16:
        return {8: 10, 16: 11, 18: 13}.get(row, 8 if top == 6 else 0)
    if col == 17: return {15: 7, 7: 9, 17: 12}.get(row, 0)
    return 0


def evaluate_classifier(proc, x, y, word38=0, word39=0):
    """Bounded whitelist execution of original P14 only, for independent checks."""
    rows = {r['address']: r for r in proc['instructions']}
    pc = 0x07CC; stack = []; local = {3: y, 4: x}
    table = {38: word38, 39: word39}
    for _ in range(160):
        r = rows[pc]; op = r['operation']; o = r['operands']; nxt = pc + r['length']
        if op == 'push_short_constant': stack.append(o['value'])
        elif op == 'load_local_short': stack.append(local[o['index']])
        elif op == 'store_local': local[o['index']] = stack.pop()
        elif op == 'address_table_indexed':
            assert o['selector_or_depth'] == 29
            stack.append(('table', o['index']))
        elif op == 'load_packed_field':
            shift = stack.pop(); bits = stack.pop(); addr = stack.pop()
            stack.append((table[addr[1]] >> shift) & ((1 << bits) - 1))
        elif op in ('add16', 'subtract16', 'divide_signed16', 'compare_equal16',
                    'compare_signed_greater16', 'bitwise_and16'):
            b = stack.pop(); a = stack.pop()
            stack.append({'add16': lambda: signed16(a+b),
                          'subtract16': lambda: signed16(a-b),
                          'divide_signed16': lambda: truncdiv(a,b),
                          'compare_equal16': lambda: int(a==b),
                          'compare_signed_greater16': lambda: int(a>b),
                          'bitwise_and16': lambda: a&b}[op]())
        elif op == 'branch_even_word': nxt = r['successors'][1 if stack.pop() & 1 else 0]
        elif op == 'jump_encoded': nxt = r['successors'][0]
        elif op == 'case_table_branch':
            v = stack.pop(); lo=o['lower']; hi=o['upper']
            nxt = r['successors'][1+v-lo if lo <= v <= hi else 0]
        elif op == 'return_restore_context': return local[1]
        else: raise ValueError(f'Unapproved classifier operation {op}')
        pc = nxt
    raise ValueError('Classifier instruction budget exhausted')


def axis_step(delta):
    return max(-2, min(2, delta))


def native_movement(blocked):
    """Execute original native P22, intercepting P9 with declared collision data."""
    inv=json.loads((ROOT/'analysis/archive-inventory.json').read_text())
    archive=next(a for a in inv['archives'] if a['name']=='SYSTEM.LIBRARY')
    source=next(s for s in archive['segments'] if s['segment_number']==22)
    raw=(ROOT/source['path']).read_bytes()
    if SHA(raw)!=source['sha256']: raise ValueError('Library source changed')
    normalized=apply_relocations(raw,mixed_directory(raw))
    cpu=CPU(); cpu.memory[0x4000:0x4000+len(normalized)]=normalized
    def word(p,v): cpu.memory[p:p+2]=(v&65535).to_bytes(2,'little')
    # P13 fixture pointer=(53,112), actor=(48,114): requested=(2,1).
    word(0x3000,48);word(0x3002,114)
    # Pascal pushes left-to-right words, then native JSR return address.
    for value in (12,13,2,1,0x3000,0x3002): cpu.push_word(value)
    cpu.push_word(0x2fff);cpu.pc=0x54fe
    calls=[]; candidates=[]
    for _ in range(1000):
        if cpu.pc==0x5376:
            ret=cpu.pop_word(); sprite=cpu.pop_word()
            mode=cpu.read(0x92dc); point=[cpu.word(0x92d8),cpu.read(0x92d6)]
            calls.append(dict(mode=mode,sprite=sprite,point=point))
            if mode==2:
                candidates.append(point)
                cpu.write(0x9000,int(tuple(point) in blocked))
            cpu.pc=ret+1
        else: cpu.step()
        if cpu.pc==0x3000:
            if cpu.sp != 255: raise AssertionError('Native argument cleanup differs')
            return dict(actor_before=[48,114],pointer=[53,112],requested_delta=[2,1],
                        blocked_points=[list(p) for p in sorted(blocked)],
                        candidate_points=candidates,actor_after=[cpu.word(0x3000),cpu.word(0x3002)],
                        sprite_calls=calls,steps=cpu.steps,
                        limitation='P9 collision/drawing intercepted; synthetic oracle, not captured game execution',
                        library_sha256=source['sha256'])
    raise ValueError('Native movement probe budget exhausted')


def main():
    source,raw,p=load_segment(15)
    for proc,address,op,operands in (
        (1,0x0998,'call_external_segment',dict(segment_operand=22,procedure=2)),
        (1,0x0A03,'call_current_dynamic_link',dict(procedure=16)),
        (13,0x078A,'call_external_segment',dict(segment_operand=22,procedure=22)),
        (13,0x07B2,'call_external_segment',dict(segment_operand=22,procedure=22)),
        (16,0x08EE,'call_current_lexical_link',dict(procedure=14))):
        require(p[proc],address,op,**operands)
    count=0
    for x in range(35,130):
        for y in range(44,163):
            for w38,w39 in ((0,0),(1,0),(0,1),(64,32)):
                if action_at(x,y,w38,w39)!=evaluate_classifier(p[14],x,y,w38,w39):
                    raise AssertionError(f'Classifier disagreement {x,y,w38,w39}')
                count+=1
    from export_initial_ship import verified_pages
    metadata,_=verified_pages('utility',83,2)
    profile,profile_sectors=verified_pages('utility',27+10*metadata[1],2)
    word=lambda i:int.from_bytes(profile[2*(i-36):2*(i-35)],'little')
    actor=[word(40),word(41)&255]
    actual_action=action_at(*actor,word(38),word(39))
    require(p[11],0x05C7,'load_table_indexed',selector_or_depth=29,index=40)
    require(p[11],0x05D3,'store_nonlocal',selector_or_depth=1,index=5)
    case=require(p[11],0x062A,'case_table_branch')
    previous_mode=(word(45)>>4)&15
    if previous_mode!=11 or case['successors'][previous_mode+1]!=0x05C7:
        raise ValueError('Selected profile no longer follows saved-coordinate restore')
    report=dict(schema_version=1,source_sha256=source['sha256'],confidence='source-confirmed; controlled fixtures',
        evidence=[span(source,raw,n,a,b) for n,a,b in ((1,0x0995,0x0A0A),(13,0x070C,0x07C0),(14,0x07CC,0x08A3),(16,0x08E6,0x0965))],
        classifier_checks=count,
        supplied_profile_trace=dict(side='utility',absolute_block=27+10*metadata[1],
            sectors=profile_sectors,profile_record_sha256=SHA(profile),
            state_word45=word(45),previous_mode=previous_mode,actor=actor,
            word38=word(38),word39=word(39),classifier_result=actual_action,
            example_stationary_pointer=[actor[0]+3,actor[1]-3],
            condition='Pointer at declared stationary target; button0 observed down then released; actor remains at supplied saved position',
            result='P16 new ID1 after P11 previous_action=0; P15 then mode0 and P4 cockpit instruments',
            limitation='Source-derived conditional trace, not captured live input'),
        rea_native_confirmation=dict(evidence_id='ev_4d639db5476cf53d2fd3134f0c34c92d65ccb6e5bd4575c40a1c0c0de2923fe8',
            address_range=['0xAABC','0xAB82'],segment_memory_base='0x95BE',
            sha256='1307ab43ea5af86dc593aca34ab5cedb83404233812557756e0ffa114613e7e4'),
        classifier_case_columns={str(6+i):hex(v) for i,v in enumerate(require(p[14],0x087F,'case_table_branch')['successors'][1:])},
        action_dispatch={'1':'set packed mode 0, call P4 cockpit instrumentation',
                         '3':'P7, set mode3 and packed state flags',
                         '4':'P6, clear two flags; mode3 unless word347; actor y+=20',
                         'other_positive':'segment14 P1 by-reference action ID unless word347'},
        semantics={'held_button0':'P13 moves actor toward pointer minus/plus anchor offsets',
                   'released_button0':'P16 classifies actor coordinates, suppresses repeated action ID',
                   'button1_edge':'P15 then segment8 P1',
                   'collision':'native P22 tries diagonal, x only, y only; P9 mode2 pixel-mask collision; P13 retries unit step if unchanged'},
        native_fixtures=[native_movement(set()),native_movement({(50,115)}),
                         native_movement({(50,115),(50,114)}),
                         native_movement({(50,115),(50,114),(48,115)})],
        unknowns=['Original mask/palette bytes used by each collision plane need independent extraction and replay',
                  'Action IDs 5–13 require full segment14 semantic labels',
                  'No measured real-time walking speed or captured joystick trajectory'])
    (ROOT/'analysis/ship-actions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(classifier_checks=count,native_fixture_results=[f['actor_after'] for f in report['native_fixtures']])))


if __name__=='__main__':main()
