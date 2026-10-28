import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from initial_game_flow import button_ready, disk_side_gate, require, signed16


class InitialGameFlowTests(unittest.TestCase):
    def test_exact_marker_in_both_side_modes(self):
        block = bytearray(512)
        for value in range(256):
            block[252] = value
            self.assertEqual(disk_side_gate(block, False), 'accepted' if value == 9 else 'wrong_side')
            self.assertEqual(disk_side_gate(block, True), 'accepted' if value == 0 else 'wrong_side')

    def test_io_transfer_precedes_marker_and_signed_predicate_is_explicit(self):
        block = bytearray(512); block[252] = 9
        self.assertEqual(disk_side_gate(block, False, 106), 'nonlocal_exit')
        self.assertEqual(disk_side_gate(block, False, 32767), 'nonlocal_exit')
        # This documents the original signed comparison, not a platform I/O API.
        self.assertEqual(disk_side_gate(block, False, 0xFFFF), 'accepted')
        self.assertEqual(signed16(0x8000), -32768)
        with self.assertRaises(ValueError): disk_side_gate(bytes(511), False)

    def test_original_branch_checks_low_bit_of_button_or(self):
        self.assertFalse(button_ready(0, 0))
        self.assertTrue(button_ready(0, 1))
        self.assertTrue(button_ready(1, 0))
        self.assertFalse(button_ready(2, 4))
        self.assertTrue(button_ready(2, 3))

    def test_source_pattern_guard_fails_closed(self):
        proc = {'instructions': [dict(address=1, operation='load_local_short', operands={'index': 3})]}
        self.assertEqual(require(proc, 1, 'load_local_short', index=3)['address'], 1)
        with self.assertRaises(ValueError): require(proc, 1, 'load_local_short', index=2)
        with self.assertRaises(ValueError): require(proc, 1, 'store_local', index=3)


if __name__ == '__main__': unittest.main()
