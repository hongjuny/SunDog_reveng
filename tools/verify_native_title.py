#!/usr/bin/env python3
"""Compare native Swift title animation with original decoded CFG/native writes."""
import hashlib,json,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()
def main():
    subprocess.run([sys.executable,str(ROOT/'tools/export_title_logo.py')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'tools/title_logo_evidence.py')],cwd=ROOT,check=True)
    out=ROOT/'analysis/local/title-logo';cases=out/'cases.json';binary=out/'verify-native-title'
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic/TitleLogo.swift',ROOT/'tests/native/VerifyTitleLogo.swift']
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,'-target',platform.machine()+'-apple-macosx14.0',
                    '-module-cache-path',str(out/'module-cache'),*map(str,sources),'-o',str(binary)],check=True)
    report=json.loads(subprocess.check_output([str(binary),str(cases)],text=True))
    report.update(method='Compiled Swift logo animation versus original P13/P14/P15/P16 CFG and original native P9/P10/P11/P12 writes',
                  evidence='analysis/title-logo-evidence.json',fixture_sha256=SHA(cases.read_bytes()),
                  source_files={str(p.relative_to(ROOT)):SHA(p.read_bytes()) for p in sources},
                  limitations=['No original sound-generator delay or exact scene timing is claimed.',
                               'Only the visual title animation and final composition are compared.'])
    (ROOT/'analysis/native-title-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
