#!/bin/bash
# One httperf run at a fixed request rate against http://emi.local/.
# Runs on the Minikube host, where emi.local points to $(minikube ip) in /etc/hosts.
# Every session of workload.txt is a single POST /api/emi with random valid
# inputs, so sessions per second = requests per second.
# httperf can keep at most 1024 connections open, so the timeout is 4 s:
# at 200 req/s that is at most 800 open connections.
# usage: ./scripts/run_httperf.sh RATE SECONDS OUTFILE
RATE=$1
DUR=$2
OUT=$(realpath -m "$3")
cd "$(dirname "$0")"
[ -f workload.txt ] || python3 gen_workload.py 1000 > workload.txt

# httperf busy-waits on one CPU core, so it is pinned to CPU 3 and the Minikube
# node is kept on CPUs 0-2 (docker update --cpuset-cpus=0-2 minikube).
taskset -c 3 httperf --hog --server emi.local --port 80 \
        --wsesslog=$((RATE * DUR)),0,workload.txt --rate "$RATE" --timeout 4 \
        --add-header='Content-Type: application/json\n' > "$OUT" 2>&1
