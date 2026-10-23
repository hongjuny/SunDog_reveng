# Native macOS startup screen

Version0.5.1 fixes the missing SUN DOG lettering. Startup has two separate stages:

1. Native4000..41FF reveals the disk's spaceship/planet background from its center.
2. SYSTEM.LIBRARY segment26 P13/P14/P16 adds the striped border and six animated
   letters, using a separate6,144-byte original sprite resource and native P9–P12.

The earlier claim that the logo was embedded in the first bitmap was incorrect.
The final background-only RGBA digest80d586... is different from the later complete
title digest923de39473c6046f65036f70682777fa824574e9e38e61f04b4d6f865df9d400.
Both phases are now separately checked. The app contains rewritten Swift logic;
no Apple II CPU or p-code interpreter is part of the product.

```sh
python3 tools/build_native.py --tests --include-local-assets
open -n Build/SunDog.app
```

The local-assets flag reconstructs original data from verified Utility sectors
and bundles it for local use. The background is loader blocks203..219; the logo
is blocks67..79, with six letter records, eight prerasterized frames per letter,
and128 bytes per frame. Original art and the resulting app stay ignored by Git.
A resource failure is explicit; a missing logo is not silently accepted as a
complete title. Build without local assets does not include copyrighted artwork.

The background rewrite matches8,041 ordered original HGR writes. Its recovered
515,593-cycle schedule is sampled using a declared nominal1.023MHz host clock.
The logo rewrite matches155 visual steps,14,256 ordered HGR writes and every
intermediate page of the source-bound original P16 controller/native primitives.
The app currently presents logo steps16ms apart. This host pacing is an explicit
choice: original sound-generator delays and complete p-code execution timing are
not reproduced. Sound and later menus/gameplay are not implemented.

Evidence: [background boot path](boot-to-splash.md),
[background reveal](splash-reveal.md), [logo resource](title-logo-asset.md), and
[logo code](title-logo.md). The code/data distinction and prior mistaken claim
are retained in the research log. Native logo P11 also has a new actual
REA/Ghidra record; full evidence and original bytes remain local.

Verification:

```sh
python3 tools/verify_native_splash.py
python3 tools/verify_native_title.py
python3 tools/verify_splash_app.py
```

The real bundle's default diagnostic now checks the complete title:

```sh
Build/SunDog.app/Contents/MacOS/SunDog --diagnose \
  --export-startup analysis/local/title.png
```

Use `--background-only --at-cycle 250000` for the first-stage cycle diagnostic.
Nine intermediate background states remain independently compared with original
native writes. The complete-title diagnostic must match the later original HGR
and RGBA digests, not just the earlier background reference. The build fails if
logo composition is absent or incomplete.

The user observed the background animation on desktop, confirming that stage's
window presentation. The corrected logo window still requires desktop observation;
headless bundle composition is not represented as GUI proof. The native view uses
CoreGraphics image presentation. Physical raster timing and NTSC monitor fidelity
remain outside the declared decoder/profile verification.
