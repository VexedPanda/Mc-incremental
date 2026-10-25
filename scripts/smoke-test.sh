#!/usr/bin/env bash
# Server smoke test for the Pack.
#
# Installs NeoForge (version from pack/pack.toml) as a headless server, installs
# the Pack server-side with packwiz-installer straight from the local pack/
# directory, boots it, and waits for the KubeJS smoke-test script
# (pack/kubejs/server_scripts/smoke_test.js) to log its result and stop the server.
#
# Contract with smoke_test.js:
#   - this script writes `smoke-test.json` in the server directory; the KubeJS
#     script only runs its assertions when that file exists (players never have it)
#   - the KubeJS script logs exactly one of these lines, then stops the server:
#       SMOKE-TEST RESULT: PASS
#       SMOKE-TEST RESULT: FAIL
#
# Exits 0 on PASS; non-zero on FAIL, a missing marker, a crash, or a timeout.
#
# Environment:
#   SMOKE_CACHE_DIR  downloads + installed NeoForge server (default /tmp/mc-incremental-smoke-cache)
#   SMOKE_WORK_DIR   server directory for this run; kept afterwards when set
#                    (default: a fresh mktemp dir, deleted afterwards unless SMOKE_KEEP=1)
#   SMOKE_TIMEOUT    seconds to wait for the server to finish (default 600)
#   SMOKE_MEMORY     server max heap (default 3G)
#   SMOKE_PORT       server port (default: random 30000-39999, to avoid clashing with other servers)
#   SMOKE_KEEP       1 keeps a mktemp work dir for inspection
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACK_DIR="$REPO_ROOT/pack"
CACHE_DIR="${SMOKE_CACHE_DIR:-/tmp/mc-incremental-smoke-cache}"
TIMEOUT="${SMOKE_TIMEOUT:-600}"
MEMORY="${SMOKE_MEMORY:-3G}"
# Ask the kernel for a free port so parallel runs (other worktrees/agents) never collide.
PORT="${SMOKE_PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')}"

PACKWIZ_INSTALLER_VERSION="v0.5.14"
PACKWIZ_BOOTSTRAP_VERSION="v0.0.3"
PASS_MARKER="SMOKE-TEST RESULT: PASS"
FAIL_MARKER="SMOKE-TEST RESULT: FAIL"

log() { echo "[smoke-test] $*" >&2; }

NEOFORGE_VERSION="$(sed -n 's/^neoforge *= *"\(.*\)"/\1/p' "$PACK_DIR/pack.toml")"
[ -n "$NEOFORGE_VERSION" ] || { log "could not read neoforge version from pack/pack.toml"; exit 2; }

if [ -n "${SMOKE_WORK_DIR:-}" ]; then
  WORK_DIR="$SMOKE_WORK_DIR"
  rm -rf "$WORK_DIR"
  mkdir -p "$WORK_DIR"
else
  WORK_DIR="$(mktemp -d /tmp/mc-incremental-smoke.XXXXXX)"
  if [ "${SMOKE_KEEP:-0}" != 1 ]; then
    trap 'rm -rf "$WORK_DIR"' EXIT
  fi
fi
WORK_DIR="$(cd "$WORK_DIR" && pwd)"
log "work dir: $WORK_DIR"

fetch() { # url dest
  [ -s "$2" ] && return 0
  log "downloading $1"
  curl -fsSL --retry 3 -o "$2.part" "$1"
  mv "$2.part" "$2"
}

mkdir -p "$CACHE_DIR"
# Serialise cache downloads and the one-time server install across parallel runs.
exec 9>"$CACHE_DIR/.lock"
flock 9
fetch "https://maven.neoforged.net/releases/net/neoforged/neoforge/$NEOFORGE_VERSION/neoforge-$NEOFORGE_VERSION-installer.jar" \
  "$CACHE_DIR/neoforge-$NEOFORGE_VERSION-installer.jar"
fetch "https://github.com/packwiz/packwiz-installer/releases/download/$PACKWIZ_INSTALLER_VERSION/packwiz-installer.jar" \
  "$CACHE_DIR/packwiz-installer-$PACKWIZ_INSTALLER_VERSION.jar"
fetch "https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/$PACKWIZ_BOOTSTRAP_VERSION/packwiz-installer-bootstrap.jar" \
  "$CACHE_DIR/packwiz-installer-bootstrap-$PACKWIZ_BOOTSTRAP_VERSION.jar"

# Install the NeoForge server once into the cache, then copy it per run.
SERVER_BASE="$CACHE_DIR/neoforge-$NEOFORGE_VERSION-server"
if [ ! -f "$SERVER_BASE/.installed" ]; then
  log "installing NeoForge $NEOFORGE_VERSION server"
  rm -rf "$SERVER_BASE"
  mkdir -p "$SERVER_BASE"
  (cd "$SERVER_BASE" && java -jar "$CACHE_DIR/neoforge-$NEOFORGE_VERSION-installer.jar" --installServer . > installer.log 2>&1) \
    || { log "NeoForge installer failed, see $SERVER_BASE/installer.log"; exit 2; }
  touch "$SERVER_BASE/.installed"
fi
cp -a "$SERVER_BASE/libraries" "$WORK_DIR/"
flock -u 9

log "installing the Pack (server side) from $PACK_DIR"
(cd "$WORK_DIR" && java -jar "$CACHE_DIR/packwiz-installer-bootstrap-$PACKWIZ_BOOTSTRAP_VERSION.jar" \
  -g --bootstrap-no-update --bootstrap-main-jar "$CACHE_DIR/packwiz-installer-$PACKWIZ_INSTALLER_VERSION.jar" \
  -s server "file://$PACK_DIR/pack.toml" > packwiz-installer.log 2>&1) \
  || { tail -n 30 "$WORK_DIR/packwiz-installer.log" >&2; log "FAIL: packwiz-installer failed"; exit 1; }

echo "eula=true" > "$WORK_DIR/eula.txt"
# Start from the Pack's shipped server.properties defaults (view/simulation distance, ...)
# and only override the keys this test needs.
[ -f "$WORK_DIR/server.properties" ] \
  || { log "FAIL: the Pack did not install server.properties defaults"; exit 1; }
set_prop() { # key value: replace the key in place, or append it
  if grep -q "^$1=" "$WORK_DIR/server.properties"; then
    sed -i "s|^$1=.*|$1=$2|" "$WORK_DIR/server.properties"
  else
    echo "$1=$2" >> "$WORK_DIR/server.properties"
  fi
}
set_prop online-mode false
set_prop level-seed mc-incremental-smoke
set_prop spawn-protection 0
set_prop server-port "$PORT"
set_prop enable-rcon false
set_prop enable-query false
echo '{"enabled": true}' > "$WORK_DIR/smoke-test.json"

log "booting server on port $PORT (timeout ${TIMEOUT}s)"
start=$(date +%s)
set +e
# java directly (not run.sh) so the timeout signals the JVM itself, not a wrapper shell.
# The -D marker tags this JVM with its own work dir: to find or stop *your* server, match on it
# (pgrep -f "mcincremental.smoke.workdir=$WORK_DIR"); never kill other java processes.
(cd "$WORK_DIR" && timeout --kill-after=30 "$TIMEOUT" \
  java "-Xmx$MEMORY" "-Dmcincremental.smoke.workdir=$WORK_DIR" @libraries/net/neoforged/neoforge/"$NEOFORGE_VERSION"/unix_args.txt nogui \
  < /dev/null > console.log 2>&1)
status=$?
set -e
log "server exited with status $status after $(( $(date +%s) - start ))s"

fail() {
  tail -n 40 "$WORK_DIR/console.log" >&2 || true
  log "FAIL: $*"
  exit 1
}

grep -F 'SMOKE-TEST' "$WORK_DIR/console.log" >&2 || true

if [ "$status" = 124 ] || [ "$status" = 137 ]; then
  fail "timed out after ${TIMEOUT}s"
fi
if [ -n "$(ls -A "$WORK_DIR/crash-reports" 2>/dev/null)" ]; then
  fail "server crashed (see crash-reports/ in $WORK_DIR)"
fi
if grep -qF "$FAIL_MARKER" "$WORK_DIR/console.log"; then
  fail "assertions failed"
fi
if [ "$status" != 0 ]; then
  fail "server exited with status $status"
fi
if ! grep -qF "$PASS_MARKER" "$WORK_DIR/console.log"; then
  fail "no '$PASS_MARKER' marker in the server log"
fi
log "PASS"
