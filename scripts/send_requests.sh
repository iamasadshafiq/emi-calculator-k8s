#!/bin/bash
# Sends N POST requests to /api/emi through the Ingress and counts how many
# requests each pod served (servedBy field of the JSON reply).
# usage: ./scripts/send_requests.sh [N] [logfile] [url]
N=${1:-30}
LOG=${2:-/dev/null}
URL=${3:-http://emi.local}
TMP=$(mktemp)

for i in $(seq 1 "$N"); do
  P=$((RANDOM % 900000 + 100000))
  R=$((RANDOM % 20 + 5))
  M=$(((RANDOM % 10 + 1) * 12))
  POD=$(curl -s -m 10 -X POST "$URL/api/emi" -H 'Content-Type: application/json' \
          -d "{\"principal\": $P, \"rate\": $R, \"months\": $M}" |
        grep -o '"servedBy":"[^"]*"' | cut -d'"' -f4)
  echo "$(date +%H:%M:%S.%3N) request $i servedBy=${POD:-FAILED}"
done > "$TMP"

[ "$LOG" != "/dev/null" ] && cp "$TMP" "$LOG"
echo "requests served per pod ($N requests):"
sed 's/.*servedBy=//' "$TMP" | sort | uniq -c
rm -f "$TMP"
