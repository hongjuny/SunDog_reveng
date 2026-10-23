#!/usr/bin/env python3
"""Structural checks; mathematical matches do not identify active runtime formats."""
import json,pathlib,struct
from disk_analysis import load,DOS_TO_PHYSICAL,digest
from boot_regions import pages
root=pathlib.Path(__file__).resolve().parents[1]
b,provenance=pages(201,36)
def hgr_address(y):
    if not 0<=y<192:raise ValueError('row out of range')
    return 0x2000+(y&7)*1024+((y>>3)&7)*128+(y>>6)*40
rows=[dict(row=y,observed=b[0x210+y]+256*b[0x2d0+y],expected=hgr_address(y)) for y in range(192)]
source=[]
for n in (2,3):source.append(dict(memory_page=0x40+n,**provenance[n]))
(root/'analysis/graphics-evidence.json').write_text(json.dumps(dict(side='utility',region='initial-4000',lookup_routine=0x4200,low_table=0x4210,high_table=0x42d0,source_sectors=source,all_rows_match=all(r['observed']==r['expected'] for r in rows),rows=rows,confidence='high: all 192 row base addresses match Apple II HGR page 1 formula; no whole-game engine attribution'),indent=2)+'\n')
d=load(root/'extracted/utility.do');groups=[]
for p in range(0,len(d)-26,2):
    start,end,kind=struct.unpack_from('<HHH',d,p);n=d[p+6]
    if (start,end,kind,n)!=(0,3,0,6) or d[p+7:p+13]!=b'SUNDOG':continue
    entries=[];q=p+26;previous=3
    while q+26<=len(d):
        start,end,kind=struct.unpack_from('<HHH',d,q);n=d[q+6]
        name=d[q+7:q+7+n]
        if not (start==previous and start<end<=280 and kind<=8 and 1<=n<=15 and all(x in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789. _-' for x in name)):break
        entries.append(dict(offset=q,track=q//4096,sector=q//256%16,byte_in_sector=q%256,start_block=start,end_block=end,kind=kind,name=name.decode()))
        previous=end;q+=26
    if entries:groups.append(dict(side='utility',offset=p,track=p//4096,sector=p//256%16,entry_count=len(entries),covers_blocks_3_through_279=previous==280,entries=entries,confidence='medium for directory-shaped contiguous extents; active location and addressing unconfirmed'))
(root/'analysis/pascal-candidates.json').write_text(json.dumps(groups,indent=2)+'\n')
print(json.dumps(dict(hgr_rows_matched=sum(r['observed']==r['expected'] for r in rows),directory_groups=len(groups))))
