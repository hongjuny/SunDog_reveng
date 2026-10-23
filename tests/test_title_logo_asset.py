import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from export_title_logo import compose_final, row_offset


class TitleLogoAssetTests(unittest.TestCase):
    def test_final_frame_uses_six_frame7_sprites_and_or80(self):
        background=bytes([0x13])*8192
        glyphs=bytes((i//1024*17+i//128*3+i%128)&127 for i in range(6144))
        page=compose_final(background,glyphs)
        self.assertEqual(page[row_offset(44)+10], glyphs[2*1024+7*128]|128)
        self.assertEqual(page[row_offset(67)+28],glyphs[5*1024+7*128+23*4+3]|128)
        self.assertEqual(page[row_offset(44)+4],0)
    def test_bars_clear_and_outside_preservation(self):
        background=bytes([0x13])*8192
        page=compose_final(background,bytes(6144))
        self.assertEqual(page[row_offset(36):row_offset(36)+4],bytes([0xaa,0xd5,0xaa,0xd5]))
        self.assertEqual(page[row_offset(72)+29],0)
        self.assertEqual(page[row_offset(32)+1],0)
        for row,column in ((0,0),(31,29),(80,0),(44,30)):
            self.assertEqual(page[row_offset(row)+column],0x13)
    def test_invalid_asset_sizes_and_coordinates(self):
        for background,glyphs in ((bytes(8191),bytes(6144)),(bytes(8192),bytes(6143))):
            with self.assertRaises(ValueError):compose_final(background,glyphs)
        with self.assertRaises(ValueError):row_offset(-1)
        with self.assertRaises(ValueError):row_offset(192)


if __name__=='__main__':unittest.main()
