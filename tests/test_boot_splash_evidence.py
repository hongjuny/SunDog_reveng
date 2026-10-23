import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from boot_splash_evidence import rom_post_read, bootstrap_reentry


class BootSplashTests(unittest.TestCase):
    def test_rom_post_read_threshold_and_continue_branch(self):
        rom = bytearray(256)
        rom[0xeb:0xfb] = bytes.fromhex('e6 27 e6 3d a5 3d cd 00 08 a6 2b 90 db 4c 01 08')
        exact = rom_post_read(rom, sector=2, threshold=3, page=9)
        self.assertEqual(exact, dict(next_pc=0x801, sector=3, destination_page=10, slot_x=0x60))
        remaining = rom_post_read(rom, sector=0, threshold=3, page=8)
        self.assertEqual(remaining['next_pc'], 0xc6d3)

    def test_game_header_expands_before_rom_reentry(self):
        boot = bytearray(768)
        boot[1:0x19] = bytes.fromhex('e0 60 f0 03 4c b3 08 ad 00 08 c9 04 b0 0a 69 02 8d 00 08 e6 3d 4c 5c c6')
        a = bootstrap_reentry(boot, header=1, sector=1)
        b = bootstrap_reentry(boot, header=3, sector=3)
        final = bootstrap_reentry(boot, header=5, sector=5)
        self.assertEqual((a['header'], a['sector'], a['next_pc']), (3, 2, 0xc65c))
        self.assertEqual((b['header'], b['sector'], b['next_pc']), (5, 4, 0xc65c))
        self.assertEqual((final['header'], final['sector'], final['next_pc']), (5, 5, 0x819))


if __name__ == '__main__': unittest.main()
