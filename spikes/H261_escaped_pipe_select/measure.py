#!/usr/bin/env python3
"""H261 — the old SELECT command against the queue's own parser, both directions.

A number without its generator does not exist (D6), and this file exists because
the RESULT cited it before it was written: the first draft of the write-up quoted
`measure.py` in its Reproduce block while the path held an empty file.

usage: python3 spikes/H261_escaped_pipe_select/measure.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from statuscheck import queue_status, CLOSED

text = open(os.path.join(ROOT, 'WORK_QUEUE.md')).read()
rows = [l for l in text.splitlines() if re.match(r'^\| *[A-Z]+[0-9]+[a-z]? *\|', l)]
esc = [l for l in rows if r'\|' in l]

print("H261 — the SELECT command in prompts/ok-1.md §6 against the queue's own parser")
print(f"rows={len(rows)}  rows containing an escaped pipe={len(esc)}")

qs = queue_status(text)


def naive_open(line):
    """Exactly what `awk -F'|' ... $4 !~ /DONE|.../` does, in python."""
    f = line.split('|')
    return len(f) > 3 and not re.search(r'DONE|WITHDRAWN|RETRACTED|PARKED', f[3])


offered, hidden = [], []
for line in rows:
    rid = re.match(r'^\| *([A-Za-z0-9]+) *\|', line).group(1)
    if not rid.startswith('H'):
        continue
    st = qs.get(rid)
    truth_open = st is not None and st not in CLOSED
    n = naive_open(line)
    if n and not truth_open:
        offered.append((rid, st))
    if truth_open and not n:
        hidden.append((rid, st))

print()
print(f"A · CLOSED rows the old command OFFERS as work: {len(offered)}")
for rid, st in offered:
    print(f"     {rid:6s} queue={st}")
print()
print(f"B · OPEN rows the old command HIDES: {len(hidden)}")
for rid, st in hidden:
    print(f"     {rid:6s} queue={st}")
print()
print("Both directions are real and the second is the one I did not predict:")
print("a row whose ITEM text contains the word DONE lands in field 4 after the")
print("naive split, so the command reads the item as a status and drops the row.")
