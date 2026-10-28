import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from post_title_render_evidence import rectangle, draw_character, compose_choices

class PostTitleRenderTests(unittest.TestCase):
    def test_partial_byte_clear_preserves_neighbor_pixels(self):
        page=bytearray([0xff]*8192)
        rectangle(page,2,4,0,0)
        self.assertEqual(page[0],0xe3)
        self.assertEqual(page[1],0xff)
        self.assertEqual(page[1024],0xff)
    def test_mode10_preserves_global_byte_parity(self):
        page=bytearray(8192)
        rectangle(page,7,20,0,0,mode=10)
        self.assertEqual(list(page[1:3]),[0xaa,0xd5])
        with self.assertRaises(ValueError):rectangle(page,-1,3,0,0)
    def test_pointer_xor_twice_restores_original_page(self):
        page=bytearray((i*31)&255 for i in range(8192));original=bytes(page)
        font=bytes((i*17)&127 for i in range(1024))
        draw_character(page,font,1,196,140,mask=0)
        self.assertNotEqual(page,original)
        draw_character(page,font,1,196,140,mask=0)
        self.assertEqual(page,original)
    def test_button_capacity_stops_before_unimplemented_record(self):
        with self.assertRaises(ValueError):compose_choices(bytes(8192),bytes(1024),[],[[65]]*4,{},None)

if __name__=='__main__':unittest.main()
