# Graphics evidence — initial native region

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
