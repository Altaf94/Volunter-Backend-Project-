#!/usr/bin/env bash
# Migrate the full main app database (schema + all rows + sequence values) to Heroku Postgres.
# Use this when manual or partial tools left some tables empty.
#
# Prereqs: PostgreSQL client tools (pg_dump, pg_restore) on PATH — e.g. brew install libpq
#
# 1) From Heroku, copy the addon URL (must allow SSL); append sslmode if missing:
#    heroku config:get DATABASE_URL -a YOUR_APP
#
# 2) Set URLs (use your local DB name, often northenvolunteerdb from .env):
#    export SOURCE_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/northenvolunteerdb"
#    export TARGET_DATABASE_URL="postgres://...amazonaws.com:5432/xxxx?sslmode=require"
#
# 3) Strongly recommended before re-running after a failed partial import (DESTRUCTIVE):
#    heroku pg:reset DATABASE --confirm YOUR_APP
#
#    Or, without reset, attempt drop-before-create during restore (can still be noisy):
#    export PGPRESTORE_FLAGS="--clean --if-exists"
#
# 4) Run (from repo root):
#    chmod +x scripts/migrate_local_to_heroku.sh
#    ./scripts/migrate_local_to_heroku.sh
#
# One-line alternative (Heroku CLI; replaces the remote with your local database name):
#    heroku pg:reset DATABASE --confirm YOUR_APP
#    heroku pg:push northenvolunteerdb DATABASE_URL -a YOUR_APP

set -euo pipefail

normalize_url() {
  # Strip SQLAlchemy asyncpg driver; libpq only needs postgresql:// or postgres://
  local u="$1"
  u="${u#postgresql+asyncpg://}"
  u="${u#postgres+asyncpg://}"
  if [[ "$u" != *"://"* ]]; then
    u="postgresql://${u}"
  fi
  echo "$u"
}

append_ssl() {
  local u="$1"
  if [[ "$u" != *"sslmode="* ]]; then
    if [[ "$u" == *\?* ]]; then
      u="${u}&sslmode=require"
    else
      u="${u}?sslmode=require"
    fi
  fi
  echo "$u"
}

: "${SOURCE_DATABASE_URL:?Set SOURCE_DATABASE_URL to your local Postgres URL}"
: "${TARGET_DATABASE_URL:?Set TARGET_DATABASE_URL to Heroku DATABASE_URL}"

SRC=$(normalize_url "$SOURCE_DATABASE_URL")
DST=$(normalize_url "$TARGET_DATABASE_URL")
# Heroku requires SSL; ensure sslmode=require on the target
DST=$(append_ssl "$DST")

DUMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/volunteer_pgdump.XXXXXX")"
DUMP_FILE="${DUMP_DIR}/local_full.dump"
trap 'rm -rf "$DUMP_DIR"' EXIT

echo "==> Dumping local database to custom-format archive..."
pg_dump \
  -Fc \
  --no-acl \
  --no-owner \
  --encoding=UTF8 \
  -d "$SRC" \
  -f "$DUMP_FILE"

echo "==> Restoring into Heroku (this can take a while)..."
# Default: no --clean (best after heroku pg:reset). PGPRESTORE_FLAGS e.g. --clean --if-exists
# Exit codes: 0 = ok, 1 = ok but non-fatal issues, 2+ = fatal
set +e
pg_restore \
  -d "$DST" \
  --no-acl \
  --no-owner \
  --verbose \
  ${PGPRESTORE_FLAGS-} \
  "$DUMP_FILE"
st=$?
set -e
if [[ "$st" -ge 2 ]]; then
  echo "pg_restore failed (exit $st). If the target already has a partial schema, run: heroku pg:reset DATABASE --confirm YOUR_APP" >&2
  exit "$st"
fi
if [[ "$st" -eq 1 ]]; then
  echo "Note: pg_restore returned 1 (non-fatal warnings). Review the log. For a clean copy, use heroku pg:reset first."
fi

echo "==> Done. Verify on Heroku: table counts, app smoke test."
echo "    heroku psql -a YOUR_APP -c \"SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;\""
