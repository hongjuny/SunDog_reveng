#!/usr/bin/env python3
"""Export the original boot title bitmap directly from verified Utility sectors.

No emulator, captured screenshot or copied application code is used to construct
the asset. A retained original RAM checkpoint is corroboration only.
"""
import hashlib
import json
from pathlib import Path

from boot_regions import pages
from disk_analysis import load

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda value: hashlib.sha256(value).hexdigest()
REGION_SHA = '1b9dfd8bbaa973ea73bc650e1c9161f3991d00d6a071bc2403d59582fdc6f29d'
RAW_SHA = '2b21fb1fc35477e73882e6f4003788631aa28e32d7cc6ed7991cdbaa317d17c1'
SPLASH_SHA = '623c8808ab8653a9d20bcbc26ce5cf4058a458764915a9b0c0071d9e35508c37'


def row_offset(row):
    if not 0 <= row < 192:
        raise ValueError('HGR row outside 0..191')
    return (row & 7) * 1024 + ((row >> 3) & 7) * 128 + (row >> 6) * 40


def normalize_hgr(raw):
    """Copy the 7,680 displayed bytes; canonicalize 512 non-display holes to zero."""
    if len(raw) != 8192:
        raise ValueError('Splash source must be exactly 8,192 bytes')
    page = bytearray(8192)
    for row in range(192):
        offset = row_offset(row)
        page[offset:offset + 40] = raw[offset:offset + 40]
    return bytes(page)


def main():
    disk_path = ROOT / 'extracted/utility.do'
    disk = load(disk_path)
    region, _ = pages(201, 36, disk)
    if SHA(region) != REGION_SHA:
        raise ValueError('Boot graphics region is not the established original')
    raw, sectors = pages(203, 32, disk)
    if raw != region[0x400:] or SHA(raw) != RAW_SHA:
        raise ValueError('Original title bitmap source differs')
    verification_path = ROOT / 'analysis/woz-full-checks.json'
    verification = json.loads(verification_path.read_text())
    decoded = {(r['track'], r['sector']): r for r in verification['sectors'] if r['side'] == 'utility'}
    sources = []
    for index, sector in enumerate(sectors):
        value = raw[index * 256:(index + 1) * 256]
        proof = decoded[sector['track'], sector['sector']]
        if proof['returncode'] != 0 or not proof['matches'] or proof['decoded_bytes'] != 256 or proof['sha256'] != SHA(value):
            raise ValueError('Original WOZ sector does not attest title source')
        sources.append(dict(side='utility', **sector, destination_offset=index * 256,
                            initial_load_address=0x4400 + index * 256, length=256, sha256=SHA(value)))
    asset = normalize_hgr(raw)
    if SHA(asset) != SPLASH_SHA:
        raise ValueError('Normalized original title differs')
    capture_dir = ROOT / 'analysis/local/reference/20261023-115822'
    capture_path = capture_dir / 'pc-fef2-main.bin'
    corroboration = dict(available=False, role='Optional corroboration; never the asset source')
    if capture_path.exists():
        manifest = json.loads((capture_dir / 'manifest.json').read_text())
        checkpoint = next(r for r in manifest['checkpoints'] if r.get('pc') == '0xfef2')
        memory = capture_path.read_bytes()
        if len(memory) != 65536 or SHA(memory) != checkpoint['main_sha256']:
            raise ValueError('Retained boot reference RAM identity differs')
        switches = dict(part.split('=', 1) for part in checkpoint['softswitches'].split() if '=' in part)
        if any(switches.get(key) != value for key, value in {'TEXT': '0', 'HIRES': '1', 'MIXED': '0', 'PAGE2': '0'}.items()):
            raise ValueError('Retained reference is not full-screen HGR page 1')
        if memory[0x2000:0x4000] != asset:
            raise ValueError('Disk-derived splash differs from observed original boot RAM')
        corroboration = dict(available=True, path=str(capture_path.relative_to(ROOT)),
                             memory_sha256=SHA(memory), checkpoint='0xFEF2',
                             page_address=0x2000, full_page_equal=True, visible_bytes_equal=7680,
                             role='Original post-animation boot RAM corroborates disk-derived asset; not used for construction')
    output = ROOT / 'analysis/local/native-assets/sundog-splash.hgr'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(asset)
    report = dict(artifact=str(output.relative_to(ROOT)), length=8192, sha256=SHA(asset),
                  raw_sha256=SHA(raw), width=280, height=192, decoded_width=560,
                  identity='Original boot spaceship/planet background, without the later SUN DOG logo',
                  method='Direct verified disk-sector extraction in original loader order; HGR non-display-hole normalization',
                  source_side='utility', source_image=str(disk_path.relative_to(ROOT)), source_image_sha256=SHA(disk),
                  loader=dict(entry=0x4000, region_start_block=201, region_pages=36,
                              region_sha256=SHA(region), image_start_block=203, image_pages=32,
                              image_loaded_address=0x4400, target_address=0x2000,
                              source_minus_destination=0x2400,
                              row_helper=0x4200, low_table=0x4210, high_table=0x42d0,
                              copy_examples=[dict(read=0x4030, write=0x4032), dict(read=0x40e3, write=0x40e5),
                                             dict(read=0x41d4, write=0x41d6)]),
                  displayed_bytes=7680, nondisplay_padding_bytes=512,
                  padding_policy='Zero, matching cleared boot HGR RAM; no displayed pixel byte is changed',
                  woz_verification_sha256=SHA(verification_path.read_bytes()), sources=sources,
                  corroboration=corroboration,
                  confidence='High for original boot background bytes; the later SUN DOG logo is separate',
                  limitations=['Initial native reveal animation and timing are not implemented by this static asset.',
                               'RGB/NTSC color fidelity depends on the separately declared HGR decoder profile.',
                               'Displaying this splash does not implement the game or Utility menu.'])
    (ROOT / 'analysis/splash-asset.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('artifact', 'length', 'sha256')}))


if __name__ == '__main__':
    main()
