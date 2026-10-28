"""Boundary cases from the original pointer correction and rectangle semantics."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from joystick_pointer_evidence import axis_setup, correct_counters, cursor_operations, pointer_position


class JoystickPointerTests(unittest.TestCase):
    def test_lsr_carry_rounding(self):
        # X=14 gives q=7: carry from second LSR rounds 3.5 upward.
        self.assertEqual(correct_counters(100, 14), (97, 6))
        self.assertEqual(correct_counters(100, 18), (97, 9))

    def test_native_saturation(self):
        self.assertEqual(correct_counters(0, 0), (0, 0))
        self.assertEqual(correct_counters(255, 255), (139, 95))
        with self.assertRaises(ValueError):
            correct_counters(256, 0)

    def test_scale_threshold_and_odd_centering(self):
        self.assertEqual(axis_setup(10, 150, 140), (1, 10))
        self.assertEqual(axis_setup(10, 151, 140), (2, -59))
        self.assertEqual(axis_setup(138, 265, 140), (1, 132))

    def test_full_screen_and_initial_menu(self):
        self.assertEqual(pointer_position(0, 0, (0, 279, 0, 191)), (3, 5))
        self.assertEqual(pointer_position(139, 95, (0, 279, 0, 191)), (274, 188))
        self.assertEqual(pointer_position(70, 48, (135, 270, 90, 181)), (202, 137))

    def test_cursor_update_order(self):
        self.assertEqual(cursor_operations((20, 30), (20, 30)), [])
        self.assertEqual(cursor_operations((20, 30), (21, 30)), [('xor', (20, 30)), ('store', (21, 30)), ('xor', (21, 30))])


if __name__ == '__main__':
    unittest.main()
