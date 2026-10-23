# Separate original SUN DOG logo resource

The boot `$4000` bitmap is the spaceship and planet only. Its reveal ends before
the SUN DOG lettering appears. Treating the later logo-complete reference as the
same boot image was incorrect. The logo is a separate6144-byte sprite resource
read by SYSTEM.LIBRARY segment26 procedure14 and displayed by its procedure16.

P14 pushes buffer`$4000`, count12, requested block64 and read flag1, then calls
segment22 P53. That disk wrapper uses unit4, multiplies count by512 and adds3 to
the requested block. The resulting read is original Utility loader blocks67..79
exclusive:24 sectors,6144 bytes, loaded at`$4000..$57FF`. The source hashes and
every original DOS/physical sector coordinate are in `analysis/title-logo-asset.json`.

`python3 tools/export_title_logo.py` exports these original disk bytes directly to
the ignored local asset `analysis/local/native-assets/sundog-logo.bin`. Its SHA-256
is `c49ef7d757ac42f03b2d33ef8fd95c9c83faf02a0d29ac27ad9af1a756d9c2a2`.
All24 sectors must match the independently decoded original WOZ verification.
The actual first-logo-write checkpoint separately corroborates that all6144
loaded RAM bytes equal this resource. No screenshot supplies any asset byte.

The layout is six glyph slots, each1024 bytes. Each glyph has eight128-byte frames.
A frame contains24 rows of four bytes, followed by32 noncopied bytes. Native P11
selects `glyph*1024+frame*128+$4000`, copies the96 visible frame bytes, and ORs
each byte with`$80`. Thus this is neither the normal text font nor a single HGR
screen page. Final glyph frame7 is placed at HGR rows44..67, byte columns
0,5,10,15,20 and25.

For an independent final-state check, `compose_final` preserves the boot picture
outside rows32..79/columns0..29, clears that rectangle, creates alternating`$AA`
and`$D5` byte bars on rows36..39 and72..75 (last column29 stayszero), then places
all six frame7 sprites. The resulting full8192-byte HGR page is byte-for-byte
equal to the retained logo-complete original run, SHA-256
`7e4f8f739f8b9d40a411f462036f740e1b518ce547184d03c5f4c746d0cc317d`.
This final-state check is distinct from the moving-letter P16 animation proof.

Confidence is high for original asset identity, sector order, frame layout and
the final image. Timing, intermediate movement and background restoration are
documented by the original-code logo analysis, not inferred from this final
static image. Original sprite bytes and reference RAM remain private. Three
deterministic tests exercise frame addressing, phase-bit OR, bars/clearing,
outside preservation and invalid dimensions using synthetic content only.
