#!/usr/bin/env python3
"""Build project-owned Swift code with swiftc; no nested SwiftPM sandbox required."""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def build(tests=False):
    directory=ROOT/'analysis/local/native-build';directory.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'analysis/local/swift-direct-cache';cache.mkdir(parents=True,exist_ok=True)
    arch=platform.machine()
    swift=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    common=[swift,'-swift-version','6','-O','-sdk',sdk,'-module-cache-path',str(cache),'-target',arch+'-apple-macosx14.0']
    def run(args):subprocess.run(args,cwd=ROOT,check=True)
    def sources(target):return [str(p) for p in sorted((ROOT/'Sources'/target).glob('*.swift'))]
    def library(name,dependencies=()):
        run(common+['-parse-as-library','-emit-library','-static','-emit-module','-module-name',name,
                    '-emit-module-path',str(directory/(name+'.swiftmodule')),'-I',str(directory),'-L',str(directory)]+
                    ['-l'+d for d in dependencies]+sources(name)+['-o',str(directory/('lib'+name+'.a'))])
    library('AppleIIVideo');library('SunDogCore',('AppleIIVideo',))
    for target in ('SunDogInspect','SunDogMac'):
        run(common+['-parse-as-library','-I',str(directory),'-L',str(directory),'-lSunDogCore','-lAppleIIVideo']+
            sources(target)+['-o',str(directory/target)])
    app=ROOT/'Build/SunDog.app';macos=app/'Contents/MacOS';macos.mkdir(parents=True,exist_ok=True)
    shutil.copy2(directory/'SunDogMac',macos/'SunDog')
    info=dict(CFBundleExecutable='SunDog',CFBundleIdentifier='org.sundog.port.reference',
              CFBundleName='SunDog',CFBundleDisplayName='SunDog',CFBundlePackageType='APPL',
              CFBundleShortVersionString='0.1.0',CFBundleVersion='1',LSMinimumSystemVersion='14.0',
              NSHighResolutionCapable=True,NSPrincipalClass='NSApplication')
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    run(['codesign','--force','--sign','-',str(app)])
    run(['codesign','--verify','--strict',str(app)])
    if tests:
        developer=Path(subprocess.check_output(['xcode-select','-p'],text=True).strip())
        frameworks=developer/'Platforms/MacOSX.platform/Developer/Library/Frameworks'
        testing_lib=developer/'Platforms/MacOSX.platform/Developer/usr/lib'
        bundle=directory/'VideoTests.xctest'
        binary=bundle/'Contents/MacOS/VideoTests'
        binary.parent.mkdir(parents=True,exist_ok=True)
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(dict(
            CFBundleExecutable='VideoTests',CFBundleIdentifier='org.sundog.port.tests',
            CFBundlePackageType='BNDL',CFBundleName='VideoTests')))
        run([swift,'-swift-version','6','-O','-parse-as-library','-emit-library','-module-name','SunDogVideoTests',
             '-module-cache-path',str(cache),'-target',arch+'-apple-macosx14.0','-sdk',sdk,
             '-I',str(directory),'-L',str(directory),'-lSunDogCore','-lAppleIIVideo',
             '-I',str(testing_lib),'-L',str(testing_lib),'-lXCTestSwiftSupport',
             '-F',str(frameworks),'-framework','XCTest',
             '-Xlinker','-rpath','-Xlinker',str(frameworks),
             '-Xlinker','-rpath','-Xlinker',str(testing_lib),
             str(ROOT/'tests/VideoTests/HGRDecoderTests.swift'),'-o',str(binary)])
        run(['xcrun','xctest',str(bundle)])
    print(json.dumps(dict(app=str(app),inspector=str(directory/'SunDogInspect'),architecture=arch,
                         deployment='macOS 14+',scope='Reference screen viewer; no game VM yet')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tests',action='store_true');a=p.parse_args();build(a.tests)
