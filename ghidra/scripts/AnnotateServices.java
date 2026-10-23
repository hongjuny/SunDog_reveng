// Persist only the selected service-interface evidence; nonresident I/O remains open.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import com.google.gson.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
public class AnnotateServices extends GhidraScript {
 public void run() throws Exception {
  if(!currentProgram.getName().equals("interpreter-ready.bin"))throw new IllegalArgumentException("Interpreter-ready program required");
  JsonObject report=JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
  byte[] snapshot=new byte[0x3000];currentProgram.getMemory().getBytes(toAddr(0xd000),snapshot);
  String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(snapshot));
  if(!digest.equals(report.get("snapshot_sha256").getAsString()))throw new IllegalArgumentException("Native snapshot identity differs");
  JsonArray saved=new JsonArray();
  for(JsonElement value:report.getAsJsonArray("services")) {
   JsonObject row=value.getAsJsonObject();int entry=row.get("entry").getAsInt();int selector=row.get("selector").getAsInt();
   byte[] bytes=new byte[row.get("end_exclusive").getAsInt()-entry];currentProgram.getMemory().getBytes(toAddr(entry),bytes);
   if(!HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)).equals(row.get("sha256").getAsString()))throw new IllegalArgumentException("Service bytes differ");
   String label=String.format("service_9e_%02x_%s",selector,row.get("name").getAsString());
   String comment="Selected 9E interface: normal return advances p-code by two bytes. Scope: "+row.get("tested_scope").getAsString()+". Complete loader/disk or arbitrary-pointer semantics are not claimed. Actual REA="+row.get("rea_evidence_id").getAsString();
   createLabel(toAddr(entry),label,true);setPreComment(toAddr(entry),comment);
   CodeUnit unit=currentProgram.getListing().getCodeUnitAt(toAddr(entry));
   if(unit==null || !comment.equals(unit.getComment(CodeUnit.PRE_COMMENT)))throw new IllegalStateException("Service comment readback differs");
   JsonObject record=new JsonObject();record.addProperty("selector",selector);record.addProperty("entry",entry);record.addProperty("label",label);record.addProperty("readback_matches",true);saved.add(record);
  }
  Files.writeString(Path.of(getScriptArgs()[1]),new GsonBuilder().setPrettyPrinting().create().toJson(saved)+"\n");
  println("Persisted five selected service interface annotations.");
 }
}
