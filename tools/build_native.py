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

def build(tests=False, include_local_assets=False):
    directory=ROOT/'analysis/local/native-build';directory.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'analysis/local/swift-direct-cache';cache.mkdir(parents=True,exist_ok=True)
    arch=platform.machine()
    swift=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    common=[swift,'-swift-version','6','-O','-sdk',sdk,'-module-cache-path',str(cache),'-target',arch+'-apple-macosx14.0']
    def run(args):subprocess.run(args,cwd=ROOT,check=True)
    def sources(target):
        directory = ROOT/'native/SunDogLogic' if target == 'SunDogLogic' else ROOT/'Sources'/target
        return [str(p) for p in sorted(directory.glob('*.swift'))]
    def library(name,dependencies=()):
        run(common+['-parse-as-library','-emit-library','-static','-emit-module','-module-name',name,
                    '-emit-module-path',str(directory/(name+'.swiftmodule')),'-I',str(directory),'-L',str(directory)]+
                    ['-l'+d for d in dependencies]+sources(name)+['-o',str(directory/('lib'+name+'.a'))])
    library('AppleIIVideo');library('SunDogLogic');library('SunDogCore',('AppleIIVideo','SunDogLogic'))
    for target in ('SunDogInspect','SunDogMac','SunDogReference','SunDogRender'):
        run(common+['-parse-as-library','-I',str(directory),'-L',str(directory),'-lSunDogCore','-lAppleIIVideo','-lSunDogLogic']+
            sources(target)+['-o',str(directory/target)])
    app=ROOT/'Build/SunDog.app';macos=app/'Contents/MacOS';macos.mkdir(parents=True,exist_ok=True)
    shutil.copy2(directory/'SunDogMac',macos/'SunDog')
    resources=app/'Contents/Resources';resources.mkdir(parents=True,exist_ok=True)
    for name in ('sundog-font.bin','sundog-splash.hgr','sundog-splash.json','sundog-splash-timing.json',
                 'sundog-title-logo.bin','sundog-title-logo.json'):
        asset=resources/name
        if asset.exists():asset.unlink()
    if include_local_assets:
        subprocess.run([os.sys.executable,str(ROOT/'tools/export_splash.py')],cwd=ROOT,check=True)
        subprocess.run([os.sys.executable,str(ROOT/'tools/export_title_logo.py')],cwd=ROOT,check=True)
        subprocess.run([os.sys.executable,str(ROOT/'tools/verify_native_splash.py')],cwd=ROOT,check=True)
        subprocess.run([os.sys.executable,str(ROOT/'tools/verify_native_title.py')],cwd=ROOT,check=True)
        shutil.copy2(ROOT/'analysis/local/native-assets/sundog-splash.hgr',resources/'sundog-splash.hgr')
        shutil.copy2(ROOT/'analysis/splash-asset.json',resources/'sundog-splash.json')
        shutil.copy2(ROOT/'analysis/local/native-assets/sundog-splash-timing.json',resources/'sundog-splash-timing.json')
        shutil.copy2(ROOT/'analysis/local/native-assets/sundog-logo.bin',resources/'sundog-title-logo.bin')
        shutil.copy2(ROOT/'analysis/title-logo-asset.json',resources/'sundog-title-logo.json')
    info=dict(CFBundleExecutable='SunDog',CFBundleIdentifier='org.sundog.port.native',
              CFBundleName='SunDog',CFBundleDisplayName='SunDog',CFBundlePackageType='APPL',
              CFBundleShortVersionString='0.5.1',CFBundleVersion='7',LSMinimumSystemVersion='14.0',
              NSHighResolutionCapable=True,NSPrincipalClass='NSApplication')
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    run(['codesign','--force','--sign','-',str(app)])
    run(['codesign','--verify','--strict',str(app)])
    if include_local_assets:
        diagnostic=json.loads(subprocess.check_output([str(macos/'SunDog'),'--diagnose',
                            '--export-startup',str(directory/'startup-splash.png')],text=True))
        if diagnostic['frame_width']!=560 or diagnostic['frame_height']!=192 or diagnostic['visible_pixels']<=0:
            raise RuntimeError('Bundled app did not generate a visible startup frame')
        if diagnostic['screen']!='original-title' or not diagnostic['title_complete']:
            raise RuntimeError('App did not compose the complete original title logo')
        (directory/'startup-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
        subprocess.run([os.sys.executable,str(ROOT/'tools/verify_splash_app.py')],cwd=ROOT,check=True)
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
             '-I',str(directory),'-L',str(directory),'-lSunDogCore','-lAppleIIVideo','-lSunDogLogic',
             '-I',str(testing_lib),'-L',str(testing_lib),'-lXCTestSwiftSupport',
             '-F',str(frameworks),'-framework','XCTest',
             '-Xlinker','-rpath','-Xlinker',str(frameworks),
             '-Xlinker','-rpath','-Xlinker',str(testing_lib),
             *[str(p) for p in sorted((ROOT/'tests/VideoTests').glob('*.swift'))],'-o',str(binary)])
        run(['xcrun','xctest',str(bundle)])
    print(json.dumps(dict(app=str(app),inspector=str(directory/'SunDogInspect'),architecture=arch,
                         deployment='macOS 14+',local_assets=include_local_assets,
                         scope='Boot background reveal followed by original title-logo sequence; gameplay is not implemented')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tests',action='store_true')
    p.add_argument('--include-local-assets',action='store_true',help='Bundle verified original splash for personal local use; do not distribute this bundle')
    a=p.parse_args();build(a.tests,a.include_local_assets)
