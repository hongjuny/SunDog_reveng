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

class BootMappingTests(unittest.TestCase):
 def test_loader_skew(self):
  # Independent anchors from CiderPress2 tables; each 512-byte block has two pages.
  from boot_regions import skew
  self.assertEqual(skew,(0,2,4,6,8,10,12,14,1,3,5,7,9,11,13,15))
  self.assertEqual(DOS_TO_PHYSICAL.index(skew[(201*2)%16]),13)

 def test_synthetic_boot_region(self):
  from boot_regions import pages
  import struct
  image=b''.join(struct.pack('<H',n)+bytes(254) for n in range(560))
  b,provenance=pages(201,2,image)
  self.assertEqual(struct.unpack_from('<H',b)[0],25*16+13)
  self.assertEqual(struct.unpack_from('<H',b,256)[0],25*16+12)
  self.assertEqual(provenance[0]['offset'],offset(25,13))
if __name__=='__main__':unittest.main()
