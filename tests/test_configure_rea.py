import pathlib,sys,tempfile,tomllib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from configure_rea import merge_environment,write_config
BASE='''# keep comment\nmodel = "existing-model"\n[mcp_servers.rea]\ncommand = "npx"\nargs = ["-y", "rea-agents@6.7.0", "mcp"]\n[mcp_servers.other]\ncommand = "other-tool"\n'''
FRAGMENT='''[mcp_servers.rea.env]\nGHIDRA_INSTALL_DIR = "/ghidra"\nJAVA_HOME = "/jdk"\nREA_DARWIN_MODULE_CACHE_PATH = "/cache"\nREA_DARWIN_SWIFTC_PATH = "/swiftc"\nSDKROOT = "/sdk"\n'''
class ConfigureTests(unittest.TestCase):
 def test_unrelated_settings_are_preserved(self):
  result,changes=merge_environment(BASE,FRAGMENT)
  before=tomllib.loads(BASE);after=tomllib.loads(result)
  self.assertEqual(before['mcp_servers']['other'],after['mcp_servers']['other'])
  self.assertEqual(before['model'],after['model']);self.assertEqual(after['mcp_servers']['rea']['command'],'npx')
  self.assertTrue(result.startswith(BASE.rstrip('\n')));self.assertEqual(len(changes),5)
 def test_existing_environment_is_merged(self):
  original=BASE+'[mcp_servers.rea.env]\nKEEP = "unchanged"\nJAVA_HOME = "/old"\n[projects.example]\ntrust_level = "trusted"\n'
  result,_=merge_environment(original,FRAGMENT);x=tomllib.loads(result)
  self.assertEqual(x['mcp_servers']['rea']['env']['KEEP'],'unchanged')
  self.assertEqual(x['projects']['example']['trust_level'],'trusted')
  second,changes=merge_environment(result,FRAGMENT);self.assertEqual(second,result);self.assertFalse(changes)
 def test_backup_and_symlink_are_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);real=root/'real.toml';real.write_text(BASE);visible=root/'config.toml';visible.symlink_to(real)
   report=write_config(visible,FRAGMENT)
   self.assertTrue(visible.is_symlink());self.assertEqual(pathlib.Path(report['backup']).read_text(),BASE)
   self.assertEqual(report['status'],'applied');self.assertEqual(write_config(visible,FRAGMENT)['status'],'already_configured')
 def test_fragment_cannot_change_tool_policy(self):
  with self.assertRaises(ValueError):merge_environment(BASE,FRAGMENT+'[mcp_servers.rea.tools.open_binary]\napproval_mode = "approve"\n')
if __name__=='__main__':unittest.main()
