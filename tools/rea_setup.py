#!/usr/bin/env python3
"""Prepare an integration plan and bounded verification input; never edit client config."""
import argparse,hashlib,json,os,pathlib,struct,tomllib
ROOT=pathlib.Path(__file__).resolve().parents[1]

def binary_identity(path):
    p=pathlib.Path(path);raw=p.read_bytes()
    arm64=len(raw)>=8 and raw[:4]==bytes.fromhex('cffaedfe') and struct.unpack_from('<I',raw,4)[0]==0x0100000c
    return dict(path=str(p),size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mach_o_arm64=arm64)

def prepare():
    # D27B starts a real native fetch-loop entry and includes all of its local
    # short-immediate branch. D000 is a DATA table, not a raw execution seed.
    data=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    start,end,base=0xd27b,0xd2a0,0xd000
    raw=data[start-base:end-base]
    if raw[0x18:0x25]!=bytes.fromhex('a000b15810ef0a8d9ed26c00d0'):raise ValueError('fetch signature differs')
    target=ROOT/'analysis/regions/rea-fetch.bin';target.write_bytes(raw)
    source=json.loads((ROOT/'analysis/runtime-dispatch.json').read_text())
    regions=json.loads((ROOT/'analysis/boot-regions.json').read_text())
    source_sector=next(r for r in regions if r['name']=='runtime-bank1')['sectors'][(start-base)//256]
    disk_offset=source_sector['offset']+start%256
    disk=(ROOT/'extracted/utility.do').read_bytes()
    if disk[disk_offset:disk_offset+len(raw)]!=raw:raise ValueError('probe bytes differ from original logical sector')
    report=dict(path=str(target.relative_to(ROOT)),architecture='6502',load_and_entry=f'0x{start:x}',length=len(raw),sha256=hashlib.sha256(raw).hexdigest(),source_snapshot='analysis/regions/interpreter-ready.bin',source_snapshot_offset=start-base,source_disk='utility',source_sector=source_sector,source_disk_offset=disk_offset,source_byte_in_sector=start%256,check_address='0xd293',check_bytes='a000',expected_mnemonic='LDY',xref_scope='bounded fetch-loop slice only; not whole-program reference completeness',native_primary_patch=source['primary_patch'])
    (ROOT/'analysis/rea-probe-input.json').write_text(json.dumps(report,indent=2)+'\n')
    # Keep the installed server command, arguments and tool policy unchanged.
    values={
        'GHIDRA_INSTALL_DIR':'/Users/ay5/Applications/ghidra_12.1.4_PUBLIC',
        'JAVA_HOME':'/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home',
        'REA_DARWIN_MODULE_CACHE_PATH':str(ROOT/'analysis/local/rea/module-cache'),
        'REA_DARWIN_SWIFTC_PATH':'/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc',
        'SDKROOT':'/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',
    }
    config='[mcp_servers.rea.env]\n'+''.join(k+' = '+json.dumps(v)+'\n' for k,v in values.items())
    tomllib.loads(config)
    (ROOT/'analysis/rea-launch-proposed.toml').write_text('# Proposed environment only; not applied. Merge with any existing REA env values.\n'+config)
    print(json.dumps(report))

def check():
    install=pathlib.Path(os.environ['GHIDRA_INSTALL_DIR'])
    candidates=[install/'Ghidra/Features/Decompiler'/p/'mac_arm_64/decompile' for p in ('os','build/os')]
    native=next((p for p in candidates if p.is_file() and binary_identity(p)['mach_o_arm64']),None)
    java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java'
    result=dict(installation=str(install),application_properties=(install/'Ghidra/application.properties').is_file(),headless=(install/'support/analyzeHeadless').is_file(),native_decompiler=None if native is None else binary_identity(native),java=str(java),java_executable=os.access(java,os.X_OK),swift_module_cache=os.environ['REA_DARWIN_MODULE_CACHE_PATH'],swift_compiler=os.environ['REA_DARWIN_SWIFTC_PATH'],sdk=os.environ['SDKROOT'],scope='file validation only, not a successful REA provider session')
    print(json.dumps(result,indent=2))
    if native is None or not result['java_executable'] or not result['headless']:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check-files',action='store_true');args=p.parse_args()
    check() if args.check_files else prepare()
