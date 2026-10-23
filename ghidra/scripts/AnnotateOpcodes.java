// Persist only semantics established for the current interpreter-ready snapshot.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import com.google.gson.*;
import java.nio.file.*;
import java.util.*;
public class AnnotateOpcodes extends GhidraScript {
 public void run() throws Exception {
  if(!currentProgram.getName().equals("interpreter-ready.bin")) throw new IllegalArgumentException("Opcode annotations require interpreter-ready.bin");
  JsonObject report=JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
  Map<Integer,List<JsonObject>> groups=new TreeMap<>();
  JsonArray annotations=new JsonArray();
  for(JsonElement value:report.getAsJsonArray("primary")) {
   JsonObject row=value.getAsJsonObject();
   if(!row.get("status").getAsString().equals("verified_selected_semantics")) continue;
   int handler=row.get("handler").getAsInt();groups.computeIfAbsent(handler,n->new ArrayList<>()).add(row);
  }
  for(Map.Entry<Integer,List<JsonObject>> entry:groups.entrySet()) {
   JsonObject first=entry.getValue().get(0);String rule=first.get("rule").getAsString();
   createLabel(toAddr(entry.getKey()),"pc_"+rule,true);
   StringBuilder comment=new StringBuilder("Selected semantics checked against actual native bytes with synthetic probes. Not a hardware/REA trace. Initial interpreter-ready snapshot only.\n");
   for(JsonObject row:entry.getValue()) comment.append(String.format("%02X: %s; operands=%s; advance=%s. %s\n",row.get("opcode").getAsInt(),row.get("semantic").getAsString(),row.get("operands").getAsString(),row.get("advance").isJsonPrimitive()?row.get("advance").getAsString():"unresolved",row.get("notes").getAsString()));
   setPreComment(toAddr(entry.getKey()),comment.toString());
   CodeUnit unit=currentProgram.getListing().getCodeUnitAt(toAddr(entry.getKey()));
   if(unit==null || !comment.toString().equals(unit.getComment(CodeUnit.PRE_COMMENT))) throw new IllegalStateException("Comment readback failed");
   JsonObject saved=new JsonObject();saved.addProperty("handler",entry.getKey());saved.addProperty("label","pc_"+rule);saved.addProperty("comment_readback_matches",true);
   JsonArray aliases=new JsonArray();for(JsonObject row:entry.getValue())aliases.add(row.get("opcode").getAsInt());saved.add("opcodes",aliases);annotations.add(saved);
  }
  createLabel(toAddr(0xd155),"read_scaled_index",true);
  setPreComment(toAddr(0xd155),"Read a 7-bit one-byte or 15-bit two-byte index; return 2*index in 68/69. Long form consumes an extra byte by incrementing 58/59. Not a little-endian u16 operand.");
  createLabel(toAddr(0xd171),"follow_static_links",true);
  setPreComment(toAddr(0xd299),"ASL leaves A=(opcode*2)&FF, C=1, Y=0 for high opcodes. Shared short frame/indirect handlers rely on these entry values; equal handler pointers do not mean equal opcode semantics.");
  if(getScriptArgs().length>1) Files.writeString(Path.of(getScriptArgs()[1]),new GsonBuilder().setPrettyPrinting().create().toJson(annotations)+"\n");
  println("Annotated "+groups.size()+" native handler entries from verified selected-semantics catalogue.");
 }
}
