#!/usr/bin/env python3
"""Process reuse is safe for the measured job class -- as a command.

The LEDGER annotated this claim with `repro: .../target/release/soakrun`, a
prebuilt binary. A binary is an artifact, not a reproducer: it cannot re-derive
the number, and if it were rebuilt from a changed tree nothing would say so.

The claim: run one program at many positions inside a SINGLE reused process and
its canonicalised result never drifts.

The control is in the same table and is what makes the claim mean anything: the
RAW hash must differ across those positions. Raw carries hyperon's
process-global variable counter (`$x#24605`), so a reused process is exactly
where drift shows. If raw came back constant, the run would not be exercising
process reuse at all and `canon == 1` would be vacuous.

    python3 soak_check.py [--positions 30]
"""
import argparse
import collections
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SOAK = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                    'target', 'release', 'soakrun')
CORPUS = os.path.join(ROOT, 'spikes', 'S57_hyperon_corpus', 'corpus')

# A data-origin variable is the whole point: it is what carries the counter into
# printed output. A program returning () would be stable no matter how broken
# process reuse was.
PROBE = '(implies (Frog $x) (Green $x))\n!(match &self (implies $p $q) ($p $q))\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--positions', type=int, default=30)
    ap.add_argument('--fuel', default='200000')
    a = ap.parse_args()

    if not os.path.exists(SOAK):
        sys.exit(f'soakrun not built: {SOAK}\n'
                 f'  cargo build --release  in spikes/S15_android_device/fuelrun')

    others = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))[:a.positions]
    with tempfile.TemporaryDirectory() as td:
        probe = os.path.join(td, 'probe.metta')
        with open(probe, 'w') as f:
            f.write(PROBE)
        # Interleave: probe, other, probe, other ... so the probe is evaluated
        # at many different points in one process's history.
        args = []
        for o in others:
            args += [probe, os.path.join(CORPUS, o)]
        args.append(probe)
        r = subprocess.run([SOAK, a.fuel] + args, capture_output=True,
                           text=True, timeout=600)
    if r.returncode != 0:
        sys.exit(f'soakrun failed rc={r.returncode}\n{r.stderr[-800:]}')

    rows = [l.split('\t') for l in r.stdout.splitlines()[1:] if l.strip()]
    probe_rows = [x for x in rows if x[1].endswith('probe.metta')]
    if len(probe_rows) < 3:
        sys.exit(f'only {len(probe_rows)} probe rows -- the interleave did not run')

    raw = collections.Counter(x[2] for x in probe_rows)
    canon = collections.Counter(x[3] for x in probe_rows)
    alpha = collections.Counter(x[4] for x in probe_rows)

    print(f'probe evaluated at {len(probe_rows)} positions in ONE process')
    print(f'  raw   distinct {len(raw):3d}   <- control: process history MUST leak here')
    print(f'  canon distinct {len(canon):3d}   <- the claim')
    print(f'  alpha distinct {len(alpha):3d}')

    bad = []
    if len(raw) < 2:
        bad.append('CONTROL DEAD: raw hash is constant, so this run does not '
                   'exercise process reuse and canon==1 proves nothing')
    if len(canon) != 1:
        bad.append(f'CLAIM BROKEN: canon drifted across positions ({len(canon)} values)')
    if len(alpha) != 1:
        bad.append(f'CLAIM BROKEN: alpha drifted across positions ({len(alpha)} values)')
    for b in bad:
        print('  !! ' + b)
    print('\nprocess reuse: ' + ('SAFE (control live)' if not bad else 'NOT ESTABLISHED'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
