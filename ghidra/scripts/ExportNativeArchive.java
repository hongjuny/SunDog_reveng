// Export bounded normalized native archive listings, functions and references.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.data.*;
import ghidra.program.model.symbol.*;
import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
public class ExportNativeArchive extends GhidraScript {
 int base;
 JsonArray ranges(boolean[] bytes,int first,boolean value) {
  JsonArray result=new JsonArray();int i=0;
  while(i<bytes.length) {if(bytes[i]!=value){i++;continue;}int start=i;while(i<bytes.length && bytes[i]==value)i++;
   JsonObject r=new JsonObject();r.addProperty("start_offset",first+start);r.addProperty("end_exclusive",first+i);result.add(r);}
  return result;
 }
 public void run() throws Exception {
  JsonObject spec=JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
  base=spec.getAsJsonObject("declared_view").get("segment_base").getAsInt();int length=spec.get("length").getAsInt();
  byte[] raw=new byte[length];currentProgram.getMemory().getBytes(toAddr(base),raw);
  if(!HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw)).equals(spec.get("normalized_sha256").getAsString()))throw new IllegalStateException("Normalized image hash mismatch");
  clearListing(toAddr(base),toAddr(base+length-1));
  // Protect every byte outside validated native bodies from speculative 6502 decoding.
  boolean[] nativeBytes=new boolean[length];
  for(JsonElement value:spec.getAsJsonArray("procedures")) {
   JsonObject p=value.getAsJsonObject();int a=p.get("body_start").getAsInt(),b=p.get("body_end_exclusive").getAsInt();
   Arrays.fill(nativeBytes,a,b,true);
   for(JsonElement item:p.getAsJsonArray("inline_data")){JsonObject d=item.getAsJsonObject();Arrays.fill(nativeBytes,d.get("start_offset").getAsInt(),d.get("end_exclusive").getAsInt(),false);}
  }
  for(int i=0;i<length;) {if(nativeBytes[i]){i++;continue;}int a=i;while(i<length&&!nativeBytes[i])i++;
   createData(toAddr(base+a),new ArrayDataType(ByteDataType.dataType,i-a,1));}
  for(JsonElement value:spec.getAsJsonArray("procedures")) {
   JsonObject p=value.getAsJsonObject();int entry=base+p.get("entry_address").getAsInt();
   disassemble(toAddr(entry));createLabel(toAddr(entry),"segment_"+spec.get("segment_number").getAsInt()+"_native_"+p.get("number").getAsInt(),true);
   createFunction(toAddr(entry),null);
   for(JsonElement item:p.getAsJsonArray("extra_code_entries")){int helper=base+item.getAsInt();disassemble(toAddr(helper));createLabel(toAddr(helper),"native_helper_"+Integer.toHexString(helper),true);createFunction(toAddr(helper),null);}
   setPreComment(toAddr(entry),"Original native procedure, normalized synthetic segment base 4000/global base 9000. Relocation tables reconstructed from E3FD/E5C7 loader; addresses are not an observed runtime placement.");
  }
  JsonObject output=new JsonObject();output.addProperty("language",currentProgram.getLanguageID().toString());output.addProperty("normalized_sha256",spec.get("normalized_sha256").getAsString());
  JsonArray procedures=new JsonArray();
  for(JsonElement value:spec.getAsJsonArray("procedures")) {
   JsonObject p=value.getAsJsonObject();int first=p.get("body_start").getAsInt(),end=p.get("body_end_exclusive").getAsInt();
   boolean[] classified=new boolean[end-first];
   for(JsonElement item:p.getAsJsonArray("inline_data")) {
    JsonObject d=item.getAsJsonObject();int a=d.get("start_offset").getAsInt(),b=d.get("end_exclusive").getAsInt();Arrays.fill(classified,a-first,b-first,true);
    if(d.get("kind").getAsString().equals("word_alignment_after_JMP")) {
     Instruction before=currentProgram.getListing().getInstructionAt(toAddr(base+a-3));
     if(before==null || before.getLength()!=3 || !before.getMnemonicString().equals("JMP"))throw new IllegalStateException("Alignment predecessor not proven JMP");
    }
    if(d.get("kind").getAsString().equals("word_alignment_after_RTS")) {
     Instruction before=currentProgram.getListing().getInstructionAt(toAddr(base+a-1));
     if(before==null || before.getLength()!=1 || !before.getMnemonicString().equals("RTS"))throw new IllegalStateException("Alignment predecessor not proven RTS");
    }
   }
   JsonArray instructions=new JsonArray(),refs=new JsonArray();
   InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(toAddr(base+first),toAddr(base+end-1)),true);
   while(it.hasNext()) {
    Instruction instruction=it.next();int offset=(int)instruction.getAddress().getOffset()-base;
    if(offset+instruction.getLength()>end)throw new IllegalStateException("Instruction crosses relocation boundary");
    Arrays.fill(classified,offset-first,offset-first+instruction.getLength(),true);
    JsonObject row=new JsonObject();row.addProperty("offset",offset);row.addProperty("length",instruction.getLength());row.addProperty("flow",instruction.getFlowType().toString());instructions.add(row);
    for(Reference ref:instruction.getReferencesFrom()) {
     JsonObject r=new JsonObject();r.addProperty("from_offset",offset);r.addProperty("to",ref.getToAddress().getOffset());r.addProperty("kind",ref.getReferenceType().toString());refs.add(r);
    }
   }
   JsonObject row=new JsonObject();row.addProperty("number",p.get("number").getAsInt());row.addProperty("entry_offset",first);row.addProperty("body_end_exclusive",end);
   row.add("instruction_spans",instructions);row.add("inline_data",p.getAsJsonArray("inline_data"));row.add("references",refs);row.add("unclassified_ranges",ranges(classified,first,false));procedures.add(row);
  }
  output.add("procedures",procedures);
  Files.writeString(Path.of(getScriptArgs()[1]),new GsonBuilder().setPrettyPrinting().create().toJson(output)+"\n");
  try(PrintWriter writer=new PrintWriter(getScriptArgs()[2])) {
   InstructionIterator it=currentProgram.getListing().getInstructions(true);
   while(it.hasNext()){Instruction i=it.next();writer.println(i.getAddress()+"  "+i);for(Reference r:i.getReferencesFrom())writer.println("  -> "+r.getToAddress()+" "+r.getReferenceType());}
   writer.println("FUNCTIONS");FunctionIterator functions=currentProgram.getFunctionManager().getFunctions(true);
   while(functions.hasNext()){Function f=functions.next();writer.println(f.getEntryPoint()+" "+f.getName()+" "+f.getBody());}
  }
  println("NATIVE_ARCHIVE_EXPORT_OK");
 }
}
