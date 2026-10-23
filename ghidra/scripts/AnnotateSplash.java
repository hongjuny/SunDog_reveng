import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.symbol.SourceType;
import com.google.gson.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class AnnotateSplash extends GhidraScript {
    public void run() throws Exception {
        byte[] source = new byte[0x2400];
        currentProgram.getMemory().getBytes(toAddr(0x4000), source);
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(source));
        if (!digest.equals("1b9dfd8bbaa973ea73bc650e1c9161f3991d00d6a071bc2403d59582fdc6f29d"))
            throw new IllegalStateException("Wrong splash source program");
        int[] addresses = {0x4000,0x4014,0x405e,0x40e3,0x4112,0x41a5,0x41d4,0x41e2,0x41ff,0x4200};
        String[] names = {"SplashReveal", "SplashCenterSeed", "SplashExpandIteration", "SplashTopFiveRows",
            "SplashRightEdge", "SplashBottomFiveRows", "SplashLeftEdge", "SplashExpandBounds", "SplashReturn", "SplashHGRAddress"};
        String[] comments = {
            "Original spaceship/planet background reveal, without SUN DOG logo; copies bitmap source = HGR destination + $2400. No p-code is involved. REA ev_51ca2df4d888134ce1cd657612ad428abb24719ec6ba9280940d9ed59c2a72ff.",
            "Four center writes: rows95/96 and byte columns19/20.",
            "19 iterations. Initial L18 R21 T90 B101; each iteration L-- R++ T-=5 B+=5.",
            "Increasing columns; five ascending rows per column. Source pointers are corresponding HGR pointers + $2400.",
            "Right byte column; ascending rows top through bottom, inclusive.",
            "Decreasing columns; five descending rows per column.",
            "Left byte column; descending rows bottom through top+1. Top row is excluded here.",
            "Expand bounds by one byte horizontally and five rows vertically; count19 ends at columns0/39, rows0/191.",
            "RTS returns to bootstrap0867 for the observed JSR0864 path; runtime/Language Card loads follow the picture.",
            "A=byte column, X=row. Returns HGR page1 address in zp18/19. Verified row tables and all192 rows. REA ev_d1836c939bcb0c2c50178c38f60aac98adaf1db2dda742bbcde0a90b2e41f851."
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
        println("SPLASH_ANNOTATIONS_OK");
    }
}
