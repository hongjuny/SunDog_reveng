"""Synthetic validator fixtures only; none are retained as REA analysis Evidence."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from rea_memory_views import verify_read

class ReaMemoryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(evidence_id='synthetic-unit-test-only', provider={'id': 'ghidra'},
                           operation='read_bytes', subject={'digest': {'sha256': 'test-target'}},
                           normalized_result=dict(address='0xd152', bytes_hex='4c69f2',
                                                  complete=True, requested_bytes=3, returned_bytes=3))

    def test_complete_matching_read(self):
        self.assertTrue(verify_read(self.record, 'test-target', 0xd152, bytes.fromhex('4c69f2')))

    def test_partial_read_is_rejected_even_if_bytes_match(self):
        for field, value in [('complete', False), ('returned_bytes', 2), ('requested_bytes', 4)]:
            with self.subTest(field=field):
                r = copy.deepcopy(self.record)
                r['normalized_result'][field] = value
                with self.assertRaises(ValueError):
                    verify_read(r, 'test-target', 0xd152, bytes.fromhex('4c69f2'))

    def test_same_address_different_bank_bytes_are_rejected(self):
        with self.assertRaises(ValueError):
            verify_read(self.record, 'test-target', 0xd152, bytes.fromhex('206bd2'))

    def test_wrong_target_or_operation_is_rejected(self):
        for field, value in [('operation', 'doctor'), ('evidence_id', '')]:
            with self.subTest(field=field):
                r = copy.deepcopy(self.record)
                r[field] = value
                with self.assertRaises(ValueError):
                    verify_read(r, 'test-target', 0xd152, bytes.fromhex('4c69f2'))
        with self.assertRaises(ValueError):
            verify_read(self.record, 'other-target', 0xd152, bytes.fromhex('4c69f2'))

    def test_wrong_address_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_read(self.record, 'test-target', 0xd153, bytes.fromhex('4c69f2'))

if __name__ == '__main__':
    unittest.main()
