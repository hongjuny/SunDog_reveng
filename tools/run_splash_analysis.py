#!/usr/bin/env python3
"""Persist checked splash labels in the existing native-stage Ghidra project."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    env = dict(os.environ,
        JAVA_HOME='/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home',
        JAVA_TOOL_OPTIONS=f'-Duser.home={ROOT}/analysis/local/home -Djava.io.tmpdir={ROOT}/analysis/local/tmp')
    log = ROOT / 'analysis/local/ghidra-splash.log'
    command = ['/Users/ay5/Applications/ghidra_12.1.4_PUBLIC/support/analyzeHeadless',
        str(ROOT / 'ghidra/projects'), 'SunDogNativeStages', '-process', 'initial-4000.bin', '-noanalysis',
        '-scriptPath', str(ROOT / 'ghidra/scripts'), '-postScript', 'AnnotateSplash.java',
        str(ROOT / 'analysis/ghidra-splash-annotations.json')]
    with log.open('w') as out:
        subprocess.run(command, cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    if 'SPLASH_ANNOTATIONS_OK' not in log.read_text():
        raise ValueError('Ghidra did not confirm annotation readback; inspect private log')
    if 'Save succeeded for processed file: /initial-4000.bin' not in log.read_text():
        raise ValueError('Ghidra did not confirm project save')
    print('Splash annotations checked and saved in SunDogNativeStages')

if __name__ == '__main__':
    main()
