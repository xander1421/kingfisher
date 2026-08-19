#!/usr/bin/env python3
"""A1 — every liveness test applied to a pid that came out of `.loop_lock.<CS>`.

A LIVENESS TEST IS ONLY THIS ROW'S SUBJECT IF THE pid CAME FROM A LOCK. The first
version of this census counted `kill -0 "$turn"` in run_loop.sh's heartbeat -- a
TURN pid, legitimately tested by pid alone, because the launcher spawned it and
knows what it is. Scoring it would have inflated the count by one and pointed the
row at code that is correct.

The window rule is mechanical: a hit counts if `loop_lock`, `from_lock` or `$LOCK`
appears within the 12 lines above it. Excluded hits are PRINTED rather than
dropped -- a census that hides its exclusions is one whose number cannot be
checked. This file is separate from probe.sh because the same nesting that
produced H232's dead mutants (a heredoc inside a shell function) was reproduced
here in one cycle: the python for this arm lived in a heredoc inside probe.sh and
its own heredoc terminated the outer one.

usage: python3 sites.py <repo-root>       exit 0 always; the count is the output
"""
import re, sys, pathlib

SITES = [
    ("run_loop.sh",                   "acquire + per-turn re-read"),
    ("bringup.sh",                    "supervisor: decides MISSING"),
    ("spikes/harness/bringup.sh",     "preflight copy: decides stale-clear"),
    ("spikes/harness/fleetcensus.sh", "census: status word"),
    ("spikes/harness/registry.py",    "registry: lead provenance"),
    ("spikes/harness/whois.py",       "whois: 'live' vs 'STALE'"),
]
# CALL SITES COUNT, NOT ONLY INLINE TESTS. registry.py reads the lock at :142 and
# tests it at :147 with `_pid_alive(...)`, whose BODY is 30 lines away in a generic
# helper -- so a window rule keyed on inline `os.kill` found the helper (excluded,
# correctly: it is not a lock pid there) and MISSED the reader. The first count
# printed 4 with registry.py absent from it, which is the under-report that mirrors
# the over-report above.
LIVENESS = re.compile(r'kill -0|os\.kill\(|\["ps", "-p"|ps -p |_pid_alive\(|lane_lock_pid\(')
CMD = re.compile(r"-o command=|'command'|comm=|launcher_alive")

root = pathlib.Path(sys.argv[1])
pidonly = excluded = counted = 0
for rel, what in SITES:
    lines = (root / rel).read_text().splitlines()
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith('#') or not LIVENESS.search(ln):
            continue
        window = '\n'.join(lines[max(0, i - 13):i])
        if not any(k in window for k in ('loop_lock', 'from_lock', '$LOCK')):
            excluded += 1
            print(f"    {rel}:{i:<5} EXCLUDED — this pid does not come from a lock")
            print(f"        {s[:78]}")
            continue
        counted += 1
        kind = 'pid+command' if CMD.search(ln) else 'PID ONLY'
        if kind == 'PID ONLY':
            pidonly += 1
        print(f"    {rel}:{i:<5} {kind:<12} {what}")
        print(f"        {s[:78]}")
print(f"    lock-pid liveness tests: {counted}, of them PID ALONE: {pidonly}"
      f"   (excluded as not lock pids: {excluded})")
