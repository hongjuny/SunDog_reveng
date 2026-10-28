#!/usr/bin/env python3
"""Compile original startup decisions in Swift and compare source-bound cases."""
import hashlib
import itertools
import json
import platform
from pathlib import Path
import subprocess
import sys
from post_title_flow import ROOT,source_segment,menu_contract,choice_route,begin_gate_step
SHA=lambda raw:hashlib.sha256(raw).hexdigest()

def original_gate(procedures, remaining, first, second):
    """Evaluate only the small original 0488..049E gate expression; no calls/VM."""
    rows={r['address']:r for r in procedures[6]['instructions']};stack=[];local={8:remaining};pc=0x488
    for _ in range(40):
        if pc in (0x481,0x4a0):return local[8],pc==0x4a0
        row=rows[pc];op=row['opcode'];next_pc=row['successors'][0] if row['successors'] else None
        if op<128:stack.append(op)
        elif op==0xdf:stack.append(local[8])
        elif op==0xcc:local[row['operands']['index']]=stack.pop()
        elif op==0x95:
            b=stack.pop();a=stack.pop();stack.append(((a-b+32768)&65535)-32768)
        elif op==0xcd:
            if row['operands']!={'segment_operand':22,'procedure':2}:raise ValueError('Unknown gate call')
            stack.pop();stack.pop();selector=stack.pop();stack.append(int(first if selector==0 else second))
        elif op==0x8d:b=stack.pop();a=stack.pop();stack.append(a|b)
        elif op==0xc8:b=stack.pop();a=stack.pop();stack.append(int(a<=b))
        elif op==0xa1:next_pc=row['successors'][0 if stack.pop()&1==0 else 1]
        else:raise ValueError('Unsupported original gate expression')
        pc=next_pc
    raise ValueError('Gate expression budget exceeded')

def main():
    subprocess.run([sys.executable,str(ROOT/'tools/post_title_flow.py')],cwd=ROOT,check=True)
    _,_,procedures=source_segment('SYSTEM.LIBRARY',26)
    profiles=[]
    for mode,slot,state,damage,skip,words in itertools.product(('utility','play'),(1,4),(0,2,11,12,13,15),(False,True),(False,True),((0,0),(64,0xc000),(0x100,1))):
        stateword=0xa000|(state<<8)|0xbb;w42,w43=words
        p=dict(skipIntro=skip,slotIndex=slot,stateWord=stateword,word42=w42,word43=w43,damaged=damage)
        expected=menu_contract(mode=='play',slot,stateword,damage)
        profiles.append(dict(mode=mode,profile=p,choices=expected['choices'],newGame=w43&0x3fff==0 and w42>>8==0 and w42&0x3f==0))
    gates=[]
    for remaining,first,second in itertools.product((11400,100,2,1,0,-1,-32768),(False,True),(False,True)):
        original=original_gate(procedures,remaining,first,second)
        if original!=begin_gate_step(remaining,first,second):raise AssertionError('Rewritten gate differs from original expression')
        gates.append(dict(remaining=remaining,first=first,second=second,next=original[0],finished=original[1]))
    routes=[]
    for mode,choice in itertools.product(('utility','play'),(1,2,3)):
        r=choice_route(mode=='play',choice)
        routes.append(dict(mode=mode,choice=choice,destination=r['target'],template=r.get('template_block'),skip=r.get('set_skip_title_marker',False)))
    out=ROOT/'analysis/local/native-startup';out.mkdir(parents=True,exist_ok=True)
    cases=out/'cases.json';cases.write_text(json.dumps(dict(profiles=profiles,gates=gates,routes=routes),separators=(',',':'))+'\n')
    swift=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic/ButtonInput.swift',ROOT/'native/SunDogLogic/StartupFlow.swift',ROOT/'tests/native/VerifyStartupFlow.swift']
    binary=out/'verify-startup'
    subprocess.run([swift,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,'-target',platform.machine()+'-apple-macosx14.0',
                    '-module-cache-path',str(out/'module-cache'),*map(str,sources),'-o',str(binary)],check=True)
    report=json.loads(subprocess.check_output([str(binary),str(cases)],text=True))
    report.update(method='Swift startup rules versus source-bound P6 predicates, branch routes and original gate-expression evaluation',
                  evidence='analysis/post-title-flow.json',original_gate_cases=len(gates),cases_sha256=SHA(cases.read_bytes()),
                  source_files={str(p.relative_to(ROOT)):SHA(p.read_bytes()) for p in sources},
                  limitations=['The 11400-count gate has no inferred physical duration.',
                               'ButtonInput is separately native-verified; no physical input or complete game runtime is executed here.',
                               'Original directory writes and slot6 reboot are represented by route metadata, never performed by this module.'])
    (ROOT/'analysis/native-startup-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
