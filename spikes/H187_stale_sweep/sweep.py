#!/usr/bin/env python3
"""H187 — how many certified spikes would REFUSE if `certify` ran on them today.

RUN:  python3 spikes/H187_stale_sweep/sweep.py

NOTHING IS RE-EXECUTED AND NO RULE IS REIMPLEMENTED. `stalecheck.py` calls
`provenance`'s own `newest_source_mtime` / `artifact_time` / `_newest_file_mtime`
and applies `record()`'s two-clock rule; this file drives it, decomposes the
result, and certifies the measurement. Re-running 145 spikes would take hours,
execute six lanes' arbitrary code, and OVERWRITE their `provenance.json` -- an
instrument that destroys the record it measures is disqualified before it starts.

THE COUNTS MOVE WHILE THIS RUNS. Four lanes commit continuously; the scan took
31s and the spike census changed by one between two runs an hour apart. So the
HEAD sha and the wall clock are recorded WITH the counts, and every number here
is "at that sha", never "the number".
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))

from kfcheck import certify, Control                      # noqa: E402
from provenance import Falsifier                          # noqa: E402
import stalecheck as sc                                   # noqa: E402


def git(*a, cwd=ROOT):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True,
                          text=True).stdout.strip()


def decompose(rows):
    """Split the STALE set by the property that decides what it MEANS.

    NOT a taxonomy and NOT a threshold -- both were rejected in stalecheck v2's
    rationale block. The split here is over facts already printed on each row:
    the dep's commit count in the last 24h, and exact SELF (realpath equality).
    A reader who disagrees with the buckets can recompute them from the detail
    string, which is why the raw detail is persisted alongside.
    """
    out = {'self': [], 'churny': [], 'quiet': [], 'unknown': []}
    for name, state, detail in rows:
        if state != sc.STALE:
            continue
        churn = detail.split('[dep churn: ')[-1].rstrip(']')
        if 'SELF' in churn:
            out['self'].append((name, detail))
        elif churn.startswith('?'):
            out['unknown'].append((name, detail))
        else:
            n = int(churn.split()[0])
            (out['churny'] if n >= 3 else out['quiet']).append((name, detail))
    return out


def main():
    t0 = time.time()
    head = git('rev-parse', 'HEAD')
    stamp = int(t0)

    rows, unscanned = sc.scan(ROOT)
    assert unscanned == 0, 'unbounded scan must reach every dir'
    stale = [r for r in rows if r[1] == sc.STALE]
    und = [r for r in rows if r[1] == sc.UNDECIDABLE]
    clean = [r for r in rows if r[1] == sc.CLEAN]
    buckets = decompose(rows)

    # The denominator, and it is NOT the spike count. 305 directories live under
    # spikes/; only those carrying a provenance.json were ever certified at all.
    spike_dirs = [d for d in os.listdir(os.path.join(ROOT, 'spikes'))
                  if os.path.isdir(os.path.join(ROOT, 'spikes', d))]

    # ---- C1: this recomputation agrees with a REAL certify() run, BOTH ways --
    # Delegated to stalecheck's own --selfcheck, which builds two synthetic
    # spikes, calls kfcheck.certify() on them for real, and compares. Driven as a
    # subprocess so the arm exercises the shipped entry point rather than an
    # import of the same functions.
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'spikes', 'harness',
                                                     'stalecheck.py'), '--selfcheck'],
                       capture_output=True, text=True)
    c1 = Control('agreement_with_real_certify',
                 'a recomputed verdict never compared against the thing it '
                 'recomputes is an assertion, not a measurement (A15)',
                 null_must_contain='the CLEAN arm -- a rule that always answered '
                                   'STALE would satisfy the stale arm on its own',
                 can_fail_because='certify() and stalecheck.verdict() return '
                                  'different states for the same synthetic pair')
    c1.observe(r.returncode == 0, [r.returncode, r.stdout.strip().splitlines()[-1]],
               'stalecheck --selfcheck, 6 arms incl. two real certify() runs')

    # ---- C2: the mutation arm. Disabling HALF the two-clock rule must turn the
    # selfcheck red. This is here because it did NOT, in v1: every arm stayed
    # green with the second opinion deleted, so that half was untested.
    mut = os.path.join(ROOT, 'spikes', 'harness', '.h187_mutant.py')
    src = open(os.path.join(ROOT, 'spikes', 'harness', 'stalecheck.py'),
               encoding='utf-8').read()
    needle = '            if src_mt and int(os.path.getmtime(a)) >= src_mt:'
    assert needle in src, 'mutation anchor absent -- a silent no-op mutation ' \
                          'would report the control fired when nothing changed'
    open(mut, 'w').write(src.replace(needle, '            if False:'))
    try:
        rm = subprocess.run([sys.executable, mut, '--selfcheck'],
                            capture_output=True, text=True)
    finally:
        os.unlink(mut)
    c2 = Control('mutation_kills_selfcheck',
                 'v1 shipped with the mtime second opinion -- half the rule -- '
                 'unreached by any arm; deleting it left every check green',
                 null_must_contain='a green mutant, which is exactly what v1 '
                                   'produced and is how this control was earned',
                 can_fail_because='the synthetic cases never reach the second '
                                  'clock, so removing it changes no verdict')
    c2.observe(rm.returncode != 0, [rm.returncode],
               'second-opinion clause replaced with `if False:`')

    # ---- C3: a record missing its inputs is UNDECIDABLE, never CLEAN (H30) ---
    c3 = Control('undecidable_is_not_clean',
                 'scoring an unreconstructable record as clean is how a narrowed '
                 'scope reads as coverage',
                 null_must_contain='a run in which no record is missing inputs, '
                                   'which would make this control vacuous',
                 can_fail_because='no provenance.json on disk lacks source_mtimes '
                                  'or artifact paths')
    c3.observe(len(und) > 0, [len(und)] + [n for n, _s, _d in und][:5],
               'records that cannot be reconstructed at all')

    # ---- Falsifiers, preregistered in CHANNEL.md before this ran --------------
    f1 = Falsifier('f1_class_is_theoretical',
                   'if zero spikes would refuse today the class is theoretical '
                   'and H187 closes WRONG',
                   fires_when='every provenance.json on disk is fresher than its '
                              'declared deps, i.e. the STALE count is 0',
                   null_must_contain='a tree in which every certified spike is '
                                     'fresh, which is the state the row denies')
    f1.observe(len(stale) == 0, [len(stale)], 'STALE count; firing kills the row')

    f2 = Falsifier('f2_instrument_disagrees',
                   'if this recomputation disagrees with a real certify run, no '
                   'count it produces means anything',
                   fires_when='certify() and stalecheck.verdict() return '
                              'different states for the same synthetic input',
                   null_must_contain='a disagreement, which C1 is built to '
                                     'surface in both directions')
    f2.observe(r.returncode != 0, [r.returncode], 'inverse of C1; firing voids the row')

    f3 = Falsifier('f3_undecidable_exists',
                   'records that cannot be reconstructed are counted and NAMED '
                   'rather than silently scored clean',
                   fires_when='at least one provenance.json lacks source_mtimes '
                              'or artifact paths and cannot be checked at all',
                   null_must_contain='zero undecidable records, i.e. every spike '
                                     'declaring deps and artifact paths')
    f3.observe(len(und) > 0, [len(und)], 'FIRED = these records are uncheckable')

    result = {
        'head': head, 'stamp': stamp, 'scan_seconds': round(time.time() - t0, 1),
        'spike_dirs': len(spike_dirs),
        'with_provenance': len(rows),
        'clean': len(clean), 'stale': len(stale), 'undecidable': len(und),
        'stale_by_mode': {k: [{'spike': n, 'detail': d} for n, d in v]
                          for k, v in buckets.items()},
        'undecidable_named': [{'spike': n, 'why': d} for n, _s, d in und],
        'note': ('churn thresholds in stale_by_mode are a READING AID computed '
                 'from the detail string, not a rule: 3+ commits/24h is where '
                 'this tree separates spikes/harness (20) and kitchen (3) from '
                 'everything else (0-2). The raw detail is kept so a reader can '
                 'disagree and recompute.'),
    }
    json.dump(result, open(os.path.join(HERE, 'sweep.json'), 'w'), indent=2)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'harness')],
        artifacts=[os.path.join(HERE, 'sweep.json')],
        controls=[c1, c2, c3],
        falsifiers=[f1, f2, f3],
        captures=[('head', head)],
        falsifier='zero spikes would refuse if certify ran today (F1)',
        allow_dirty=True,
        note='measurement only; no spike is re-executed and none is repaired here')

    print(f'H187 at {head[:8]}: {len(spike_dirs)} spike dirs, {len(rows)} certified, '
          f'{len(clean)} CLEAN / {len(stale)} STALE / {len(und)} UNDECIDABLE')
    for k in ('quiet', 'churny', 'self', 'unknown'):
        print(f'  stale/{k:8s} {len(buckets[k])}')
    print(f'certify ok: {ok}')
    for p in problems:
        print('  PROBLEM:', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
