#!/usr/bin/env python3
"""Re-run every driver behind a headline. The regression sweep, as a command.

`REGRESSION_SWEEP.md` recorded that 2 of these 7 were silently broken by one
change, and both sat behind headline numbers. That finding was annotated in the
LEDGER as `repro: REGRESSION_SWEEP.md` -- a document, which re-derives nothing.
A sweep whose only reproducer is its own writeup cannot catch the next
regression, which is the exact failure it exists to describe.

    python3 sweep.py            # all drivers
    python3 sweep.py --quick    # skip the ones needing the phone or a server

Exit 1 if any driver is broken. A driver that REFUSES on a safety gate (hot
phone, no external power) is reported DECLINED and does not fail the sweep --
the gate working is not the driver breaking.
"""
import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DECLINED = re.compile(r'gate REFUSED|device is not quiet|REFUSING:|not on external power')
# A THIRD outcome, distinct from both PASS and FAIL: the driver is intact and
# the environment moved out from under it. run_lan.py hit this when the phone
# joined a VPN (tun1, src 10.184.0.5) and left the host subnet. Scoring that as
# FAIL blames the code; scoring it as DECLINED hides that a headline path is
# currently unreproducible. It is its own category and it must be loud.
PRECONDITION = re.compile(r'not on the host subnet|no route to host|connection refused'
                          r'|no devices/emulators')

# (path, args, needs_device). `server.py` is imported by the run_* drivers
# rather than run standalone, so it is exercised as a module import.
DRIVERS = [
    ('harness/bansurface.py', [], False),
    ('harness/canon.py', [], False),
    ('harness/units.py', [], False),
    ('harness/instrument.py', [], False),
    ('harness/edits.py', [], False),
    ('harness/provenance.py', [], False),
    ('harness/kfcheck.py', [], False),
    ('M1_5_shardstore/shardstore.py', [], False),
    ('M1_8_quorum3/test_adjudicate.py', [], False),
    ('M1_8_quorum3/classify.py', [], False),
    ('M1_3_worker/test_preflight.py', [], False),
    ('M1_7_transport/run.py', ['67'], True),
    ('M1_7_transport/run_app.py', ['67'], True),
    ('M1_7_transport/run_lan.py', ['67'], True),
    ('M1_8_quorum3/q3.py', ['--alpha'], True),
]


def run(rel, args, timeout):
    full = os.path.join(HERE, rel)
    if not os.path.exists(full):
        return 'MISSING', 0, ''
    t0 = time.time()
    try:
        p = subprocess.run(['python3', full] + args, cwd=os.path.dirname(full),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', timeout, ''
    tail = (p.stdout + p.stderr)[-800:]
    secs = round(time.time() - t0, 1)
    if p.returncode == 0:
        return 'PASS', secs, tail
    if DECLINED.search(tail):
        return 'DECLINED', secs, tail
    if PRECONDITION.search(tail):
        return 'PRECONDITION', secs, tail
    return f'FAIL(rc={p.returncode})', secs, tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--timeout', type=int, default=600)
    a = ap.parse_args()

    bad, unmet = [], []
    for rel, args, needs_dev in DRIVERS:
        if a.quick and needs_dev:
            print(f'{"SKIPPED":14s}        {rel}')
            continue
        status, secs, tail = run(rel, args, a.timeout)
        print(f'{status:14s} {secs:6}s  {rel} {" ".join(args)}')
        if status == 'PRECONDITION':
            unmet.append(rel)
            for ln in tail.strip().splitlines()[-2:]:
                print(f'                       | {ln[:100]}')
        if status.startswith(('FAIL', 'MISSING', 'TIMEOUT')):
            bad.append(rel)
            for ln in tail.strip().splitlines()[-3:]:
                print(f'                       | {ln[:100]}')
    print(f'\n{len(DRIVERS)} drivers, broken: {bad or "none"}, '
          f'precondition unmet: {unmet or "none"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
