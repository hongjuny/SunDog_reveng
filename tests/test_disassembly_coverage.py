import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from disassembly_coverage import Space,classify_pcode,ranges

def instruction(address,opcode,length,successors=(),data=(),operands=None):
    return dict(address=address,opcode=opcode,length=length,successors=list(successors),data_ranges=list(data),operands=operands or {})

class DisassemblyCoverageTests(unittest.TestCase):
    def test_ranges_are_disjoint_and_half_open(self):
        self.assertEqual(ranges([4,1,2,2,7,8]),[[1,3],[4,5],[7,9]])
    def test_exact_zero_separator_needs_terminal_and_word_boundary(self):
        p=dict(entry_address=1,attribute_address=4,trailer_address=12)
        rows=[instruction(1,0xad,2)]
        roles,padding,unknown,conflicts=classify_pcode(Space([(0,bytes(16))]),p,rows)
        self.assertEqual(len(padding),1);self.assertEqual(unknown,[]);self.assertFalse(conflicts)
        self.assertEqual(roles[3],{'unreferenced_zero_alignment'})
        rows=[instruction(1,0xad,2,[3])]
        _,padding,unknown,_=classify_pcode(Space([(0,bytes(16))]),p,rows)
        self.assertFalse(padding);self.assertEqual(unknown,[[3,4]])
    def test_zero_run_or_nonzero_is_never_silently_padding(self):
        p=dict(entry_address=1,attribute_address=6,trailer_address=14)
        _,padding,unknown,_=classify_pcode(Space([(0,bytes(18))]),p,[instruction(1,0xad,2)])
        self.assertFalse(padding);self.assertEqual(unknown,[[3,6]])
        p=dict(entry_address=1,attribute_address=4,trailer_address=12)
        raw=bytearray(16);raw[3]=255
        _,padding,unknown,_=classify_pcode(Space([(0,raw)]),p,[instruction(1,0xad,2)])
        self.assertFalse(padding);self.assertEqual(unknown,[[3,4]])
    def test_inline_payload_is_not_counted_as_instruction_encoding(self):
        p=dict(entry_address=0,attribute_address=8,trailer_address=16)
        rows=[instruction(0,0xa6,6,[6],[(2,6)]),instruction(6,0xad,2)]
        roles,padding,unknown,conflicts=classify_pcode(Space([(0,bytes(20))]),p,rows)
        self.assertEqual(roles[2],{'inline_payload'});self.assertEqual(roles[0],{'pcode_encoding'})
        self.assertFalse(unknown);self.assertFalse(conflicts)
    def test_metadata_word_may_also_be_a_referenced_branch_cell(self):
        p=dict(entry_address=0,attribute_address=2,trailer_address=10)
        rows=[instruction(0,0xb9,2,[0],operands={'branch_cell':8})]
        roles,_,unknown,conflicts=classify_pcode(Space([(0,bytes(14))]),p,rows)
        self.assertEqual(roles[8],{'procedure_attributes','backward_branch_cell'})
        self.assertFalse(unknown);self.assertFalse(conflicts)
    def test_instruction_and_branch_pool_conflict_is_reported(self):
        p=dict(entry_address=0,attribute_address=2,trailer_address=10)
        rows=[instruction(0,0xb9,2,[0],operands={'branch_cell':1})]
        _,_,_,conflicts=classify_pcode(Space([(0,bytes(14))]),p,rows)
        self.assertEqual(conflicts[0]['address'],1)
    def test_case_alignment_and_cells_are_separate(self):
        p=dict(entry_address=0,attribute_address=12,trailer_address=20)
        rows=[instruction(0,0xac,6,[6,6],[(8,12)]),instruction(6,0xb9,2,[0])]
        roles,_,unknown,conflicts=classify_pcode(Space([(0,bytes(24))]),p,rows)
        self.assertEqual(roles[1],{'instruction_alignment'})
        self.assertEqual(roles[8],{'case_table'})
        self.assertFalse(unknown);self.assertFalse(conflicts)
