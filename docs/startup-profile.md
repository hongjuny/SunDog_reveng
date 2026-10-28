# Original startup profile and first SHIP image

The supplied Utility disk selects a profile whose saved mode is **2**, so the first scene dispatches to Play SYSTEM.STARTUP segment 15, procedure 1 (SHIP). The state word is `0x32BB`: the dispatcher uses bits 8–11, not bits 12–15. Reading its high nibble as mode 3 would incorrectly select the exterior scene.

Reproduce the evidence with:

```sh
python3 tools/startup_profile_evidence.py
python3 tools/verify_native_ship.py
```

The first command exports a private image resource and regenerates `analysis/startup-profile.json` and `analysis/initial-ship-asset.json`. Reports contain original disk sectors, image offsets and per-sector hashes. Exported game bytes remain under ignored `analysis/local/`; they must not be published.

## Source and confidence

The original Utility metadata at absolute Pascal block 83 selects profile index 1. Segment 26 P6's profile formula selects relative block `24 + 10*1 = 34`; the game's block mapping adds 3, giving Utility absolute block 37. Its 512-byte header is loaded directly into table 29 starting at word 36. Therefore header offset 18 supplies word 45 (`0x32BB`), and offset 92 supplies word 82 (`0x0080`). The profile's name is Bowie; profile eligibility and menu behavior are documented separately in the post-title flow investigation.

The original root segment 1 P3 case dispatch at source offset `$0041` selects the segment 15 P1 call at `$0034` for mode 2. The call is on Play track 17, sector 5, byte `$34` (logical image offset 70964). Source hashes and the precise opcode contract are checked by the script. This resolves the initially unknown supplied-profile mode in the earlier generic startup analysis; other save profiles can select other scenes.

Segment 7 P5 initializes table 29 word 32 to 26. Segment 15 P8 checks word 82 bit 7 at `$0315`; the supplied profile has that bit set. Its image load therefore selects relative block 26, absolute Play block 29, four 512-byte blocks. If the bit were clear, the alternative would be absolute block 33. The preceding temporary load uses absolute block 41 and must not be mistaken for the final SHIP image. Every selected sector is matched to the original WOZ verification inventory; no unreadable Play track 34 sector is used.

Confidence is high for the supplied profile, mode, conditional resource selection and decoded base bitmap. Exact sector coordinates for every contributing sector are retained in the generated reports rather than copied manually here.

## Native image contract

SYSTEM.LIBRARY segment 24 P5, native source offset `$1010`, expands the selected stream into the 8192-byte HGR page at `$2000–$3FFF`. The first byte is a nonzero destination stride. Each column advances through the page by that stride. A token with bit 7 clear repeats the next byte `token+1` times; a token with bit 7 set copies `(token&127)+1` literal bytes. A column stops at the page end, including when a run ends early there.

The supplied image has stride 1. It consumes 1687 of its 2048 source bytes. The decoded page SHA-256 is `e3f6e1f949b7600953fbacd152c05d8da531a0fd657c9ea19eb7b1fe2c3fdf56`.

`native/SunDogLogic/ShipScreenDecoder.swift` implements this bounded transform directly. The verification script compares the compiled Swift result and consumed source cursor to bounded execution of the original native routine, using both original resource choices and 18 deterministic synthetic streams across nine strides. All 20 cases match, including all 8192 output bytes; four malformed sources are rejected. Original instruction addresses agree with the persisted Ghidra native instruction boundaries. This CPU probe is an analysis test, not an app execution backend.

Segment 22 P19 with its final parameter zero sets drawing bounds without filling them: its call to native P7 is conditional on a nonzero final parameter. Thus the full-window P19 call following decompression does not erase the base image.

## Native implementation boundary

The native app may display this exact disk-derived SHIP base bitmap once the original Play-side header gate succeeds. That is a verified first-scene graphics layer. Subsequent status text, cursor overlays, input actions, movement, interactions, and the meanings of the remainder of the loaded 5KB state record still require reconstruction. Displaying this bitmap alone does not constitute a playable first scene.
