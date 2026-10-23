# REA–Ghidra integration checkpoint

## Current state

**Not yet passed.** Installed components and a bounded Ghidra reference target are
verified. The running REA MCP server still lacks GHIDRA_INSTALL_DIR. A scoped CLI
attempt fixed the Swift cache problem, but its owned Java probe is blocked in this
shell environment with `spawn EPERM`; direct `ps` also returns operation not
permitted. REA uses a process baseline before launching owned providers. No
ownership/cleanup checks or host restrictions were disabled.

The complete installation is `/Users/ay5/Applications/ghidra_12.1.4_PUBLIC`.
Its valid ARM64 decompiler is under
`Ghidra/Features/Decompiler/build/os/mac_arm_64/decompile` (3,360,632 bytes).
The 14-byte `404: Not Found` file under `/Applications` is not that installation's
working binary. The earlier conclusion that no ARM decompiler was installed was
incorrect. A redundant local source build completed while diagnosing this; it is
ignored under `analysis/local/ghidra-native/` and did not replace installed files.

`analysis/rea-installation-check.json` records executable identity and file checks;
this is not a successful REA analysis result. `tools/rea-env.sh --check-files`
reproduces the file check. Java 21 works when invoked directly.

## Concrete connection change

The current global `[mcp_servers.rea]` launches
`npx -y rea-agents@6.7.0 mcp`, with no REA environment table.
`analysis/rea-launch-proposed.toml` is an **unapplied fragment**, containing only
`[mcp_servers.rea.env]` values. Merge those variables into the existing server's
environment, preserving its command, arguments, other variables and tool policy.
The global `/Users/ay5/.codex/config.toml` is outside this session's writable roots;
project `.codex` configuration is also read-only. Neither was modified.

The fragment supplies the existing Ghidra root, Java 21, an explicit Swift module
cache, and the existing Xcode Swift compiler/SDK paths. The operative REA setting
is **REA_DARWIN_MODULE_CACHE_PATH**: generic Swift/Clang cache variables alone did
not fix the helper compilation because REA selects its module cache internally.

Restart/reconnect the REA MCP server after applying the environment. The selected
configuration syntax and server settings were checked against
[official OpenAI documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
The project launcher is an alternative way to start REA with the same environment:

```sh
sh tools/rea-env.sh --mcp
```

That is a stdio MCP server command, not an analysis to run and leave attached to an
interactive terminal. CLI diagnostics can instead use `sh tools/rea-env.sh doctor --json`.
The latter still needs normal process inspection access; repeating it inside the
same restricted shell will not fix EPERM.

## Reconnection acceptance test

`python3 tools/rea_setup.py` exports a **37-byte native fetch-loop slice** from the
interpreter-ready snapshot, at its actual load/entry address `$D27B`. It verifies
those bytes against Utility T30, DOS sector 7, byte 123 (image offset 124795).
`analysis/rea-probe-input.json` records the hash and provenance. The slice contains
`$D293: LDY #0`, its surrounding conditional branches and its JMP through `$D000`.
The indirect table is outside this bounded input; its runtime targets are unknown
in this probe. It must not be presented as a complete whole-program reference map.

Use these MCP operations after reconnection:

1. `binary_session`: verify a configured Ghidra provider and its Java/native checks.
2. `open_binary`: absolute path to `analysis/regions/rea-fetch.bin`,
   `format=raw-binary`, `architecture=6502`, `entry_point=0xd27b`,
   `provider_id=ghidra`.
3. `inspect_native_load_image`: retain source mapping and hash verification.
4. `inspect_native_instruction` at `0xd293`: require decoded LDY, bytes A000, length 2.
5. `procedure_assembly` at `0xd27b` and `xrefs` at `0xd293`: compare the bounded
   references to `ghidra/exports/rea-fetch-reference.txt`.
6. Export actual REA Evidence and close the session. Persist annotations in the
   existing Ghidra project/scripts; REA's working database is ephemeral.

Do not open `interpreter-ready.bin` with an execution seed of `$D000`: that address
is a dispatch **data table**. REA's raw-binary profile ties file offset zero to its
entry/base, which is why the separate native slice is used for this smoke test.

A saved REA instruction Evidence record can be checked with:

```sh
python3 tools/verify_rea_probe.py analysis/local/rea/instruction-evidence.json
```

The validator requires a Ghidra provider, an Evidence ID, and the decoded byte and
instruction facts. It does not accept a doctor result or direct Ghidra export as
REA analysis. No successful `analysis/rea-crosscheck.json` exists yet.
