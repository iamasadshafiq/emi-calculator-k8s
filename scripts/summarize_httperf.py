#!/usr/bin/env python3
"""
Reads the httperf reports of the 15 fixed-replica runs and writes
results/fixed/summary.csv (one line per run).

error_count = httperf errors (timeouts, refused/reset connections, ...) + replies with a 4xx/5xx status

usage: python3 scripts/summarize_httperf.py [results/fixed]
"""
import csv
import glob
import os
import re
import sys

folder = sys.argv[1] if len(sys.argv) > 1 else "results/fixed"


def num(pattern, text, cast=float, default=0):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else default


rows = []
for path in glob.glob(os.path.join(folder, "r*_rate*_httperf.txt")):
    m = re.search(r"r(\d+)_rate(\d+)_httperf", path)
    text = open(path).read()
    errors = num(r"Errors: total (\d+)", text, int)
    s4 = num(r"4xx=(\d+)", text, int)
    s5 = num(r"5xx=(\d+)", text, int)
    rows.append({
        "replicas": int(m.group(1)),
        "rate": int(m.group(2)),
        "requests": num(r"requests (\d+)", text, int),
        "replies": num(r"replies (\d+)", text, int),
        "reply_rate": num(r"Reply rate \[replies/s\]: min [\d.]+ avg ([\d.]+)", text),
        "avg_response_ms": num(r"Reply time \[ms\]: response ([\d.]+)", text),
        "status_2xx": num(r"2xx=(\d+)", text, int),
        "status_5xx": s5,
        "client_timeouts": num(r"client-timo (\d+)", text, int),
        "conn_refused": num(r"connrefused (\d+)", text, int),
        "conn_reset": num(r"connreset (\d+)", text, int),
        "fd_unavail": num(r"fd-unavail (\d+)", text, int),
        "httperf_errors": errors,
        "error_count": errors + s4 + s5,
    })

rows.sort(key=lambda r: (r["replicas"], r["rate"]))
out = os.path.join(folder, "summary.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print("%-8s %-5s %-9s %-8s %-16s %s" % ("replicas", "rate", "requests", "replies", "avg_response_ms", "errors"))
for r in rows:
    print("%-8d %-5d %-9d %-8d %-16.1f %d" % (r["replicas"], r["rate"], r["requests"], r["replies"],
                                             r["avg_response_ms"], r["error_count"]))
print("written", out)
