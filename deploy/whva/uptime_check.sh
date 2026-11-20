#!/usr/bin/env bash
# Uptime monitor for the public site and the dashboards. Run every 5 minutes
# on whva by whva-uptime.timer; each run appends one line per URL to
# ~/uptime/uptime.log and, when a URL is down, a line to ~/uptime/alerts.log
# (and posts it to ALERT_WEBHOOK_URL if that is set, as {"text": ...}, the
# format Teams and Slack incoming webhooks accept). One alert per outage: a
# URL is reported when it goes down and when it is back, not every 5 minutes.
#
#   ./uptime_check.sh            check now
#   ./uptime_check.sh --report   availability and response times per URL
#
# Settings (environment variables, all optional):
#   UPTIME_URLS        space-separated (default: the website and apss)
#   UPTIME_DIR         default ~/uptime
#   UPTIME_TIMEOUT     seconds before a request counts as down (default 15)
#   ALERT_WEBHOOK_URL  where to post alerts

set -uo pipefail

URLS="${UPTIME_URLS:-https://whva.cs.uwindsor.ca/ https://apss.cs.uwindsor.ca/health}"
DIR="${UPTIME_DIR:-$HOME/uptime}"
TIMEOUT="${UPTIME_TIMEOUT:-15}"
LOG="$DIR/uptime.log"
ALERTS="$DIR/alerts.log"
mkdir -p "$DIR/state"

if [ "${1:-}" = "--report" ]; then
  [ -f "$LOG" ] || { echo "No checks logged yet ($LOG)"; exit 0; }
  # log line: <UTC time> <url> <UP|DOWN> <http code> <seconds>
  awk '{ n[$2]++; if ($3 == "UP") { up[$2]++; t[$2] += $5; if ($5 > mx[$2]) mx[$2] = $5 } }
       END { printf "%-45s %8s %10s %9s %9s\n", "url", "checks", "available", "avg (s)", "max (s)";
             for (u in n) printf "%-45s %8d %9.2f%% %9.3f %9.3f\n", u, n[u], 100 * up[u] / n[u],
                                 up[u] ? t[u] / up[u] : 0, mx[u] }' "$LOG"
  echo "first check: $(head -1 "$LOG" | cut -d' ' -f1)   last: $(tail -1 "$LOG" | cut -d' ' -f1)"
  exit 0
fi

alert() {
  echo "$(date -u +%FT%TZ) $1" >> "$ALERTS"
  if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
    curl -s -m 10 -H 'Content-Type: application/json' \
         -d "{\"text\": \"Windsor Housing uptime: $1\"}" "$ALERT_WEBHOOK_URL" > /dev/null || true
  fi
}

for url in $URLS; do
  now=$(date -u +%FT%TZ)
  out=$(curl -s -o /dev/null -m "$TIMEOUT" -w '%{http_code} %{time_total}' "$url" 2>/dev/null) || out="000 $TIMEOUT"
  code=${out% *}; secs=${out#* }
  # Up: any 2xx or 3xx answer (apss redirects to its login page).
  if [ "${code:0:1}" = "2" ] || [ "${code:0:1}" = "3" ]; then status=UP; else status=DOWN; fi
  echo "$now $url $status $code $secs" >> "$LOG"

  key=$(printf '%s' "$url" | tr -c 'A-Za-z0-9' '_')
  previous=$(cat "$DIR/state/$key" 2>/dev/null || echo UP)
  if [ "$status" != "$previous" ]; then
    if [ "$status" = DOWN ]; then alert "DOWN $url (HTTP $code)"; else alert "back UP $url"; fi
    echo "$status" > "$DIR/state/$key"
  fi
done
