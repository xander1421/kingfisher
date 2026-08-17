#!/usr/bin/env python3
"""Do the named reproducers still reproduce?

`reprocheck` answers "does this claim NAME a reproducer, and does that path
exist". Existence is not runnability and runnability is not agreement, so a
claim can pass reprocheck while naming a document, a stale binary, or a script
that now errors. Two A-grade claims have already gone stale, both found by
accident.

This runs them and records what happened. Classification:

  PASS       exited 0
  FAIL       exited non-zero -- the claim's own reproducer is broken
  NOT-RUNNABLE   the annotation names a .md, or a binary with no source entry
  NEEDS-DEVICE   requires the phone or a live server; run separately

Cost is bounded per reproducer; anything over the timeout is reported as such
rather than killed silently.

    python3 audit.py            # everything cheap
    python3 audit.py --all      # include the slow device-dependent ones
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
LEDGER = os.path.join(ROOT, 'out', 'LEDGER.md')
REPRO = re.compile(r'repro: `([^\s`]*/[^`]*)`')
# A non-zero exit that means "I refused on purpose", not "I am broken".
DECLINED = re.compile(r'gate REFUSED|device is not quiet|REFUSING:|not on external power')
# A THIRD outcome, distinct from both PASS and FAIL: the driver is intact and
# the environment moved out from under it. run_lan.py hit this when the phone
# joined a VPN (tun1, src 10.184.0.5) and left the host subnet. Scoring that as
# FAIL blames the code; scoring it as DECLINED hides that a headline path is
# currently unreproducible. It is its own category and it must be loud.
PRECONDITION = re.compile(r'not on the host subnet|no route to host|connection refused'
                          r'|no devices/emulators')

# Reproducers that need the phone attached, a listening server, or minutes of
# wall clock. Named explicitly so "cheap run" never silently skips something.
SLOW = {
    'spikes/M1_7_transport/run.py',
    'spikes/M1_8_quorum3/q3.py',
    'spikes/M1_7_transport/latency_floor.py',
    'spikes/M1_7_transport/handshake.py',
    'spikes/M1_10_patchlive/probe.py',
    'spikes/M1_9_mutation/mutate.py',
}


def annotations():
    """(path, args, claim) for every repro annotation, de-duplicated."""
    text = open(LEDGER).read()
    seen, out = set(), []
    for m in REPRO.finditer(text):
        spec = m.group(1).strip()
        line = text[:m.start()].split('\n')[-1]
        title = re.search(r'^\| \*\*(.{0,70})', line)
        claim = (title.group(1) if title else '?').rstrip('*| ')
        if spec in seen:
            continue
        seen.add(spec)
        parts = spec.split()
        out.append((parts[0], parts[1:], claim))
    return out


def classify(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return 'MISSING'
    if path.endswith('.md'):
        # A document cannot re-derive a number. reprocheck scored these as
        # annotated because the path exists.
        return 'NOT-RUNNABLE'
    if not path.endswith(('.py', '.sh')):
        return 'NOT-RUNNABLE'      # a prebuilt binary is an artifact, not a reproducer
    if path in SLOW:
        return 'NEEDS-DEVICE'
    return 'RUN'


def run(path, args, timeout):
    full = os.path.join(ROOT, path)
    cmd = (['python3', full] if path.endswith('.py') else ['sh', full]) + list(args)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=os.path.dirname(full), capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, round(time.time() - t0, 1), (p.stdout + p.stderr)[-600:]
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='include NEEDS-DEVICE')
    ap.add_argument('--timeout', type=int, default=180)
    a = ap.parse_args()

    rows = []
    for path, args, claim in annotations():
        kind = classify(path)
        if kind == 'NEEDS-DEVICE' and a.all:
            kind = 'RUN'
        if kind == 'RUN':
            rc, secs, tail = run(path, args, a.timeout)
            if rc == 0:
                status = 'PASS'
            elif PRECONDITION.search(tail):
                status = 'PRECONDITION'
            elif DECLINED.search(tail):
                # A safety gate that REFUSES is the gate working. Scoring it as
                # FAIL would report a healthy claim as stale -- the mirror of an
                # inert check: both misreport, one optimistically and one
                # pessimistically. q3.py exited 2 here because the phone was hot
                # from the previous cycle's 120 adb probe runs, which is the
                # thermal rail doing its job.
                status = 'DECLINED'
            else:
                status = f'FAIL(rc={rc})'
        else:
            status, secs, tail = kind, 0, ''
        rows.append({'path': path, 'args': args, 'claim': claim,
                     'status': status, 'secs': secs, 'tail': tail})
        print(f'{status:14s} {secs:6}s  {path} {" ".join(args)}')
        if status.startswith('FAIL'):
            for ln in tail.strip().splitlines()[-3:]:
                print(f'                        | {ln[:100]}')

    json.dump(rows, open(os.path.join(HERE, 'audit.json'), 'w'), indent=1)
    tally = {}
    for r in rows:
        k = r['status'].split('(')[0]
        tally[k] = tally.get(k, 0) + 1
    print(f'\n{tally}   (of {len(rows)} annotations)')
    return rows


def demo():
    """The parser is the claim. A regex that matched nothing would report
    'every reproducer passes' over an empty set."""
    ann = annotations()
    assert len(ann) >= 10, f'only {len(ann)} annotations parsed -- regex drifted'
    assert any(p.endswith('.md') for p, _, _ in ann), \
        'expected at least one .md annotation; those are the NOT-RUNNABLE case'
    assert classify('out/LEDGER.md') == 'NOT-RUNNABLE'
    print(f'audit: parsed {len(ann)} annotations')


if __name__ == '__main__':
    demo()
    main()
