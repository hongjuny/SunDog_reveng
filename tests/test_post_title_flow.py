import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from post_title_flow import begin_gate_step, menu_contract, choice_route, save_checksum

class PostTitleFlowTests(unittest.TestCase):
    def test_button_gate_consumes_iteration_before_exit_test(self):
        self.assertEqual(begin_gate_step(11400,False,False),(11399,False))
        self.assertEqual(begin_gate_step(1,False,False),(0,True))
        self.assertEqual(begin_gate_step(100,True,False),(99,True))
        self.assertEqual(begin_gate_step(100,False,True),(99,True))
    def test_cross_mode_choices_require_boot_directory_change(self):
        self.assertEqual(choice_route(False,2)['template_block'],80)
        self.assertEqual(choice_route(True,1)['template_block'],81)
        self.assertEqual(choice_route(False,1)['action'],'return_to_caller')
        self.assertEqual(choice_route(True,2)['action'],'return_to_caller')
        self.assertEqual(choice_route(False,3)['template_block'],82)
        self.assertFalse(choice_route(True,3)['set_skip_title_marker'])
    def test_game_over_and_invalid_slot_disable_play_only(self):
        for state in (12,13):
            self.assertEqual(menu_contract(False,1,state<<8)['choices'],[1,3])
        self.assertEqual(menu_contract(False,4,0)['choices'],[1,3])
        self.assertEqual(menu_contract(False,1,0,True)['choices'],[1,3])
        self.assertEqual(menu_contract(False,1,0)['choices'],[2,1,3])
        with self.assertRaises(ValueError):choice_route(False,2,False)
        with self.assertRaises(ValueError):choice_route(False,0)
    def test_checksum_uses_independent_byte_columns(self):
        data=bytearray(5120);data[:4]=bytes([255,1,2,3])
        self.assertEqual(save_checksum(data),0x0401)
        with self.assertRaises(ValueError):save_checksum(data[:-1])

if __name__=='__main__':unittest.main()
