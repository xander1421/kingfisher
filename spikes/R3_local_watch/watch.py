#!/usr/bin/env python3
"""Fleet triage on the LOCAL model. Zero Claude quota.

WHY THIS IS THE LOCAL TIER'S FIRST JOB. Six times today the operator asked
"why did it stop", and six times the answer required reading lane logs and
separating three causes that look identical from outside:

  quota      the vendor refused; the lane is fine and will return at reset
  stale      a lock/fuse/STOP outlived its process and blocks relaunch
  wedged     a turn ran to the 3600s cap and was terminated mid-work

Heartbeats cannot tell them apart -- the beat is written by a background timer,
so it is freshest exactly when a lane is thrashing. `children=0` is normal
between turns. Log silence is normal DURING a turn. All three signals read the
same for a healthy lane and a dead one, which is why this needed a human every
time.

The classification is deterministic Python. The local model is used ONLY to
write the one-line human summary, because that is the part worth a model and
the part that costs nothing if it is wrong. A 4B that hallucinates a cause
would be worse than no watchdog, so the cause is never its call.

    python3 watch.py             # one pass
    python3 watch.py --serve     # loop every 120s, write STATUS.md
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LOCAL = 'http://127.0.0.1:8081/v1/chat/completions'
QUOTA = re.compile(r'hit your (weekly|usage|session|daily) limit|rate.?limit|too many requests', re.I)
RESET = re.compile(r'resets\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', re.I)


def roster():
    p = os.path.join(ROOT, 'roster.txt')
    out = []
    for line in open(p):
        line = re.sub(r'#.*', '', line).strip()
        if line:
            out.append(line.split()[0])
    return out


def classify(lane):
    """Deterministic. The model never decides a cause."""
    log = os.path.join(ROOT, f'loop_{lane}.log')
    alive = subprocess.run(['pgrep', '-f', f'You are {lane}\\.'],
                           capture_output=True).returncode == 0
    tail = ''
    if os.path.exists(log):
        tail = subprocess.run(['tail', '-40', log], capture_output=True,
                              text=True).stdout
    stale = [f for f in (f'.loop_lock.{lane}', f'.loop_blocks.{lane}',
                         f'.loop_exit.{lane}')
             if os.path.exists(os.path.join(ROOT, f)) and not alive]
    # The fail counter is HISTORICAL. Every lane's log still carries
    # "(fail 26)" from the session-limit window, and printing that beside
    # "OK, 6 commits in 60m" reads as "healthy while failing 26 times". The
    # number is true and the impression is false, which is the same defect as
    # a fresh heartbeat on a thrashing lane. Only counted when it is CURRENT --
    # i.e. the lane has landed nothing since, so the failures are still the
    # story.
    fails = 0
    m = re.findall(r'\(fail (\d+)\)', tail)
    if m:
        fails = int(m[-1])
    commits = int(subprocess.run(
        f"cd {ROOT} && git log --since='60 minutes ago' --all --pretty=%B "
        f"| grep -c '^Atom: {lane}' || true", shell=True,
        capture_output=True, text=True).stdout.strip() or 0)

    if QUOTA.search(tail) and not commits:
        r = RESET.search(tail)
        return 'QUOTA', f"vendor refused; resets {r.group(1) if r else 'unknown'}", fails, commits
    if not alive and stale:
        return 'STALE', f"dead with {', '.join(stale)} left behind", fails, commits
    if 'exceeded' in tail and 'terminating' in tail and not commits:
        return 'WEDGED', 'turn hit the cap and was terminated', fails, commits
    if not alive:
        return 'DOWN', 'no process', fails, commits
    if commits == 0:
        return 'IDLE', 'alive but nothing landed in 60m', fails, commits
    return 'OK', f'{commits} commits in 60m', fails, commits


def summarise(rows):
    """The ONLY model call. One sentence, and it is allowed to be wrong --
    every cause above is already decided in Python."""
    facts = '; '.join(f'{l}={s}({d})' for l, s, d, _, _ in rows)
    body = json.dumps({
        'model': 'local',
        'messages': [{'role': 'user', 'content':
                      'One sentence, under 25 words, plain English, for an '
                      'operator glancing at a dashboard. Do not invent causes. '
                      f'Fleet state: {facts} /no_think'}],
        'max_tokens': 90, 'temperature': 0}).encode()
    try:
        req = urllib.request.Request(LOCAL, body, {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r)['choices'][0]['message']['content'].strip()
    except Exception as e:
        # A dead local tier must not look like a healthy fleet.
        return f'(local model unavailable: {type(e).__name__})'


def once():
    rows = []
    for lane in roster():
        st, why, fails, commits = classify(lane)
        rows.append((lane, st, why, fails, commits))
    worst = [r for r in rows if r[1] not in ('OK',)]
    line = summarise(rows)
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {len(rows)-len(worst)}/{len(rows)} OK')
    for lane, st, why, fails, commits in rows:
        flag = '  ' if st == 'OK' else '!!'
        show_fails = fails and st != 'OK'
        print(f'  {flag} {lane:11s} {st:6s} {why}'
              + (f' (fail {fails}, current)' if show_fails else ''))
    print(f'  summary: {line}')
    md = [f'# Fleet status — {ts}', '',
          f'{len(rows)-len(worst)}/{len(rows)} lanes OK', '',
          f'> {line}', '', '| lane | state | detail | commits/60m |', '|---|---|---|---|']
    md += [f'| {l} | {s} | {w} | {c} |' for l, s, w, _, c in rows]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'STATUS.md'),
         'w').write('\n'.join(md) + '\n')
    return rows


def main():
    if '--serve' in sys.argv:
        while True:
            try:
                once()
            except Exception as e:
                print(f'watch: {type(e).__name__}: {e}', file=sys.stderr)
            time.sleep(120)
    once()
    return 0


if __name__ == '__main__':
    sys.exit(main())
