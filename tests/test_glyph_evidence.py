import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from glyph_evidence import compose_row,hgr_row
from native_probe import CPU

class GlyphEvidenceTests(unittest.TestCase):
    def test_single_bit_and_cross_byte_shift(self):
        self.assertEqual(compose_row(255,255,1,0,127,0),(129,255))
        self.assertEqual(compose_row(128,128,3,6,63,0),(192,129))
    def test_phase_bits_preserved_and_font_high_bit_ignored(self):
        for phase in (0,128):
            for shift in range(7):
                result=compose_row(phase|0x55,phase|0x2a,0x7f,shift,0x7f,0x7f)
                self.assertEqual([v&128 for v in result],[phase,phase])
                self.assertEqual(result,compose_row(phase|0x55,phase|0x2a,0xff,shift,0x7f,0x7f))
        self.assertEqual(compose_row(0x91,0xc2,0,2,0,127),(0x91,0xc2))
        with self.assertRaises(ValueError):compose_row(0,0,0,7,0,0)
    def test_hgr_row_endpoints(self):
        self.assertEqual([hgr_row(y) for y in (0,8,64,191)],[0x2000,0x2080,0x2028,0x3fd0])
    def test_native_or_absolute_instruction_flags(self):
        c=CPU();c.pc=0x1000;c.memory[0x1000:0x1003]=bytes([0x0d,0,0x20]);c.memory[0x2000]=128;c.a=1;c.c=1
        c.step();self.assertEqual((c.a,c.n,c.z,c.c,c.pc),(129,1,0,1,0x1003))
