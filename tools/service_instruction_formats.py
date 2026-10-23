#!/usr/bin/env python3
"""Disassembly-only 9E instruction formats; not complete service behavior proofs."""
import hashlib,json
from pathlib import Path
from runtime_evidence import provenance
ROOT=Path(__file__).resolve().parents[1]
# Actual native branch/continuation extents. Native callees may be outside a view;
# normal returns are conditional. EXIT and error/reset paths are terminal transfers.
VIEWS={0x00:(0xeedc,0xeee7,'check_io_result','fallthrough'),0x01:(0xd673,0xd6af,'allocate','fallthrough'),
0x02:(0xe878,0xe8dc,'copy_forward','fallthrough'),0x03:(0xe878,0xe8dc,'copy_backward','fallthrough'),
0x04:(0xe75c,0xe803,'exit_procedure','nonlocal_exit'),0x05:(0xf041,0xf14a,'unit_read','fallthrough'),
0x06:(0xf046,0xf14a,'unit_write','fallthrough'),0x09:(0xe819,0xe835,'clear_pointer_pair','fallthrough'),
0x0a:(0xe68a,0xe6cf,'fill_bytes','fallthrough'),0x0b:(0xe6cf,0xe75c,'scan_bytes','fallthrough'),
0x0c:(0xeeff,0xef7d,'unit_status','fallthrough'),0x15:(0xe66b,0xe675,'acquire_segment','fallthrough'),
0x16:(0xe675,0xe67f,'release_segment','fallthrough'),0x20:(0xd6af,0xd6c6,'snapshot_allocation_cursor','fallthrough'),
0x21:(0xd6c6,0xd6e4,'restore_allocation_cursor','fallthrough'),0x22:(0xeed1,0xeedc,'read_io_result','fallthrough'),
0x23:(0xeee7,0xeef5,'unit_query','fallthrough'),0x25:(0xeef5,0xeeff,'validate_unit','fallthrough'),
0x26:(0xef7d,0xf00e,'unit_initialization','fallthrough'),0x27:(0xe80b,0xe819,'raise_runtime_error','error_transfer'),
0x28:(0xe8dc,0xe8ff,'available_words','fallthrough')}

def prepare():
    raw=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes();rows=[]
    for selector,(start,end,name,flow) in VIEWS.items():
        path=ROOT/f'analysis/regions/rea-service-format-{selector:02x}.bin';data=raw[start-0xd000:end-0xd000];path.write_bytes(data)
        old=ROOT/f'analysis/local/rea/service-{selector:02x}.json'
        if selector==3:old=ROOT/'analysis/local/rea/service-format-02.json'
        if old.exists():
            evidence=json.loads(old.read_text())
            if evidence['subject']['digest']['sha256']!=hashlib.sha256(data).hexdigest():old=None
        else:old=None
        rows.append(dict(selector=selector,entry=start,end_exclusive=end,name=name,flow=flow,path=str(path.relative_to(ROOT)),
                         sha256=hashlib.sha256(data).hexdigest(),existing_evidence=str(old.relative_to(ROOT)) if old else None))
    (ROOT/'analysis/local/service-format-inputs.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

def verify():
    raw=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes();dispatch=json.loads((ROOT/'analysis/runtime-dispatch.json').read_text())
    # These native instructions establish two-byte dispatch and normal advancement.
    if raw[0xe67f-0xd000:0xe68a-0xd000]!=bytes.fromhex('a001b1580a8d88e66c00d1'):raise ValueError('selector reader differs')
    if raw[0xd27b-0xd000:0xd284-0xd000]!=bytes.fromhex('a5581869028558900f'):raise ValueError('normal PC+2 continuation differs')
    rows=[]
    inputs=json.loads((ROOT/'analysis/local/service-format-inputs.json').read_text())
    for entry in dispatch['secondary']:
        selector=entry['selector'];handler=entry['handler']
        if handler==0:
            rows.append(dict(selector=selector,native_handler=0,pcode_length=2,flow='invalid_service',name='zero_dispatch_cell',format_verified=True,
                             proof='selector byte is consumed by common dispatcher; zero baseline target is invalid',source=entry['table_source']));continue
        if handler==0xd1ef:
            rows.append(dict(selector=selector,native_handler=handler,pcode_length=2,flow='error_transfer',name='shared_error_111',format_verified=True,
                             proof='shared primary/native exception prefix; not a returning service',source=entry['handler_source']));continue
        spec=next(s for s in inputs if s['selector']==selector)
        if handler!=spec['entry']:raise ValueError('service table entry differs')
        path=ROOT/(spec['existing_evidence'] or f'analysis/local/rea/service-format-{selector:02x}.json')
        if selector==3:path=ROOT/'analysis/local/rea/service-format-02.json'
        evidence=json.loads(path.read_text())
        if evidence['provider']['id']!='ghidra' or evidence['subject']['digest']['sha256']!=spec['sha256']:raise ValueError('native evidence identity differs')
        # Selector 2/3 rereads only byte +1. Other fixed-inline native handlers
        # receive their parameters from stack/frame/device state, not p-code +2.
        row=dict(selector=selector,native_handler=handler,pcode_length=2,name=spec['name'],flow=spec['flow'],format_verified=True,
                 source=provenance(handler),native_slice_sha256=spec['sha256'],rea_evidence_id=evidence['evidence_id'],
                 proof='native selector reader +1, stack-based arguments and explicit continuation/transfer; full service behavior not claimed')
        if selector==4:row['transfer']='exit target = (target trailer - 4) - word(target trailer - 4); frame unwind may select another procedure'
        rows.append(row)
    result=dict(method='Instruction encoding and native control-transfer classification, distinct from complete I/O/loader semantics',
                snapshot_sha256=hashlib.sha256(raw).hexdigest(),opcode=0x9e,services=rows,
                scope='41 baseline selector cells; reserved/error cells explicitly terminal; callable service normal returns conditional',
                limitations=['Indirect/native device behavior is not reconstructed by an instruction-length proof.',
                             'Nonlocal EXIT destination may depend on stack arguments and runtime frames.',
                             'Runtime dispatch-table patches must be represented as separate states.'])
    (ROOT/'analysis/service-instruction-formats.json').write_text(json.dumps(result,indent=2)+'\n');print('Verified 41 baseline service formats/control classes.')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args();prepare() if a.prepare else verify()
