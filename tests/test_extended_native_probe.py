"""Independent tiny programs for native instruction forms used by later handlers."""
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from native_probe import CPU

class ExtendedNativeTests(unittest.TestCase):
    def program(self,raw):
        c=CPU();c.pc=0x8000;c.memory[0x8000:0x8000+len(raw)]=raw
        return c

    def test_indirect_y_compare_and_xor_wrap_zero_page(self):
        for raw,expected in ((b'\xd1\xff',(0x80,0,0,1)),(b'\x51\xff',(1,1,0,0))):
            c=self.program(raw);c.a=0x80;c.c=1;c.y=1
            c.memory[255]=255;c.memory[0]=0x40;c.memory[0x4100]=0x81
            c.step();self.assertEqual((c.a,c.c,c.z,c.n),expected)

    def test_absolute_indexed_load_and_mask_cross_page(self):
        c=self.program(bytes.fromhex('bcff403dff40'));c.x=1;c.a=0xf1;c.c=1;c.memory[0x4100]=0x80
        c.step();self.assertEqual((c.y,c.x,c.n),(0x80,1,1))
        c.step();self.assertEqual((c.a,c.c,c.z,c.n),(0x80,1,0,1))

    def test_indexed_compare_modes_preserve_accumulator(self):
        for raw,x,address in ((bytes.fromhex('d5fe'),2,0),(bytes.fromhex('ddff40'),1,0x4100)):
            c=self.program(raw);c.x=x;c.a=0x7f;c.memory[address]=0x80
            c.step();self.assertEqual((c.a,c.c,c.z,c.n),(0x7f,0,0,1))

    def test_cpx_and_absolute_store_preserve_flags(self):
        c=self.program(bytes.fromhex('e4fe8e0030'));c.x=0x81;c.memory[0xfe]=0x80
        c.step();self.assertEqual((c.c,c.z,c.n),(1,0,0))
        c.step();self.assertEqual((c.read(0x3000),c.c,c.z,c.n),(0x81,1,0,0))

    def test_indexed_increment_wraps_address_and_value(self):
        c=self.program(bytes.fromhex('feffff'));c.x=1;c.c=1;c.memory[0]=255
        c.step();self.assertEqual((c.read(0),c.c,c.z,c.n),(0,1,1,0))

if __name__=='__main__':unittest.main()
