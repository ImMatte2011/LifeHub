#!/bin/sh
set -eu
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: $0 path/to/lifehub-backup.dump" >&2
  exit 2
fi
pg_restore --list "$1" >/dev/null
pg_restore --clean --if-exists --no-owner --dbname "${DATABASE_URL_SYNC:?Set DATABASE_URL_SYNC}" "$1"
