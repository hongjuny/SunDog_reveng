import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from trade_scaling_evidence import scale_selected

class TradeScalingTests(unittest.TestCase):
    def test_original_threshold_discontinuity_is_preserved(self):
        self.assertEqual(scale_selected(8,4094,8),(4094,'multiply-before-divide'))
        self.assertEqual(scale_selected(8,4095,8),(4088,'divide-before-multiply'))
        self.assertEqual(scale_selected(8,5000,3),(13328,'divide-before-multiply'))
        self.assertNotEqual(scale_selected(8,5000,3)[0],8*5000//3)
    def test_signed_word_product_wrap_is_preserved(self):
        self.assertEqual(scale_selected(32767,32767,1)[0],1)
        self.assertEqual(scale_selected(3,7,2)[0],10)
    def test_zero_and_unverified_domains_fail_explicitly(self):
        for values in ((0,1,1),(1,1,0),(0,0,0)):
            with self.assertRaises(ZeroDivisionError):scale_selected(*values)
        for values in ((-1,1,1),(1,-1,1),(1,1,-1)):
            with self.assertRaises(ValueError):scale_selected(*values)
