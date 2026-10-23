# Pascal runtime — evidence and limits

The project context and original developer establish UCSD Pascal use; the native
boot trace does not yet identify the exact Apple II p-system release or opcode
set. The Atari ST implementation is a comparative reference only.

## Disk evidence

`analysis/pascal-candidates.json` records four directory-shaped groups on Utility:

| DOS image offset | Track / sector / byte | Entries after volume | Extent coverage |
|---|---|---:|---|
| `$9100` | 9 / 1 / 0 | 6 | contiguous blocks 3–279 |
| `$A000` | 10 / 0 / 0 | 6 | contiguous blocks 3–279 |
| `$AB00` | 10 / 11 / 0 | 7 | contiguous blocks 3–279 |
| `$AD00` | 10 / 13 / 0 | 6 | contiguous blocks 3–279 |

Each begins with a `SUNDOG` volume-shaped record followed by 26-byte entries with
plausible block extents. Names include `SYSTEM.DATA`, `SUNDOG.LIBRARY`,
`SYSTEM.LIBRARY`, `SYSTEM.STARTUP`, `SYSTEM.APPLE`, and `SYSTEM.PASCAL`.
Some groups assign different names/kinds to the same extents; one includes demo
entries. Confidence is medium for the directory interpretation, low for active
filesystem attribution. They could be templates, historical directory copies,
or application data; they are not at a proven active directory location.
The weak single-entry heuristic also finds `MAINB.LIB.TEXT`, `GRND.LIB.TEXT`,
`SHIP.LIB.TEXT`, and `DUMMY.CODE` in the shared area around `$E560`.
These strings do not demonstrate live subsystems or source-code availability.

The bootstrap's 219–251 block load coincides with `SYSTEM.APPLE` in several
candidate groups. This supports a native-system interpretation but does not prove
that the bootloader consults any directory; it uses explicit block numbers.
The final 251–280 `SYSTEM.PASCAL` extent has not yet been parsed or loaded in the
boot trace. All block identities remain conditional on the demonstrated loader
mapping rather than on filenames alone.

## Unresolved

No interpreter dispatch table, bytecode set, segment descriptor format, relocation
format, stack layout or Pascal/native calling convention has been established.
No p-code disassembler is implemented. Shared Tracks 13–17 are candidates for
common resources, with no confirmed interpreter or graphics identity.
Runtime initialization continues through a bank switch and a native relocation;
see boot documentation. The next useful evidence is the relocated initializer's
memory writes and the subsequent loads, followed by the actual opcode-fetch loop.
