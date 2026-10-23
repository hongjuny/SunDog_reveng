#!/usr/bin/env python3
"""Export source identities and observations, never game/ROM bytes or screenshots."""
import json
from pathlib import Path
from reference_runtime import ROOT, sha
from boot_regions import pages


def export():
    inventory=[]
    for manifest in sorted((ROOT/'analysis/local/reference').glob('*/manifest.json')):
        source=json.loads(manifest.read_text())
        records=source.get('checkpoints',source.get('events',[]))
        inventory.append(dict(capture=str(manifest.parent.relative_to(ROOT)),
            manifest_sha256=sha(manifest.read_bytes()),status=source['status'],method=source.get('method'),
            model=source.get('model'),media_file=source.get('media_file'),
            original_media_sha256=source.get('original_media_sha256'),rom_hashes=source.get('rom_hashes'),
            executable=source.get('executable',{}).get('sha256',source.get('executable_sha256')),
            error=source.get('error'),keyboard_latch_verified=source.get('keyboard_latch_verified',False),
            unchanged=source.get('original_unchanged',source.get('private_copy_unchanged',source.get('mounted_copy_unchanged'))),
            records=[{k:r[k] for k in ('label','pc','cpu','state','softswitches','pcode_pc','main_sha256',
                        'boot_sector_matches','relocation_matches','segment0_matches','frame') if k in r} for r in records]))
    raw,provenance=pages(219,48)
    facts=[]
    disk=(ROOT/'extracted/utility.do').read_bytes()
    for address,meaning in ((0xd6a5,'Register-preserving input/poll routine; increments BF13/BF14'),
                            (0xd6e0,'LDA C000 keyboard latch read')):
        relative=address-0xd000;p=provenance[relative//256];location=dict(p,byte_in_sector=relative%256)
        offset=p['offset']+relative%256
        assert raw[relative:relative+3]==disk[offset:offset+3]
        facts.append(dict(side='utility',bank='lc2',address=hex(address),meaning=meaning,
                          location=location,image_offset=offset,confidence='static instruction observed; keyboard read also runtime observed'))
    result=dict(reference='a2m 3.0.0; upstream d863ad98487639445db16134d260221839cb72e9 plus local inherited-fd/raw-LF/path patches',
                hardware_model='Apple II Plus / NMOS 6502 / Language Card',
                limitations=['Emulator observations are not physical Apple II observations',
                             'Frontend wait-frame counts are not deterministic machine-frame or elapsed-time measurements',
                             'Play Track 34 remains unreadable and was not used as valid zero data',
                             'First capture has incorrect derived channel conversion and is excluded from visual validation'],
                input_native_facts=facts,rea_evidence_id='ev_57c20871b560617e0baefb49f3981d05bdd48c5d0ec71ebaed8b7699ac0d1c4e',
                captures=inventory)
    (ROOT/'analysis/reference-execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(captures=len(inventory),input_native_facts=facts)))

if __name__=='__main__':export()
