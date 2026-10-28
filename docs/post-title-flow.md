# Initial progression after the animated SUN DOG logo

The next original step is not yet a city or spaceship scene. SYSTEM.LIBRARY
segment26 P6 displays an introductory panel, waits for either joystick button,
then offers Play SunDog, Use utilities and Run demo. The Play option is conditional
on the selected game state. The source-bound report is
`analysis/post-title-flow.json`; full listings and extracted text remain private.

## Actual callers and disk context

SUNDOG.LIBRARY segment1 P8 pushes0 at `$0056` and calls26/P6 at `$0057`: this is
the Utility entry. Play SYSTEM.STARTUP segment7 P5 pushes1 at `$01C6` and calls
26/P6 at `$01C7`: this is the Play entry. These are distinct callers, not a guessed
interpretation of which file happens to be mounted in a modern application.

P6 reads relative block80 through segment22 P53, whose disk wrapper adds3. The
supplied Utility block83 has a header selecting game index1. Header byte0 is zero
in the supplied cold context. A nonzero byte0 suppresses the logo **and the whole
intro/menu**: the branch at `$03AA` goes to `$06CD`, clears byte0, writes the header
back and returns directly to its caller. The same block on the Play image is not
interchangeable metadata. Never derive a Play initial profile by blindly reading
the Utility-specific header position from the other side.

## First input gate

When header byte0 is zero, P6 calls logo P13, then uses segment22 P44/P48 to render
eight original strings at `$03AF..$0479`. The final two strings ask the player to
press either joystick button. The strings are exported only to
`analysis/local/post-title-flow/intro-strings.json`; they are not embedded as copied
game text in the public report.

The loop initializes local8 to11,400, calls segment22 native P3, decrements local8,
and polls segment22 native P2 with selectors0 and1. It exits when either rising
edge is true, or signed16 remaining<=0. Native P3 shifts a four-byte pseudo-random
state; it is not a keyboard reader. The decrement happens before the exit test.
11,400 is a **logical iteration budget**, not a measured number of milliseconds,
video frames or seconds. Physical device timing remains unresolved.

Ctrl-U does not appear as a direct predicate in this loop. The older reference
record injected Ctrl-U at an earlier BIOS keyboard boundary; that observation
must not be used to replace this joystick gate with a keyboard comparison.

The retained logical-media after720 checkpoint shows the actual introductory
panel, with table29 word12/top90, word14/left135, word13/right270 and word11/bottom181.
P44 initially sets cursor x137/y100. The later retained advanced checkpoint shows
the three-choice menu. Both references are digest-bound; neither is an app image
asset or an executed proof of every branch described here.

## Cold Utility profile reconstructed from the disk

The source can supply the selected profile without copying the retained RAM.
P6 uses header byte1 as its game index. It calculates relative data block
`10*index+24`, then P53 adds3. For index1, the ten-block record starts at actual
block37. Native22 P24 preserves an address value on the stack, so the early one-
block read targets `table29 + 2*36`. Thus source byte18 becomes table29 word45,
byte12 becomes word42, byte14 becomes word43, and byte438 is the Pascal-string
field at word255 used for the greeting name.

The supplied cold profile has word45=`12987` (`$32BB`), giving state nibble**2**,
not3; word42=5174 and word43=13. The ten-block checksum is `$A697`, exactly matching
the stored word at block26 offset94. The original native26 P3 checksum body is
replayed on that record, checked against Ghidra boundaries, and agrees. It adds
the low and high byte columns independently modulo256 rather than using an
ordinary16-bit additive checksum. The selected name is exported from the actual
disk field, not taken from the later Ctrl-U RAM snapshot or hard-coded in Swift.

`tools/post_title_flow.py` writes the local-only profile asset
`analysis/local/native-assets/sundog-startup-profile.json`. This is the supplied
immutable Utility cold profile, not a claim that arbitrary game saves or newly
created games have been reconstructed. Its camelCase fields decode directly as
`StartupFlow.Profile`; the extra name/source fields are for the resource consumer.

## Menu eligibility and outcomes

The original menu IDs are1=Use utilities,2=Play SunDog,3=Run demo. Play is absent
when state nibble12/13, checksum mismatch, or selected index>=4. P6 distinguishes
start versus continue with:

```
(word43 & $3FFF) == 0 && (word42 >> 8) == 0 && (word42 & $3F) == 0
```

The supplied selected game is eligible to continue, not to start as an empty game.

| Current caller mode | Choice | Original action |
|---|---|---|
| Utility0 | Utilities1 | Return to Utility caller |
| Utility0 | Play2 | Set skip marker; copy directory template block80 to target; boot slot6 |
| Play1 | Play2 | Return to Play caller |
| Play1 | Utilities1 | Set skip marker; copy directory template block81 to target; boot slot6 |
| Either | Demo3 | Copy template block82; boot slot6 |

The target directory block comes from header byte7 (79 in the supplied image).
Blocks80/81/82 are actual alternate Pascal directory images. In particular, the
Play template changes which archive is named SYSTEM.STARTUP. After copying the
directory, P6 calls P2 with the short parameter string, then native P8 executes
`LDA $C08A; JMP $C600`. This is direct slot6 ROM boot entry, not an indirect jump
through the CPU reset vector. Demo does not perform the same skip-marker write.

The native rewrite represents these operations as mode-route metadata. It must
not rewrite original media just to navigate a modern UI. On Play continuation,
segment7 P5 next calls its P3(false) media-validation/flip prompt and segment22 P52;
further initialization precedes the game mode dispatcher. This contract does not
yet implement a playable scene, a save system or complete disk-switch behavior.

## Native module and verification

`native/SunDogLogic/StartupFlow.swift` contains the first gate and menu decisions.
It exposes typed modes, the profile, eligible choices, a logical `poll(first:second:)`
operation, and explicit destination/legacy-directory metadata from `select(_:)`.
It reuses the separately native-verified `ButtonInput` latch/edge filter. A skip
profile starts in transitionReady with a same-mode `selectedRoute`; a cold profile
starts in awaitingBegin. No emulator or p-code execution backend is linked.

Run `python3 tools/verify_native_startup.py`. It verifies288 profile combinations,
all11,400 timeout polls, both edge channels, six mode/choice routes, invalid-action
rejection and28 source-expression cases. Four deterministic Python tests need no
media. The comparison is source-bound static logic plus the original isolated
checksum and gate-expression checks; it does not observe all physical input or
original application paths. Clocking host polls and device mapping are explicit
frontend choices and cannot be described as original timing without more evidence.
