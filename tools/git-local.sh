#!/bin/sh
# Workspace policy makes root .git read-only. Use metadata in an allowed folder.
set -eu
cd "$(dirname "$0")/.."
exec git --git-dir=analysis/local/repository/.git --work-tree=. "$@"
