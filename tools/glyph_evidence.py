#!/usr/bin/env python3
"""Derive and check the original glyph row compositor on declared synthetic inputs.

Uses the existing bounded native-instruction probe for analysis only. No ROM,
disks, Apple II runtime or application backend is provided.
"""
import hashlib,json
from pathlib import Path
from native_probe import CPU
from pcode_analysis import mixed_directory
ROOT=Path(__file__).resolve().parents[1]

def hgr_row(y):return 0x2000+(y&7)*0x400+((y>>3)&7)*0x80+(y>>6)*0x28

def compose_row(left,right,glyph,shift,mask_low,mask_high):
    """Normal (non-2) native body, excluding caller setup, clipping and positioning."""
    if not 0<=shift<=6:raise ValueError('HGR bit shift outside selected legal range')
    glyph &= 0x7f
    if not (glyph|mask_low):return left,right
    glyph_low=(glyph<<shift)&0x7f
    glyph_high=glyph>>(7-shift) if shift else 0
    mask0=(mask_low<<shift)&0x7f
    mask1=((mask_high<<shift)|((mask_low&0x7f)>>(7-shift) if shift else 0))&0x7f
    keep0=0x80|(~mask0&0x7f);keep1=0x80|(~mask1&0x7f)
    return (left&keep0)^glyph_low,(right&keep1)^glyph_high

def run():
    source=ROOT/'analysis/regions/archives/SYSTEM.LIBRARY-slot-01.bin';raw=source.read_bytes()
    proc=next(p for p in mixed_directory(raw) if p['number']==9)
    if proc['kind']!='native-6502' or proc['entry_address']!=0x1376:raise ValueError('glyph descriptor differs')
    body=raw[proc['entry_address']:proc['attribute_address']]
    evidence=json.loads((ROOT/'analysis/local/rea/library22-glyph-raw.json').read_text())
    if evidence['subject']['digest']['sha256']!=hashlib.sha256(body).hexdigest():raise ValueError('REA evidence refers to different native bytes')
    defined={int(line.split(':',1)[0],16) for line in evidence['normalized_result'].splitlines() if line.startswith('0x')}
    visited=set();cases=0
    glyphs=bytes([0x15,0x2a,0x01,0,0x7f,0x40,0x03,0x10])
    for shift in range(7):
        for mask_low in (0,0x3f,0x7f,0x55,0xff):
            for mask_high in (0,0x0f,0x7f):
                for baseline in (7,31,127,191):
                    c=CPU();c.memory[0x1376:0x1376+len(body)]=body
                    c.memory[0x2000:0x4000]=bytes(0x80|((i*13+19)&0x7f) for i in range(8192))
                    def word(p,n):c.memory[p:p+2]=n.to_bytes(2,'little')
                    word(0x2c6,0x5000);word(0x2d8,35+shift)
                    c.memory[0x2c8]=mask_low;c.memory[0x2dc]=0
                    c.memory[0x2c]=baseline;c.memory[0x32]=5;c.memory[0x34]=shift
                    c.memory[4]=mask_low;c.memory[5]=mask_high;c.memory[0x12]=65;c.memory[0x13]=0
                    c.memory[0x5000+65*8:0x5000+66*8]=glyphs
                    for y in range(192):
                        address=hgr_row(y);c.memory[0xdc0+y]=address&255;c.memory[0xe80+y]=address>>8
                    expected=bytearray(c.memory[0x2000:0x4000])
                    for row in range(8):
                        p=hgr_row(baseline-7+row)+5-0x2000
                        expected[p],expected[p+1]=compose_row(expected[p],expected[p+1],glyphs[7-row],shift,mask_low,mask_high)
                    c.pc=0x13d0;c.run({0x14bf},max_steps=5000)
                    if c.memory[0x2000:0x4000]!=expected:raise AssertionError('native row composition differs from reconstructed bit operations')
                    if c.word(0x2d8)!=41+shift:raise AssertionError('native x advance differs')
                    if not c.visited<=defined:raise AssertionError('probe left REA/Ghidra defined instruction boundaries')
                    visited.update(c.visited);cases+=1
    result=dict(method='Normal drawing body 13D0..14BF checked against independent bit-expression model on synthetic font, RAM, masks and position; analysis only',
                source_side='utility',archive='SYSTEM.LIBRARY',slot=1,segment_number=22,procedure=9,
                source_sha256=hashlib.sha256(raw).hexdigest(),native_slice_sha256=hashlib.sha256(body).hexdigest(),
                native_body_entry=0x13d0,stop_before=0x14bf,cases=cases,native_instruction_addresses=[hex(a) for a in sorted(visited)],
                ghidra_boundaries_agree=True,rea_evidence_id=evidence['evidence_id'],
                checked=['8 rows, bottom-to-top font storage','7 possible HGR bit shifts','adjacent-byte masking and XOR','existing HGR phase bits','x advances by 6'],
                not_checked=['Caller argument/return setup','Coordinate helper and clipping','Mode 2 collision/query branch','Original font glyph contents','Window/event/game logic','Physical display colour'])
    (ROOT/'analysis/glyph-compositor-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=cases,native_instructions=len(visited),result='matched')))
if __name__=='__main__':run()
