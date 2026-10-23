// Captured library-native input implementation; no original bytes are edited.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import com.google.gson.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
public class AnnotateInput extends GhidraScript {
 public void run() throws Exception {
  if(!currentProgram.getName().equals("rea-library22-input2-captured.bin"))throw new IllegalArgumentException("Captured input slice required");
  JsonObject report=JsonParser.parseString(Files.readString(Path.of(getScriptArgs()[0]))).getAsJsonObject();
  int entry=report.get("captured_entry").getAsInt();byte[] bytes=new byte[216];currentProgram.getMemory().getBytes(toAddr(entry),bytes);
  if(!HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)).equals(report.get("captured_function_sha256").getAsString()))throw new IllegalArgumentException("Input bytes differ");
  int[] addresses={0xa208,0xa243,0xa267,0xa280,0xa29b,0xa2b1};
  String[] names={"library22_native2_channel_poll","input_read_selected_channel","input_rising_edge_filter","input_restore_add_dispatch","add16_input_latch_hook","input_chain_saved_add16"};
  String[] comments={"Original library-native input function. 512 synthetic sample/pending/history cases. Initial hook gate and physical timing remain open.","Selector low two bits choose C061+index. Only bit 7 contributes to down state, together with the pending latch.","Selector bit 2 clear: return down AND NOT previous; update previous. Bit set skips this history update and returns level.","Exact selector 8 restores saved D004/D005 and returns false. Installed flag is not cleared here.","Preserve A/status; OR C061/C062 into two pending bytes. Retained bank-1 D004 points here instead of baseline opcode-82 handler D71D.","JMP operand at A2B2/A2B3 contains saved original ADD16 dispatch target. This is mutable code, not an unrelated data word."};
  JsonArray rows=new JsonArray();
  for(int i=0;i<addresses.length;i++) {
   createLabel(toAddr(addresses[i]),names[i],true);setPreComment(toAddr(addresses[i]),comments[i]);
   CodeUnit unit=currentProgram.getListing().getCodeUnitAt(toAddr(addresses[i]));
   if(unit==null || !comments[i].equals(unit.getComment(CodeUnit.PRE_COMMENT)))throw new IllegalStateException("Input annotation readback failed");
   JsonObject row=new JsonObject();row.addProperty("address",addresses[i]);row.addProperty("label",names[i]);row.addProperty("readback_matches",true);rows.add(row);
  }
  Files.writeString(Path.of(getScriptArgs()[1]),new GsonBuilder().setPrettyPrinting().create().toJson(rows)+"\n");
  println("Persisted six original input/hook annotations.");
 }
}
