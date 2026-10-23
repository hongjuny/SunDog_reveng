import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_probe import CPU
from pcode_analysis import Space,decode_one

class SecondaryServiceTests(unittest.TestCase):
    def test_absolute_x_store_and_decrement_cross_page(self):
        c=CPU();c.pc=0x8000;c.memory[0x8000:0x8006]=bytes([0x9d,0xff,0x40,0xde,0xff,0x40]);c.x=1;c.a=0;c.c=1
        c.step();self.assertEqual(c.read(0x4100),0)
        c.step();self.assertEqual((c.read(0x4100),c.n,c.z,c.c),(255,1,0,1))
    def test_ldx_absolute_updates_nz_only(self):
        for value in (0,1,128,255):
            c=CPU();c.pc=0x8000;c.memory[0x8000:0x8003]=bytes([0xae,0,0x40]);c.memory[0x4000]=value;c.c=1
            c.step();self.assertEqual((c.x,c.n,c.z,c.c),(value,value>>7,int(value==0),1))
    def test_named_service_decode_keeps_normal_return_condition(self):
        catalogue={0x9e:dict(rule='secondary_dispatch',handler=0xe67f,operands='u8 selector')}
        service={0x15:dict(pcode_length=2,name='acquire_segment',rea_evidence_id='synthetic-test-evidence')}
        row=decode_one(Space([(0,bytes([0x9e,0x15]))]),0,0,catalogue,service)
        self.assertEqual(row['successors'],[2]);self.assertEqual(row['service_name'],'acquire_segment')
        self.assertIn('conditional',row['service_continuation'])
        stopped=decode_one(Space([(0,bytes([0x9e,5]))]),0,0,catalogue,service)
        self.assertIn('boundary',stopped);self.assertFalse(stopped['successors'])
    def test_short_local_frame_index_is_one_based(self):
        c={op:dict(rule='load_local_short',handler=0xd2ea,operands='none') for op in (0xd8,0xdc)}
        for op,expected in ((0xd8,1),(0xdc,5)):
            self.assertEqual(decode_one(Space([(0,bytes([op]))]),0,0,c)['operands']['index'],expected)
