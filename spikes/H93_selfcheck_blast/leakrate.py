#!/usr/bin/env python3
"""H93 · leakrate.py v1 — is the leak a RATE or one draw?

§7 of the spawn brief: *one draw is not a measurement, one point is not a rate.*
So the leak is measured over N runs, and against a CONTROLLED PAIR rather than by
subtracting a separately-measured background (the rule that turned a "59%" into
41% in this repo). ARM A runs the suspect module N times; ARM B runs a swept
module with ZERO temp creations N times, on the same host in the same window.
The difference between the arms is the leak; anything the machine leaks on its
own appears in BOTH arms.

CONTROL C5 (must fire): ARM B's delta must be ~0. Fails if the counter picks up
unrelated system activity, which would make ARM A's number unattributable.
CONTROL C6 (must fire): ARM A's delta must equal N. Fails if the leak is
occasional rather than per-run -- a different and weaker claim, and it would be
reported as such.
"""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
H = os.path.join(ROOT, 'spikes', 'harness')
T = os.environ.get('TMPDIR', '/tmp').rstrip('/')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def bare():
    """mkdtemp() with no prefix -> `tmp` + 8 chars. Counting the SHAPE, because
    the leak carries no marker; the controlled pair is what makes it attributable."""
    try:
        return {n for n in os.listdir(T) if n.startswith('tmp') and len(n) == 11
                and os.path.isdir(os.path.join(T, n))}
    except OSError:
        return set()


def arm(mod, n):
    before = bare()
    for _ in range(n):
        subprocess.run([sys.executable, os.path.join(H, mod), '--selfcheck'],
                       cwd=ROOT, capture_output=True)
    return sorted(bare() - before)


a = arm('retrofit_d6.py', N)
b = arm('idscope.py', N)
print(f'ARM A  retrofit_d6.py x{N}: +{len(a)} leaked dirs  {a}')
print(f'ARM B  idscope.py     x{N}: +{len(b)} leaked dirs  {b}')
print(f'C5 control arm is quiet: {len(b) == 0}   '
      f'(fails if the counter sees unrelated system activity)')
print(f'C6 leak is PER RUN, not occasional: {len(a) == N}   '
      f'(fails if the leak is intermittent; that is a weaker claim and would be said)')
print(f'\nleak = {len(a) - len(b)} dirs per {N} runs. bringup.sh runs the sweep at '
      f'StartInterval 600 => {(len(a)-len(b))/N * 144:.0f} leaked dirs/day.')
for d in a:
    subprocess.run(['rm', '-rf', os.path.join(T, d)])
print(f'cleaned up {len(a)} dirs this probe created.')
