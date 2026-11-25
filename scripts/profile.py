#!/usr/bin/env python3
"""
Profiler for the load tests (runs on the Minikube host).

  * host CPU: read from /proc/stat every second (same value as 100 - %idle of mpstat)
  * pods:     kubectl top pods -n emi every 15 seconds (CPU in millicores, memory in Mi)

Both are written to CSV files with a timestamp column:
  <prefix>_host_cpu.csv   timestamp,elapsed_s,cpu_percent
  <prefix>_pods.csv       timestamp,elapsed_s,pod,cpu_millicores,memory_mi

usage: python3 profile.py <prefix> [seconds]      (without seconds: runs until Ctrl+C / kill)
"""
import csv
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

NAMESPACE = "emi"
POD_INTERVAL = 15

prefix = sys.argv[1]
duration = float(sys.argv[2]) if len(sys.argv) > 2 else None
stop = threading.Event()
signal.signal(signal.SIGINT, lambda *a: stop.set())
signal.signal(signal.SIGTERM, lambda *a: stop.set())
t0 = time.time()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cpu_times():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:]]
    idle = v[3] + v[4]                      # idle + iowait
    return idle, sum(v[:8])


def host_cpu():
    with open(prefix + "_host_cpu.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "elapsed_s", "cpu_percent"])
        idle0, total0 = cpu_times()
        while not stop.wait(1.0):
            idle1, total1 = cpu_times()
            dt = total1 - total0
            usage = 100.0 * (1 - (idle1 - idle0) / dt) if dt else 0.0
            w.writerow([now(), round(time.time() - t0, 1), round(usage, 1)])
            f.flush()
            idle0, total0 = idle1, total1


def pods():
    with open(prefix + "_pods.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "elapsed_s", "pod", "cpu_millicores", "memory_mi"])
        while True:
            started = time.time()
            r = subprocess.run(["kubectl", "top", "pods", "-n", NAMESPACE, "--no-headers"],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    w.writerow([now(), round(started - t0, 1), parts[0],
                                parts[1].rstrip("m"), parts[2].rstrip("Mi")])
            f.flush()
            if stop.wait(max(0.0, POD_INTERVAL - (time.time() - started))):
                break


threads = [threading.Thread(target=host_cpu), threading.Thread(target=pods)]
for t in threads:
    t.start()
if duration:
    stop.wait(duration)
    stop.set()
else:
    while not stop.is_set():
        time.sleep(0.5)
for t in threads:
    t.join()
