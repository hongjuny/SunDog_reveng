import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from splash_reveal_evidence import RevealProbe, reveal_offsets, row_offset


class SplashRevealTests(unittest.TestCase):
    def test_complete_visible_coverage_without_padding(self):
        offsets, milestones = reveal_offsets()
        visible = {row_offset(y)+x for y in range(192) for x in range(40)}
        self.assertEqual(set(offsets), visible)
        self.assertEqual(len(offsets), 8041)
        self.assertEqual(len(set(offsets)), 7680)
        self.assertEqual(len(milestones), 20)
        self.assertEqual(milestones[-1]['write_count'], 8041)
    def test_seed_and_exact_first_ring_order(self):
        offsets, milestones = reveal_offsets()
        self.assertEqual(offsets[:4], [row_offset(y)+x for y in (95,96) for x in (19,20)])
        self.assertEqual(offsets[4:9], [row_offset(y)+18 for y in range(90,95)])
        self.assertEqual(offsets[24:36], [row_offset(y)+21 for y in range(90,102)])
        self.assertEqual(offsets[56:67], [row_offset(y)+18 for y in range(101,90,-1)])
        self.assertEqual(milestones[1]['write_count'], 67)
    def test_final_ring_bounds(self):
        _, milestones = reveal_offsets()
        ring = milestones[-1]
        self.assertEqual([ring[k] for k in ('left','right','top','bottom')], [0,39,0,191])
        with self.assertRaises(ValueError): row_offset(192)
        with self.assertRaises(ValueError): row_offset(-1)
    def test_branch_page_cycle_penalty(self):
        c=RevealProbe();c.pc=0x40fe;c.memory[0x40fe:0x4100]=bytes([0xd0,0xfe]);c.z=0
        c.step()
        self.assertEqual((c.pc,c.cycles),(0x40fe,4))
        c.z=1;c.step()
        self.assertEqual((c.pc,c.cycles),(0x4100,6))
    def test_indexed_page_cycle_penalty(self):
        c=RevealProbe();c.pc=0x4000;c.x=90
        c.memory[0x4000:0x4003]=bytes([0xbd,0xd0,0x42]);c.memory[0x432a]=0x7f
        c.step()
        self.assertEqual((c.a,c.cycles),(0x7f,5))
    def test_indirect_store_timestamp_and_pointer_increment(self):
        c=RevealProbe();c.pc=0x4000;c.memory[4:6]=bytes([0,0x20])
        c.memory[0x4000:0x4006]=bytes([0xa9,0x7f,0x81,4,0xf6,4])
        c.step();c.step();c.step()
        self.assertEqual(c.events,[dict(offset=0,value=0x7f,cycles=8)])
        self.assertEqual((c.read(4),c.cycles),(1,14))


if __name__=='__main__':unittest.main()
