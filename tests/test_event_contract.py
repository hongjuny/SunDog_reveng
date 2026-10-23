import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_contract import root_reference,source_point
from verify_native_selection import selected,s16,div16

class EventContractTests(unittest.TestCase):
    def test_nested_local_is_not_mistaken_for_root_reference(self):
        p=dict(number=20,lexical_level=3)
        row=dict(operation='load_nonlocal',operands=dict(selector_or_depth=1,index=5))
        self.assertIsNone(root_reference(p,row))
        row['operands']['selector_or_depth']=2
        self.assertEqual(root_reference(p,row),5)
    def test_p1_short_local_and_upper_reference_bound(self):
        p=dict(number=1,lexical_level=1)
        self.assertEqual(root_reference(p,dict(operation='load_local_short',operands=dict(index=1))),1)
        self.assertIsNone(root_reference(p,dict(operation='load_local',operands=dict(index=9))))
    def test_signed_wrap_and_truncation(self):
        self.assertEqual(s16(32768),-32768)
        self.assertEqual(div16(-32768,-1),-32768)
        self.assertEqual(div16(-7,8),0)
        self.assertEqual(div16(7,-3),-2)
    def test_magnitude_remainder_is_not_signed_modulo(self):
        self.assertEqual(selected(-1,-1,0,3,8),(1,1))
        self.assertEqual(selected(0,0,-33,-6,8),(1,1))
        with self.assertRaises(ZeroDivisionError):selected(0,0,0,0,0)
    def test_source_point_preserves_physical_and_logical_coordinates(self):
        s=dict(sectors=[dict(track=2,sector=3,physical_sector=6,offset=8960),dict(track=2,sector=4,physical_sector=8,offset=9216)])
        p=source_point(s,257)
        self.assertEqual((p['track'],p['sector'],p['byte_in_sector'],p['image_offset']),(2,4,1,9217))
