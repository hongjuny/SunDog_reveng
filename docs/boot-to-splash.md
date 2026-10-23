# ROM boot to original title display

The title is drawn before the Pascal system starts. The complete selected path is
slot6 Disk II ROM → `$0801` → ROM `$C65C` twice → `$0819` → `$08FF` → native `$4000`
→ return `$0867`. The large SUN DOG lettering, spaceship and planet are already
pixels in the bitmap; this first title does not call the later Pascal text or
font engine.

`python3 tools/boot_splash_evidence.py` reproduces the source checks and writes
`analysis/boot-splash-chain.json`. It consumes the original Utility image, mapped
boot region and existing hash-bound ROM/RAM evidence. It does not start a new
emulator or incorporate a machine runtime in the app.

## ROM-assisted three-sector bootstrap

The retained slot6 ROM has SHA-256
`de1e3e035878bab43d0af8fe38f5839c527e9548647036598ee6fe7ec74d2a7d`.
It was captured from the existing AppleIIPlus reference run and matches that
run's manifest. This is an exact ROM/model binding, not proof that every physical
Disk II controller supplied with the historical game had the same ROM.

The ROM initially reads physical T0/S0 to `$0800`. Its post-read code at
`$C6EB..$C6FA` increments destination page `$27` and sector number `$3D`, compares
the new sector number with byte `$0800`, and returns to `$0801` when the threshold
is met. If more sectors are required, its backward branch targets `$C6D3`.
Thus the initial byte01 is a sector-count threshold, not an instruction.

| Physical sector just read | Destination | Header threshold | Post-read sector | Game continuation |
|---:|---:|---:|---:|---|
| 0 | `$0800` | 1 | 1 | Set header3, increment sector to2, jump `$C65C` |
| 2 | `$0900` | 3 | 3 | Set header5, increment sector to4, jump `$C65C` |
| 4 | `$0A00` | 5 | 5 | Header≥4; proceed at `$0819` |

The game checks X=`$60` at `$0801`; a different slot takes the error path at
`$08B3`. The two game increments skip physical sectors1 and3. The three loaded
physical sectors0,2,4 correspond to DOS logical sectors0,14,13, with image offsets
0,3584,3328. Their hashes and source coordinates are recorded in the report.
The script runs the original ROM footer and game header fragments on declared
RAM fixtures, stopping before any device access. It also independently checks
the retained actual `$0801` and `$08FF` checkpoints.

## Cold-start screen preparation

At `$0819`, the loader tests resident bytes around `$4000` against its existing
error-message region. Matching can bypass both first load and title display,
entering `$0867` directly. A mismatch can also skip clearing when the decremented
Y becomes zero. These branches must not be silently collapsed into unconditional
cold boot.

Replaying this fragment in the retained cold-start RAM context reaches the clear
loop at `$082E`. It performs exactly8,192 sequential zero writes over
`$2000..$3FFF`. The script stops at `$0842`, before soft-switch reads. The next
four source instructions read `$C057`, `$C054`, `$C052`, `$C050`, selecting HGR,
page1, full-screen graphics. The retained `$08FF` and `$4000` snapshots agree with
these switch states; HGR is completely zero at the observed `$4000` entry.

## Load and call the display routine

At `$0853..$085F`, the bootstrap prepares destination page40, page count24hex=36,
and block00C9hex=201. `$0861` calls the game's disk routine `$08FF`; its sector
order comes from the game's physical-sector table, not `.do` file adjacency.
All36 source sectors are reconstructed and checked against the exact9,216 bytes
captured at `$4000..$63FF` before display begins.

- `$4000..$43FF`: native display code and row-address tables.
- `$4400..$63FF`: original8,192-byte HGR picture source.

`$0864: JSR $4000` pushes return value0866. At the retained `$4000` breakpoint,
SP=FE and stack bytes `$01FF/$0100` encode0866, so the eventual native RTS at
`$41FF` returns to `$0867`. The bitmap routine uses helper `$4200`, then reads
picture bytes at destination+$2400 and writes HGR page1. Ordered reveals and
loop timing are documented separately in the reveal analysis.

After the return, `$0867` begins the Language Card operations and further loads.
The post-title `$FEF2` checkpoint's entire HGR page equals the normalized original
disk bitmap. Only later does startup reach the p-machine fetch loop `$D293`.
There is no Pascal interpreter or character-renderer call in the title path.

## Observed time versus inferred time

The retained logical-media run records `$0801` at cycle1,792,442, first `$08FF`
at1,933,974, native title entry `$4000` at3,756,740 and post-title `$FEF2`
at6,818,202. The interval4000→FEF2 includes title execution **and subsequent disk
loads**, so it is not a measurement of the reveal duration. The run used
re-encoded logical media, not original WOZ bit timing. These historical counters
corroborate ordering but cannot establish physical disk or monitor timing.

Confidence is high for this source-specific control/data path and retained model.
Original hardware timing, alternate resident paths and display signal fidelity
remain separate. The public report contains metadata and addresses; complete ROM,
game bytes, RAM and listings stay in ignored local paths.
