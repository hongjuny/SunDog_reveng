import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from text_layout_evidence import TextCFG, Boundary


def procedure(rows):
    return {48:dict(procedure=dict(entry_address=0),instructions=rows)}


def instruction(address,opcode,operands=None,successors=None):
    return dict(address=address,opcode=opcode,operands=operands or {},successors=successors or [])


class TextCFGEvidenceTests(unittest.TestCase):
    def state(self):return dict(left=0,right=80,bottom=100,x=2,y=15)

    def test_branch_uses_low_bit_not_general_nonzero(self):
        # Word 2 is false to native A1 even though it is nonzero.
        rows=[instruction(0,2,successors=[1]),instruction(1,0xa1,successors=[3,4]),
              instruction(3,0xad,dict(result_words=0)),instruction(4,0xff)]
        cfg=TextCFG(procedure(rows),self.state())
        self.assertIsNone(cfg.run('')['boundary'])
        self.assertNotIn((48,4),cfg.visited)

    def test_local_byte_writes_preserve_real_aliasing(self):
        cfg=TextCFG({},self.state())
        base=0x7000
        cfg.put(base+2*59,0x1234)
        cfg.memory[base+2*49+20]=0xab
        self.assertEqual(cfg.word(base+2*59),0x12ab)

    def test_capacity_fails_instead_of_truncating(self):
        rows=[instruction(0,0xc6,dict(index=2),[1]),instruction(1,0xd8,dict(index=1),[2]),
              instruction(2,0xaa,dict(count=1),[3]),instruction(3,0xad,dict(result_words=0))]
        self.assertEqual(TextCFG(procedure(rows),self.state()).run('AB')['boundary'],'string_error_113')
        self.assertIsNone(TextCFG(procedure(rows),self.state()).run('A')['boundary'])

    def test_unknown_calls_do_not_run_speculatively(self):
        cfg=TextCFG({},self.state())
        with self.assertRaises(Boundary):cfg.call(31)
        with self.assertRaisesRegex(Boundary,'bottom_P44'):cfg.call(44)


if __name__=='__main__':unittest.main()
