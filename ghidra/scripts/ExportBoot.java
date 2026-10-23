// Import the staged boot RAM image with loader base 0800; exports remain local.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
public class ExportBoot extends GhidraScript {
 public void run() throws Exception {
  int[] entries=getScriptArgs().length>1 ? new int[]{Integer.parseInt(getScriptArgs()[1],16)} : new int[]{0x801,0x8ff};
  for(int n:entries){disassemble(toAddr(n)); createLabel(toAddr(n),n==0x801?"boot_entry":n==0x8ff?"disk_loader":"region_entry",true); createFunction(toAddr(n),null);}
  if (getScriptArgs().length==1) {
   createLabel(toAddr(0x094e),"read_sector",true);
   createLabel(toAddr(0x097a),"decode_6and2",true);
   createLabel(toAddr(0x0992),"read_data_field",true);
   createLabel(toAddr(0x09fa),"read_address_field",true);
   createLabel(toAddr(0x0a56),"seek_track",true);
   setPreComment(toAddr(0x0801),"Utility T0 DOS0 + ROM-loaded physical sectors 2,4. Header mutates 01 -> 03 -> 05. Static staged view; ROM not imported.");
  } else if(entries[0]==0x4000) {
   createLabel(toAddr(0x4200),"hgr_row_pointer",true);
   createLabel(toAddr(0x4210),"hgr_row_low",true);
   createLabel(toAddr(0x42d0),"hgr_row_high",true);
   setPreComment(toAddr(0x4000),"Utility blocks 201..218 using loader sector table; native graphics candidate. All 192 row table addresses verified against HGR page 1.");
  } else if(entries[0]==0xfef2) {
   setPreComment(toAddr(0xfef2),"Static boot handoff through loaded FFF8 vector. Reads C08B then jumps D152, switching the D000 bank. Use runtime-bank1.bin for the post-switch D000 mapping; lc-bank2.bin is the pre-switch view.");
  }
  String dest=getScriptArgs()[0];
  try(PrintWriter w=new PrintWriter(dest)){
   InstructionIterator it=currentProgram.getListing().getInstructions(true);
   while(it.hasNext()){Instruction i=it.next(); w.println(i.getAddress()+"  "+i.toString()); for(Reference r:i.getReferencesFrom()) w.println("  -> "+r.getToAddress()+" "+r.getReferenceType());}
   w.println("FUNCTIONS"); FunctionIterator fs=currentProgram.getFunctionManager().getFunctions(true);while(fs.hasNext()){Function f=fs.next();w.println(f.getEntryPoint()+" "+f.getName()+" "+f.getBody());}
  }
 }
}
