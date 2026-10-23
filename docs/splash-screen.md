# Original initial background bitmap

The later SUN DOG lettering is now reconstructed separately in
[logo code](title-logo.md) and [original sprite data](title-logo-asset.md).

The original ship-and-planet background is embedded directly in the Utility
boot's initial graphics region. It contains no SUN DOG lettering. It is not
generated from a modern drawing or copied from
a captured PNG. `tools/export_splash.py` reconstructs the loader's block/sector
order and writes the original HGR bitmap to the ignored local file
`analysis/local/native-assets/sundog-splash.hgr`.

The boot loads 36 pages from block201 at `$4000..$63FF`. The first1,024 bytes
contain the native display routine and HGR row tables. The following8,192 bytes,
loaded at `$4400..$63FF`, are the picture: block203 through219 exclusive,32
sectors. The native display routine at `$4000` obtains destination HGR addresses
using helper `$4200`, then adds `$24` to the address high byte to read the picture.
Examples are `$4030→$4032`, `$40E3→$40E5`, and `$41D4→$41D6`. Thus picture source
is destination+$2400. The native routine progressively reveals the picture;
this asset exporter supplies the final static background image. The subsequent
[reveal reconstruction](splash-reveal.md) recovers the routine's complete ordered
writes and CPU cycles and connects them to the native app.

All192 HGR row offsets use the independently verified formula:

```
(row & 7)*1024 + ((row >> 3) & 7)*128 + (row >> 6)*40
```

Each row has40 visible bytes. The source's512 non-display holes are canonicalized
to zero, matching the initially cleared HGR RAM. All7,680 visible bytes remain
unchanged. The normalized8,192-byte page SHA-256 is
`623c8808ab8653a9d20bcbc26ce5cf4058a458764915a9b0c0071d9e35508c37`.

The script verifies the initial region identity and checks every source sector
against the full original-WOZ decode report. Exact side/track/DOS-sector/physical
sector/image-offset/page-source hashes are recorded in
`analysis/splash-asset.json`; original bitmap bytes remain untracked.

The existing post-animation boot checkpoint at `$FEF2` independently corroborates
this result. Its full HGR page at `$2000..$3FFF` equals the disk-derived normalized
asset byte for byte, with full-screen HGR page1 selected. Its RAM is not used to
construct the asset. This checkpoint precedes both the logo addition and the
Utility menu. The later `follow-20261023-115323/after-720-frames` capture contains
the orange SUN DOG logo, while this earlier bitmap does not. The earlier claim
that both images contained the same logo was incorrect. No new emulator
execution or emulator product backend was introduced.

Confidence is high for original background bytes, source mapping and this early
background-stage identity. It is not a complete title-screen reconstruction.
Physical monitor color fidelity still depends on the declared decoder;
the subsequent menu and gameplay are not implemented by showing this picture.
The native reveal now uses the recovered write-cycle schedule with a declared
nominal host clock; original physical scanout remains a separate fidelity limit.

Reproduce with `python3 tools/export_splash.py`. Three deterministic tests cover
visible-byte preservation, zeroed holes, invalid sizes/rows, and original loader
sector ordering with synthetic disks.
