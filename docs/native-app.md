# macOS native port — first implementation

`Build/SunDog.app` version 0.3.1 is a native rendering/input preview, not a playable
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

Edit the 7-bit text to exercise the original text placement and glyph compositor.
P48 accepts up to 80 bytes. Backslash is its conditional newline marker; repeated
newlines at the left margin are ignored. Ordinary leading spaces are omitted;
vertical bar forces a space glyph. ASCII LF is an ordinary glyph, not a newline.
The selected safe word length is 20 bytes, because longer words can alias the
original procedure's later scalar locals. Bottom-window handling is not ported;
reaching it reports a boundary instead of silently truncating text.
Click the display for focus.
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
- `WindowTextLayout` and `NativeTextPage`: reconstructed P48 tokenization and
  word wrapping, P47 pre/post character wrap, and P45 eight-row newline. The
  preview's selected window coordinates remain host policy. P48's P11(3) selects
  mask003F and drawing mode3. P12 stores the direct coordinates when its line
  mode is disabled; this verified mode connects logical layout to native P9.
- Existing HGR color profile and CoreGraphics image display. The color profile remains a
  declared approximation, not a measured NTSC display match.

Offline output using the same page composition is available for comparison:

```sh
analysis/local/native-build/SunDogRender \
  analysis/local/native-assets/sundog-font.bin \
  analysis/local/native-assets/native-preview.png
```

Validation: 420 original native glyph fixtures compare complete 8,192-byte pages
and next x with Swift; 512 filter and 256 latch fixtures compare input state;
the existing arithmetic helper has 733 comparison cases. Fifty decoded-original
CFG cases verify glyph positions and final cursors (including two explicit bottom
boundaries), and 273 original native helper cases verify column/shift conversion.
Eleven Swift XCTest cases
cover display decoding, page layout, invalid inputs and interleaved host buttons;
103 Python tests pass. Reproduce comparisons with `tools/verify_native_glyph.py`,
`tools/verify_native_input.py`, `tools/verify_native_rules.py` and
`tools/verify_native_text_layout.py`. The layout comparison evaluates only the
whitelisted original decoded procedures with explicit native-call hooks; it is
not a claim of full original application execution.

The core library also now contains [segment21 map selection](event-contract.md):
293 original-fragment comparisons cover signed16 arithmetic, wrapping origins,
signed division, magnitude remainder and raw/nibble results. This function is not
connected to the preview canvas: the actual scene map construction and lifecycle
are still unresolved. A synthetic comparison map is never presented as game data.

GUI verification remains incomplete in the restricted agent session: LaunchServices
returned `kLSNoExecutableErr` although the signed arm64 executable exists. A direct
launch aborted in `_RegisterApplication` during `NSApplication` initialization,
before the native screen model was entered. Build, signature checks, XCTest and
offline PNG rendering passed. This does not establish that interactive window or
Metal presentation has been exercised successfully.

After the reported blank startup, the prototype's default screen was changed
from a silent-error Metal path to a CoreGraphics image. The old Metal path could
fail after device discovery and leave only a log; that is a demonstrated code
defect, not confirmation of the specific cause on the user's desktop. The app
now requests foreground activation and shows an explicit error/open-font panel
when no frame exists. Its title and initial text identify it as a rendering
prototype with gameplay absent.

`Build/SunDog.app/Contents/MacOS/SunDog --diagnose` runs the actual bundle's model
without starting NSApplication, checks its bundled font and reports generated
frame dimensions/nonblack pixels. Asset-containing builds require this check
to pass. This verifies startup content, not a visible window or game launch.

Next required game work is P44 scrolling/window reset, native clipping and line
modes, segment 21's scene workspace lifecycle, and scene-specific data ownership/state changes. Trading, travel,
city scenes, sound and original save/load are not implemented. The disassembly
milestone establishes code structure; it does not supply these missing semantics.
