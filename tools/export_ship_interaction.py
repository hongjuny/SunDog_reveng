#!/usr/bin/env python3
"""Export verified saved actor state for local native interaction, no binary publication."""
import json
from initial_game_flow import ROOT, load_segment, require, SHA
from export_initial_ship import verified_pages

def main():
    source,raw,p=load_segment(7)
    require(p[4],0xEC,'push_short_constant',value=2)
    require(p[4],0xED,'store_table_indexed',index=298)
    metadata,_=verified_pages('utility',83,2)
    data,sectors=verified_pages('utility',27+10*metadata[1],2)
    word=lambda i:int.from_bytes(data[2*(i-36):2*(i-35)],'little')
    if (word(45)>>4)&15!=11 or (word(45)>>8)&15!=2:
        raise ValueError('Only verified SHIP saved-coordinate route is supported')
    state=dict(x=word(40),y=word(41)&255,word38=word(38),word39=word(39),pointerGlyph=2)
    out=ROOT/'analysis/local/native-assets/sundog-ship-interaction.json'
    out.write_text(json.dumps(state,indent=2)+'\n')
    report=dict(side='utility',sectors=sectors,profile_sha256=SHA(data),asset_sha256=SHA(out.read_bytes()),
        source_startup_sha256=source['sha256'],actor_words=[40,41],pointer_glyph_source=dict(segment=7,procedure=4,address=0xEC),
        font_source='analysis/native-font-asset.json',sprite_ids=dict(actor=12,collision=13,pointer=2),
        limitations=['Verified supplied saved-coordinate SHIP route only','No hardware pacing claim'])
    (ROOT/'analysis/ship-interaction-assets.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified SHIP saved state exported locally')
if __name__=='__main__':main()
