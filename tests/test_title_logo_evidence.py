import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from title_logo_evidence import LogoProbe,LogoCFG

def proc(number,rows):
    return dict(procedure=dict(number=number,entry_address=0,lexical_level=1),instructions=rows)
def row(a,op,o=None,nextpc=None):
    return dict(address=a,opcode=op,operands=o or {},successors=[] if nextpc is None else [nextpc])

class TitleLogoEvidenceTests(unittest.TestCase):
    def test_indexed_indirect_zero_page_wrap(self):
        c=LogoProbe();c.pc=0x4000;c.x=1;c.memory[0x4000:0x4002]=bytes([0xa1,0xfe])
        c.memory[0xff]=0x00;c.memory[0]=0x30;c.memory[0x3000]=0x7f
        c.step();self.assertEqual(c.a,0x7f)
    def test_indirect_store_records_destination(self):
        c=LogoProbe();c.pc=0x4000;c.a=0x55;c.memory[0x4000:0x4002]=bytes([0x81,4])
        c.memory[4:6]=bytes([0x01,0x22]);c.step()
        self.assertEqual(c.writes,[(0x2201,0x55)])
    def test_unapproved_external_call_fails(self):
        r=proc(13,[row(0,0xcd,dict(segment_operand=22,procedure=99))])
        with self.assertRaisesRegex(ValueError,'outside logo contract'):LogoCFG({13:r},LogoProbe()).call(13)
    def test_branch_uses_low_bit_not_nonzero(self):
        rows=[row(0,2,nextpc=1),dict(address=1,opcode=0xa1,operands={},successors=[4,2]),
              row(2,0xcd,dict(segment_operand=22,procedure=99)),row(4,0xad)]
        state=LogoCFG({13:proc(13,rows)},LogoProbe());state.call(13)
        self.assertIn((13,4),state.visited)
        self.assertNotIn((13,2),state.visited)

if __name__=='__main__':unittest.main()
