#!/bin/sh
# Project-scoped environment for the existing REA installation. No config edits.
set -eu
cd "$(dirname "$0")/.."
REA_BIN=${REA_BIN:-/Users/ay5/.npm/_npx/a1722018f28f9df2/node_modules/.bin/rea}
GHIDRA_INSTALL_DIR=${GHIDRA_INSTALL_DIR:-/Users/ay5/Applications/ghidra_12.1.4_PUBLIC}
JAVA_HOME=${JAVA_HOME:-/Library/Java/JavaVirtualMachines/ibm-semeru-open-21.jdk/Contents/Home}
rea_local="$PWD/analysis/local/rea"
mkdir -p "$rea_local/home" "$rea_local/tmp" "$rea_local/module-cache"
REA_DARWIN_MODULE_CACHE_PATH="$rea_local/module-cache"
REA_DARWIN_SWIFTC_PATH=${REA_DARWIN_SWIFTC_PATH:-/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc}
SDKROOT=${SDKROOT:-/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk}
JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Duser.home=$rea_local/home -Djava.io.tmpdir=$rea_local/tmp"
TMPDIR="$rea_local/tmp/"
export GHIDRA_INSTALL_DIR JAVA_HOME REA_DARWIN_MODULE_CACHE_PATH REA_DARWIN_SWIFTC_PATH SDKROOT JAVA_TOOL_OPTIONS TMPDIR
if [ "${1:-}" = --check-files ]; then
    exec python3 tools/rea_setup.py --check-files
fi
if [ "$#" -eq 0 ]; then set -- --mcp; fi
exec "$REA_BIN" "$@"
