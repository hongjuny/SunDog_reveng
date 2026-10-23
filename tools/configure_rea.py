#!/usr/bin/env python3
"""Review/apply the prepared REA environment without replacing other Codex settings."""
import argparse,copy,hashlib,json,os,pathlib,re,stat,tempfile,tomllib
ROOT=pathlib.Path(__file__).resolve().parents[1]
KEYS={'GHIDRA_INSTALL_DIR','JAVA_HOME','REA_DARWIN_MODULE_CACHE_PATH','REA_DARWIN_SWIFTC_PATH','SDKROOT'}

def merge_environment(original,fragment):
    before=tomllib.loads(original);proposal=tomllib.loads(fragment)
    if set(proposal)!={'mcp_servers'} or set(proposal['mcp_servers'])!={'rea'} or set(proposal['mcp_servers']['rea'])!={'env'}:raise ValueError('fragment must contain only the REA environment table')
    requested=proposal['mcp_servers']['rea']['env']
    if set(requested)!=KEYS or not all(isinstance(v,str) for v in requested.values()):raise ValueError('expected the five prepared REA path variables')
    rea=before.get('mcp_servers',{}).get('rea')
    if rea is None:raise ValueError('REA registration is missing; refusing to replace another server')
    current=rea.get('env',{})
    changes={k:{'before':current.get(k),'after':v} for k,v in requested.items() if current.get(k)!=v}
    if not changes:return original,changes
    expected=copy.deepcopy(before);expected['mcp_servers']['rea'].setdefault('env',{}).update(requested)
    header=re.search(r'^\s*\[mcp_servers\.rea\.env\]\s*(?:#[^\n]*)?$',original,re.M)
    if header:
        end=re.search(r'^\s*\[',original[header.end():],re.M)
        limit=header.end()+end.start() if end else len(original)
        body=original[header.end():limit]
        for key,item in changes.items():
            line=key+' = '+json.dumps(item['after'])
            pattern=r'^\s*'+re.escape(key)+r'\s*=.*$'
            if re.search(pattern,body,re.M):body=re.sub(pattern,lambda _:line,body,count=1,flags=re.M)
            else:body=body.rstrip('\n')+'\n'+line+'\n'
        candidate=original[:header.end()]+body+original[limit:]
    else:
        candidate=original.rstrip('\n')+'\n\n[mcp_servers.rea.env]\n'+''.join(k+' = '+json.dumps(v)+'\n' for k,v in requested.items())
    # Full parsed equality is the guard against changing another server, approval
    # setting, model, project setting, or unrelated environment variable.
    if tomllib.loads(candidate)!=expected:raise ValueError('merge would alter unrelated configuration')
    return candidate,changes

def apply_config(config_path,fragment):
    visible=pathlib.Path(config_path).expanduser();target=visible.resolve(strict=True)
    original_bytes=target.read_bytes();original=original_bytes.decode('utf-8')
    candidate,changes=merge_environment(original,fragment)
    sha=hashlib.sha256(original_bytes).hexdigest()
    backup=target.with_name(target.name+'.rea-backup-'+sha[:16])
    result=dict(config=str(visible),resolved_config=str(target),backup=str(backup),configuration_sha256=sha,changes=changes,other_parsed_settings_preserved=True)
    return candidate,original_bytes,result

def write_config(config_path,fragment):
    candidate,original,result=apply_config(config_path,fragment)
    if not result['changes']:return dict(**result,status='already_configured')
    target=pathlib.Path(result['resolved_config']);backup=pathlib.Path(result['backup'])
    # Check write access before making a backup. O_RDWR does not change contents.
    fd=os.open(target,os.O_RDWR)
    os.close(fd)
    if backup.exists():
        if backup.read_bytes()!=original:raise ValueError('backup identity conflict')
    else:
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(original);stream.flush();os.fsync(stream.fileno())
    temporary=None
    try:
        fd,name=tempfile.mkstemp(prefix=target.name+'.rea-',dir=target.parent);temporary=pathlib.Path(name)
        os.fchmod(fd,stat.S_IMODE(target.stat().st_mode))
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(candidate);stream.flush();os.fsync(stream.fileno())
        if target.read_bytes()!=original:raise ValueError('configuration changed during preparation; retry from a fresh review')
        os.replace(temporary,target);temporary=None
        if tomllib.loads(target.read_text())!=tomllib.loads(candidate):raise ValueError('configuration readback mismatch')
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return dict(**result,status='applied',requires_reconnect=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,default=pathlib.Path.home()/'.codex/config.toml');ap.add_argument('--fragment',type=pathlib.Path,default=ROOT/'analysis/rea-launch-proposed.toml');ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    fragment=args.fragment.read_text()
    if args.apply:
        try:result=write_config(args.config,fragment)
        except PermissionError as error:
            print(json.dumps(dict(status='permission_denied',path=error.filename,errno=error.errno,message=error.strerror,requires='Apply the reviewed change in a terminal with normal access to this configuration file, then reconnect REA.'),indent=2))
            raise SystemExit(2)
    else:
        _,_,result=apply_config(args.config,fragment);result['status']='review_only'
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
