#!/bin/sh
# Weekly OSV database sync for PyReach runners (S4-T6).
#
# Install as a cron job on the runner host (runs as the `pyreach` user):
#   0 3 * * 0 pyreach /opt/pyreach/bin/sync-pyreach-osv.sh
#
# Ownership: DB file `pyreach:pyreach` (rw for owner, r for the CI group).
# Log rotation: configure logrotate for /var/log/pyreach-sync.log
# (see ci/README.md). POSIX sh only; no bashisms.
#
# Set PYREACH_OSV_SOURCE to an OSV archive mirrored onto the runner host.

set -eu

PYREACH_DB="${PYREACH_DB_PATH:-/opt/pyreach/osv.db}"
PYREACH_LOG="${PYREACH_SYNC_LOG:-/var/log/pyreach-sync.log}"
PYREACH_OSV_SOURCE="${PYREACH_OSV_SOURCE:-}"

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$1" >> "$PYREACH_LOG"
}

log "Starting OSV sync (db=$PYREACH_DB)..."
if [ -z "$PYREACH_OSV_SOURCE" ]; then
    log "OSV sync FAILED: set PYREACH_OSV_SOURCE to a local mirrored dump."
    exit 2
fi
if pyreach sync-osv --db-path "$PYREACH_DB" --source "$PYREACH_OSV_SOURCE" --incremental >> "$PYREACH_LOG" 2>&1; then
    log "OSV sync completed successfully."
else
    code="$?"
    log "OSV sync FAILED with code $code."
    exit "$code"
fi
