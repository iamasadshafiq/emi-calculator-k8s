#!/usr/bin/env python3
"""
Draws the three graphs of Milestone 04 from the files in results/.

  graph1_response_time.png   average response time vs request rate (1, 2, 3 replicas)
  graph2_pod_cpu.png         CPU of every pod during the 100 req/s run with 3 replicas
  graph3_autoscaling.png     request rate, average CPU utilisation and replicas (HPA test)

usage: python3 scripts/plot_graphs.py        (needs matplotlib)
"""
import csv
import os
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUT = os.path.join(RESULTS, "graphs")
os.makedirs(OUT, exist_ok=True)
CPU_REQUEST_M = 100          # CPU request of every pod in millicores (100m = 100 %)
FMT = "%Y-%m-%d %H:%M:%S"


def read(path):
    with open(path) as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ graph 1
rows = read(os.path.join(RESULTS, "fixed", "summary.csv"))
plt.figure(figsize=(7.5, 4.5))
for replicas, marker in ((1, "o"), (2, "s"), (3, "^")):
    sel = [r for r in rows if int(r["replicas"]) == replicas]
    plt.plot([int(r["rate"]) for r in sel], [float(r["avg_response_ms"]) for r in sel],
             marker=marker, label="%d replica%s" % (replicas, "" if replicas == 1 else "s"))
plt.xlabel("Request rate (requests/s)")
plt.ylabel("Average response time (ms)")
plt.title("Graph 1: average response time vs request rate")
plt.xticks([10, 25, 50, 100, 200])
plt.yscale("log")
plt.grid(True, which="both", alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT, "graph1_response_time.png"), dpi=160)
plt.close()

# ------------------------------------------------------------------ graph 2
RUN = "r3_rate100"
pods = read(os.path.join(RESULTS, "fixed", RUN + "_pods.csv"))
start = None
for line in open(os.path.join(RESULTS, "fixed", "run_times.csv")):
    ts, replicas, rate = line.strip().split(",")
    if replicas == "3" and rate == "100":
        start = datetime.strptime(ts, FMT)
series = defaultdict(list)
for r in pods:
    t = (datetime.strptime(r["timestamp"], FMT) - start).total_seconds()
    series[r["pod"]].append((t, 100.0 * float(r["cpu_millicores"]) / CPU_REQUEST_M))
plt.figure(figsize=(7.5, 4.5))
for pod in sorted(series):
    xs, ys = zip(*series[pod])
    plt.plot(xs, ys, marker="o", markersize=3, linestyle="--" if pod.startswith("mongo") else "-", label=pod)
plt.axvspan(0, 60, color="grey", alpha=0.12, label="load (100 req/s)")
plt.xlabel("Time since the start of the load (s)")
plt.ylabel("CPU utilisation (% of the 100m CPU request)")
plt.title("Graph 2: CPU of each pod, 100 req/s with 3 web replicas")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "graph2_pod_cpu.png"), dpi=160)
plt.close()

# ------------------------------------------------------------------ graph 3
hpa = [r for r in read(os.path.join(RESULTS, "autoscale", "hpa.csv")) if r["replicas"]]
phases = read(os.path.join(RESULTS, "autoscale", "phases.csv"))
t = [int(r["elapsed_s"]) / 60 for r in hpa]
cpu = [float(r["cpu_percent"]) if r["cpu_percent"] else float("nan") for r in hpa]
replicas = [int(r["replicas"]) for r in hpa]
rate_x, rate_y = [], []
for p in phases:
    rate_x += [int(p["elapsed_s"]) / 60, (int(p["elapsed_s"]) + int(p["seconds"])) / 60]
    rate_y += [int(p["rate"]), int(p["rate"])]

fig, ax = plt.subplots(3, 1, figsize=(7.5, 7.5), sharex=True)
ax[0].plot(rate_x, rate_y, color="tab:blue")
ax[0].set_ylabel("Request rate\n(requests/s)")
ax[0].set_ylim(0, 120)
ax[1].plot(t, cpu, color="tab:red", marker="o", markersize=3)
ax[1].axhline(50, color="grey", linestyle="--", label="HPA target 50 %")
ax[1].set_ylabel("Average CPU utilisation\n(% of request)")
ax[1].legend(fontsize=8)
ax[2].step(t, replicas, where="post", color="tab:green")
ax[2].set_ylabel("Web replicas")
ax[2].set_yticks(range(0, 6))
ax[2].set_xlabel("Time (minutes)")
for a in ax:
    a.grid(True, alpha=0.3)
    a.set_xlim(0, 10)
ax[0].set_title("Graph 3: autoscaling test (HPA 1-5 pods, target 50 % CPU)")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "graph3_autoscaling.png"), dpi=160)
plt.close()
print("graphs written to", OUT)
