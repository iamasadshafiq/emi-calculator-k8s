#!/bin/bash
# Milestone 04, fixed replicas: 3 replica counts x 5 request rates = 15 runs of 60 s.
# Runs on the Minikube host. The HPA must not exist during these runs.
# For every run it saves in results/fixed/:
#   r<replicas>_rate<rate>_httperf.txt    httperf report
#   r<replicas>_rate<rate>_host_cpu.csv   host CPU every second
#   r<replicas>_rate<rate>_pods.csv       kubectl top pods every 15 s
# usage: ./scripts/run_fixed_experiments.sh
OUT=results/fixed
DURATION=60
mkdir -p "$OUT"

for REPLICAS in 1 2 3; do
  echo "$(date +%T) ===== $REPLICAS replica(s) ====="
  kubectl scale deployment emi-web --replicas=$REPLICAS -n emi
  kubectl rollout status deployment/emi-web -n emi
  sleep 45                                   # removed pods terminate, CPU settles

  for RATE in 10 25 50 100 200; do
    NAME=r${REPLICAS}_rate${RATE}
    # start every run with all replicas Ready
    kubectl rollout status deployment/emi-web -n emi --timeout=300s > /dev/null
    echo "$(date +%T) run $NAME"
    python3 scripts/profile.py "$OUT/$NAME" &
    PROFILER=$!
    sleep 15                                 # a few idle samples before the load
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$REPLICAS,$RATE" >> "$OUT/run_times.csv"
    ./scripts/run_httperf.sh $RATE $DURATION "$OUT/${NAME}_httperf.txt"
    sleep 30                                 # kubectl top is about 30 s behind
    kill $PROFILER; wait $PROFILER
    grep -E "Reply time|Errors: total|Reply status" "$OUT/${NAME}_httperf.txt"
    sleep 15
  done
done
echo "$(date +%T) all runs finished"
