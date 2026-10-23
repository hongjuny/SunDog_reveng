// Persist bounded native glyph findings; labels do not imply complete game semantics.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import com.google.gson.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
public class AnnotateGlyph extends GhidraScript {
 public void run() throws Exception {
  if(!currentProgram.getName().equals("rea-library22-char9-captured.bin"))throw new IllegalArgumentException("Captured glyph slice required");
  JsonObject report=JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
  JsonObject mapping=report.getAsJsonObject("captured_mapping");int entry=mapping.get("native9_address").getAsInt();
  byte[] data=new byte[mapping.get("native_slice_length").getAsInt()];
  if(currentProgram.getMemory().getBytes(toAddr(entry),data)!=data.length)throw new IllegalStateException("Incomplete captured span");
  String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
  if(!digest.equals(mapping.get("captured_slice_sha256").getAsString()))throw new IllegalArgumentException("Captured source identity differs");
  int[] offsets={0,0x13ea-0x1376,0x141b-0x1376,0x1448-0x1376,0x145f-0x1376,0x1470-0x1376};
  String[] names={"library22_native9_glyph","glyph_font_offset_char_times_8","glyph_eight_row_loop","glyph_hgr_two_byte_composite","glyph_advance_x_by_6","glyph_mode2_query_candidate"};
  String[] comments={"SYSTEM.LIBRARY segment 22 procedure 9. Captured binding checked against source and three relocation bases. REA="+report.getAsJsonObject("rea_evidence_ids").get("captured_native").getAsString(),"Font pointer plus character*8. Font data contents/provenance remain separate.","Eight font rows, read in reverse order; screen row increases. Caller baseline/clipping contract not fully reconstructed.","Normal drawing: preserve masks then XOR shifted glyph into two adjacent HGR bytes. 420 bounded synthetic cases; not a full game execution claim.","Normal body advances its x word by six; layout wrapper has its own cursor state.","Mode 2 tests intersections and writes a status word. Exact public API and all mask modes remain unverified."};
  JsonArray saved=new JsonArray();
  for(int i=0;i<offsets.length;i++) {
   int address=entry+offsets[i];createLabel(toAddr(address),names[i],true);setPreComment(toAddr(address),comments[i]);
   CodeUnit unit=currentProgram.getListing().getCodeUnitAt(toAddr(address));
   if(unit==null || !comments[i].equals(unit.getComment(CodeUnit.PRE_COMMENT)))throw new IllegalStateException("Annotation readback failed");
   JsonObject row=new JsonObject();row.addProperty("address",address);row.addProperty("label",names[i]);row.addProperty("comment_readback_matches",true);saved.add(row);
  }
  Files.writeString(Path.of(getScriptArgs()[1]),new GsonBuilder().setPrettyPrinting().create().toJson(saved)+"\n");
  println("Persisted six bounded glyph annotations with readback.");
 }
}
