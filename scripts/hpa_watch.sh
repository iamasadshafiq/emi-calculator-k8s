#!/bin/bash
# Records the HPA every 15 seconds: average CPU utilisation, current and desired replicas.
# usage: ./scripts/hpa_watch.sh OUTFILE.csv SECONDS
OUT=$1
DUR=${2:-600}
START=$(date +%s)
echo "timestamp,elapsed_s,cpu_percent,target_percent,replicas,desired_replicas" > "$OUT"
N=0
while [ $((N * 15)) -le "$DUR" ]; do
  # sample number N is taken at START + N*15 seconds
  WAIT=$((START + N * 15 - $(date +%s)))
  [ "$WAIT" -gt 0 ] && sleep "$WAIT"
  EL=$(($(date +%s) - START))
  # TARGETS column looks like "cpu: 37%/50%"
  LINE=$(kubectl get hpa emi-web -n emi --no-headers)
  CPU=$(echo "$LINE" | grep -o '[0-9]*%/' | tr -d '%/')
  TARGET=$(echo "$LINE" | grep -o '/[0-9]*%' | tr -d '%/')
  REPLICAS=$(echo "$LINE" | awk '{print $(NF-1)}')
  DESIRED=$(kubectl get hpa emi-web -n emi -o jsonpath='{.status.desiredReplicas}')
  echo "$(date '+%Y-%m-%d %H:%M:%S'),$EL,${CPU:-},$TARGET,$REPLICAS,$DESIRED" >> "$OUT"
  N=$((N + 1))
done
