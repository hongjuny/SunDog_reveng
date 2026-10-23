#!/usr/bin/env python3
"""Reproduce native staged-view Ghidra classifications in a separate project."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--view',action='append');args=parser.parse_args()
    out=ROOT/'analysis/local/native-stages';out.mkdir(parents=True,exist_ok=True)
    views=[('boot-stage',0x800,'801,8ff'),('initial-4000',0x4000,'4000,4200'),('lc-bank2',0xd000,'fef2,'+(ROOT/'analysis/local/bios-seeds.txt').read_text().strip()),('runtime-bank1',0xd000,'feec,'+(ROOT/'analysis/local/runtime-seeds.txt').read_text().strip()),('relocated-6800',0x6800,'6800,68b9,68c4'),('interpreter-ready',0xd000,'feec,'+(ROOT/'analysis/local/ready-seeds.txt').read_text().strip()),('play-bootstrap-code',0x801,'801')]
    env=dict(os.environ,JAVA_HOME='/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home',JAVA_TOOL_OPTIONS=f'-Duser.home={ROOT}/analysis/local/home -Djava.io.tmpdir={ROOT}/analysis/local/tmp')
    records=[]
    for name,base,seeds in views:
        source=ROOT/'analysis/regions'/(name+'.bin');data=source.read_bytes();dest=out/(name+'.json')
        command=['/Users/ay5/Applications/ghidra_12.1.4_PUBLIC/support/analyzeHeadless',str(ROOT/'ghidra/projects'),'SunDogNativeStages','-import',str(source),'-overwrite','-noanalysis','-processor','6502:LE:16:default','-loader','BinaryLoader','-loader-baseAddr',f'{base:x}','-scriptPath',str(ROOT/'ghidra/scripts'),'-postScript','ExportBoot.java',str(out/(name+'.txt')),seeds,'-postScript','ExportNativeStage.java',str(dest),f'{base:x}',str(len(data))]
        if args.view is None or name in args.view:
            with (out/(name+'.log')).open('w') as f:subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        if 'NATIVE_STAGE_EXPORT_OK' not in (out/(name+'.log')).read_text():raise ValueError(name+' export failed')
        record=json.loads(dest.read_text());record.update(source_path=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(data).hexdigest(),seeds=[int(s,16) for s in seeds.split(',')],private_listing=str((out/(name+'.txt')).relative_to(ROOT)))
        records.append(record)
    (ROOT/'analysis/native-stage-disassembly.json').write_text(json.dumps(dict(method='Ghidra12.1.4 recursive native disassembly from retained stage-specific entry seeds, protected known dispatch/mask/pcode data, with explicit untyped DB ranges',views=records),indent=2)+'\n')
    print('Exported',len(records),'native stage views')
if __name__=='__main__':main()
