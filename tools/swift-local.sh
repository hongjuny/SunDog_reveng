#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p analysis/local/swift-module-cache analysis/local/swift-cache analysis/local/swift-config analysis/local/swift-security
CLANG_MODULE_CACHE_PATH="$PWD/analysis/local/swift-module-cache"
SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
export CLANG_MODULE_CACHE_PATH SWIFTPM_MODULECACHE_OVERRIDE
action=${1:-build}
if [ "$#" -gt 0 ]; then shift; fi
exec swift "$action" --scratch-path analysis/local/swift-build --cache-path analysis/local/swift-cache --config-path analysis/local/swift-config --security-path analysis/local/swift-security "$@"
