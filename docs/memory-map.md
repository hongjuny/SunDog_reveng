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
