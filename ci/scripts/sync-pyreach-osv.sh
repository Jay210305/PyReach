#!/bin/sh
set -eu
: "${PYREACH_OSV_SOURCE:?Set an approved local JSONL directory}"
: "${PYREACH_DB_PATH:=/opt/pyreach/osv.db}"
exec pyreach sync-osv --source "$PYREACH_OSV_SOURCE" --db-path "$PYREACH_DB_PATH" --incremental
