#!/usr/bin/env python3
"""S28 -- does IN-PROCESS concurrency perturb MeTTa results?

`out/LEDGER.md` grades "Co-tenancy does not perturb results" **B** on 8
concurrent *processes*, and marks the in-process case `Untested` while naming
the mechanism it expects to fail:

    "`NEXT_VARIABLE_ID.fetch_add(..., Relaxed)` keeps ids unique but makes
     WHICH thread gets which id scheduling-dependent. Each process starts its
     counter at 1, which is exactly why this passed."

M1.3b answered the SEQUENTIAL case -- many different jobs in one process with a
fresh `Metta` each -- and a sequential run cannot exhibit a scheduling-dependent
property. It matters because the phone runs MeTTa IN-PROCESS (M1.1) and
WorkManager reuses the app process, so the deployed configuration is the
untested one.

THE COMPARISON, and it is the whole design. Running threads and looking for a
diff inside one run cannot work: the process-global counter makes every job's
raw digest position-dependent, so digests differ between positions whether or
not scheduling reaches the output (that is M1.3b's own result, and its control).
What isolates threading is running the SAME command as a FRESH PROCESS several
times and asking whether the run's digest MULTISET is stable across invocations.
A one-thread process has a deterministic counter history, so its multiset must
be identical every time. If the T-thread multiset is not, scheduling reached the
output.

FALSIFIERS, stated in `CHANNEL.md` before this was written:
  F1 (the kill)   raw multiset stable across invocations at T threads => the
                  Relaxed ordering does not reach the output, the row's own
                  stated mechanism is wrong, and B stands unqualified.
  F2 (the scope)  raw varies but canon/alpha stable => in-process concurrency is
                  safe UNDER CANONICALISATION; what dies is the unqualified B,
                  not the co-tenancy claim.
  F3 (no verdict) the 1-thread arm also varies => the instrument has a
                  nondeterminism unrelated to threading; report irreproducibility
                  rather than treating it as a kill.

    python3 s28.py [--threads 4] [--invocations 5] [--others 6]
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify                       # noqa: E402
from provenance import Control                    # noqa: E402

BIN = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                   'target', 'release', 'threadrun')
SOAK = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                    'target', 'release', 'soakrun')
SRC = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun', 'src',
                   'bin', 'threadrun.rs')
CORPUS = os.path.join(ROOT, 'spikes', 'S57_hyperon_corpus', 'corpus')
PROBE = os.path.join(HERE, 'probe.metta')
FUEL = '200000'


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def job_list(n_others):
    """probe, other, probe, other, ... probe -- M1.3b's interleave verbatim,
    so the probe is evaluated at many points in one process's history."""
    others = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))[:n_others]
    args = []
    for o in others:
        args += [PROBE, os.path.join(CORPUS, o)]
    args.append(PROBE)
    return args


def run(binary, argv, timeout=900):
    t0 = time.time()
    r = subprocess.run([binary] + argv, capture_output=True, text=True,
                       timeout=timeout)
    wall = time.time() - t0
    if r.returncode != 0:
        sys.exit('%s failed rc=%d\n%s' % (binary, r.returncode, r.stderr[-800:]))
    return r.stdout, wall


def parse(stdout):
    """-> list of dicts. Header lines start with '#' or 'repeat'."""
    rows = []
    for line in stdout.splitlines():
        if not line.strip() or line.startswith('#') or line.startswith('repeat'):
            continue
        f = line.split('\t')
        rows.append({'repeat': f[0], 'thread': f[1], 'pos': f[2], 'program': f[3],
                     'fuel_used': f[4],
                     # keyed by position, so a fuel count SWAPPING between two
                     # positions is a change; a bare multiset of counts would
                     # hide that.
                     'fuel_at_pos': '%s:%s' % (f[2], f[4]),
                     'raw': f[5], 'canon': f[6], 'alpha': f[7]})
    return rows


def multiset_sig(rows, col):
    """Order-independent signature of one digest column for a whole invocation.

    Sorted, so a scheduling difference that only reorders output does NOT show
    up as a change -- only a difference in the digests THEMSELVES does.
    """
    return hashlib.sha256('\n'.join(sorted(r[col] for r in rows))
                          .encode()).hexdigest()[:16]


def arm(threads, invocations, jobs):
    """Run the same command `invocations` times as SEPARATE processes."""
    sigs = {'raw': [], 'canon': [], 'alpha': [], 'fuel_at_pos': []}
    walls, per_invocation = [], []
    for _ in range(invocations):
        out, wall = run(BIN, [FUEL, str(threads), '1'] + jobs)
        rows = parse(out)
        for col in sigs:
            sigs[col].append(multiset_sig(rows, col))
        walls.append(wall)
        per_invocation.append(rows)
    return {'threads': threads, 'invocations': invocations,
            'job_runs_per_invocation': len(per_invocation[0]),
            'sigs': sigs,
            'distinct': {c: len(set(v)) for c, v in sigs.items()},
            'wall_median': sorted(walls)[len(walls) // 2],
            'walls': [round(w, 2) for w in walls],
            'rows': per_invocation}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--invocations', type=int, default=5)
    ap.add_argument('--others', type=int, default=6)
    a = ap.parse_args()

    for p in (BIN, SOAK):
        if not os.path.exists(p):
            sys.exit('not built: %s\n  cargo build --release  in '
                     'spikes/S15_android_device/fuelrun' % p)

    jobs = job_list(a.others)
    bin_sha = sha256_file(BIN)

    # ---- C2: the intervention size, printed before any verdict. -------------
    print('# S28 threads=%d invocations=%d jobs_per_invocation=%d '
          'job_runs_1thread=%d job_runs_%dthread=%d fuel=%s'
          % (a.threads, a.invocations, len(jobs), len(jobs), a.threads,
             len(jobs) * a.threads, FUEL))
    print('# threadrun sha256=%s' % bin_sha)

    # ---- the two arms, same binary, argv differing only in the thread count --
    one = arm(1, a.invocations, jobs)
    many = arm(a.threads, a.invocations, jobs)

    # ---- C0: this binary must reproduce soakrun's digests exactly at 1 thread.
    # Keyed on POSITION, not on print order: it compares every digest of every
    # job exactly, and it does not go red merely because a binary changed how it
    # sorts its table. v1 compared ordered lists and went red for exactly that
    # reason -- threadrun v1 sorted a numeric field as a string.
    soak_out, _ = run(SOAK, [FUEL] + jobs)
    soak_cols = {l.split('\t')[0]: l.split('\t')[2:5]
                 for l in soak_out.splitlines()[1:] if l.strip()}
    thr_cols = {r['pos']: [r['raw'], r['canon'], r['alpha']]
                for r in one['rows'][0]}
    c0_match = soak_cols == thr_cols

    # ---- C3: does the process-global counter reach printed output at all? ----
    # M1.3b's CONTROL DEAD, re-derived here. Within ONE 1-thread invocation the
    # probe sits at many positions; its raw digest must differ across them. If it
    # does not, nothing downstream means anything.
    probe_raw = [r['raw'] for r in one['rows'][0] if r['program'] == 'probe.metta']
    probe_canon = [r['canon'] for r in one['rows'][0] if r['program'] == 'probe.metta']

    # ---- C4: were the threads concurrent, or serialised by a global lock? ----
    # If hyperon serialises, stability is explained by serialisation and NOT by
    # safety -- evidence vs conclusion. Serialised => wall_T ~ T * wall_1.
    speedup = one['wall_median'] * a.threads / many['wall_median'] \
        if many['wall_median'] else 0.0

    # ---- effect size, because a verdict is not a magnitude -------------------
    # "5 of 5 multisets differ" does not say whether ONE digest moved or all of
    # them. Against invocation 0, how many of the N-thread run's digests recur?
    def overlap(runs, col):
        base = collections.Counter(r[col] for r in runs[0])
        out = []
        for rows in runs[1:]:
            other = collections.Counter(r[col] for r in rows)
            out.append(sum((base & other).values()))
        return {'total_per_invocation': len(runs[0]), 'kept_vs_invocation_0': out}

    effect = {c: overlap(many['rows'], c) for c in ('raw', 'canon', 'alpha')}

    out = {
        'threads': a.threads, 'invocations': a.invocations,
        'jobs_per_invocation': len(jobs),
        'threadrun_sha256': bin_sha,
        'arm_1_thread': {k: one[k] for k in
                         ('distinct', 'sigs', 'wall_median', 'walls',
                          'job_runs_per_invocation')},
        'arm_n_thread': {k: many[k] for k in
                         ('distinct', 'sigs', 'wall_median', 'walls',
                          'job_runs_per_invocation')},
        'c0_soakrun_identical': c0_match,
        'probe_positions': len(probe_raw),
        'probe_raw_distinct': len(set(probe_raw)),
        'probe_canon_distinct': len(set(probe_canon)),
        'parallel_speedup_vs_serialised': round(speedup, 2),
        'effect_size_n_thread': effect,
    }

    # ---- the verdict, read off the falsifiers stated before the run ----------
    if one['distinct']['raw'] > 1:
        verdict = 'F3 FIRED -- NO VERDICT'                    # instrument noise
    elif many['distinct']['raw'] > 1:
        verdict = ('F2' if many['distinct']['canon'] == 1
                   and many['distinct']['alpha'] == 1
                   else 'RAW AND CANON BOTH VARY')
    else:
        verdict = 'F1 FIRED -- the row\'s stated mechanism does not reach output'
    out['verdict'] = verdict

    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    # ---- controls -----------------------------------------------------------
    C = []

    c = Control(
        'C0_instrument_reproduces_soakrun',
        'threadrun at 1 thread must reproduce soakrun\'s digest columns byte '
        'for byte on the same argv, or it is a DIFFERENT instrument and the '
        'comparison to M1.3b\'s published result is not a comparison at all',
        null_must_contain='canon/canon_alpha copied rather than reimplemented, '
                          'so a drift in either shows here',
        can_fail_because='any of the three digest columns differs on any row')
    c.observe(c0_match,
              {'rows_compared': len(soak_cols), 'identical': c0_match,
               'mismatched_positions': sorted(
                   p for p in set(soak_cols) | set(thr_cols)
                   if soak_cols.get(p) != thr_cols.get(p))})
    C.append(c)

    c = Control(
        'C1_same_build_both_arms',
        'the two arms must be the same binary with argv differing ONLY in the '
        'thread count, so the comparison is threads-vs-no-threads and not '
        'binary-vs-binary (A24: two builds of the same source are not the same '
        'artefact)',
        null_must_contain='a rebuild between arms, a different job list, or a '
                          'binary older than its own source (A24)',
        can_fail_because='the binary is rebuilt mid-run, the two arms are handed '
                         'different program lists, or threadrun predates '
                         'threadrun.rs')
    fresh = os.path.getmtime(BIN) >= os.path.getmtime(SRC)
    c.observe(fresh
              and one['job_runs_per_invocation'] == len(jobs)
              and many['job_runs_per_invocation'] == len(jobs) * a.threads,
              {'binary_sha256': bin_sha,
               'binary_newer_than_source': fresh,
               'argv_delta': 'threads %d -> %d' % (1, a.threads),
               'jobs_1': one['job_runs_per_invocation'],
               'jobs_n': many['job_runs_per_invocation']})
    C.append(c)

    c = Control(
        'C2_intervention_is_not_a_no_op',
        'an unchanged digest under a SMALL intervention is a disconnected wire. '
        'The N-thread arm must actually run N times the job-runs of the 1-thread '
        'arm inside one process',
        null_must_contain='threads that never spawned, which would make the '
                          'job-run counts equal',
        can_fail_because='job_runs_n / job_runs_1 != threads')
    c.observe(many['job_runs_per_invocation']
              == one['job_runs_per_invocation'] * a.threads,
              {'job_runs_1': one['job_runs_per_invocation'],
               'job_runs_n': many['job_runs_per_invocation'],
               'threads': a.threads})
    C.append(c)

    c = Control(
        'C3_counter_reaches_printed_output',
        'M1.3b\'s CONTROL DEAD, re-derived: the process-global variable counter '
        'must leak into the RAW digest, or every stability result below is '
        'vacuous -- a run that cannot show drift proves nothing by not showing it',
        null_must_contain='a probe whose result is ground and carries no '
                          'data-origin variable, which would be stable however '
                          'broken process reuse was',
        can_fail_because='the probe\'s raw digest is constant across its '
                         'positions in one process')
    c.observe(len(set(probe_raw)) > 1,
              {'positions': len(probe_raw), 'raw_distinct': len(set(probe_raw)),
               'canon_distinct': len(set(probe_canon))})
    C.append(c)

    c = Control(
        'C5_fuel_is_the_quantity_that_decides_severity',
        '`fuel_used` is IN M1.8\'s agreement key `(status, fuel_used, '
        'sorted_hash)`. If fuel moves under concurrency the divergence is in the '
        'computation itself and no canonicalisation can repair it; if only the '
        'variable ids move, canon does. Measured as its own column rather than '
        'inferred from the fact that `canon` leaves the `fuel=` line alone',
        null_must_contain='a fuel count differing at any position between any '
                          'two invocations of the N-thread arm',
        can_fail_because='the fuel_at_pos multiset is not identical across all '
                         'invocations')
    c.observe(many['distinct']['fuel_at_pos'] == 1,
              {'distinct_fuel_signatures_n_thread':
                   many['distinct']['fuel_at_pos'],
               'distinct_fuel_signatures_1_thread':
                   one['distinct']['fuel_at_pos'],
               'invocations': a.invocations})
    C.append(c)

    c = Control(
        'C4_threads_are_not_serialised',
        'if hyperon holds a global lock, the threads run one at a time and '
        'stability is explained by SERIALISATION rather than by safety. That is '
        'the evidence-vs-conclusion split: a serialised run cannot exhibit the '
        'scheduling dependence under test, so it would make a negative result '
        'unattributable',
        null_must_contain='wall_N ~= N * wall_1, the serialised signature',
        can_fail_because='parallel speedup at or below 1.2x, i.e. the N-thread '
                         'arm took about N times as long as the 1-thread arm')
    c.observe(speedup > 1.2,
              {'wall_1_median_s': round(one['wall_median'], 2),
               'wall_n_median_s': round(many['wall_median'], 2),
               'threads': a.threads, 'speedup_vs_serialised': round(speedup, 2)})
    C.append(c)

    # ---- report -------------------------------------------------------------
    print('\n1 thread : distinct multisets over %d invocations  raw=%d canon=%d '
          'alpha=%d   wall_median=%.1fs'
          % (a.invocations, one['distinct']['raw'], one['distinct']['canon'],
             one['distinct']['alpha'], one['wall_median']))
    print('%d threads: distinct multisets over %d invocations  raw=%d canon=%d '
          'alpha=%d   wall_median=%.1fs'
          % (a.threads, a.invocations, many['distinct']['raw'],
             many['distinct']['canon'], many['distinct']['alpha'],
             many['wall_median']))
    print('effect size at %d threads, digests recurring vs invocation 0 '
          '(of %d): raw %s  canon %s'
          % (a.threads, effect['raw']['total_per_invocation'],
             effect['raw']['kept_vs_invocation_0'],
             effect['canon']['kept_vs_invocation_0']))
    print('fuel_used at %d threads: distinct signatures over %d invocations = %d '
          '(1 means every fuel count identical at every position)'
          % (a.threads, a.invocations, many['distinct']['fuel_at_pos']))
    print('C0 soakrun-identical=%s  C3 probe raw distinct=%d/%d  '
          'C4 speedup=%.2fx' % (c0_match, len(set(probe_raw)), len(probe_raw),
                                speedup))
    print('VERDICT: %s' % verdict)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun', 'src'),
              os.path.join(ROOT, 'spikes', 'M1_3b_process_reuse')],
        artifacts=[os.path.join(HERE, 'result.json')],
        controls=C,
        falsifier='a stable RAW digest multiset across repeated %d-thread '
                  'invocations, which would show the Relaxed variable counter '
                  'never reaches printed output and leave the LEDGER row\'s B '
                  'standing unqualified' % a.threads)
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
