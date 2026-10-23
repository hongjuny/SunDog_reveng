#!/usr/bin/env python3
"""Stage ROM-assisted bootstrap. Physical sector 1 and 3 are skipped by INC $3D."""
import json,pathlib
from disk_analysis import load,offset,DOS_TO_PHYSICAL,digest
root=pathlib.Path(__file__).resolve().parents[1]; data=load(root/'extracted/utility.do')
parts=[]; mapping=[]
for page,physical in enumerate((0,2,4)):
    slot=DOS_TO_PHYSICAL.index(physical); p=offset(0,slot); b=data[p:p+256]; parts.append(b)
    mapping.append(dict(side='utility',track=0,dos_sector=slot,physical_sector=physical,offset=p,address=0x800+page*256,length=256,sha256=digest(b),confidence='conditional on standard Disk II ROM; derived from boot INC $3D'))
out=root/'analysis/regions';out.mkdir(exist_ok=True);(out/'boot-stage.bin').write_bytes(b''.join(parts))
(root/'analysis/boot-mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
