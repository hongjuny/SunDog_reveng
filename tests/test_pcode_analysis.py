import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pcode_analysis import Space,DecodeBoundary,decode_one,walk,mixed_directory

# Synthetic instruction fixtures; no original media required.
def catalogue():
    c={op:dict(rule='single',handler=0x4000,operands='none') for op in range(128,256)}
    for op,name in [(0xa1,'branch_even_word'),(0xb9,'jump_encoded'),(0xcd,'call_external_segment'),
                    (0x9e,'secondary_dispatch'),(0xad,'return_restore_context')]:c[op]['rule']=name
    return c

class PCodeAnalysisTests(unittest.TestCase):
    def test_variable_index_and_truncation(self):
        c=catalogue()
        self.assertEqual(decode_one(Space([(0,bytes([0xca,0x7f]))]),0,0,c)['length'],2)
        r=decode_one(Space([(0,bytes([0xca,0x81,0x23]))]),0,0,c)
        self.assertEqual((r['length'],r['operands']['index']),(3,0x123))
        with self.assertRaises(DecodeBoundary):decode_one(Space([(0,bytes([0xca,0x81]))]),0,0,c)
    def test_long_branch_is_trailer_relative_cell_not_signed_displacement(self):
        raw=bytearray(64);raw[0:2]=bytes([0xb9,0xe0]);raw[28:30]=(20).to_bytes(2,'little')
        r=decode_one(Space([(0,raw)]),0,60,catalogue())
        self.assertEqual(r['successors'],[8]);self.assertEqual(r['operands']['branch_cell'],28)
        raw[0]=0xa1
        self.assertEqual(decode_one(Space([(0,raw)]),0,60,catalogue())['successors'],[8,2])
    def test_inline_payload_is_skipped(self):
        raw=bytes([0xd0,3,0xcd,22,9,0xad,0])
        p=dict(entry_address=0,attribute_address=7,trailer_address=15)
        r=walk(Space([(0,raw)]),p,catalogue())
        self.assertEqual([i['address'] for i in r['instructions']],[0,5])
        self.assertFalse(any(i['calls'] for i in r['instructions']))
    def test_unknown_service_stops_instead_of_guessing_length(self):
        raw=bytes([0x9e,5,0xcd,22,9,0xad,0]);p=dict(entry_address=0,attribute_address=7,trailer_address=15)
        r=walk(Space([(0,raw)]),p,catalogue())
        self.assertEqual(len(r['instructions']),1)
        self.assertEqual(r['boundaries'][0]['selector'],5)
        self.assertFalse(r['complete_within_static_model'])
    def test_case_bounds_and_self_relative_targets(self):
        raw=bytearray(24);raw[0]=0xac;raw[2:4]=(-1).to_bytes(2,'little',signed=True);raw[4:6]=(0).to_bytes(2,'little')
        raw[8:10]=(8-2).to_bytes(2,'little');raw[10:12]=(10-4).to_bytes(2,'little')
        r=decode_one(Space([(0,raw)]),0,0,catalogue())
        self.assertEqual(r['successors'],[6,2,4]);self.assertEqual(r['data_ranges'],[(8,12)])
    def test_inline_word_parity_and_wrap_boundary(self):
        r=decode_one(Space([(1,bytes([0xb3,1,0,0x34,0x12]))]),1,0,catalogue())
        self.assertEqual(r['length'],5);self.assertEqual(r['data_ranges'],[(4,6)])
        with self.assertRaises(DecodeBoundary):decode_one(Space([(0,bytes([0xb3,0]))]),0,0,catalogue())
    def test_mixed_native_and_pcode_directory(self):
        raw=bytearray(32);raw[10:12]=(6).to_bytes(2,'little');raw[12]=0;raw[13]=29
        raw[22:24]=(22).to_bytes(2,'little');raw[24]=1;raw[25]=1
        raw[26:28]=(14).to_bytes(2,'little');raw[28:30]=(4).to_bytes(2,'little');raw[30:32]=bytes([22,2])
        rows=mixed_directory(raw)
        self.assertEqual([(r['number'],r['kind'],r['entry_address']) for r in rows],[(1,'pcode',0),(2,'native-6502',4)])
        raw[24]=7
        with self.assertRaises(ValueError):mixed_directory(raw)
    def test_missing_region_is_not_zero_filled(self):
        with self.assertRaises(DecodeBoundary):Space([(0,b'\x00')]).read(0,2)
