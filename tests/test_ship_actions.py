import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ship_action_evidence import action_at, axis_step, truncdiv, native_movement


class ShipActionTests(unittest.TestCase):
    def test_grid_boundaries_and_conditional_equipment(self):
        self.assertEqual(action_at(39,99),1)
        self.assertEqual(action_at(38,99),0)
        self.assertEqual(action_at(46,99),0)
        self.assertEqual(action_at(53,115),0)
        self.assertEqual(action_at(53,115,1),4)
        self.assertEqual(action_at(95,115,0,1),3)
        self.assertEqual(action_at(53,115,64,32),0)

    def test_upper_hatch_uses_distinct_y_anchor(self):
        self.assertEqual(action_at(109,52),0)
        self.assertEqual(action_at(109,53),8)
        self.assertEqual(action_at(109,60),8)
        self.assertEqual(action_at(109,61),0)

    def test_signed_division_and_small_steps(self):
        self.assertEqual(truncdiv(-1,7),0)
        self.assertEqual([axis_step(x) for x in (-20,-1,0,1,20)],[-2,-1,0,1,2])

    def test_original_native_slide_order(self):
        cases=[(set(),[50,115]),({(50,115)},[50,114]),
               ({(50,115),(50,114)},[48,115]),
               ({(50,115),(50,114),(48,115)},[48,114])]
        for blocked,expected in cases:
            with self.subTest(blocked=blocked):
                self.assertEqual(native_movement(blocked)['actor_after'],expected)


if __name__=='__main__':unittest.main()
