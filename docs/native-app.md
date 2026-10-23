# macOS native port — first implementation

`Build/SunDog.app` version 0.2 is a native rendering/input preview, not a playable
SunDog game. It draws original font data with reconstructed Swift glyph operations
and routes macOS button samples through the original rising-edge filter rules.
It does not load reference screenshots as its screen. The older capture viewer
is now the separate `SunDogReference` executable.

Build and run locally:

```sh
python3 tools/build_native.py --tests --include-local-assets
open Build/SunDog.app
```

The optional asset flag verifies and copies the 1,024-byte original font from the
user's media into this local bundle. Both the font and bundle remain ignored by
Git; do not distribute this asset-containing build. Without the flag, use Open
Original Font to select the exported file or pass `--font PATH` to the executable.
Rebuilding without the flag removes a previously bundled font.

Edit the 7-bit text to exercise the glyph compositor. Click the display for focus.
Space/primary click map to preview channel 0; Return/secondary click map to channel
1. Counters record rising edges, including interleaved presses. These host mappings
and per-event sampling are preview policy, not recovered Apple II device mappings
or timing. Focus loss releases both samples.

The app combines:

- [Original glyph compositor](native-glyph.md): eight bottom-first rows, adjacent
  HGR bytes, masks, XOR, phase-bit preservation and six-pixel advance.
- [Verified font prefix](native-font-asset.md): actual relocated pointer and four
  matching original sectors, 128 character slots.
- [Original input filter](native-input.md): pending press OR, edge/history and
  level behavior; no copied interpreter or original game execution backend.
- `NativeTextPage`: host preview placement, wrapping and overflow policy. This
  is explicitly separate from Pascal P48 line/escape handling and window clipping.
- Existing HGR color profile and Metal display. The color profile remains a
  declared approximation, not a measured NTSC display match.

Offline output using the same page composition is available for comparison:

```sh
analysis/local/native-build/SunDogRender \
  analysis/local/native-assets/sundog-font.bin \
  analysis/local/native-assets/native-preview.png
```

Validation: 420 original native glyph fixtures compare complete 8,192-byte pages
and next x with Swift; 512 filter and 256 latch fixtures compare input state;
the existing arithmetic helper has 733 comparison cases. Ten Swift XCTest cases
cover display decoding, page layout, invalid inputs and interleaved host buttons;
94 Python tests pass. Reproduce comparisons with `tools/verify_native_glyph.py`,
`tools/verify_native_input.py` and `tools/verify_native_rules.py`.

GUI verification remains incomplete in the restricted agent session: LaunchServices
returned `kLSNoExecutableErr` although the signed arm64 executable exists. A direct
launch aborted in `_RegisterApplication` during `NSApplication` initialization,
before the native screen model was entered. Build, signature checks, XCTest and
offline PNG rendering passed. This does not establish that interactive window or
Metal presentation has been exercised successfully.

Next required game work is P48/P47 layout and clipping, segment 21's eight-reference
event contract, and scene-specific data ownership/state changes. Trading, travel,
city scenes, sound and original save/load are not implemented. The disassembly
milestone establishes code structure; it does not supply these missing semantics.
