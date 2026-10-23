# Memory map — static boot states

Source: Utility disk, boot staging manifests and Ghidra exports; confidence high
for explicit loads/writes, conditional on successful disk reads and standard
Language Card hardware. This is not a full p-system memory map.

| Address | Boot role | Evidence |
|---|---|---|
| `$00`, `$02`, `$0F` | disk loader sector position, page count, starting block low byte | `$08FF–$093D` |
| `$26–$27`, `$2B`, `$3D` | ROM disk buffer, slot, sector state | standard slot-ROM algorithm |
| `$3E–$3F` | native disk destination pointer | `$0910–$091D`, `$098C` |
| `$F0–$F1` | target track and physical sector | `$090E`, `$0930` |
| `$0200–$02FF`, `$0300–$0355` | disk decode scratch buffers | `$097A–$0991` and field reader |
| `$0478` | current/observed track state used by seek path | `$0850`, `$0953–$0966` |
| `$0800` | mutable boot sector count: 1 → 3 → 5 | `$0808–$0816` |
| `$0801–$08CE` | bootstrap code plus message/data | T0 DOS slot 0 |
| `$08FF–$0AFF` | native disk loader and tables | boot staging manifest |
| `$2000–$3FFF` | HGR page 1, conditionally cleared | `$082E–$0840` |
| `$4000–$63FF` | first loaded native code/data region | block 201, 36 pages |
| `$D000–$DFFF` bank 2 | first part of 48-page runtime load | block 219 onward |
| `$D000–$DFFF` bank 1 | later 16-page load, replacing visible low-bank code after switch | block 243 onward |
| `$E000–$FFFF` | common Language Card RAM, from 48-page load | includes `$FFF8 → $FEF2` |

I/O reads at `$C057/$C054/$C052/$C050` select high-resolution page 1, full-screen
graphics. `$C051` selects text on the error path. Language Card accesses are
stateful; do not treat all `$C08x` values as equivalent. See boot process for the
order of accesses. The later runtime can reuse zero-page and ordinary RAM;
none of these boot assignments is assumed permanent.

The later `$F269` copy relocates common-bank `$F290–$F78F` to `$6800–$6CFF`.
The initializer at `$6800` clears `$0000–$1FFF` on its initial path, invalidating
the boot snapshot, then switches to bank 2 before an indirect jump to `$DAA9`.

## Milestone 2: interpreter-ready state

| Address | Role after native initialization | Evidence |
|---|---|---|
| `$58/$59` | p-code instruction pointer, initially `$F248` | `$E229–$E237`, `$D293–$D29F` |
| `$5C/$5D` | downward allocation pointer used by segment loader | `$E49B–$E4A6` |
| `$6000–$61FF` | temporary directory/dictionary buffer | initial native disk-read arguments |
| `$BE3E` onward | sixteen six-byte segment records | `$6B32–$6B7A` |
| `$BC72–$BD1B` | 170-byte helper from dictionary slot 15 | initial top `$BD1C` minus 170 |
| bank 1 `$D000–$D0FF` | primary native handler addresses | self-modified indirect JMP at `$D29D` |
| `$D100` onward, bank 1 | secondary handler cells | `$E67F–$E689` |
| common `$F248–$FE7B` | initial SYSTEM.PASCAL segment 0 | explicit top `$FE7C` minus 3124 |
| `$FF00–$FF3C` | validated BIOS wrapper entries | `$FF9E` switches to bank 2 and later restores bank 1 |
| `$BF1A/$BF1B` | saved native caller return address during BIOS wrapper | `$FFAB–$FFC4` |

The final initialization loop clears `$6000–$6C30`, including most of its own
relocated code. The final loop/jump at `$6C31–$6C45` survives long enough to enter
`$D293`. Do not retain the old `$F269/$F290` native definitions after the segment 0
load, or the `$6800` definitions after that final clear. The interpreter-ready
Ghidra view marks the segment 0 range as p-code data rather than 6502 instructions.

## Milestone 3: direct Ghidra view verification

`analysis/memory-view-validation.json` verifies low-bank composition, shared upper
RAM, the 3124-byte segment 0 overlay and the unchanged bytes outside that overlay.
There are 2818 differing byte values between the two snapshots; this is a byte
comparison count, not a claim that only 2818 bytes were copied or written.

In the interpreter-ready Ghidra Program, `$D000–$D0FF` is `word[128]`,
`$D100–$D151` is `word[41]`, and `$F248–$FE7B` is `byte[3124]`. None contains native
instructions in the listing. The initialized RAM block hash matches the bounded
source snapshot. Ghidra also creates ZERO_PAGE and STACK blocks, but both are
**uninitialized**; they must not be treated as observed zero-filled memory.

The synthetic handler probes intentionally supply RAM/stack values for isolated
checks. Their initialized test memory is not an observed machine state or a
replacement for the uninitialized Ghidra blocks.

## Actual REA comparison

Six bounded REA/Ghidra imports passed complete byte comparisons on 2026-10-23.
The bank-specific D152 instructions, common-memory overlay, native copy loop and
relocated initializer agree with the static snapshots. See
[REA memory views](rea-memory-views.md) and `analysis/rea-memory-crosscheck.json`
for scope, Evidence IDs and reproduction. Full array typing remains in the
persistent Ghidra Program; REA does not mirror those annotations or emulate banks.

## Primary opcode completion: additional typed runtime data

Native packed-field handlers and all seventeen source values identify DDD6–DDF7
as word[17] masks, with cell n equal to 2^n−1. The native call resolver pushes the
data word E189–E18A (E17D), so RTS reaches the newly seeded E17E trampoline. E18B
is its patched segment marker. These data ranges are persisted as word/byte data,
with zero native instructions verified on readback. Source hashes and Utility
track/sector/offset provenance are in `analysis/opcode-coverage.json`.

The common frame layout, synthetic call/return checks and remaining service
boundaries are documented in [primary completion](primary-opcode-completion.md).
