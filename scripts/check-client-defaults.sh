#!/usr/bin/env bash
# Client defaults check for the Pack (#46).
#
# Installs the Pack client-side with packwiz-installer, straight from the local pack/
# directory, into a fresh temp dir and asserts the shipped options.txt landed with
# renderDistance:2. The headless smoke test (scripts/smoke-test.sh) only covers the
# server side, so this is the check for client-only defaults.
#
# A client install downloads every client-side mod but still takes only seconds, so the
# Pack PR workflow runs it.
#
# Requirements: bash, java 21, curl, flock (util-linux).
#
# Environment:
#   SMOKE_CACHE_DIR  shared with smoke-test.sh: installer jars (default /tmp/mc-incremental-smoke-cache)
#   SMOKE_KEEP       1 keeps the temp client dir for inspection
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACK_DIR="$REPO_ROOT/pack"
CACHE_DIR="${SMOKE_CACHE_DIR:-/tmp/mc-incremental-smoke-cache}"
PACKWIZ_INSTALLER_VERSION="v0.5.14"
PACKWIZ_BOOTSTRAP_VERSION="v0.0.3"

log() { echo "[client-defaults] $*" >&2; }

for tool in java curl flock; do
  command -v "$tool" > /dev/null || { log "missing required tool: $tool"; exit 2; }
done

CLIENT_DIR="$(mktemp -d /tmp/mc-incremental-client.XXXXXX)"
if [ "${SMOKE_KEEP:-0}" != 1 ]; then
  trap 'rm -rf "$CLIENT_DIR"' EXIT
fi
log "client dir: $CLIENT_DIR"

fetch() { # url dest
  [ -s "$2" ] && return 0
  log "downloading $1"
  curl -fsSL --retry 3 -o "$2.part" "$1"
  mv "$2.part" "$2"
}
mkdir -p "$CACHE_DIR"
exec 9>"$CACHE_DIR/.lock"
flock 9
fetch "https://github.com/packwiz/packwiz-installer/releases/download/$PACKWIZ_INSTALLER_VERSION/packwiz-installer.jar" \
  "$CACHE_DIR/packwiz-installer-$PACKWIZ_INSTALLER_VERSION.jar"
fetch "https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/$PACKWIZ_BOOTSTRAP_VERSION/packwiz-installer-bootstrap.jar" \
  "$CACHE_DIR/packwiz-installer-bootstrap-$PACKWIZ_BOOTSTRAP_VERSION.jar"
flock -u 9

log "installing the Pack (client side) from $PACK_DIR"
(cd "$CLIENT_DIR" && java -jar "$CACHE_DIR/packwiz-installer-bootstrap-$PACKWIZ_BOOTSTRAP_VERSION.jar" \
  -g --bootstrap-no-update --bootstrap-main-jar "$CACHE_DIR/packwiz-installer-$PACKWIZ_INSTALLER_VERSION.jar" \
  -s client "file://$PACK_DIR/pack.toml" > packwiz-installer.log 2>&1) \
  || { tail -n 30 "$CLIENT_DIR/packwiz-installer.log" >&2; log "FAIL: packwiz-installer failed"; exit 1; }

[ -f "$CLIENT_DIR/options.txt" ] || { log "FAIL: the Pack did not install options.txt"; exit 1; }
if ! grep -qx 'renderDistance:2' "$CLIENT_DIR/options.txt"; then
  cat "$CLIENT_DIR/options.txt" >&2
  log "FAIL: options.txt does not set renderDistance:2"
  exit 1
fi
log "PASS: options.txt sets renderDistance:2"
