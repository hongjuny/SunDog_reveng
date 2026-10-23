// Import the staged boot RAM image with loader base 0800; exports remain local.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.data.*;
import java.io.*;
public class ExportBoot extends GhidraScript {
 public void run() throws Exception {
  boolean ready=currentProgram.getName().equals("interpreter-ready.bin");
  if(ready || currentProgram.getName().equals("runtime-bank1.bin")) {
   clearListing(toAddr(0xd000),toAddr(0xd151));
   createData(toAddr(0xd000),new ArrayDataType(WordDataType.dataType,128,2));
   createData(toAddr(0xd100),new ArrayDataType(WordDataType.dataType,41,2));
   clearListing(toAddr(0xddd6),toAddr(0xddf7));
   createData(toAddr(0xddd6),new ArrayDataType(WordDataType.dataType,17,2));
   createLabel(toAddr(0xddd6),"packed_field_masks",true);
   clearListing(toAddr(0xe189),toAddr(0xe18b));
   createData(toAddr(0xe189),WordDataType.dataType);
   createData(toAddr(0xe18b),ByteDataType.dataType);
   setPreComment(toAddr(0xe17e),"Native procedure return trampoline: data word E189 supplies E17D to the native stack, so RTS reaches E17E. E18B is a patched segment marker; nonnegative marker invokes E646 before fetch.");
  }
  if(ready) {
   clearListing(toAddr(0xf248),toAddr(0xfe7b));
   createData(toAddr(0xf248),new ArrayDataType(ByteDataType.dataType,3124,1));
   createLabel(toAddr(0xf248),"system_pascal_segment0_pcode",true);
   setPreComment(toAddr(0xf248),"P-code data, not 6502 instructions. Static load arithmetic and procedure directory put procedure 1 here. Overwrites the original F269/F290 initializer region.");
  }
  String[] seeds=getScriptArgs().length>1 ? getScriptArgs()[1].split(",") : new String[]{"801","8ff"};
  int[] entries=new int[seeds.length];
  for(int j=0;j<seeds.length;j++) entries[j]=Integer.parseInt(seeds[j],16);
  for(int n:entries){disassemble(toAddr(n)); createLabel(toAddr(n),n==0x801?"boot_entry":n==0x8ff?"disk_loader":"region_entry_"+Integer.toHexString(n),true); createFunction(toAddr(n),null);}
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
  if(currentProgram.getName().equals("runtime-bank1.bin") || ready) {
   createLabel(toAddr(0xd000),"primary_pcode_dispatch",true);
   createLabel(toAddr(0xd100),"secondary_dispatch_cells",true);
   createLabel(toAddr(0xd293),"pcode_fetch",true);
   setPreComment(toAddr(0xd293),"Fetches through ZP 58/59; 00..7F push a two-byte immediate using PHA. 80..FF index D000 words by patching the operand at D29E. Requires bank 1, with writable Language Card RAM.");
   setPreComment(toAddr(0xe67f),"Opcode 9E reads its following byte and patches E688 to dispatch through D100. Valid selector range not yet established.");
  }
  String dest=getScriptArgs()[0];
  try(PrintWriter w=new PrintWriter(dest)){
   InstructionIterator it=currentProgram.getListing().getInstructions(true);
   while(it.hasNext()){Instruction i=it.next(); w.println(i.getAddress()+"  "+i.toString()); for(Reference r:i.getReferencesFrom()) w.println("  -> "+r.getToAddress()+" "+r.getReferenceType());}
   w.println("FUNCTIONS"); FunctionIterator fs=currentProgram.getFunctionManager().getFunctions(true);while(fs.hasNext()){Function f=fs.next();w.println(f.getEntryPoint()+" "+f.getName()+" "+f.getBody());}
  }
 }
}
