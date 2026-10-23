# Graphics evidence — initial native region

The initial region's purpose is now established: native4000..41FF reveals the
original ship-and-planet background via helper4200, before Pascal starts. The
SUN DOG lettering is absent from this bitmap and appears later; the previous
complete-title interpretation was incorrect. The full write order,
cycle accounting and Swift port are documented in [splash reveal](splash-reveal.md)
and [native startup app](native-app.md). Earlier uncertainties below record the
investigation's initial stage.

The bootstrap reads `$C057`, `$C054`, `$C052`, `$C050` at `$0842–$084B`, selecting
HGR page 1 and full-screen graphics. Its conditional clearing loop writes
`$2000–$3FFF`. Source is Utility T0 DOS sector 0, corresponding image offsets
`$0042–$004D` and `$002E–$0041`; confidence high for static operations, unobserved
for the branch actually taken at boot.

The Utility region loaded from block 201 into `$4000–$63FF` contains a helper at
`$4200` that combines tables at `$4210` and `$42D0` with a horizontal offset.
Every one of the 192 table addresses equals:

```
$2000 + (row & 7)*$400 + ((row >> 3) & 7)*$80 + (row >> 6)*$28
```

`analysis/graphics-evidence.json` records each comparison and source sector.
`tools/structural_evidence.py` reproduces it. Confidence is high for an HGR page 1
row-address table and native graphics addressing. The helper's data flow is
supported by Ghidra, not inferred from entropy. Source tables straddle loaded
pages `$42` and `$43`: the manifest maps them to Utility T25 DOS sectors 11 and 10.

The entry routine copies bytes through pointers derived by this helper and adds
`$24` to source pointer high bytes in several paths. Its complete purpose,
resident-signature interaction, graphical content, and later reuse remain open.
This is an identified native graphics component, not a reconstructed game-wide
renderer. Mouse/joystick, window composition, sprites, text, and screen-update
scheduling remain unidentified. No performance conclusions have been measured.

Milestone 2 narrows the common-resource candidates: the entire directory-mapped
SYSTEM.LIBRARY extent is identical across both sides, with four type-7 (6502)
and three type-2 (little-endian p-code) stored descriptors. Their graphics/UI
responsibilities are still unknown. The Utility SYSTEM.STARTUP descriptor range
also conflicts with independently verified native boot/graphics data, so its
p-code-looking header cannot classify every byte in that range as p-code.

## Game/library rendering path — reconstruction restart

The new [game-code analysis](game-code-analysis.md) supersedes the earlier
statement that no text/UI path was identified. SYSTEM.LIBRARY segment 22 is
mixed: 45 p-code and 18 native procedures. P48 string processing calls P47
character placement, which calls P12 positioning and native P9. Normal glyph
composition uses eight rows, two adjacent HGR bytes, mask/shift/XOR and a six-unit
x advance. The normal body matches 420 declared synthetic cases; caller setup,
clipping and mode-2 behavior remain separate. Source locations, actual REA IDs,
retained-memory correspondence and limitations are in `analysis/graphics-call-chain.json`
and `analysis/glyph-compositor-evidence.json`. This reconstructs an original
rendering operation; it does not implement a game VM or emulator application.
