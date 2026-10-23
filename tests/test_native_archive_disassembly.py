"""Synthetic relocation fixtures do not require copyrighted disk bytes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_archive_disassembly import relocations,apply_relocations

class RelocationTests(unittest.TestCase):
    def fixture(self):
        data=bytearray(96)
        def word(a,v):data[a:a+2]=v.to_bytes(2,'little')
        # Four reverse arrays, one relocation each; count cells 76,72,68,64.
        for count,target in zip((76,72,68,64),(10,14,18,22)):
            word(count,1);word(count-2,count-2-target);word(target,3)
        return bytes(data),dict(kind='native-6502',entry_address=8,trailer_address=80)
    def test_backward_arrays_and_body_boundary(self):
        data,p=self.fixture();r=relocations(data,p)
        self.assertEqual(r['body_end_exclusive'],62)
        self.assertEqual([g['entries'][0]['target'] for g in r['groups']],[10,14,18,22])
    def test_distinct_base_classes(self):
        data,p=self.fixture();r=apply_relocations(data,[p],0x4000,0x9000,0xd1af)
        self.assertEqual([int.from_bytes(r[a:a+2],'little') for a in (10,14,18,22)],[0x9003,0x4003,0x400b,0xd1b2])
        self.assertEqual(data[10:12],b'\x03\x00')
    def test_invalid_count_is_rejected(self):
        data,p=self.fixture();b=bytearray(data);b[76:78]=b'\xff\xff'
        with self.assertRaises(ValueError):relocations(bytes(b),p)
    def test_target_outside_body_is_rejected(self):
        data,p=self.fixture();b=bytearray(data);b[74:76]=(74-2).to_bytes(2,'little')
        with self.assertRaises(ValueError):relocations(bytes(b),p)
    def test_duplicate_target_is_rejected(self):
        data,p=self.fixture();b=bytearray(data);b[70:72]=(70-10).to_bytes(2,'little')
        with self.assertRaises(ValueError):relocations(bytes(b),p)
    def test_adjacent_word_overlap_is_rejected(self):
        data,p=self.fixture();b=bytearray(data);b[70:72]=(70-11).to_bytes(2,'little')
        with self.assertRaises(ValueError):relocations(bytes(b),p)
    def test_truncated_source_is_rejected(self):
        data,p=self.fixture()
        with self.assertRaises(ValueError):relocations(data[:70],p)

if __name__=='__main__':unittest.main()
