#!/bin/sh
set -eu
umask 077
mkdir -p /backups
while true; do
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  file="/backups/lifehub-${stamp}.dump"
  temp="${file}.partial"
  if pg_dump --format=custom --no-owner --file "$temp" && pg_restore --list "$temp" >/dev/null; then
    mv "$temp" "$file"
    find /backups -type f -name 'lifehub-*.dump' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
    echo "Backup verified: $file"
  else
    rm -f "$temp"
    echo "Backup failed: $file" >&2
  fi
  sleep "${BACKUP_INTERVAL_SECONDS:-86400}"
done
