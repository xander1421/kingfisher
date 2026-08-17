#!/usr/bin/env python3
"""Does the locality/imbalance tension S61 predicted appear at low coverage?

S61's 102x imbalance was at coverage ~5 holders in a 1000-device fleet. The
first fleet run used prefill 25% on 8 devices -- coverage 2 of 8, which is a
much denser regime. Sweeping prefill DOWN is sweeping coverage down.
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location('fleet', os.path.join(HERE, 'fleet.py'))

class A:  # argparse stand-in
    corpus = os.path.join(HERE, '..', 'S57_hyperon_corpus', 'corpus')
    quorum = 3; cap_mb = 64; fuel = 2000000; limit = 0
    fleet = 8; prefill = 0.25; seed = 0xC0FFEE

src = open(os.path.join(HERE, 'fleet.py')).read().split('def main()')[0]
mod = {'__name__': 'fleet_lib', '__file__': os.path.join(HERE, 'fleet.py')}
exec(compile(src, 'fleet.py', 'exec'), mod)

import bansurface
progs = sorted(f for f in os.listdir(A.corpus) if f.endswith('.metta'))
progs = [p for p in progs
         if bansurface.admit(open(os.path.join(A.corpus, p), 'rb').read())[0]][:24]

print(f"{'fleet':>5} {'prefill':>8} {'coverage':>9}  "
      f"{'random KiB':>10} {'pure KiB':>9} {'save%':>6}  "
      f"{'imb rand':>8} {'imb pure':>8} {'imb pure+lb':>11}")
out = []
for fleet in (8, 16, 32):
    for prefill in (0.5, 0.25, 0.10, 0.05):
        A.fleet, A.prefill = fleet, prefill
        r = {p: mod['run'](p, progs, A.corpus, A)
             for p in ('random', 'locality_pure', 'locality_lb')}
        cov = fleet * prefill
        save = 100*(r['random']['fetch_bytes'] - r['locality_pure']['fetch_bytes']) \
               / max(r['random']['fetch_bytes'], 1)
        row = dict(fleet=fleet, prefill=prefill, coverage=round(cov, 2), save=round(save, 1),
                   imb_random=round(r['random']['imbalance'], 2),
                   imb_pure=round(r['locality_pure']['imbalance'], 2),
                   imb_lb=round(r['locality_lb']['imbalance'], 2),
                   unanimous=r['locality_pure']['unanimous'], n=len(progs))
        out.append(row)
        print(f"{fleet:>5} {prefill:>8.0%} {cov:>9.1f}  "
              f"{r['random']['fetch_bytes']/1024:>10.1f} "
              f"{r['locality_pure']['fetch_bytes']/1024:>9.1f} {save:>5.1f}%  "
              f"{row['imb_random']:>8.1f} {row['imb_pure']:>8.1f} {row['imb_lb']:>11.1f}")
json.dump(out, open(os.path.join(HERE, 'sweep.json'), 'w'), indent=1)
print('\n-> sweep.json')
