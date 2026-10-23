# Original font prefix for native rendering

`python3 tools/export_native_font.py` writes the original 128-slot font prefix to
ignored `analysis/local/native-assets/sundog-font.bin`. It exports 1,024 bytes,
SHA-256 `eeadc8615ae25ac5611744c0f32589698d4d3cc4c57808a98df85268d08ca775`.
The public [provenance report](../analysis/native-font-asset.json) contains hashes
and coordinates, not glyph bytes.

In the retained Utility-menu snapshot, segment-22 native P9 reads its font
pointer from `$B082/$B083`. These are the source `$02C6/$02C7` fields relocated by
data-29 base `$ADBC`; reading unrelocated `$02C6` in that snapshot would yield a
false pointer. Actual saved REA/Ghidra assembly shows the reads at `$A9A9` and
`$A9B0`. The pointer value is `$1000`. Native code multiplies the character's low
byte by eight and adds this pointer. P48 passes string bytes through P47 to P9
without character translation on the normal character path (`$09B7/$09B8`,
`$08BF/$08C0`). Backslash, vertical bar and spaces have separate layout behavior
in P48, so a basic glyph preview does not establish full string layout semantics.

The four captured pages `$1000`, `$1100`, `$1200`, `$1300` match Utility Track 0
DOS logical sectors 9, 8, 7, 6 respectively, each byte for byte. The exporter
requires those matches and the previously recorded sector and capture hashes.
This is source binding, not classification from visual appearance or entropy.
Eight-byte glyph slots are stored bottom row first; the normal compositor masks
row bytes with `$7F`. All selected slots 0–127 are available, including control
and symbol slots. A native text field may restrict input to 7-bit characters as
an explicit UI constraint; it must not silently transliterate Unicode.

Confidence is high for this selected prefix and pointer binding. The full bank
extent, loader operation and later font selection remain open. Native P9 can
form offsets for 256 low-byte values, but that alone does not certify the next
1,024 bytes as font data. No assets are embedded in public sources, and no new
emulator session was used for this export.
