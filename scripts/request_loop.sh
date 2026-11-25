#!/bin/bash
# Keeps sending POST /api/emi through the Ingress for a number of seconds
# (about 5 requests per second) and logs every reply. Used to check that the
# application keeps answering during pod failures and rolling updates.
# usage: ./scripts/request_loop.sh [seconds] [url] > logfile
# log line: time  http_code  seconds  servedBy  version
DUR=${1:-60}
URL=${2:-http://emi.local}
TMP=$(mktemp)
declare -A PER_POD PER_VERSION
total=0; ok=0; failed=0
END=$((SECONDS + DUR))

while [ $SECONDS -lt $END ]; do
  P=$((RANDOM % 900000 + 100000))
  R=$((RANDOM % 20 + 5))
  M=$(((RANDOM % 10 + 1) * 12))
  OUT=$(curl -s -m 20 -o "$TMP" -w '%{http_code} %{time_total}' -X POST "$URL/api/emi" \
          -H 'Content-Type: application/json' -d "{\"principal\": $P, \"rate\": $R, \"months\": $M}")
  CODE=${OUT%% *}
  total=$((total + 1))
  if [ "$CODE" = "200" ]; then
    ok=$((ok + 1))
    POD=$(grep -o '"servedBy":"[^"]*"' "$TMP" | cut -d'"' -f4)
    VER=$(grep -o '"version":"[^"]*"' "$TMP" | cut -d'"' -f4)
    PER_POD[$POD]=$((${PER_POD[$POD]:-0} + 1))
    PER_VERSION[$VER]=$((${PER_VERSION[$VER]:-0} + 1))
  else
    failed=$((failed + 1)); POD=-; VER=-
  fi
  echo "$(date +%H:%M:%S.%3N) $OUT $POD $VER"
  sleep 0.15
done
rm -f "$TMP"

echo "---- summary ----"
for p in "${!PER_POD[@]}"; do echo "pod $p: ${PER_POD[$p]} requests"; done | sort
for v in "${!PER_VERSION[@]}"; do echo "version $v: ${PER_VERSION[$v]} requests"; done | sort
echo "total=$total ok=$ok failed=$failed"
