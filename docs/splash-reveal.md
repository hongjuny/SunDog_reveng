# Original native splash reveal

The ship-and-planet background renderer is the native routine `$4000..$41FF`; its HGR row-address
helper is `$4200..$420F`. This is the routine called by the boot at `$0864`, before
Language Card runtime initialization. It does not call Pascal or draw letters
from the font. It progressively copies the ship-and-planet bitmap from
`$4400..$63FF` into HGR page1 at `$2000..$3FFF`. The SUN DOG logo is not present
in this bitmap or the resulting `$FEF2` screen. Its later rendering stage remains
a separate investigation; the exact reveal proof below covers the background only.

Original source is Utility T25 DOS sector13 for entry `$4000` (image offset105728),
sector12 for its second code page, and sector11 for helper `$4200`. Source digest,
track/sector/byte provenance and actual REA IDs are in
`analysis/splash-reveal-evidence.json`. The region SHA-256 is
`1b9dfd8bbaa973ea73bc650e1c9161f3991d00d6a071bc2403d59582fdc6f29d`.

## Drawing order

`$0000/$0001` hold left/right byte columns; `$0002/$0003` hold top/bottom scanlines;
`$0023` is the ring counter. Each HGR byte represents seven logical horizontal
pixels. Initial bounds are left18, right21, top90, bottom101. The setup first
copies four center bytes in this exact order:

1. row95 column19
2. row95 column20
3. row96 column19
4. row96 column20

For each iteration i=0..18, the bounds are L=18−i, R=21+i, T=90−5i, B=101+5i.
The routine then performs these ordered writes:

| Native range | Ordered copy |
|---|---|
| `$405E..$40F4` | For each column L..R, copy rows T,T+1,T+2,T+3,T+4 in that order |
| `$40F6..$411E` | At columnR, copy rows T..B |
| `$4120..$41B6` | For each column R..L in reverse, copy rows B,B−1,B−2,B−3,B−4 |
| `$41B8..$41E0` | At columnL, copy rows B down through T+1; **T is excluded** |
| `$41E2..$41FC` | L−=1, R+=1, T−=5, B+=5, increment ring count; repeat until19 |

The five pointer pairs used by each horizontal strip are interleaved: the outer
loop advances a column, and the inner loop copies its five rows. Reconstructing
this as five full-row copies gives the same final picture but a different reveal.
Right-edge writes duplicate part of the top strip, and the bottom and left phases
also retain the original duplicates. On iteration18 the bounds are columns0..39,
rows0..191. `$41FF RTS` ends the routine; there is no keyboard wait or timer call
inside this routine.

Each source pointer is the destination HGR address plus `$2400`. Helper `$4200`
uses the verified low/high row tables at `$4210/$42D0`, adds the byte column, and
returns its address in `$18/$19`. The source and destination low-byte pointer
increments/decrements need no carry on these valid row/column bounds. The
high-level reconstruction operates on `rowOffset(row)+column`, with the same
nonlinear HGR row formula used by the renderer.

## Exact comparison and timing

`python3 tools/splash_reveal_evidence.py` runs only this bounded original native
routine in declared synthetic RAM, with a blank page and a synthetic return.
It admits four additional addressing forms in its own isolated probe subclass;
no product CPU or device model is added. Every visited instruction address must
exist in the actual REA/Ghidra exports:

- display: `ev_51ca2df4d888134ce1cd657612ad428abb24719ec6ba9280940d9ed59c2a72ff`
- row helper: `ev_d1836c939bcb0c2c50178c38f60aac98adaf1db2dda742bbcde0a90b2e41f851`

The independent geometric reconstruction matches **all8,041 writes in order and
value**, including duplicate writes. They cover exactly7,680 unique visible HGR
bytes and leave512 non-display bytes untouched. Final page SHA-256 is
`623c8808ab8653a9d20bcbc26ce5cf4058a458764915a9b0c0071d9e35508c37`, identical to
the disk-derived splash and retained original post-animation RAM.

The replay executes143,457 instructions and accounts for515,593 NMOS CPU cycles.
The origin is the first cycle of the LDA at `$4000`; the caller's six-cycle JSR
is excluded and the final six-cycle RTS is included. Each display store timestamp
marks its final instruction cycle. The first write is cycle105, the final display
write is515,530, and the last ring counter increment completes at515,579.
Base cycle facts are independently compared against the installed CiderPress2
`Cpu6502`/`OpDef` source; indexed-read page crossing and taken-branch/page-crossing
penalties are applied to the actual path. Both reference source hashes are saved.

This is exact instruction-cycle accounting under the declared binary-mode NMOS
model, without interrupts or wait states. It is not a measurement of original
physical refresh timing. Converting cycles to host seconds requires a separately
declared clock rate; macOS display scheduling can coalesce writes. Boot disk I/O,
resident-skip and clear branches, physical color and later menus remain outside
this routine's timing claim.

Private `analysis/local/splash-reveal/writes.json` contains the original asset,
all ordered writes, per-write cycle offsets, 20 seed/ring milestones, total cycles
and final page for an independent native-language comparator. It is not committed.
Public output contains only source identities, addresses, counters and hashes.
Six deterministic media-independent tests cover visible coverage, exact seed and
first-ring order, final bounds, taken cross-page branch timing, indexed-read page
penalty and indirect store/write timestamps.
