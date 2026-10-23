"""Synthetic assembly fixtures test comparison completeness, not game semantics."""
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from rea_opcode_views import compare_assembly

class ReaOpcodeComparisonTests(unittest.TestCase):
    listing = '8000  NOP\n8001  RTS\n'
    def test_complete_assembly_matches(self):
        self.assertEqual(compare_assembly('0x8000: NOP\n0x8001: RTS', self.listing, b'\xea\x60', 0x8000), 2)

    def test_partial_and_duplicate_assembly_fail(self):
        for assembly in ('0x8000: NOP', '0x8000: NOP\n0x8001: RTS\n0x8001: RTS'):
            with self.subTest(assembly=assembly), self.assertRaises(ValueError):
                compare_assembly(assembly, self.listing, b'\xea\x60', 0x8000)

    def test_wrong_instruction_or_outside_slice_fails(self):
        for assembly in ('0x8000: RTS\n0x8001: RTS', '0x8000: NOP\n0x8001: RTS\n0x8002: RTS'):
            with self.subTest(assembly=assembly), self.assertRaises(ValueError):
                compare_assembly(assembly, self.listing, b'\xea\x60', 0x8000)

if __name__ == '__main__':
    unittest.main()
