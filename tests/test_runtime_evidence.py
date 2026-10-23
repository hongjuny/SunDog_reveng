import pathlib,struct,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from verify_woz import parse_sector_dump
from runtime_evidence import catalogue
from archive_evidence import directory,dictionary
from boot_handoff import procedure_directory

class DecoderTests(unittest.TestCase):
 def test_complete_dump_and_rejected_partial(self):
  rows=[f'{n:06x}: '+' '.join(f'{x:02x}' for x in range(n,n+16))+'  ignored text' for n in range(0,256,16)]
  self.assertEqual(parse_sector_dump('\n'.join(rows)),bytes(range(256)))
  self.assertIsNone(parse_sector_dump('\n'.join(rows[:-1])))
  self.assertIsNone(parse_sector_dump('\n'.join(rows[::-1])))

class RuntimeTests(unittest.TestCase):
 def fixture(self):
  b1=bytearray(4096);b2=bytearray(12288)
  for i in range(128):struct.pack_into('<H',b1,i*2,0xd200+i)
  struct.pack_into('<H',b1,0x3c,0xe67f)
  b1[0x293:0x2a0]=bytes.fromhex('a000b15810ef0a8d9ed26c00d0')
  b2[0x167f:0x168a]=bytes.fromhex('a001b1580a8d88e66c00d1')
  for i in range(21):
   p=0x2f00+i*3;b2[p:p+3]=bytes.fromhex('209eff')
   p+=0x5c;b2[p]=0x4c;struct.pack_into('<H',b2,p+1,0xd800+i)
  return b1,b2
 def test_dispatch_and_native_wrapper_arithmetic(self):
  r=catalogue(*self.fixture())
  self.assertEqual(r['secondary_dispatch_opcode'],0x9e)
  self.assertEqual(r['primary'][-1]['table_address'],0xd0fe)
  self.assertEqual(r['bios_wrappers'][6]['trampoline'],0xff6e)
 def test_changed_fetch_is_rejected(self):
  b1,b2=self.fixture();b1[0x293]=0
  with self.assertRaises(ValueError):catalogue(b1,b2)

class ArchiveTests(unittest.TestCase):
 def test_directory_count_and_bounds(self):
  d=bytearray(512);struct.pack_into('<H',d,16,1)
  struct.pack_into('<HHH',d,26,10,20,2);d[32]=4;d[33:37]=b'TEST'
  self.assertEqual(directory(d)[0]['start_block'],10)
  struct.pack_into('<H',d,28,281)
  with self.assertRaises(ValueError):directory(d)
 def test_allocation_and_outside_extent_are_distinct(self):
  d=bytearray(512);struct.pack_into('<HH',d,0,0,1024);struct.pack_into('<H',d,0xc0,7)
  struct.pack_into('<HH',d,4,2,1024)
  r=dictionary(d,3)
  self.assertEqual([x['status'] for x in r],['allocation_only','outside_directory_extent'])
 def test_cross_region_procedure_pointer(self):
  main=bytearray(32);helper=bytearray(12)
  struct.pack_into('<H',main,28,18);main[10:12]=bytes((1,255));struct.pack_into('<H',main,8,8)
  struct.pack_into('<H',main,26,0x801a-0x700a);helper[10:12]=bytes((2,1));struct.pack_into('<H',helper,8,8)
  main[-1]=2
  r=procedure_directory(main,0x8000,[(0x7000,helper)])
  self.assertEqual([x['entry_address'] for x in r],[0x8000,0x7000])
  self.assertEqual(r[0]['lexical_level'],-1)
  self.assertTrue(r[1]['outside_main_segment'])
  with self.assertRaises(ValueError):procedure_directory(main,0x8000)
if __name__=='__main__':unittest.main()
