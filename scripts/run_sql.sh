#!/usr/bin/env bash
# Load .env and run psql with the same DB the app uses (local POSTGRES_* or DATABASE_URL).
# Usage: ./scripts/run_sql.sh [path-to.sql]
# Example: ./scripts/run_sql.sh add_duty_type_all.sql
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
[ -f .env ] && . ./.env
set +a

SQL_FILE="${1:-add_duty_type_all.sql}"
if [ ! -f "$SQL_FILE" ]; then
  echo "File not found: $SQL_FILE" >&2
  exit 1
fi

if [ -n "${DATABASE_URL:-}" ]; then
  u="$DATABASE_URL"
  case "$u" in
    postgresql+asyncpg://*) u="postgresql://${u#postgresql+asyncpg://}" ;;
    postgres://*)          u="postgresql://${u#postgres://}" ;;
  esac
  PSQLURL="$u"
else
  PSQLURL="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-password}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-northenvolunteerdb}"
fi

psql "$PSQLURL" -f "$SQL_FILE"
