#!/usr/bin/env bash
# Daily backup of our `warehouse` schema in the university's `whva`
# database (psql.cs.uwindsor.ca). Runs on the whva server, which can reach
# the database (our laptops cannot), from the systemd timer
# whva-backup.timer. See docs/production_hardening.md, section 6.
#
# The password is never in this file: pg_dump reads it from ~/.pgpass
# (chmod 600), the standard PostgreSQL password file.
#
#   ./backup_whva_warehouse.sh          one backup now
#
# Settings (environment variables, all optional):
#   PGHOST                 default psql.cs.uwindsor.ca
#   PGDATABASE             default whva
#   PGUSER                 default the logged-in user
#   BACKUP_DIR             default ~/backups
#   BACKUP_RETENTION_DAYS  default 14

set -euo pipefail

export PGHOST="${PGHOST:-psql.cs.uwindsor.ca}"
export PGDATABASE="${PGDATABASE:-whva}"
export PGUSER="${PGUSER:-$(id -un)}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
KEEP_DAYS="${BACKUP_RETENTION_DAYS:-14}"

umask 077
mkdir -p "$BACKUP_DIR"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/whva_warehouse_$stamp.dump"

# -w: fail instead of waiting for a password nobody will type.
# Custom format (-Fc) is compressed and lets pg_restore pick objects.
# Grants are kept, so a restore gives Superset's connection its read access back.
pg_dump -w --schema=warehouse --no-owner -Fc -f "$out.part"

# A file that pg_restore cannot list is not a backup.
pg_restore --list "$out.part" > /dev/null
mv "$out.part" "$out"

find "$BACKUP_DIR" -maxdepth 1 -name 'whva_warehouse_*.dump' -mtime +"$KEEP_DAYS" -delete

echo "$(date -u +%FT%TZ) backup ok: $out ($(du -h "$out" | cut -f1))"
