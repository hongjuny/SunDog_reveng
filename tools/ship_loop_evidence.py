#!/usr/bin/env python3
"""Static, source-bound SHIP loop evidence; not a game interpreter."""
import json
from pathlib import Path
from initial_game_flow import load_segment, require, span

ROOT = Path(__file__).resolve().parents[1]


def loop_continues(state):
    return ((state >> 8) & 15) in (2, 10)


def level_transition(previous, current):
    if bool(previous) == bool(current):
        return 'unchanged'
    return 'press_reset_target' if current else 'release_hit_test'


def modal_requested(second_button_edge, state):
    return bool(second_button_edge & 1) or ((state >> 8) & 15) == 10


def movement_step(delta):
    """P13 sign*2 clipped to remaining distance; input is a signed delta."""
    return max(-2, min(2, delta))


def build_report():
    source, raw, p = load_segment(15)
    root_source, root_raw, root = load_segment(1)
    guards = []

    def check(proc, address, operation, **operands):
        row = require(p[proc], address, operation, **operands)
        guards.append(dict(procedure=proc, address=address, operation=operation,
                           operands=operands))
        return row

    require(root[3], 0x0034, 'call_external_segment', segment_operand=15, procedure=1)
    root_case = require(root[3], 0x0041, 'case_table_branch', lower=0, upper=9)
    if root_case['successors'][3] != 0x0034:
        raise ValueError('Root mode2 no longer selects SHIP')
    if require(root[3], 0x0076, 'branch_even_word')['successors'] != [0x0027, 0x0078]:
        raise ValueError('Root post-SHIP dispatch predicate changed')
    external = [(1, 0x0998, 22, 2), (1, 0x09A3, 22, 43),
                (1, 0x09A9, 22, 2), (1, 0x09BB, 8, 1),
                (1, 0x09DF, 24, 9), (1, 0x09E5, 22, 2),
                (1, 0x09EF, 22, 2), (1, 0x09FA, 22, 2),
                (11, 0x06DA, 22, 42), (13, 0x072E, 22, 34),
                (13, 0x073B, 22, 35), (13, 0x076F, 22, 41),
                (13, 0x078A, 22, 22), (13, 0x07B2, 22, 22),
                (13, 0x07BB, 22, 41), (15, 0x08B8, 22, 41),
                (16, 0x0957, 14, 1)]
    for proc, addr, seg, callee in external:
        check(proc, addr, 'call_external_segment', segment_operand=seg, procedure=callee)
    for addr, callee in [(0x099D, 13), (0x09B7, 15), (0x09C8, 11),
                         (0x09EA, 13), (0x0A03, 16)]:
        check(1, addr, 'call_current_dynamic_link', procedure=callee)
    check(1, 0x0980, 'call_current_dynamic_link', procedure=11)
    for addr, value in [(0x0985, 4), (0x0986, 8), (0x0988, 2),
                        (0x0990, 10), (0x0995, 4), (0x09A6, 1),
                        (0x09B2, 10), (0x0A11, 2)]:
        check(1, addr, 'push_short_constant', value=value)
    for addr, successors in [(0x0993, [0x0A0C, 0x0995]),
                              (0x09B5, [0x09CA, 0x09B7]),
                              (0x0A01, [0x0A07, 0x0A03]),
                              (0x0A0A, [0x0982])]:
        operation = 'jump_encoded' if addr == 0x0A0A else 'branch_even_word'
        if check(1, addr, operation)['successors'] != successors:
            raise ValueError(f'SHIP branch target changed at {addr:04X}')
    check(1, 0x09D0, 'store_table_indexed', selector_or_depth=29, index=354)
    check(1, 0x09D8, 'load_table_indexed', selector_or_depth=29, index=353)
    check(11, 0x0692, 'push_short_constant', value=15)
    check(16, 0x08EE, 'call_current_lexical_link', procedure=14)
    check(16, 0x08FE, 'secondary_dispatch', effective_selector=4)
    for addr, callee in [(0x091B, 15), (0x092B, 4), (0x0936, 7), (0x0941, 6), (0x0961, 11)]:
        check(16, addr, 'call_current_lexical_link', procedure=callee)
    # The arithmetic is compared to source, not inferred from sprite appearance.
    for addr, operation in [(0x0710, 'subtract16'), (0x0714, 'subtract16'),
                             (0x071B, 'add16'), (0x071F, 'subtract16'),
                             (0x0735, 'add16'), (0x0754, 'add16')]:
        check(13, addr, operation)
    ranges = [(1, 0x0970, 0x0A2B), (11, 0x04FE, 0x06DF),
              (13, 0x070C, 0x07C0), (14, 0x07CC, 0x08A3),
              (15, 0x08B2, 0x08DC), (16, 0x08E6, 0x0965),
              (4, 0x0080, 0x020F), (6, 0x023A, 0x026F), (7, 0x027A, 0x02DD)]
    return dict(
        method='Static decoded CFG, original segment hash and opcode/operand guards; no runtime execution',
        confidence='high for guarded control flow; gameplay names and timing remain qualified',
        source_sha256=source['sha256'], root_source_sha256=root_source['sha256'],
        root_entry=span(root_source, root_raw, 3, 0x0020, 0x0084),
        root_dispatch=dict(entry='Root1P3 clears word347 then mode2 calls15P1 at0034',
                           on_return='Modes3/4 or>=11 release24 and return; other modes repeat dispatch',
                           downstream='Root1P6 chooses rootP3 for mode<=2, rootP4 otherwise; exits mode>=11'),
        evidence_spans=[span(source, raw, *r) for r in ranges], guards=guards,
        state=dict(table=29, word=45, current_mode=dict(shift=8, bits=4),
                   previous_mode=dict(shift=4, bits=4), action_nibble=dict(shift=0, bits=4),
                   ship_loop_modes=[2, 10], mode2='SHIP interior control loop'),
        initialization=dict(procedure=11, pointer_init_call='22P42@06DA',
                            tick_threshold=dict(word=353, value=15),
                            button_level_history_local=12, initial_button_level=0,
                            actor_locals=[6, 5], pointer_locals=[3, 2],
                            persisted_actor_words=[40, 41],
                            previous_mode_controls_reentry=True),
        loop_order=[
            dict(address=0x0982, effect='Continue only for mode2 or10'),
            dict(address=0x0998, effect='Selector4 button0 level: if down, P13 moves actor toward old pointer'),
            dict(address=0x09A3, effect='22P43 samples/updates pointer locals3/2'),
            dict(address=0x09A9, effect='Selector1 button1 rising edge OR mode10: P15 then8P1; P11 if resulting mode<11'),
            dict(address=0x09CA, effect='Increment word354; signed >= word353 invokes24P9'),
            dict(address=0x09E5, effect='Button0 level: P13 moves actor toward updated pointer'),
            dict(address=0x09EF, effect='Compare level with local12; press resets local4=0; release callsP16'),
            dict(address=0x0A0A, effect='Return to mode predicate; cleanup records previousmode2 and releases27,14,8')],
        held_motion=dict(procedure=13, delta=['(local3-3)-local6', '(local2+3)-local5'],
                         primary_step='sign(delta)*min(2,abs(delta))',
                         collision_call='22P22 with references to actor locals6/5',
                         fallback='If both actor coordinates unchanged, retry with sign-only deltas',
                         screen='22P41 before and after move; 22P22 updates actor/rendering'),
        release_action=dict(procedure=16, hit_test='P14(actorlocal6,actorlocal5), not pointer position',
                            repeated_target='If result equals local4, service EXIT(15,16)',
                            preparation='P15 removes pointer, saves previousmode2/actionnibble11 and actor words40/41, callsP5',
                            branches={'0': 'No positive-target modal', '1': 'mode0 then P4 cockpit redraw',
                                      '3': 'P7 sets mode3, previousmode2, bits13=0/12=1',
                                      '4': 'P6 clears bitarray116/117; mode3 if !word347; word292=6; actorlocal5+=20; P5',
                                      'other_positive': 'If !word347,14P1(&local1); if still !word347,P11 reinitializes'}),
        modal_boundary=dict(segment=8, procedure=1, entry='button1 rising edge or mode10',
                            distinction='P15 persists actor/context in RAM; this alone does not prove disk save',
                            return_path='mode<11 callsP11; top predicate finally exits if mode not2/10'),
        unknowns=['24P9 exact time-unit and word354 reset ownership',
                  'Meaning of word347 and mode10 beyond proven modal routing',
                  'Full8P1 save/quit menu and eventual disk-write chain',
                  'Measured frame pacing, physical joystick feel and render ordering under real runtime',
                  'Semantic labels of each P14 numeric target; use separately verified action evidence'])


def main():
    result = build_report()
    path = ROOT / 'analysis/ship-main-loop.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
