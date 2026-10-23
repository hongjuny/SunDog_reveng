# Native input state

`native/SunDogLogic/ButtonInput.swift` translates the established state transitions
of SYSTEM.LIBRARY segment 22 native procedure 2 into Swift. It accepts four raw
channel bytes from its caller. Host mouse/button mappings and event timing are
separate product choices; this module assigns no physical meaning to a channel.

`ButtonInput()` initializes four zero pending bytes and four false edge-history
values. A throwing state initializer is available for restoration and comparison.
`latch(first:second:)` ORs raw bytes into channels 0 and 1 only, matching the
original ADD16 hook. `poll(selector:sample:)` supports selectors 0...8:

| Selector | Result and state effect |
|---|---|
| 0...3 | Channel `selector & 3`; bit 7 of sample OR pending becomes down; return rising edge and update history |
| 4...7 | Same channels; return level and leave edge history unchanged |
| 8 | Return false with `restoreDispatch=true`; leave pending/history intact |

A down result clears the selected pending byte. Without down, even nonzero low
pending bits remain. The native host interprets selector 8 as a lifecycle signal;
the Swift code does not patch an interpreter or execute original instructions.
Selectors greater than 8 and incorrectly sized state arrays throw errors.

Reproduce with `python3 tools/verify_native_input.py`. The verifier runs 512
synthetic filter cases and 256 hook-body cases through the original bounded 6502
probe, checks that visited instructions are covered by retained REA/Ghidra
evidence, then directly compiles Swift and compares its results and channel state
against those outputs. The Swift verifier also checks restore signaling and
rejection of all 247 unsupported selectors. Detailed cases stay under ignored
`analysis/local/native-input/`; public hashes/counts are in
`analysis/native-input-verification.json`.

Source side, track/sector and procedure address, source/capture hashes and actual
REA evidence IDs remain in `analysis/button-input-evidence.json` and
[input-system.md](input-system.md). Verification uses synthetic RAM for hardware
samples, not live MMIO. The initial hook installation gate, keyboard path,
segment 21 event structure and sampling schedule remain unresolved.
