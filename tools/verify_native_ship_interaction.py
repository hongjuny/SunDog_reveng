#!/usr/bin/env python3
"""Compare native Swift collision on the real SHIP background to original P9 mode2."""
import platform
import json
import subprocess
from pathlib import Path
from initial_game_flow import ROOT,SHA
from native_probe import CPU
from native_archive_disassembly import apply_relocations
from pcode_analysis import mixed_directory
from glyph_evidence import hgr_row
from ship_action_evidence import action_at

def main():
    raw=(ROOT/'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin').read_bytes()
    inv=json.loads((ROOT/'analysis/native-archive-disassembly.json').read_text())['archive_segments'][0]
    if SHA(raw)!=inv['source_sha256']:raise ValueError('Native library source changed')
    normalized=apply_relocations(raw,mixed_directory(raw))
    page=(ROOT/'analysis/local/native-assets/sundog-initial-ship.bin').read_bytes()
    from export_initial_ship import decode_image
    page,_=decode_image(page)
    font=(ROOT/'analysis/local/native-assets/sundog-font.bin').read_bytes()
    collisions=[]
    for x in range(35,131):
        for y in range(80,125,3):
            cpu=CPU();cpu.memory[0x4000:0x4000+len(normalized)]=normalized
            cpu.memory[0x2000:0x4000]=page;cpu.memory[0x6000:0x6400]=font
            def word(a,v):cpu.memory[a:a+2]=v.to_bytes(2,'little')
            word(0x92c6,0x6000);word(0x9002,8)
            cpu.memory[0x32]=x//7;cpu.memory[0x34]=x%7;cpu.memory[0x2c]=y
            cpu.memory[0x12]=13;cpu.memory[0x13]=0
            for row in range(192):
                address=hgr_row(row);cpu.memory[0xdc0+row]=address&255;cpu.memory[0xe80+row]=address>>8
            cpu.memory[4]=normalized[0x164a+8]^255
            cpu.memory[5]=normalized[0x163e+8]^255
            if (cpu.memory[4],cpu.memory[5])!=(127,127):raise ValueError('Original color8 masks changed')
            cpu.memory[0x92dc]=2
            cpu.pc=0x53d0;cpu.run({0x54b9,0x54bf},max_steps=3000)
            collisions.append(dict(x=x,y=y,hit=bool(cpu.word(0x9000))))
    actions=[dict(x=x,y=y,w38=a,w39=b,action=action_at(x,y,a,b))
             for x in range(35,130) for y in range(44,163) for a,b in [(0,0),(1,0),(0,1),(64,32)]]
    directory=ROOT/'analysis/local/native-ship-interaction';directory.mkdir(exist_ok=True)
    case=directory/'cases.json';case.write_text(json.dumps(dict(page=list(page),font=list(font),collisions=collisions,actions=actions)))
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    executable=directory/'verify'
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    subprocess.run([compiler,'-O','-sdk',sdk,'-target',platform.machine()+'-apple-macosx14.0','-module-cache-path',str(ROOT/'analysis/local/swift-direct-cache'),
                    str(ROOT/'native/SunDogLogic/GlyphCompositor.swift'),str(ROOT/'native/SunDogLogic/ShipInteraction.swift'),
                    str(ROOT/'tests/native/VerifyShipInteraction.swift'),'-o',str(executable)],check=True)
    subprocess.run([str(executable),str(case)],check=True)
    report=dict(collision_checks=len(collisions),classifier_checks=len(actions),all_matched=True,
        library_sha256=SHA(raw),font_sha256=SHA(font),background_sha256=SHA(page),
        method='Original P9 mode2 with actual glyph13, original color8 masks and original SHIP background compared against native Swift',
        limitations=['Controlled native subroutine probes, not live Apple II timing','Nested world simulation and facility scenes not included'])
    (ROOT/'analysis/native-ship-interaction-verification.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
