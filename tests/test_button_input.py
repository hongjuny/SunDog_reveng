import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from button_input_evidence import filter_sample
from native_probe import CPU
class ButtonInputTests(unittest.TestCase):
    def test_latched_pulse_and_held_edge(self):
        self.assertEqual(filter_sample(0,128,0,False),(1,0,1))
        self.assertEqual(filter_sample(128,0,1,False),(0,0,1))
        self.assertEqual(filter_sample(0,0,1,False),(0,0,0))
        self.assertEqual(filter_sample(128,0,0,False),(1,0,1))
    def test_level_poll_preserves_edge_history_and_ignores_low_bits(self):
        self.assertEqual(filter_sample(128,0,0,True),(1,0,0))
        self.assertEqual(filter_sample(127,127,0,False),(0,127,0))
        self.assertEqual(filter_sample(0,255,0,True),(1,0,0))
    def test_native_or_absolute_x_cross_page_flags(self):
        c=CPU();c.pc=0x8000;c.memory[0x8000:0x8003]=bytes([0x1d,0xff,0x40]);c.x=1;c.a=1;c.c=1;c.memory[0x4100]=128
        c.step();self.assertEqual((c.a,c.n,c.z,c.c),(129,1,0,1))
