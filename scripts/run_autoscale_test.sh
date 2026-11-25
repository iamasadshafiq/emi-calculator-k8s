#!/bin/bash
# Milestone 04, autoscaling: 10-minute test with the HPA active.
#   2 min at 10 req/s, 5 min at 100 req/s, 3 min at 10 req/s
# The phases start exactly at 0, 120 and 420 seconds.
# Saves in results/autoscale/: hpa.csv (kubectl get hpa every 15 s), phases.csv,
# the profiler CSV files and one httperf report per phase.
# usage: ./scripts/run_autoscale_test.sh      (the HPA must already be applied)
OUT=results/autoscale
mkdir -p "$OUT"

python3 scripts/profile.py "$OUT/autoscale" 600 &
./scripts/hpa_watch.sh "$OUT/hpa.csv" 600 &

echo "timestamp,elapsed_s,rate,seconds" > "$OUT/phases.csv"
START=$(date +%s)
PHASE=1
for STEP in "0 10 120" "120 100 300" "420 10 180"; do
  set -- $STEP
  WAIT=$((START + $1 - $(date +%s)))
  [ "$WAIT" -gt 0 ] && sleep "$WAIT"
  echo "$(date '+%Y-%m-%d %H:%M:%S'),$(($(date +%s) - START)),$2,$3" >> "$OUT/phases.csv"
  echo "$(date +%T) phase $PHASE: $2 req/s for $3 s"
  ./scripts/run_httperf.sh $2 $3 "$OUT/phase${PHASE}_rate$2_httperf.txt" &
  PHASE=$((PHASE + 1))
done
wait
echo "$(date +%T) autoscaling test finished"
kubectl get events -n emi --field-selector reason=SuccessfulRescale > "$OUT/rescale_events.txt"
