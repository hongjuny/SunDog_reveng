#!/usr/bin/env python3
"""Compile reconstructed Swift game rules and compare native-backed synthetic cases."""
import hashlib,json,platform,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    output=ROOT/'analysis/local/native-rules';output.mkdir(parents=True,exist_ok=True)
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic/GameIntegerScale.swift',ROOT/'tests/native/VerifyGameIntegerScale.swift']
    binary=output/'verify-game-integer-scale'
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,'-target',platform.machine()+'-apple-macosx14.0',
                    '-module-cache-path',str(output/'module-cache'),*[str(p) for p in sources],'-o',str(binary)],check=True)
    cases=ROOT/'analysis/local/trade-scaling-cases.json'
    report=json.loads(subprocess.check_output([str(binary),str(cases)],text=True))
    report.update(method='Swift native arithmetic rule versus synthetic cases already checked through original Apple II handlers',
                  source_files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
                  native_probe_report='analysis/trade-scaling-evidence.json',
                  scope='One reconstructed game arithmetic helper; no application shell or original-code execution backend')
    (ROOT/'analysis/native-rule-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
