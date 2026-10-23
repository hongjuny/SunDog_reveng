#!/usr/bin/env python3
"""Source-bound boot-to-title checks; no new device/emulator execution."""
import hashlib
import json
from pathlib import Path

from boot_regions import pages
from disk_analysis import DOS_TO_PHYSICAL, load
from native_probe import CPU

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda data: hashlib.sha256(data).hexdigest()
ROM_SHA = 'de1e3e035878bab43d0af8fe38f5839c527e9548647036598ee6fe7ec74d2a7d'


class BootProbe(CPU):
    """Only adds the three operand forms used by the declared boot snippets."""
    def step(self):
        op = self.read(self.pc)
        if op in (0xac, 0xcd, 0xd9):
            self.visited.add(self.pc); self.steps += 1
            self.fetch()
            address = self.fetch_word()
            if op == 0xac:
                self.y = self.nz(self.read(address))
            else:
                value = self.read((address + (self.y if op == 0xd9 else 0)) & 65535)
                self.c = int(self.a >= value); self.nz(self.a - value)
            return
        super().step()


def rom_post_read(rom, sector, threshold, page):
    c = BootProbe(); c.memory[0xc600:0xc700] = rom
    c.memory[0x3d] = sector; c.memory[0x800] = threshold
    c.memory[0x27] = page; c.memory[0x2b] = 0x60
    c.pc = 0xc6eb; c.run({0x801, 0xc6d3}, max_steps=20)
    return dict(next_pc=c.pc, sector=c.memory[0x3d], destination_page=c.memory[0x27], slot_x=c.x)


def bootstrap_reentry(boot, header, sector):
    c = BootProbe(); c.memory[0x800:0xb00] = boot
    c.memory[0x800] = header; c.memory[0x3d] = sector
    c.x = 0x60; c.pc = 0x801
    c.run({0xc65c, 0x819, 0x8b3}, max_steps=30)
    return dict(next_pc=c.pc, header=c.memory[0x800], sector=c.memory[0x3d])


def cold_start_clear(boot, initial):
    c = BootProbe(initial); c.memory[0x800:0xb00] = boot
    c.memory[0x800] = 5; c.pc = 0x819
    c.run({0x842, 0x867}, max_steps=50000)
    writes = [p for p, _ in c.writes if 0x2000 <= p < 0x4000]
    return dict(next_pc=c.pc, entered_clear_loop=0x82e in c.visited,
                hgr_write_count=len(writes), hgr_all_zero=not any(c.memory[0x2000:0x4000]),
                contiguous_hgr_writes=writes == list(range(0x2000, 0x4000)),
                signature_path_addresses=sorted(p for p in c.visited if 0x819 <= p < 0x842))


def main():
    disk = load(ROOT / 'extracted/utility.do')
    mapping = json.loads((ROOT / 'analysis/boot-mapping.json').read_text())
    boot = (ROOT / 'analysis/regions/boot-stage.bin').read_bytes()
    for i, row in enumerate(mapping):
        data = disk[row['offset']:row['offset'] + 256]
        if SHA(data) != row['sha256'] or boot[i*256:(i+1)*256] != data:
            raise ValueError('Boot-sector provenance differs')
        if DOS_TO_PHYSICAL[row['dos_sector']] != row['physical_sector']:
            raise ValueError('Boot-sector order differs')
    capture = ROOT / 'analysis/local/reference/20261023-115822'
    manifest = json.loads((capture / 'manifest.json').read_text())
    rom = (capture / 'slot6-rom.bin').read_bytes()
    if len(rom) != 256 or SHA(rom) != ROM_SHA or manifest['rom_hashes']['slot6'] != ROM_SHA:
        raise ValueError('Observed Disk II ROM identity differs')
    # Exact control fragments; no complete ROM listing is emitted publicly.
    if rom[0xeb:0xfb] != bytes.fromhex('e6 27 e6 3d a5 3d cd 00 08 a6 2b 90 db 4c 01 08'):
        raise ValueError('ROM post-read control fragment differs')
    if boot[0x4e:0x67] != bytes.fromhex('a9 00 8d 78 04 a9 40 85 3f a9 24 85 02 a9 c9 85 0f a9 00 20 ff 08 20 00 40'):
        raise ValueError('First-load/call parameters differ')
    sequence=[]
    for physical, threshold, page in ((0, 1, 8), (2, 3, 9), (4, 5, 10)):
        after = rom_post_read(rom, physical, threshold, page)
        reentry = bootstrap_reentry(boot, threshold, after['sector'])
        if after['next_pc'] != 0x801 or after['destination_page'] != page + 1:
            raise ValueError('ROM post-read result differs')
        expected_pc = 0x819 if threshold == 5 else 0xc65c
        if reentry['next_pc'] != expected_pc or reentry['header'] != (5 if threshold == 5 else threshold + 2):
            raise ValueError('Bootstrap header/skip result differs')
        sequence.append(dict(physical_sector=physical, threshold_before=threshold,
                             destination=page << 8, rom_post_read=after, bootstrap_reentry=reentry))
    checkpoints={}
    for row in manifest['checkpoints']:
        pc=int(row['pc'],16)
        if pc not in (0x801,0x8ff,0x4000,0xfef2,0xd293):continue
        memory=(capture/f'pc-{pc:04x}-main.bin').read_bytes()
        if len(memory)!=65536 or SHA(memory)!=row['main_sha256']:
            raise ValueError('Retained RAM identity differs')
        checkpoints[pc]=(row,memory)
    clear=cold_start_clear(boot,checkpoints[0x801][1])
    if not clear['entered_clear_loop'] or not clear['contiguous_hgr_writes'] or clear['hgr_write_count']!=8192:
        raise ValueError('Observed cold-start context does not clear HGR as expected')
    region,sectors=pages(201,36,disk)
    original_region=(ROOT/'analysis/regions/initial-4000.bin').read_bytes()
    memory=checkpoints[0x4000][1]
    if region!=original_region or memory[0x4000:0x6400]!=region:
        raise ValueError('Actual loaded native splash region differs')
    expected_boot=bytearray(boot);expected_boot[0]=5
    if memory[0x800:0xb00]!=expected_boot:
        raise ValueError('Runtime bootstrap differs beyond the observed header mutation')
    saved_return=memory[0x1ff] | (memory[0x100]<<8)
    if saved_return!=0x866 or any(memory[0x2000:0x4000]):
        raise ValueError('Title entry stack or clear-page state differs')
    splash=(ROOT/'analysis/local/native-assets/sundog-splash.hgr').read_bytes()
    if checkpoints[0xfef2][1][0x2000:0x4000]!=splash:
        raise ValueError('Post-title HGR differs from disk-derived asset')
    def source(address):
        if 0x800<=address<0xb00:
            row=mapping[(address-0x800)//256];within=address&255
            return dict(side='utility',track=row['track'],dos_sector=row['dos_sector'],physical_sector=row['physical_sector'],image_offset=row['offset']+within,byte_in_sector=within)
        row=sectors[(address-0x4000)//256];within=address&255
        return dict(side='utility',**row,image_offset=row['offset']+within,byte_in_sector=within)
    chain=[dict(address=a,source=source(a),role=role) for a,role in (
        (0x801,'Slot6 check and ROM-assisted sector-count expansion'),
        (0x819,'Resident-signature decision'),(0x82e,'Conditional full HGR clear'),
        (0x842,'Select HGR page1/full graphics'),(0x861,'Read block201,36 pages to4000'),
        (0x864,'Native JSR4000; pushed return0866'),(0x4000,'Native splash reveal entry'),
        (0x4200,'HGR destination row-address helper'),(0x41ff,'RTS returns0867'),
        (0x867,'Only after title: Language Card runtime loads'))]
    observed=[]
    for pc,(row,_) in checkpoints.items():
        fields=dict(part.split('=',1) for part in row['cpu'].split() if '=' in part)
        observed.append(dict(address=pc,cycles=int(fields['cycles']),cpu=row['cpu'],memory_sha256=row['main_sha256'],frame_sha256=row['frame']['sha256']))
    result=dict(method='Original disk and retained-ROM byte checks, bounded boot-fragment replay, and hash-bound existing execution checkpoints',
        side='utility',boot_sha256=SHA(boot),rom=dict(path=str((capture/'slot6-rom.bin').relative_to(ROOT)),sha256=ROM_SHA,
            source='Existing local a2m AppleIIPlus slot6 ROM capture; not proof of every historical physical controller ROM'),
        rom_entry=dict(initial_physical_sector=0,initial_destination=0x800,entry=0x801,header_role='Post-read sector-count threshold, not instruction'),
        header_and_sector_sequence=sequence,cold_start=clear,chain=chain,
        first_load=dict(block=201,pages=36,base=0x4000,end_exclusive=0x6400,sha256=SHA(region),captured_bytes_equal=True,
                        native_code_and_tables=[0x4000,0x4400],bitmap=[0x4400,0x6400],sectors=sectors),
        title_return=dict(jsr=0x864,saved_return=0x866,return_address=0x867,stack_offsets=[0x1ff,0x100],
                          observed_entry_stack_matches=True,complete_hgr_blank_at_entry=True),
        title_identity=dict(asset_sha256=SHA(splash),post_title_page_equal=True,
            logo='SUN DOG lettering and spaceship/planet are already bitmap pixels; no Pascal text/font rendering is needed here'),
        checkpoints=observed,
        confidence='High for this original Utility image and the retained ROM/model context',
        limitations=['Existing capture cycles include disk I/O and are not splash-only timing.',
            'No new emulator or hardware boot was run for this report.',
            'Resident-signature match can bypass first-load/title path; only retained cold-start context was replayed.',
            'Reveal animation timing and ordered stores are analyzed separately.',
            'ROM analog behavior, disk timing and display NTSC characteristics are outside fragment checks.'])
    (ROOT/'analysis/boot-splash-chain.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(header_sequence=[1,3,5],physical_sectors=[0,2,4],title_entry=0x4000,title_return=0x867,cold_clear_bytes=8192,loaded_bytes_equal=True)))


if __name__=='__main__':main()
