#!/usr/bin/env bash
# Restore test: prove a backup made by backup_whva_warehouse.sh can be
# restored. Restores the backup into an EMPTY database, then checks that
# every table has the same number of rows as the live `warehouse` schema
# and that every view runs. See docs/production_hardening.md, section 6.4.
#
#   ./restore_test.sh TARGET [SOURCE] [DUMP]
#   ./restore_test.sh --live-counts [SOURCE] > live_counts.txt
#
#   TARGET  connection string of an empty scratch database to restore into,
#           e.g. "dbname=restore_test" (never the live database: its
#           `warehouse` schema is dropped first)
#   SOURCE  the live data to compare with: a connection string (default:
#           PGHOST/PGDATABASE/PGUSER, i.e. whva on psql.cs.uwindsor.ca), or a
#           file written by --live-counts. We cannot create a scratch database
#           on the university's server, and laptops cannot reach that server,
#           so the test is run in two steps: --live-counts on whva, then the
#           restore on a laptop with that file as SOURCE.
#   DUMP    backup file (default: the newest ~/backups/whva_warehouse_*.dump)
#
# Passwords come from ~/.pgpass, never from this file. Exit code 0 = PASS.
# Row counts can differ if data was loaded after the backup was taken; the
# report says which tables differ so that can be checked.

set -euo pipefail

q() { psql "$1" -X -A -t -v ON_ERROR_STOP=1 -c "$2"; }
default_source="host=${PGHOST:-psql.cs.uwindsor.ca} dbname=${PGDATABASE:-whva} user=${PGUSER:-$(id -un)}"

if [ "${1:-}" = "--live-counts" ]; then
  src="${2:-$default_source}"
  for t in $(q "$src" "SELECT table_name FROM information_schema.tables
                       WHERE table_schema = 'warehouse' AND table_type = 'BASE TABLE' ORDER BY 1"); do
    echo "$t|$(q "$src" "SELECT count(*) FROM warehouse.\"$t\"")"
  done
  echo "__views__|$(q "$src" "SELECT count(*) FROM information_schema.views WHERE table_schema = 'warehouse'")"
  exit 0
fi

target="${1:?usage: restore_test.sh TARGET [SOURCE] [DUMP]   or   restore_test.sh --live-counts [SOURCE]}"
source_db="${2:-$default_source}"
dump="${3:-$(ls -t "$HOME"/backups/whva_warehouse_*.dump 2>/dev/null | head -1)}"
[ -n "$dump" ] && [ -f "$dump" ] || { echo "No backup file found (looked for ~/backups/whva_warehouse_*.dump)"; exit 2; }

case "$target" in
  *"dbname=whva"*|*"/whva"*) echo "Refusing to restore into the live whva database"; exit 2 ;;
esac

# Live figures: from the counts file, or from the live database.
live() {  # live <table name, or __views__>
  if [ -f "$source_db" ]; then
    grep -m1 "^$1|" "$source_db" | cut -d'|' -f2 || true
  elif [ "$1" = "__views__" ]; then
    q "$source_db" "SELECT count(*) FROM information_schema.views WHERE table_schema = 'warehouse'"
  else
    q "$source_db" "SELECT count(*) FROM warehouse.\"$1\"" 2>/dev/null || echo "missing"
  fi
}

echo "Backup:  $dump ($(du -h "$dump" | cut -f1))"
pg_restore --list "$dump" > /dev/null
echo "Restore: into an empty scratch database"
start=$(date +%s)
q "$target" "DROP SCHEMA IF EXISTS warehouse CASCADE" > /dev/null
# --no-owner/--no-acl: the scratch database does not have the university's roles.
pg_restore --no-owner --no-acl --exit-on-error -d "$target" "$dump"
echo "Restored in $(( $(date +%s) - start )) s"

fail=0
echo
printf '%-40s %12s %12s  %s\n' "table" "live" "restored" "result"
for t in $(q "$target" "SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'warehouse' AND table_type = 'BASE TABLE' ORDER BY 1"); do
  l=$(live "$t"); l="${l:-missing}"
  restored=$(q "$target" "SELECT count(*) FROM warehouse.\"$t\"")
  if [ "$l" = "$restored" ]; then r="ok"; else r="DIFFERENT"; fail=1; fi
  printf '%-40s %12s %12s  %s\n' "$t" "$l" "$restored" "$r"
done

echo
nviews=0; broken=0
for v in $(q "$target" "SELECT table_name FROM information_schema.views WHERE table_schema = 'warehouse' ORDER BY 1"); do
  nviews=$((nviews + 1))
  if ! q "$target" "SELECT count(*) FROM warehouse.\"$v\"" > /dev/null 2>&1; then
    echo "view does not run: $v"; broken=$((broken + 1)); fail=1
  fi
done
live_views=$(live "__views__")
echo "Views: $nviews restored (live: ${live_views:-unknown}), $broken failed to run"
[ "$nviews" = "$live_views" ] || fail=1

echo
if [ "$fail" = 0 ]; then echo "PASS: the backup restores completely"; else echo "FAIL: see above"; fi
exit "$fail"
