// Persist native instruction/data/undefined partitions; no bytes in JSON.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import com.google.gson.*;
import java.nio.file.*;
public class ExportNativeStage extends GhidraScript {
 public void run() throws Exception {
  int base=Integer.parseInt(getScriptArgs()[1],16),length=Integer.parseInt(getScriptArgs()[2]);
  JsonObject result=new JsonObject();result.addProperty("program",currentProgram.getName());result.addProperty("base",base);result.addProperty("length",length);
  JsonArray instructions=new JsonArray(),references=new JsonArray(),ranges=new JsonArray();int[] classes=new int[length];
  InstructionIterator it=currentProgram.getListing().getInstructions(true);
  while(it.hasNext()) {Instruction i=it.next();int address=(int)i.getAddress().getOffset();if(address<base||address+i.getLength()>base+length)continue;
   JsonObject row=new JsonObject();row.addProperty("address",address);row.addProperty("offset",address-base);row.addProperty("length",i.getLength());row.addProperty("flow",i.getFlowType().toString());instructions.add(row);
   for(int p=address-base;p<address-base+i.getLength();p++)classes[p]=1;
   for(Reference r:i.getReferencesFrom()){JsonObject ref=new JsonObject();ref.addProperty("from",address);ref.addProperty("to",r.getToAddress().getOffset());ref.addProperty("kind",r.getReferenceType().toString());references.add(ref);}
  }
  DataIterator ds=currentProgram.getListing().getDefinedData(true);while(ds.hasNext()){Data d=ds.next();int a=(int)d.getAddress().getOffset()-base;if(a<0||a+d.getLength()>length)continue;for(int p=a;p<a+d.getLength();p++)if(classes[p]==0)classes[p]=2;}
  String[] kinds={"unreferenced_DB_untyped","decoded_instruction","defined_data"};
  for(int p=0;p<length;){int a=p,c=classes[p];while(p<length&&classes[p]==c)p++;JsonObject r=new JsonObject();r.addProperty("start",base+a);r.addProperty("end_exclusive",base+p);r.addProperty("kind",kinds[c]);ranges.add(r);}
  JsonArray alternate=new JsonArray();if(currentProgram.getName().equals("lc-bank2.bin")){JsonObject r=new JsonObject();r.addProperty("address",0xd5d3);r.addProperty("length",1);r.addProperty("mnemonic","CLC");r.addProperty("evidence","D5CF BEQ D5D3 enters operand of BIT at D5D2; alternate entry decodes opcode18. Normal path SEC;BIT$18;PLA; alternate CLC;PLA.");if((currentProgram.getMemory().getByte(toAddr(0xd5d3))&255)!=0x18)throw new IllegalStateException("overlap changed");alternate.add(r);JsonObject second=new JsonObject();second.addProperty("address",0xd029);second.addProperty("length",2);second.addProperty("mnemonic","LDY");second.addProperty("evidence","D026 LDY#2; D028 BIT$01A0 masks alternate D029 LDY#1; joins D02B STY03AC. Retained REA proof: analysis/local/rea/overlap-d029.json");if((currentProgram.getMemory().getByte(toAddr(0xd029))&255)!=0xa0 || (currentProgram.getMemory().getByte(toAddr(0xd02a))&255)!=1)throw new IllegalStateException("D029 overlap changed");alternate.add(second);}
  result.add("instruction_spans",instructions);result.add("references",references);result.add("classification_ranges",ranges);result.add("alternate_instructions",alternate);result.addProperty("limitation","Unreferenced DB remains structurally untyped; neither native code nor semantic data is invented. Indirect and patched targets need runtime/context evidence.");
  Files.writeString(Path.of(getScriptArgs()[0]),new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n");println("NATIVE_STAGE_EXPORT_OK");
 }
}
