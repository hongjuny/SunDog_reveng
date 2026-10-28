import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ship_loop_evidence import loop_continues, level_transition, modal_requested, movement_step


class ShipLoopTests(unittest.TestCase):
    def test_mode_field_does_not_confuse_action_previous_and_flags(self):
        # Exhaustively vary adjacent nibbles/flags; only bits8..11 select the loop.
        for word in range(65536):
            self.assertEqual(loop_continues(word), ((word >> 8) & 15) in (2, 10))
        self.assertTrue(loop_continues(0x32BB))
        self.assertFalse(loop_continues(0x23BB))

    def test_hold_does_not_generate_repeated_release_interactions(self):
        levels = [False, True, True, True, False, False]
        events = [level_transition(a, b) for a, b in zip(levels, levels[1:])]
        self.assertEqual(events, ['press_reset_target', 'unchanged', 'unchanged',
                                  'release_hit_test', 'unchanged'])
        self.assertEqual(level_transition(True, False), 'release_hit_test')

    def test_secondary_button_modal_and_mode10_are_independent(self):
        self.assertFalse(modal_requested(0, 0x32BB))
        self.assertTrue(modal_requested(1, 0x32BB))
        self.assertTrue(modal_requested(0, 0x3ABB))
        self.assertFalse(modal_requested(2, 0x32BB))  # Native low-bit truth.

    def test_motion_clamps_without_overshooting_target(self):
        for delta in range(-280, 281):
            step = movement_step(delta)
            self.assertLessEqual(abs(step), 2)
            self.assertLessEqual(abs(step), abs(delta))
            self.assertLessEqual(abs(delta - step), abs(delta))
        self.assertEqual([movement_step(x) for x in [-3, -1, 0, 1, 3]], [-2, -1, 0, 1, 2])


if __name__ == '__main__': unittest.main()
