import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from verify_memory_views import compare_views
class ViewTests(unittest.TestCase):
 def fixture(self):
  a=bytes([0x11])*4096;b=bytes([0x22])*12288;r=a+b[4096:];s=bytes([0x33])*3124
  q=r[:0x2248]+s+r[0x2e7c:];return a,b,r,q,s
 def test_explicit_bank_and_overlay_composition(self):
  r=compare_views(*self.fixture());self.assertEqual(r['changed_bytes'],3124)
 def test_wrong_bank_is_rejected(self):
  a,b,r,q,s=self.fixture()
  with self.assertRaises(ValueError):compare_views(a,b,b,q,s)
 def test_writes_outside_overlay_are_rejected(self):
  a,b,r,q,s=self.fixture();q=bytearray(q);q[0]=0
  with self.assertRaises(ValueError):compare_views(a,b,r,q,s)
if __name__=='__main__':unittest.main()
