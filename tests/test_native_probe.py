import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from native_probe import CPU,UnsupportedInstruction
class NativeProbeTests(unittest.TestCase):
 def program(self,raw):
  c=CPU();c.memory[0x8000:0x8000+len(raw)]=raw;c.pc=0x8000;return c
 def test_adc_and_borrow_flags(self):
  c=self.program(bytes.fromhex('a9ff186901'));[c.step() for _ in range(3)]
  self.assertEqual((c.a,c.c,c.z),(0,1,1))
  c=self.program(bytes.fromhex('a90038e901'));[c.step() for _ in range(3)]
  self.assertEqual((c.a,c.c,c.n),(255,0,1))
 def test_rotate_transfers_carry(self):
  c=self.program(bytes.fromhex('a9800a26ff'));c.memory[255]=0x7f
  [c.step() for _ in range(3)]
  self.assertEqual((c.a,c.read(255),c.c),(0,255,0))
 def test_native_call_stack_and_return(self):
  c=self.program(bytes.fromhex('200090'));c.memory[0x9000]=0x60
  c.step();self.assertEqual((c.pc,c.sp,c.read(0x1fe),c.read(0x1ff)),(0x9000,253,2,0x80))
  c.step();self.assertEqual((c.pc,c.sp),(0x8003,255))
 def test_indirect_jump_has_nmos_page_wrap(self):
  c=self.program(bytes.fromhex('6cff40'));c.memory[0x40ff]=0x34;c.memory[0x4000]=0x12;c.memory[0x4100]=0x99
  c.step();self.assertEqual(c.pc,0x1234)
 def test_indirect_y_uses_zero_page_pointer_wrap(self):
  c=self.program(bytes.fromhex('a001b1ff'));c.memory[255]=0xff;c.memory[0]=0x40;c.memory[0x4100]=0x81
  c.step();c.step();self.assertEqual((c.a,c.n),(0x81,1))
 def test_y_comparison_preserves_register(self):
  c=self.program(bytes.fromhex('a001c003'));c.step();c.step()
  self.assertEqual((c.y,c.c,c.z,c.n),(1,0,0,1))
 def test_indirect_y_subtract_with_borrow_and_pointer_wrap(self):
  for a,value,carry,expected in ((0,1,1,(255,0,0,1)),(0,0,0,(255,0,0,1)),(0,0,1,(0,1,1,0)),(128,1,1,(127,1,0,0))):
   with self.subTest(a=a,value=value,carry=carry):
    c=self.program(bytes.fromhex('f1ff'));c.a=a;c.c=carry;c.y=1
    c.memory[255]=255;c.memory[0]=0x40;c.memory[0x4100]=value
    c.step();self.assertEqual((c.a,c.c,c.z,c.n),expected)
 def test_unsupported_and_budget_fail_explicitly(self):
  c=self.program(b'\xea');self.assertEqual(c.run({0x8001},max_steps=1),0x8001)
  c=self.program(b'\x00')
  with self.assertRaises(UnsupportedInstruction):c.step()
  c=self.program(bytes.fromhex('4c0080'))
  with self.assertRaises(ValueError):c.run({0x9000},max_steps=5)
 def test_negative_branch_displacement(self):
  c=self.program(bytes.fromhex('a201cad0fd'))
  c.run({0x8005});self.assertEqual((c.x,c.z),(0,1))
if __name__=='__main__':unittest.main()
