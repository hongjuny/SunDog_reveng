# Reconstructed native game logic

This target contains functions rewritten from established original game semantics.
The first is segment 20/procedure 18's integer scaling helper. Its selected input
contract and rounding order are documented in `../docs/trade-arithmetic.md`.

It now also includes the verified native glyph compositor and button filter.
See `../docs/native-app.md` for the first macOS rendering/input integration and
the explicit remaining game implementation scope.

Reproduce its native comparison from the repository root:

```sh
python3 tools/trade_scaling_evidence.py
python3 tools/verify_native_rules.py
```

The verifier directly compiles the Swift sources with the installed SDK and checks
733 synthetic inputs already compared with the original native-handler paths.
`Package.swift` exposes the same source as a library for subsequent game modules;
SwiftPM itself is not verified in the restricted agent environment.
