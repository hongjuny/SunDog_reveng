#!/usr/bin/env python3
"""Compare rewritten Swift post-title pixels with complete original HGR pages."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    subprocess.run([sys.executable,str(ROOT/'tools/post_title_render_evidence.py')],cwd=ROOT,check=True)
    output=ROOT/'analysis/local/post-title'
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic'/name for name in ('GlyphCompositor.swift','WindowTextLayout.swift','StartupTextScreen.swift')]
    sources.append(ROOT/'tests/native/VerifyStartupTextScreen.swift')
    binary=output/'verify-startup-screen'
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,'-target',
        platform.machine()+'-apple-macosx14.0','-module-cache-path',str(output/'module-cache'),*map(str,sources),'-o',str(binary)],check=True)
    cases=[output/'render-cases.json',output/'menu-render-case.json']
    report=json.loads(subprocess.check_output([str(binary),*map(str,cases)],text=True))
    report.update(method='Swift startup window, text and buttons versus full original prompt/menu HGR pages',
        evidence='analysis/post-title-render.json',
        source_files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        cases={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in cases},
        limitations=['Selected P51(40,24) window and healthy continuation menu only, not a general game UI.',
                     'Sound, opening animation and original input timing are not reproduced.',
                     'Menu cursor comparison uses the recorded original point; host input mapping is separate.'])
    (ROOT/'analysis/native-startup-screen-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
