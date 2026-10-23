# Native macOS startup screen

`Build/SunDog.app` version0.5 displays the original Apple II title and reconstructs
its center-out reveal. The app contains Swift image decoding and a rewritten
reveal algorithm, not an Apple II CPU, p-machine or disk emulator. Gameplay and
post-title transitions are not implemented.

```sh
python3 tools/build_native.py --tests --include-local-assets
open -n Build/SunDog.app
```

The local-assets flag verifies the user's original Utility sectors, reconstructs
an8,192-byte bitmap, verifies the original native reveal against Swift, and bundles
the bitmap and cycle metadata. Original artwork and the resulting app remain
ignored and must not be included in the public repository. A build without the
flag removes bundled original assets and shows an explicit missing-resource error.
No font selection or capture directory is required for the title.

The picture is the actual disk bitmap at original load addresses4400..63FF. The
SUN DOG lettering is part of that picture, not newly typeset text. The background
starts black; four center bytes appear first, then19 rectangular expansions fill
all7,680 visible HGR bytes. Repeated edge/corner writes are preserved in the
8,041-write sequence. The final frame's RGBA SHA matches the retained original
Apple II Plus reference exactly under the declared HGR decoder profile.

[Boot to title](boot-to-splash.md) documents the ROM/loader chain. The original
routine and write/cycle proof are in [reveal reconstruction](splash-reveal.md).
Ghidra annotations persist in project SunDogNativeStages and are reproducible with
`python3 tools/run_splash_analysis.py`. Actual REA/Ghidra evidence is retained
privately and identified in the public evidence reports.

The original routine takes515,593 modeled NMOS cycles, including its final RTS
but excluding the caller's JSR. The app uses1.023MHz as an explicit nominal clock
and samples the write schedule at approximately8ms intervals. Thus its duration
is about0.504seconds. Exact hardware clock variations, raster scanout, macOS
presentation timing and the preceding floppy loading delays are not emulated.

Verification commands:

```sh
python3 tools/boot_splash_evidence.py
python3 tools/verify_native_splash.py
python3 tools/verify_splash_app.py
```

The real app executable also exposes a headless diagnostic:

```sh
Build/SunDog.app/Contents/MacOS/SunDog --diagnose \
  --at-cycle 250000 --export-startup analysis/local/half-reveal.png
```

Nine bundle-generated intermediate HGR frames are checked byte-for-byte by hash
against the original routine's write fixture; the final RGBA digest is independently
compared with the original execution reference. This checks actual bundle resource
loading, timeline lookup, Swift writes and image production. It does not establish
that a desktop window has been observed in the agent session: LaunchServices
previously returned kLSNoExecutableErr there despite a valid signed executable.
GUI interaction remains unverified; the native view uses direct CoreGraphics image
presentation and has no GPU/shader initialization dependency.

The earlier font/layout/input/selection work remains in the core library and its
separate analysis tools. Its counters and text editor are no longer the startup UI.
Next game work remains scene initialization, input/state transitions, gameplay and
persistence; none is inferred from successful title display.
