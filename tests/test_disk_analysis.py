import sys, pathlib, unittest, tempfile, math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from disk_analysis import offset,stats,load,DOS_TO_PHYSICAL,analyze
class DiskTests(unittest.TestCase):
 def test_offset(self):
  self.assertEqual(offset(34,15),143104)
  for args in [(-1,0),(35,0),(0,16)]:
   with self.assertRaises(ValueError): offset(*args)
 def test_content(self):
  self.assertEqual(stats(bytes(256))['entropy'],0)
  self.assertEqual(stats(bytes(range(256)))['entropy'],8)
  self.assertEqual(stats(bytes([255])*256)['ff'],256)
 def test_order(self):
  self.assertEqual(sorted(DOS_TO_PHYSICAL),list(range(16)))
  self.assertEqual(DOS_TO_PHYSICAL.index(2),14)
  self.assertEqual(DOS_TO_PHYSICAL.index(4),13)
 def test_size(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x';p.write_bytes(b'x')
   with self.assertRaises(ValueError):load(p)
 def test_unknown_exclusion_and_mapping(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'disk').mkdir();(root/'extracted').mkdir()
   b=b''.join(bytes([t])*4096 for t in range(35))
   for side in ('play','utility'):(root/'extracted'/f'{side}.do').write_bytes(b)
   analyze(root)
   a=json.loads((root/'analysis/play-sectors.json').read_text())
   self.assertEqual(a[16]['sha256'],stats(bytes([1])*256)['sha256'])
   self.assertEqual(sum(x['status']=='unknown' for x in a),16)
   self.assertNotIn('sha256',a[-1])
   self.assertEqual(len(json.loads((root/'analysis/comparison.json').read_text())['corresponding_identical']),544)
if __name__=='__main__':unittest.main()
