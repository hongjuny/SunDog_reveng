// Export listing classification and loaded-block hashes, without game binary bytes.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import com.google.gson.*;
import java.nio.file.*;
import java.security.*;
public class ExportMemoryState extends GhidraScript {
 String sha(Address start,int size) throws Exception {
  byte[] raw=new byte[size];currentProgram.getMemory().getBytes(start,raw);
  byte[] hash=MessageDigest.getInstance("SHA-256").digest(raw);return java.util.HexFormat.of().formatHex(hash);
 }
 public void run() throws Exception {
  JsonObject result=new JsonObject();result.addProperty("program",currentProgram.getName());result.addProperty("language",currentProgram.getLanguageID().toString());
  JsonArray blocks=new JsonArray();
  for(MemoryBlock block:currentProgram.getMemory().getBlocks()) {
   JsonObject row=new JsonObject();row.addProperty("name",block.getName());row.addProperty("start",block.getStart().toString());row.addProperty("length",block.getSize());row.addProperty("initialized",block.isInitialized());
   if(block.isInitialized())row.addProperty("sha256",sha(block.getStart(),(int)block.getSize()));blocks.add(row);
  }
  result.add("blocks",blocks);JsonArray regions=new JsonArray();
  int[][] spans={{0xd000,0xd0ff},{0xd100,0xd151},{0xddd6,0xddf7},{0xe189,0xe18a},{0xe18b,0xe18b},{0xf248,0xfe7b}};
  for(int[] span:spans) {
   JsonObject row=new JsonObject();row.addProperty("start",Integer.toHexString(span[0]));row.addProperty("end_inclusive",Integer.toHexString(span[1]));
   int instructions=0;InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(toAddr(span[0]),toAddr(span[1])),true);while(it.hasNext()){it.next();instructions++;}
   row.addProperty("native_instruction_count",instructions);Data data=currentProgram.getListing().getDefinedDataAt(toAddr(span[0]));
   if(data!=null){row.addProperty("data_type",data.getDataType().getName());row.addProperty("data_length",data.getLength());}
   regions.add(row);
  }
  result.add("regions",regions);
  Files.writeString(Path.of(getScriptArgs()[0]),new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n");
 }
}
