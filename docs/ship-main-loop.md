# SHIP main loop: held movement and release interaction

Play segment 15 `SHIP` is the first supplied-profile gameplay loop. Its entry is P1 `$0970`, selected by root segment 1 P3 `$0034` when table29 word45 bits8–11 equal **2**. The supplied state word `$32BB` therefore selects SHIP. These are segment-relative p-code offsets, not 6502 RAM addresses.

The key distinction is **button0 held moves the actor toward the joystick pointer; button0 released tests the actor's current location for an interaction**. P16 passes actor locals6/5 to P14, not pointer locals3/2. A direct “click pointer hotspot and invoke action” port would miss the original walking mechanism.

Reproduce metadata with `python3 tools/ship_loop_evidence.py`; run deterministic contract tests with `python3 -m unittest discover -s tests -p 'test_ship_loop_evidence.py'`. [Machine-readable evidence](../analysis/ship-main-loop.json) records whole segment hashes, range hashes, physical Play track/sector/image offsets, opcode/operand guards and confidence. Inputs are the private inventory-bound original segment and decoder records. No full game instructions or assets are published here.

## One iteration

| Stage | Source | Proven behavior |
|---|---|---|
| Enter | 15P1 `$0970`, `$0A1E` | Acquire segments8/14/27; local13=30; local18=`SHIP`; P11 initializes |
| Predicate | 15P1 `$0982–0993` | Iterate while current mode is2 or10 |
| Held movement A | `$0998–099D` | Native22P2 selector4 tests button0 level; if down call P13 |
| Pointer | `$099F–09A3` | Native22P43 updates locals3/2 by reference |
| Modal | `$09A6–09C8` | Native22P2 selector1 rising edge OR mode10: P15,8P1; then P11 if resulting mode<11 |
| Periodic work | `$09CA–09DF` | Increment word354; if signed word354>=word353 call24P9 |
| Held movement B | `$09E2–09EA` | Poll button0 level and call P13 again if down |
| Button transition | `$09EC–0A08` | Compare level with local12; update history; press clears local4, release calls P16 |
| Repeat/leave | `$0A0A–0A1B` | Repeat predicate; on exit save previousmode2 and release27/14/8 |

P11 sets word353=15 at `$0692`, button history local12=0 at `$06B3`, actor animation/direction locals9/8=12/13 and initializes pointer via22P42 at `$06DA`. It restores/repositions actor coordinates according to previousmode. Actor position persists in word40 and low8(word41). Do not describe the threshold15 as frames, milliseconds or ticks without establishing24P9 and runtime timing.

Two held movement calls bracket pointer sampling. The first uses the prior pointer and the second uses the new sample. Button level is polled several times, so this is the normal flow, not an atomic snapshot of input. Modal return does not immediately retest loop mode: periodic work and the remaining input stages still occur before `$0982`.

## Motion and rendering

P13 `$070C–07BF` forms deltas `(pointerLocal3−3)−actorLocal6` and `(pointerLocal2+3)−actorLocal5`. For each axis it computes sign(delta)*2 and clamps the absolute step to the remaining distance (22P34/35). It invokes22P41 before movement, calls22P22 with references to actor locals6/5, and invokes22P41 afterward. If both actor coordinates are unchanged, it retries22P22 with sign-only deltas. Thus the fallback permits a smaller step; the exact collision map and actor animation rules belong to22P22 analysis.

The two coordinates are identified by caller data flow here; the screen-axis contract and precise pointer XOR implementation are documented separately in [input-system.md](input-system.md). Actor rendering and pointer rendering are distinct operations. This loop alone does not establish a full-screen repaint per iteration.

## Release interaction and scene return

P16 `$08E6–0964` asks P14 to classify the actor position. If the target equals remembered local4, service EXIT(15,16) exits that procedure; it does not exit the whole game. A press resets local4=0, preventing repeated interaction during a held movement phase. For a new positive target P15 records context before dispatch:

| Target | Source | Consequence |
|---|---|---|
| 1 | `$0924–092B` | Set currentmode0; P4 draws cockpit controls including FUEL/GUNS/SHLD/WARP |
| 3 | `$0936`→P7 | Set mode3, previousmode2; clear word45 bit13, set bit12; copy navigation/context fields |
| 4 | `$0941`→P6 | Clear bitarray116/117; set mode3 if word347 false; word292=6; actorlocal5+=20; P5 redraw |
| Other positive | `$0945–0961` | If word347 false call14P1(&local1); reinitialize viaP11 if word347 remains false |
| 0 | `$0914–0919` | No positive-target modal |

P15 `$08B2–08DB` toggles/removes the pointer via22P41, writes previousmode2 and low action nibble11, saves actor words40/41 and callsP5. These are **RAM state saves**, not proof of a disk save operation. P1 invokes8P1 after P15 for button1 edge/mode10. Tracing8P1 to a verified save/quit and disk-write path remains necessary before assigning that modal a complete UI contract.

After SHIP returns, root1P3 `$005C–007B` releases segment24 and returns for modes3/4 or>=11; otherwise it repeats its mode dispatcher. Mode0/1 then selects13P1; mode9 selects16P1. The enclosing root1P6 selects rootP3 for modes<=2, rootP4 otherwise, and stops for mode>=11. Therefore mode3 transition leaves the interior controller and goes through the root dispatcher, rather than invoking the next scene inline in P7/P6.

## Confidence and unresolved details

Control flow, packed mode selection, call identities, actor-versus-pointer arguments, level-versus-edge distinction and the guarded state writes have high static confidence. Gameplay names beyond `SHIP` and visible cockpit strings remain qualified until matched to specific resources/screens and modal code. Native selector meanings are independently established in [input-system.md](input-system.md).

Remaining questions:24P9's nested time-unit/reset and state changes (top-level calls now indexed in [game-main-loop.md](game-main-loop.md)); word347 semantics; mode10's cause; complete8P1 save/quit chain; resource-backed22P22 collision/animation contract (candidate ordering verified in [ship-actions.md](ship-actions.md)); measured pointer feel and frame pacing. No emulator or macOS gameplay implementation was added for this investigation.
