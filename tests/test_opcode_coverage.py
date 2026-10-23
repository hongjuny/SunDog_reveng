"""Coverage must not confuse a populated label or dispatcher with exhaustive runtime proof."""
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from export_opcode_catalogue import coverage

class CoverageTests(unittest.TestCase):
    def rows(self):
        return [dict(opcode=op,handler=0xd000,rule='synthetic-fixture',status='verified_selected_semantics',probe_cases=1) for op in range(128,256)]

    def test_no_checked_case_remains_unresolved(self):
        rows=self.rows();rows[0]['probe_cases']=0
        self.assertEqual(coverage({'primary':rows})['unresolved_high_opcodes'],[128])

    def test_duplicate_opcode_is_rejected(self):
        rows=self.rows();rows[1]['opcode']=128
        with self.assertRaises(ValueError):coverage({'primary':rows})

    def test_identification_does_not_claim_exhaustive_runtime(self):
        result=coverage({'primary':self.rows()})
        self.assertTrue(result['all_primary_entries_identified'])
        self.assertFalse(result['exhaustive_runtime_verified'])
        self.assertEqual(next(r for r in result['coverage_by_high_opcode'] if r['opcode']=='9E')['coverage'],'secondary-dispatch-only')
