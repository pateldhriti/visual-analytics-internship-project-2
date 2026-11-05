#!/bin/sh
# Back up the project databases with pg_dump, then delete old backups.
#
# Runs inside the db-backup container (docker/docker-compose.prod.yml) once
# a day. Can also be run by hand at any time:
#
#   docker compose --env-file .env -f docker/docker-compose.yml \
#       -f docker/docker-compose.prod.yml run --rm --no-deps \
#       --entrypoint sh db-backup /usr/local/bin/backup.sh
#
# Reads:
#   PGHOST, PGUSER, PGPASSWORD   connection
#   BACKUP_DATABASES             space-separated database names
#   BACKUP_DIR                   where dumps go (default /backups)
#   BACKUP_RETENTION_DAYS        how many days of dumps to keep (default 14)
#   BACKUP_SKIP_DATA             space-separated table patterns whose rows
#                                are not dumped (default "raw.* staging.*")
#
# What is skipped and why: the raw schema is a byte-for-byte copy of the
# government files in data/raw, and the staging schema holds intermediate
# ETL output; etl/refresh_all.py rebuilds both from data/raw. Together they
# are about 3.6 GB of the 3.7 GB housing_windsor database. Their table
# definitions are still backed up, only their rows are skipped, which keeps
# a daily dump to roughly the 100 MB of data that cannot be regenerated
# (warehouse, public, and Superset's metadata). Set BACKUP_SKIP_DATA="" to
# dump everything.
#
# Writes: $BACKUP_DIR/<database>_<UTC timestamp>.dump (pg_dump custom
# format, compressed; restore with pg_restore -- see
# docs/production_hardening.md).

set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
SKIP_DATA="${BACKUP_SKIP_DATA-raw.* staging.*}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"

# Build one --exclude-table-data option per pattern. set -f stops the
# shell from expanding "raw.*" as a filename glob.
set -f
exclude_args=""
for pattern in $SKIP_DATA; do
    exclude_args="$exclude_args --exclude-table-data=$pattern"
done

for db in $BACKUP_DATABASES; do
    target="$BACKUP_DIR/${db}_${STAMP}.dump"
    # Write to a temporary name first so a failed dump never looks like a
    # complete backup.
    # shellcheck disable=SC2086  # exclude_args is intentionally split
    pg_dump --format=custom --compress=6 --no-owner --dbname="$db" \
        $exclude_args --file="$target.partial"
    mv "$target.partial" "$target"
    echo "$(date -u +%FT%TZ) backed up $db -> $target ($(du -h "$target" | cut -f1))"
done
set +f

# Keep only the last RETENTION_DAYS days of backups.
find "$BACKUP_DIR" -name '*.dump' -type f -mtime +"$RETENTION_DAYS" -print -delete
find "$BACKUP_DIR" -name '*.partial' -type f -mmin +60 -delete
