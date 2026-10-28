# Play-side startup and initial game boundary

The first Play-side game controller is SYSTEM.STARTUP segment1. Its P6 initializes
runtime resources, calls segment7 P1 with argument1, and only then selects a scene
from bits8..11 of table29.word45. This first scene is not safely inferred from a
newly created Swift state filled with zeros. The original menu/data preparation
before scene dispatch remains material.

`python3 tools/initial_game_flow.py` checks source hashes, decoded instruction
bytes, exact operand patterns and branch destinations. It writes
`analysis/initial-game-flow.json` with Play-side track/sector/image offsets and
bounded source-span hashes. Complete original procedure listings remain private.

## Segment7's two entry modes

P1 entry0706 acquires segment25/26 references. Its argument1 selects the P4→P5→P6→P7
initialization path. Argument0 selects P8, which handles later save/exit-related
state rather than replaying startup. The distinction is explicit at070D..071A.

P4 stores initial constants into table29 words293,297,298,296,295,350,349,347,292,
354,352,353,351. Their exact values are generated in the report. This selected
constant initialization does **not** set word45. P5 establishes relative resource
bases word32=26, word30=42, word29=52, word28=61, word27=76 and word26=85, followed
by window/font preparation. These numeric fields are not renamed to gameplay
concepts without additional ownership evidence.

P5 then calls segment26 P6(1) at01C6..01C9. This is the earlier shared title/menu
controller, not simply a static logo primitive. After it returns, P5 calls its
own P3 with false at01CA..01CC. That is the concrete request for the Play side.

## Exact disk-side gate

P3 displays a disk-flip prompt. False selects PLAY; true selects UTILITY. It polls
original input selectors0 and1 and ORs their results. The branch at00C8 loops to
00BB until the low bit is set. After a button edge, P2 reads unit4, block0,
512bytes, and tests byte252:

| Requested side | Required marker |
|---|---:|
| Utility | 0 |
| Play | 9 |

P2's signed16 IORESULT>0 path invokes the verified nonlocal EXIT service with
preceding constants7,2. That is a control-transfer boundary, not a normal false
return. With no such transfer, a wrong marker returns false. P3's branch00CF
returns all the way to003E to clear/redisplay the prompt; it does not silently
continue to the game. A matching marker permits return at00D1.

The supplied disks corroborate the marker values. Both gate reads touch only
Utility/Play track0 DOS sectors0 and14 in the loader's block order. Each selected
sector is checked against the independent original-WOZ decode report. Unreadable
Play track34 is not touched or interpreted as zero data.

This is the first complete portable input/data contract for a native disk-selection
step: wait for an accepted edge, obtain the selected original side, verify its
readable block0 marker, and continue only on success. A native file picker may
replace physical disk flipping as host policy; inventing a New Game/Continue menu
or assigning state0 without tracing segment26's result would not reproduce this
contract.

## After the Play gate

The remainder of segment7 initializes windows and state/resource pointers, then
returns to segment1's dispatcher. Segment1 routes modes0/1 to segment13 P1, mode2
to segment15 P1, and other modes through its second dispatcher. Mode meanings and
the actual initial value are not established by this route table alone.

At segment13 P1's selected entry, the source explicitly loads two512-byte blocks
into0800 through segment22 P53 using relative block table29.word27+2. If P5's base
values remain unchanged, P53's documented+3 translation selects absolute block81.
This conditional resource location is reproducible; it is not yet an identified
complete first-scene bitmap. Segment13 P1 calls P2 and prepares several packed
flags before entering its input/scene loop. Its complete window rendering,
cursor commands and data lifetimes still require analysis.

Confidence is high for these source-specific operands and selected CFG edges.
No new full Play execution or faithful first-game scene is claimed by this
report. Segment26 menu/data construction, Play writes, complete state ownership
and the initial interactive render loop remain unresolved.

Media-independent tests: `python3 -m unittest discover -s tests -p test_initial_game_flow.py`.
