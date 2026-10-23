# Native glyph compositor

`native/SunDogLogic/GlyphCompositor.swift` reconstructs the normal drawing body
of SYSTEM.LIBRARY segment 22/native procedure 9, source offsets `$13D0..$14BE`.
It applies the recovered seven-bit mask/shift/XOR expressions to two adjacent
HGR bytes on each of eight scanlines. Existing high phase bits are preserved;
font bytes are consumed bottom first. The logical x position advances by six.

Public API: `GlyphCompositor.draw(glyph:page:x:baseline:maskLow:maskHigh:)` mutates
an 8,192-byte page and returns the next x. It requires exactly eight glyph bytes,
x in 0...272 and baseline in 7...191, so every two-byte write stays within the
40-byte scanline. Bad arguments throw before any mutation. Default masks are
explicit caller defaults (low `$3F`, high zero), not a claim that every original
window uses these values. The compositor accepts the recovered masks separately.

`python3 tools/verify_native_glyph.py` compiles the Swift implementation and
compares all page bytes plus next x against 420 synthetic fixtures executed
through the bounded original native body. These cover seven shifts, five low
masks, three high masks and four vertical positions, including both screen
edges. Six additional Swift checks reject malformed pages/glyphs and unsupported
coordinates without changing page data. Fixtures and reports are private in
`analysis/local/native-glyph/`; no original assets are embedded in this target.

Evidence identity is checked against `analysis/glyph-compositor-evidence.json`
and the retained actual REA record
`ev_7f31030127a94c609a6f96ffa111c85ada82528fffc46e6e1dc94e6407437e3e`.
Source archive SHA-256 is
`7d52f0e6959d0a8b9ac3f08bc78ced7e7af44ed87a00d80d4d82025ab7735f49`;
slice SHA-256 is
`7e77250cdfc3fa8e04023d274d1d12b3d63cf4c36f48dfaa41f96ef88af3a986`.
The script reuses the saved REA evidence; it does not claim a fresh REA session.
Confidence is high for the selected normal body and mask expressions. Caller
clipping/argument setup, mode-2 collision queries, original font extraction,
window layout and game events remain separate work.
