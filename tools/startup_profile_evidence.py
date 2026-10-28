#!/usr/bin/env python3
"""Join the verified disk profile, root dispatcher and first SHIP resource proof."""
import json
from export_initial_ship import ROOT, SHA, main as export_ship
from initial_game_flow import load_segment, require, coordinate


def main():
    export_ship()
    asset = json.loads((ROOT/'analysis/initial-ship-asset.json').read_text())
    source, raw, procedures = load_segment(1)
    flow = json.loads((ROOT/'analysis/startup-control-flow.json').read_text())
    if flow['source_sha256'] != SHA(raw):
        raise ValueError('Root dispatch source changed')
    field = flow['state_field']
    if (field['word_index'], field['width'], field['shift']) != (45,4,8):
        raise ValueError('Packed mode field changed')
    state = asset['profile']['state_word45']
    mode = (state >> 8) & 15
    dispatcher = next(d for d in flow['dispatchers'] if d['procedure']==3)
    entry = next(e for e in dispatcher['entries'] if e['state']==mode)
    call = entry['calls_before_join'][0]
    require(procedures[3], call['address'], 'call_external_segment',
            segment_operand=15, procedure=1)
    result = dict(method='Joined original disk-backed profile and source-bound root dispatch',
        confidence='High for the supplied Utility profile and selected base bitmap',
        profile=asset['profile'], mode_formula=field['formula'], selected_mode=mode,
        root_call=dict(segment=1,procedure=3,address=call['address'],
                       source=coordinate(source,call['address']),target_segment=15,target_procedure=1),
        scene='SHIP', resource=asset['resource'],
        decoded_page_sha256=asset['decoded_sha256'],
        evidence_reports={'asset':'analysis/initial-ship-asset.json',
                          'dispatch':'analysis/startup-control-flow.json',
                          'decoder':'analysis/native-ship-verification.json'},
        remaining=['Status and cursor overlays after the base image',
                   'The initial 5KB state record fields beyond the selected profile header',
                   'Input-driven first-scene transitions, movement and interaction'])
    (ROOT/'analysis/startup-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'mode':mode,'scene':result['scene'],'target':'segment15 P1'}))

if __name__=='__main__':main()
