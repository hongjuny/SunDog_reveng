# Segment 21 shared-reference and selection contract

The Play segment21 P1 call at startup segment1 P4 offset `$0108` passes eight
addresses in this push order: caller locals8,7,6,5,4,3,2,9. P1's attribute word at
trailer−6 is16 bytes. The original native call copier `$E1F8..$E215` pops parameter
bytes into frame+12 upward. Three controlled native copier cases establish:

| Segment21 P1 reference slot | Startup P4 local | Proven selected uses |
|---|---|---|
| 1 | 9 | Cleared by P30, set to1 by P1; bit0 participates in loop termination |
| 2 | 2 | Map-byte selection; P40 normalizes it modulo16 and has a later override255 |
| 3 | 3 | Receives signed quotient `(P1.local25−3)/8` in P12 and related paths |
| 4 | 4 | Receives signed quotient `(P1.local26+3)/7` in P12 and related paths |
| 5 | 5 | Vertical origin contribution in the selected byte-map lookup |
| 6 | 6 | Horizontal origin contribution in the selected byte-map lookup |
| 7 | 7 | Dereferenced in P3, assigned from packed table29.word37 fields in P26; initialized4 in P28 |
| 8 | 8 | Dereferenced in P3, assigned from packed table29.word37 fields in P26; initialized4 in P28 |

These are shared by-reference workspace words, not evidence of a contiguous event
record. The report identifies77 root-reference load sites. It respects lexical
levels: in lexical-level3 P20, depth1 addresses P19's frame; depth2 addresses P1.
The same distinction excludes local P34/P39 frame values from root references.
Pointer-use records that are not immediate dereferences remain unclassified effects.
They are not assumed to be writes merely because an address was loaded.

## Map selection and the native rewrite

P21 `$0AEA..$0B17` calculates column and row and reads one byte through P1.local55.
P40 `$1B9C..$1BCD` repeats that selection then reduces the byte modulo16:

```
column = magnitude_remainder16(add16(*ref6,
           divide_signed16(add16(P1.local26,3),28)),40)
row    = magnitude_remainder16(add16(*ref5,
           divide_signed16(subtract16(P1.local25,3),P1.local21)),24)
selected = byte(P1.local55 + 40*row + column)
*ref2 = selected                         // P21
*ref2 = selected % 16                    // P40, before its later conditions
```

`add16` and `subtract16` wrap as signed16. Division truncates toward zero, including
signed16 quotient overflow. Apple II opcode8E takes the nonnegative remainder
of operand magnitudes. It is not Swift/Python signed modulo. A4's operand20 scales
by20 **words**, so its row step is40 bytes; the addressable map is40×24 bytes.
A zero P1.local21 divisor enters native error106 before completing the read.

`native/SunDogLogic/TileSelection.swift` implements this lookup directly in Swift.
Its API accepts the explicit960-byte map, signed16 origin/cursor words and signed16
nonzero vertical divisor. Result exposes column,row,raw byte and its low nibble.
The function deliberately does not create missing game maps or infer what their
values mean. No p-code execution backend is linked into the app.

The verifier uses the existing bounded native-handler probe only for analysis:
original P21 and P40 instruction fragments run against synthetic frames and a
synthetic960-byte map. It compares the coordinates, selected value, P40 nibble,
stack restoration and unchanged map before invoking a compiled Swift comparator.
Negative inputs, signed16 wrap edges, divisor sign and zero are retained explicitly.
Every visited native instruction must occur in the persisted Ghidra listing.

## How this affects scene dispatch

Startup P4 subsequently uses caller local2: state5 chooses segment17 for255 and
segment18 otherwise; state6 uses **signed** comparison `local2 <= 3` for segment19,
otherwise segment20. Thus segment21 supplies a concrete data-selection result
consumed by scene dispatch. P40's255 override follows additional conditions and
cannot be substituted for every selected map byte.

P1 terminates its loop if state nibble(bits8..11 of table29.word45) differs from
saved nibble(bits4..7), table29.word347 bit0 is set, or reference1 bit0 is set.
This documents static control flow, not observed physical input timing or every
state's gameplay name.

## Evidence and reproduction

Run `python3 tools/event_contract.py` and `python3 tools/verify_native_selection.py`.
`analysis/event-contract.json` records original side, source hashes, sector/offset
provenance, parameter mapping, selected effect spans and uncertainties.
`analysis/native-selection-verification.json` records native/Swift comparison
counts and source identities. Private fixtures stay under
`analysis/local/native-selection/`; complete original listings remain private.
The native argument probe consumes the SHA-verified interpreter-ready image and
checks Ghidra instruction boundaries; it does not claim a new REA session.

Confidence is high for these source-specific pointer/arithmetic contracts. Map
initialization and original graphics resources, ownership/lifetime of all eight
references, cursor construction, input timing, full P40 side effects and complete
scene transitions remain open. A faithful scene implementation still requires
those contracts; a synthetic map is not an original game scene.
