import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.symbol.SourceType;
import com.google.gson.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class AnnotateGameplayInput extends GhidraScript {
    public void run() throws Exception {
        byte[] source = new byte[6126];
        currentProgram.getMemory().getBytes(toAddr(0x4000), source);
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(source));
        if (!digest.equals("36f6e96013a05fc236032f9e925d34649e0908dae19b5eea0e673051f5232c8c"))
            throw new IllegalStateException("Wrong native library22 program");
        int[] addresses = {0x4daa,0x54fe};
        String[] names = {"JoystickAbsoluteSample", "ActorMoveCollisionSlide"};
        String[] comments = {
            "Native library22 P5. C070 starts paddle timers; C064/C065 counted in balanced loop. Absolute coordinates, not velocity. See docs/joystick-pointer.md and REA ev_e989c265fb5ba9e6ba1a7bc3ec18acdd914187aa5d4f3a6c89a1c25899c17f7d. This program uses synthetic relocation segment4000/data9000, not actual runtime addresses.",
            "Native library22 P22. Try (dx,dy), then (dx,0), then (0,dy); P9 mode2 sets overlap scratch word9000. First unblocked candidate updates caller actor coordinates. SHIP15P13 retries one-pixel deltas when unchanged. REA ev_4d639db5476cf53d2fd3134f0c34c92d65ccb6e5bd4575c40a1c0c0de2923fe8. See docs/ship-actions.md."
        };
        JsonArray rows = new JsonArray();
        for (int i=0;i<addresses.length;i++) {
            var address=toAddr(addresses[i]);
            if (getInstructionAt(address)==null) throw new IllegalStateException("Missing instruction");
            createLabel(address,names[i],true,SourceType.USER_DEFINED);
            currentProgram.getListing().setComment(address,CodeUnit.PRE_COMMENT,comments[i]);
            if (!comments[i].equals(currentProgram.getListing().getComment(CodeUnit.PRE_COMMENT,address)))
                throw new IllegalStateException("Comment readback failed");
            JsonObject row=new JsonObject();row.addProperty("address",addresses[i]);row.addProperty("label",names[i]);
            row.addProperty("comment",comments[i]);row.addProperty("readback_verified",true);rows.add(row);
        }
        JsonObject result=new JsonObject();result.addProperty("program",currentProgram.getName());
        result.addProperty("source_sha256",digest);result.add("annotations",rows);
        Files.writeString(Path.of(getScriptArgs()[0]),new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n");
        println("GAMEPLAY_ANNOTATIONS_OK");
    }
}
