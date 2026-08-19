#!/usr/bin/env python3
"""stalecheck.py v2 — H187. Which certified spikes would REFUSE if re-run today.

THE DEFECT MEASURED
-------------------
`certify` runs when a lane EXECUTES a spike. A finished spike is never executed
again, so a green result rots silently the moment a dependency moves. Found by
re-running W5 on a gate that had lifted: it had been refusing

    STALE ARTIFACT epoch_bisect.py predates W2_witnessed_trie source by 50.3h

for two days, with nobody informed. `kitchen/test_*.py` cannot see it -- those
re-assert a recorded `result.json` rather than re-deriving it, so they stay green
straight over the rot. The queue's DONE rows are this fleet's evidence base and
their freshness was unmeasured.

WHY THIS DOES NOT RE-EXECUTE ANYTHING, AND DOES NOT REIMPLEMENT THE RULE
------------------------------------------------------------------------
Re-running 262 spikes would take hours, execute six lanes' arbitrary code, and
OVERWRITE their `provenance.json` -- that last one is disqualifying on its own:
an instrument that destroys the record it measures is the M17 defect.

So this reads what is already on disk and calls `provenance`'s OWN helpers:

    newest_source_mtime(dep, exclude=...)   the staleness floor
    artifact_time(path)                     the artifact, on the SAME clock

and applies `record()`'s two-clock rule verbatim -- commit clock first, then the
mtime second opinion, stale only if BOTH agree. That measures `certify`'s
verdict rather than a rule of mine. Both helpers are module-level and pure.

UNDECIDABLE IS ITS OWN STATE AND IS NEVER SCORED CLEAN
-------------------------------------------------------
A `provenance.json` missing `source_mtimes` or artifact paths cannot be
reconstructed. H30: a missing input REFUSES rather than degrading to a clean
verdict, and reporting those as green is exactly how a narrowed scope reads as
coverage.

    python3 stalecheck.py             report; exit 1 if any spike would refuse
    python3 stalecheck.py --selfcheck validate the recomputation both directions

==== v2, 2026-08-19, ATOM-3 — three defects removed, all in v1, all mine ======

**D1 — v1 PUBLISHED A BARE TOTAL, AND THE TOTAL IS THE WRONG-ATTRIBUTION
FAILURE.** v1's first real run said `27 STALE` and stopped there. Measured
afterwards, that 27 decomposes into modes that do not mean the same thing:

  * 10 are stale against a directory this fleet EDITS CONTINUOUSLY --
    `spikes/harness` took **20 commits in 24h**, four lanes, several within
    minutes of each other. Those spikes re-rot inside the hour, so "the owner
    re-runs it" clears nothing durable. Not rot: dep granularity.
  * 4 are stale against their OWN directory, because a SECOND experiment was
    added beside the first (`S77_proof_bytes/attack.py` at 14:06 against
    `probe_out.txt` at 12:39). Not rot either.
  * 2 are stale against a 500k-line upstream clone under `elders/`.
  * 11 are the W5 shape -- a genuinely separate dep whose source moved.

Only the last mode means what the refusal text says. Reporting "27 certified
results have rotted" would be `CLAUDE.md`'s second unmechanisable failure --
every figure correct, pointing at the wrong site.

**NO TAXONOMY, NO THRESHOLD, NO NAME LIST.** The fix is not a classifier: any
cutoff between "live" and "static" is a knob nobody measured (G97's own
finding), and a hardcoded `harness|kitchen` list is a scope that narrows itself
green the next time someone adds a shared directory (H26b). v2 attaches the
MEASUREMENT to each row instead -- the dep's commit count over the last 24h,
and an exact `SELF` marker (realpath equality, no knob). The reader sees
`<- spikes/harness [20 commits/24h]` beside `<- W2_witnessed_trie [0/24h]` and
the decomposition needs no defending.

**D2 — THE ONLY AGREEMENT ARM WAS A SPIKE ANOTHER LANE CAN EDIT.** v1 validated
the recomputation against W5's real `certify ok=True`. That arm fires when
somebody edits `W2_witnessed_trie` -- which says nothing whatever about whether
THIS instrument computes `certify`'s rule correctly. A control that fires for a
reason unrelated to the thing it guards is A15, and `selfcheckall.py`'s own
header records the cost: `demo8.py --selfcheck` sat exiting 1 for days because
its positive control depended on a live spike directory.

v2 runs **real `kfcheck.certify()`** on a synthetic spike in a tempdir, both
directions, and asserts this module agrees with it. That is the agreement test
the row's F2 actually asked for, it is deterministic, and it validates against
`certify` itself rather than against the same two helpers this file already
calls. The W5 arm is KEPT and DEMOTED to a reported observation with the reason
stated -- not deleted, because it is still the one real-tree datapoint.

**D3 — v1 HAD NO CALL SITE.** H186 closed one cycle before this one on exactly
that: a check shipped where no automatic path invokes it. `selfcheckall.py`
discovers every module and runs `--selfcheck`, which judges the CHECKER; the
SCAN mode -- the one that judges the tree -- is invoked automatically for
exactly five modules (`pre-commit.hook`'s CHECKS) plus `idscope.py` in
`bringup.sh`. v2 is wired into `bringup.sh` as a REPORTING step beside
`idscope.py`: not the pre-commit gate (one lane's stale spike must not refuse
every other lane's commits -- `pre-commit.hook` v2's F2 / H72) and not gating
inside bringup (a failing report must never stop a lane launching).

Enforced by `python3 stalecheck.py --selfcheck` (5 arms) and by
`sh spikes/H187_stale_sweep/check.sh`.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

from provenance import newest_source_mtime, artifact_time, _newest_file_mtime  # noqa: E402

STALE, CLEAN, UNDECIDABLE = 'STALE', 'CLEAN', 'UNDECIDABLE'


def churn_24h(dep):
    """Commits touching this dep dir in the last 24h, in ITS OWN repo.

    `cwd=dep` rather than a path relative to ROOT, because `elders/` holds
    separate clones and a dep there is invisible to this repo's git. Returns
    None when git cannot answer, which prints as `?` and never as `0` -- an
    unanswerable question scored as "quiet" is the H30 shape.
    """
    try:
        out = subprocess.run(['git', 'log', '--since=24 hours ago', '--format=%h',
                              '--', '.'], cwd=dep, capture_output=True, text=True,
                             timeout=20)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return len([x for x in out.stdout.split() if x])


def verdict(prov_path):
    """(state, detail, dep) for one spike, by record()'s own two-clock rule."""
    try:
        prov = json.load(open(prov_path, encoding='utf-8'))
    except Exception as e:
        return UNDECIDABLE, f'unreadable provenance.json: {e}', None

    spike_dir = os.path.dirname(os.path.abspath(prov_path))

    def _abs(p):
        # `certify(artifacts=['epoch_bisect.py', ...])` is legal and common, so a
        # recorded path may be RELATIVE TO THE SPIKE DIR. Resolving it against the
        # caller's cwd instead scored W5 -- the one spike whose real verdict I
        # know -- as UNDECIDABLE. Caught by the agreement arm of --selfcheck,
        # which is the arm that exists so a recomputation cannot drift from the
        # thing it recomputes.
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(spike_dir, p))

    deps = [_abs(d) for d in (prov.get('source_mtimes') or {}).keys()]
    arts = [_abs(a['path']) for a in (prov.get('artifacts') or []) if a.get('path')]
    if not deps:
        # Declaring no deps is itself a `record()` problem, not a clean bill --
        # but it is that spike's finding, not staleness. Report separately.
        return UNDECIDABLE, 'no deps recorded in source_mtimes (staleness never applied)', None
    if not arts:
        return UNDECIDABLE, 'no artifact paths recorded', None

    missing = [p for p in arts if not os.path.exists(p)] + \
              [d for d in deps if not os.path.isdir(d)]
    if missing:
        return UNDECIDABLE, f'recorded path absent now: {os.path.basename(missing[0])}', None

    excl = list(arts) + [os.path.join(os.path.dirname(prov_path), 'provenance.json')]
    worst = None
    for d in deps:
        src_ts, src_file = newest_source_mtime(d, exclude=excl)
        if not src_ts:
            continue
        for a in arts:
            a_ts, _clock = artifact_time(a)
            if not a_ts or a_ts >= src_ts:
                continue
            # SECOND OPINION on ONE clock, exactly as record() does: not stale if
            # the artifact's mtime is at or past the newest source mtime.
            src_mt = _newest_file_mtime(d, exclude=excl)
            if src_mt and int(os.path.getmtime(a)) >= src_mt:
                continue
            age = (src_ts - a_ts) / 3600.0
            if worst is None or age > worst[0]:
                worst = (age, os.path.basename(a), d, src_file)
    if worst:
        _age, _art, dep, _src = worst
        # SELF is exact -- realpath equality, not a name match and not a knob.
        self_dep = os.path.realpath(dep) == os.path.realpath(spike_dir)
        n = churn_24h(dep)
        churn = '?' if n is None else f'{n}'
        tag = ' SELF' if self_dep else ''
        return (STALE,
                f'{worst[1]} predates {os.path.basename(dep.rstrip("/"))} source by '
                f'{worst[0]:.1f}h (newest: {worst[3]}) '
                f'[dep churn: {churn} commits/24h{tag}]',
                dep)
    return CLEAN, '', None


def scan(root, max_seconds=None):
    """(rows, truncated). A full scan is ~30s of git calls over ~145 records.

    BOUNDED because `bringup.sh` runs this under launchd every 600s and a git
    call that blocks would wedge the fleet reconciler -- `selfcheckall.py`'s
    preregistered F3, and `timeout(1)` does not exist on this host. A truncated
    scan is reported as PARTIAL and exits non-zero: fewer stale rows than exist
    is not better news, and a short scan that prints a clean bill is the H30
    shape.
    """
    import time
    out = []
    deadline = None if max_seconds is None else time.time() + max_seconds
    spikes = os.path.join(root, 'spikes')
    names = sorted(os.listdir(spikes))
    for i, d in enumerate(names):
        if deadline and time.time() > deadline:
            return out, (len(names) - i)
        p = os.path.join(spikes, d, 'provenance.json')
        if os.path.isfile(p):
            out.append((d,) + verdict(p)[:2])
    return out, 0


def main():
    budget = None
    for a in sys.argv[1:]:
        if a.startswith('--max-seconds='):
            budget = float(a.split('=', 1)[1])
    rows, unscanned = scan(ROOT, max_seconds=budget)
    stale = [r for r in rows if r[1] == STALE]
    und = [r for r in rows if r[1] == UNDECIDABLE]
    clean = [r for r in rows if r[1] == CLEAN]

    for name, state, detail in stale:
        print(f'  STALE        {name}: {detail}')
    for name, state, detail in und:
        print(f'  UNDECIDABLE  {name}: {detail}')

    print(f'\nstalecheck: {len(rows)} spike(s) with a provenance.json · '
          f'{len(clean)} CLEAN · {len(stale)} STALE · {len(und)} UNDECIDABLE')
    if not rows:
        print('REFUSE: no provenance.json found at all -- reporting 0 stale from an '
              'empty scan is the H30 shape.')
        return 2
    if unscanned:
        print(f'PARTIAL SCAN: {unscanned} spike dir(s) not reached inside the time '
              f'budget. This count is a FLOOR, not a total, and is not a clean bill.')
        return 2
    if stale:
        print('\nA certified result whose dependency has moved is not certified. These\n'
              'would REFUSE if re-run, and nothing re-runs them. Owners, not me (H187).\n'
              'READ THE CHURN COLUMN BEFORE QUOTING THE TOTAL: a dep committed many\n'
              'times per day re-rots within the hour, so that row is dep granularity\n'
              'and not a rotted result. Only a quiet dep means what the message says.')
        return 1
    return 0


def _synthetic(tmp, stale_artifact):
    """A real two-repo spike/dep pair on disk. Returns (spike_dir, artifact)."""
    dep = os.path.join(tmp, 'dep')
    spk = os.path.join(tmp, 'spk')
    os.makedirs(dep, exist_ok=True)
    os.makedirs(spk, exist_ok=True)
    for d in (dep, spk):
        if not os.path.isdir(os.path.join(d, '.git')):
            subprocess.run(['git', 'init', '-q'], cwd=d)
            subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=d)
            subprocess.run(['git', 'config', 'user.name', 't'], cwd=d)
    art = os.path.join(spk, 'out.json')
    if not os.path.exists(art):
        open(art, 'w').write('{}')
        src = os.path.join(dep, 'src.py')
        open(src, 'w').write('x = 1\n')
        subprocess.run(['git', 'add', 'src.py'], cwd=dep)
        subprocess.run(['git', 'commit', '-qm', 'x'], cwd=dep)
    os.utime(art, (1_600_000_000, 1_600_000_000) if stale_artifact else None)
    return dep, spk, art


def selfcheck():
    """Validate the RECOMPUTATION against a real certify run, both directions.

    A recomputed verdict that has never been checked against the thing it claims
    to recompute is an assertion, not a measurement (A15).
    """
    import tempfile
    ok = True

    # DIRECTION 1: a synthetic spike whose artifact is older than its dep source
    # must come out STALE. Built with real git repos so artifact_time() and
    # newest_source_mtime() take their normal paths rather than a stub.
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, 'spikes')) as tmp:
        dep, spk, art = _synthetic(tmp, stale_artifact=True)
        prov = os.path.join(spk, 'provenance.json')
        json.dump({'source_mtimes': {dep: {}}, 'artifacts': [{'path': art}]},
                  open(prov, 'w'))
        state, detail, _ = verdict(prov)
        if state != STALE:
            print(f'SELFCHECK FAILED: a 2020 artifact against a fresh dep must be '
                  f'STALE, got {state} ({detail})')
            ok = False

        # DIRECTION 2: touch the artifact past the source -> the mtime second
        # opinion clears it. The REFUSING arm and the PASSING arm both exercised.
        os.utime(art, None)
        state, _d, _ = verdict(prov)
        if state != CLEAN:
            print(f'SELFCHECK FAILED: a regenerated artifact must clear, got {state}')
            ok = False

        # DIRECTION 3: missing inputs are UNDECIDABLE, never CLEAN (H30)
        json.dump({'artifacts': [{'path': art}]}, open(prov, 'w'))
        if verdict(prov)[0] != UNDECIDABLE:
            print('SELFCHECK FAILED: no recorded deps must be UNDECIDABLE, not CLEAN')
            ok = False

    # DIRECTION 2b (v2) — THE SECOND OPINION, WHICH NOTHING ELSE HERE REACHES.
    # Found by mutation: deleting the `src_mt`/`getmtime` clause -- half of the
    # two-clock rule, and the half that separates it from a naive mtime compare
    # -- left every other arm GREEN. A control that cannot fire is A15 and this
    # module exists to reproduce that exact rule.
    #
    # The case needs the two clocks to DISAGREE: the artifact is committed in
    # 2020 (so the COMMIT clock says stale against a dep committed now) while
    # its file mtime is newer than anything under the dep (so the MTIME clock
    # clears it). `record()` calls that CLEAN -- stale only if BOTH agree.
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, 'spikes')) as tmp:
        dep = os.path.join(tmp, 'dep')
        spk = os.path.join(tmp, 'spk')
        os.makedirs(dep)
        os.makedirs(spk)
        for d in (dep, spk):
            subprocess.run(['git', 'init', '-q'], cwd=d)
            subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=d)
            subprocess.run(['git', 'config', 'user.name', 't'], cwd=d)
        art = os.path.join(spk, 'out.json')
        open(art, 'w').write('{}')
        old = dict(os.environ, GIT_AUTHOR_DATE='2020-09-13T12:26:40',
                   GIT_COMMITTER_DATE='2020-09-13T12:26:40')
        subprocess.run(['git', 'add', 'out.json'], cwd=spk, env=old)
        subprocess.run(['git', 'commit', '-qm', 'art'], cwd=spk, env=old)
        open(os.path.join(dep, 'src.py'), 'w').write('x = 1\n')
        subprocess.run(['git', 'add', 'src.py'], cwd=dep)
        subprocess.run(['git', 'commit', '-qm', 'x'], cwd=dep)
        # STRICTLY newer, not same-second: an equality that happens to hold is
        # not a test of `>=`.
        t = _newest_file_mtime(dep, exclude=[art]) + 5
        os.utime(art, (t, t))
        prov = os.path.join(spk, 'provenance.json')
        json.dump({'source_mtimes': {dep: {}}, 'artifacts': [{'path': art}]},
                  open(prov, 'w'))
        state, detail, _ = verdict(prov)
        if state != CLEAN:
            print(f'SELFCHECK FAILED: the commit clock says stale and the mtime '
                  f'second opinion clears it -- record() calls that CLEAN, got '
                  f'{state} ({detail})')
            ok = False

    # DIRECTION 4 (v2) — AGREEMENT WITH A REAL `certify()` RUN, BOTH DIRECTIONS,
    # ON GROUND THIS MODULE OWNS. v1's only agreement arm was W5, a live spike
    # another lane can edit; that arm cannot distinguish "this module is wrong"
    # from "somebody touched W2" (A15, and `demo8 --selfcheck`'s recorded cost).
    from kfcheck import certify
    for want_stale in (True, False):
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, 'spikes')) as tmp:
            dep, spk, art = _synthetic(tmp, stale_artifact=want_stale)
            c_ok, problems = certify(spk, deps=[dep], artifacts=[art],
                                     falsifier='agreement arm, not a claim',
                                     allow_dirty=True)
            certify_says_stale = any('STALE ARTIFACT' in p for p in problems)
            mine = verdict(os.path.join(spk, 'provenance.json'))[0]
            if certify_says_stale != want_stale:
                print(f'SELFCHECK FAILED: real certify did not produce the '
                      f'{"STALE" if want_stale else "CLEAN"} case the arm needs '
                      f'(ok={c_ok}, problems={problems})')
                ok = False
            elif (mine == STALE) != certify_says_stale:
                print(f'SELFCHECK FAILED: real certify says '
                      f'stale={certify_says_stale} and this recomputation says '
                      f'{mine} -- the instrument disagrees with the thing it '
                      f'claims to recompute')
                ok = False

    # DIRECTION 6 — THE TIME BOUND REPORTS TRUNCATION RATHER THAN A SHORT TOTAL.
    # A budget that silently returns whatever it managed is the failure this
    # whole module is about: a number that reads as coverage and is not.
    rows, unscanned = scan(ROOT, max_seconds=0)
    if not unscanned:
        print('SELFCHECK FAILED: a zero-second budget must report unscanned dirs')
        ok = False
    rows, unscanned = scan(ROOT)
    if unscanned:
        print('SELFCHECK FAILED: an unbounded scan must not report truncation')
        ok = False

    # DIRECTION 5 — REPORTED, NOT ASSERTED, and the demotion is the point. W5 is
    # the one real-tree datapoint (it certified ok=True on 2026-08-19), so it is
    # worth printing; it is NOT a pass/fail arm, because its failure mode is
    # "another lane edited W2_witnessed_trie", which is not a defect in here.
    w5 = os.path.join(ROOT, 'spikes', 'W5_epoch_bisect', 'provenance.json')
    if os.path.isfile(w5):
        print(f'  (observation, not an arm) W5_epoch_bisect: {verdict(w5)[0]}')
    else:
        print('  (observation, not an arm) W5_epoch_bisect: provenance.json absent')

    print('stalecheck --selfcheck: ok' if ok else 'stalecheck --selfcheck: FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
