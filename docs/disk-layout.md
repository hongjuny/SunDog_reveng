# Disk layout — milestone 1

## Verified inventory

Both supplied logical images are 143,360 bytes: 35 tracks × 16 sectors × 256 bytes.
Offset of a DOS logical sector is `(track*16 + sector)*256`.
Both original files have WOZ2 signatures; sizes, SHA-256 identities and stored vs
computed CRC-32 values are in `analysis/media.json`. Originals are opened read-only.

Utility has 560 reported decoded sectors. Play has 544; all 16 sectors on Track
34 are unknown. This failure provenance was supplied with the input, and the
separate CiderPress2 checks record which samples can be independently read.
File contents in those slots are never treated as game data.

There are exactly **103 corresponding identical readable sectors**. All 80 sectors
on Tracks **13–17** match. `analysis/comparison.json` enumerates the remaining
matches, all repeated sector hashes (including within a side and at different
positions), and equal-byte counts for every comparable sector. Identity is exact;
it does not establish code, graphics, or runtime identity.

The DOS logical-to-physical mapping is
`0,13,11,9,7,5,3,1,14,12,10,8,6,4,2,15`.
This is distinct from its inverse. Source: the local CiderPress2
`DiskArc/GeneralChunkAccess.cs`, `sDos2Phys` and `sPhys2Dos`.
Boot-continuation consistency supports the supplied DOS ordering; geometry alone
cannot prove sector ordering. Independent WOZ samples are in `analysis/woz-checks.json`.

## Reproducible artifacts

`analysis/{utility,play}-sectors.json` records provenance, status, SHA-256, Shannon
entropy, distinct byte count, zero/FF/printable counts and all 256 histogram bins.
Unknown sectors have no byte-derived statistics. Entropy is never a type classifier.
`analysis/regions.json` inventories 69 known tracks, exported to the Git-ignored
`analysis/regions/`. Boot-specific regions have separate provenance manifests.
Raw string/search output is local-only, to avoid distributing bulk game content.

## Candidate structures

The scanner searches ASCII and high-bit-masked printable runs, literal signatures,
and aligned candidate Pascal directory entries (26-byte shape, plausible block
bounds, short names and kind fields). These filters produce false positives and
are not filesystem validation. See `docs/pascal-runtime.md`.
No standard filesystem is established. CiderPress2's failure to recognize one was
reported in the task; readable-sector access still works without filesystem recognition.

Graphics layouts remain candidates. Full-track exports permit experiments, but
no track is classified as graphics from its entropy. Cross-disk identical tracks
13–17 are high-priority common-resource candidates with unknown semantics.
