# SUN DOG logo after the background reveal

The initial `$4000` bitmap/reveal contains the spaceship and planet **without**
the SUN DOG lettering. The prior identification of the final logo screen with
that earlier bitmap was wrong. The supplied app therefore reproduced the early
background faithfully while omitting the later logo stage.

The actual logo is drawn after Pascal startup by SYSTEM.LIBRARY segment26:
P6 conditionally calls P13, which calls P14 (initialization/resource loading) and
P16 (border and moving-letter animation). Native P9/P10/P11/P12 perform the HGR
writes. Neither a modern font nor an overlay copied from a reference screenshot
is needed.

## Exact source/runtime correspondence

A new original-execution data-write breakpoint at HGR `$2201` stopped immediately
after the first border-clear store. It recorded native PC `$86DA` and p-code PC
`$7F33`. The loaded segment base is `$7E8E`, making these source offsets `$084C`
(native P9) and `$00A5` (immediately after P16's call to P9 at `$00A3`). The observed
write is a zero/background clear, not yet a nonzero orange logo pixel.

The private observation and original media remain untracked. The public report
`analysis/title-logo-evidence.json` identifies their hashes and the exact source
archive. Archive inventory segment26/slot5 supplies the Utility track/sector
mapping. Original relocation arrays reproduce all relevant native runtime bodies;
all replayed native instruction addresses are defined in the persisted Ghidra
listing. A new actual REA/Ghidra P11 slice cross-check is identified by
`ev_ef594b9512e6e5a5acc3492c78e1360b88fb51c8e6c7fa3dde65c592da18ef62`.

## Resource and primitives

P14 calls segment22 P53 with `(destination=$4000, blocks=12, relativeBlock=64,
read=1)`. P53 adds3 to that block number, reading Utility blocks67..79 exclusive:
6,144 bytes. These are six letters, each containing eight pre-rasterized frames
of128 bytes. Each frame's visible part is24 rows ×4 bytes; the remaining32 bytes
are spacing/storage. [Resource extraction](title-logo-asset.md) checks this source
against original sectors and the observed `$4000..$57FF` runtime buffer.

- Native P9 clears/frames one byte column:4 blank rows,4 patterned rows,32 blank
  rows,4 patterned rows,4 blank rows. P16 calls it for columns0..29 at top row32.
  Columns0..28 alternate `$AA/$D5`; column29 is zero. The orange horizontal bars
  occupy rows36..39 and72..75.
- Native P10 saves rows44..67, all40 columns, to a960-byte buffer at `$0400`.
- Native P11 reads `4000 + 1024*letter + 128*frame`, writes24 rows ×4 bytes at
  `floor(x/7), y`, and ORs each source byte with `$80` for the HGR phase.
- Native P12 restores one byte column of those24 rows from the saved buffer.

The six target x coordinates are0,35,70,105,140,175. Their initial x values
alternate252 and245. P16 moves each letter left by14 logical pixels while cycling
frames0..7 every two iterations. Frame8 selects frame7 again. A trailing column
restorer advances left by7 pixels per iteration, cleaning up the moving image.
The next letter starts only after the current letter's trailing restoration and
frame sequence have completed.

## Verification and native implementation

`native/SunDogLogic/TitleLogo.swift` is a direct Swift rewrite. Its constructor
accepts an8,192-byte background and6,144-byte glyph resource. `steps` exposes the
border and each visual animation iteration; `advance(to:)` applies them, and
`compose(background:glyphs:)` produces the completed screen.

Run:

```sh
python3 tools/verify_native_title.py
```

The analysis comparator executes only original decoded P13/P14/P15/P16 CFGs with
explicit hooks for the verified disk read and sound call. Native P9/P10/P11/P12
run through the existing bounded native instruction probe. The Swift output
matches all155 visual steps, all14,256 ordered HGR writes and every intermediate
page. The final page SHA-256 is
`7e4f8f739f8b9d40a411f462036f740e1b518ce547184d03c5f4c746d0cc317d`, exactly matching
the retained original screen containing the logo.

There are154 original sound-generator calls in this path. Their parameters are
recorded, but sound effects and their delay/pacing are not implemented by this
visual contract. The app's wall-clock step interval must therefore be described
as host presentation policy. Reproducing the original sound/pacing, the variable
intervening disk-load delay and later menu behavior remains separate work.
