import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from rea_setup import binary_identity
from verify_rea_probe import validate
class ReaChecks(unittest.TestCase):
 def test_404_is_not_a_native_binary(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'decompile';p.write_bytes(b'404: Not Found')
   self.assertFalse(binary_identity(p)['mach_o_arm64'])
 def test_readiness_is_not_analysis_evidence(self):
  with self.assertRaises(ValueError):validate({'healthy':True})
 def test_evidence_requires_matching_provider_and_bytes(self):
  e={'provider':{'id':'ghidra'},'evidence_id':'synthetic-unit-test-only','normalized_result':{'status':'decoded','address':'0xd293','bytes':'a0 00','mnemonic':'LDY','length':2}}
  self.assertEqual(validate(e)['status'],'verified')
  e['normalized_result']['bytes']='a0 01'
  with self.assertRaises(ValueError):validate(e)
if __name__=='__main__':unittest.main()
