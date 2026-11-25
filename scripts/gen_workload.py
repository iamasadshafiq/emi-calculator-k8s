#!/usr/bin/env python3
"""
Writes a session file for httperf (--wsesslog). Every session is one
POST /api/emi with random valid inputs, so every request also inserts a
document in MongoDB. httperf accepts at most 1000 sessions in a file and
repeats them when more requests are needed.

usage: python3 gen_workload.py [sessions] > workload.txt
"""
import random
import sys

sessions = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
random.seed()

for _ in range(sessions):
    principal = random.randrange(50_000, 5_000_001, 1000)
    rate = round(random.uniform(4, 24), 2)
    months = random.choice([6, 12, 18, 24, 36, 48, 60, 84, 120, 180, 240])
    body = '{"principal": %d, "rate": %s, "months": %d}' % (principal, rate, months)
    print("/api/emi method=POST contents='%s'" % body)
    print()
