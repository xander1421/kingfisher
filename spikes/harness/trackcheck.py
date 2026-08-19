#!/usr/bin/env python3
"""trackcheck.py v1 — H182. A `Check:` citation that resolves on disk and not in git.

THE DEFECT REMOVED
------------------
`WORK_QUEUE.md` cites **82 distinct `kitchen/test_*.py` paths** as the `Check:`
line of DONE rows -- the D6 evidence a reader is told to run. Measured
2026-08-19: **90 of 93 files in `kitchen/` were untracked**, and `git log --
kitchen/` shows the directory entered history for the first time that day.
`kitchen/` is not gitignored; nobody committed them.

§13: *"RECORD is not done until it is committed. An uncommitted result is
indistinguishable from one that was never run, and it is invisible to every
other agent."* A fresh clone could not run ~80 of the checks this repo's own
queue offers as its evidence.

WHY NO EXISTING GATE SAW IT, AND IT IS A RECORDED CLASS (H35)
-------------------------------------------------------------
`refcheck.py:473` resolves a cited path with

    os.path.exists(os.path.join(ROOT, body))

-- the WORKING TREE, not the index. The file exists for the lane that wrote it,
so `refcheck` prints "every citation resolves" on that lane's disk and would
REFUSE on a fresh clone. H35 verbatim -- *a checker that reads the WORKING TREE
while its verdict is attributed to the COMMIT* -- now at the D6-evidence layer.

This module asks the one question `os.path.exists` cannot: **is the cited file
in `git ls-files`?**

WHY IT DOES NOT SIMPLY REFUSE ON ALL 79
----------------------------------------
H14: *"a gate that fires on a known-accepted state every run is one everyone
learns to bypass."* 79 violations on day one would do exactly that, and worse,
the fix is not mine to make -- the files belong to six lanes and one lane
committing another lane's 90 untracked files is `b529081` at thirty times the
size. So the current violations are pinned as an accepted floor, printed in full
on every run so they can never read as coverage, and **a NEW untracked citation
refuses**. Committing a baselined file shrinks the debt and is always allowed.

AND THE BASELINE IS A SET, NEVER A COUNT. H167: a pinned number *"could not tell
a floor from an arrival"*. Same reason `ledgerlag.py` (H177) pins a set -- and
this row exists partly because `kitchen/test_h104.py` pins the literal string
`"all 22 harness selfcheck(s) green"`, which my own `ledgerlag.py` moved to 23.

    python3 trackcheck.py             exit 0 = no NEW untracked citation
    python3 trackcheck.py --pin       rewrite the baseline (a deliberate act)
    python3 trackcheck.py --selfcheck both directions, on a synthetic tree
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BASELINE = os.path.join(HERE, 'trackcheck_baseline.json')

# Files whose `Check:`/backticked citations are scanned. Deliberately the
# documents that OFFER evidence to a reader, not every file in the tree.
SCANNED = ['WORK_QUEUE.md', 'out/LEDGER.md', 'MISSION_LOOP.md', 'CLAUDE.md']

# A backticked repo path. First segment must be an existing top-level entry --
# same rule refcheck.py uses to separate a repo path from an upstream citation
# like `boinc/sched/credit.cpp`, so this does not fire on things outside the repo.
CITED = re.compile(r'`([A-Za-z0-9_.][A-Za-z0-9_./-]*\.(?:py|sh|md|json|txt))`')
# `Check: python3 kitchen/test_h1.py` -- cited WITHOUT backticks around the path
BARE = re.compile(r'(?:python3?|sh|bash)\s+([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|sh))')


def tracked_set(root):
    out = subprocess.run(['git', 'ls-files'], cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit('trackcheck: `git ls-files` failed -- REFUSING rather than '
                         'reporting 0 violations from a broken query (H30)')
    return set(out.stdout.split())


def citations(root):
    """(source_doc, path) for every cited repo file, deduped."""
    tops = set(os.listdir(root))
    found = set()
    for rel in SCANNED:
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding='utf-8', errors='replace').read()
        for rx in (CITED, BARE):
            for m in rx.finditer(text):
                path = m.group(1)
                if path.startswith('/') or '$' in path or '*' in path:
                    continue
                if path.split('/')[0] not in tops:
                    continue          # outside this repo -- not a broken reference
                found.add((rel, path))
    return found


def violations(root):
    """cited paths that EXIST ON DISK but are NOT tracked -- the H35 blind spot."""
    tracked = tracked_set(root)
    bad = set()
    for rel, path in citations(root):
        full = os.path.join(root, path)
        if os.path.exists(full) and path not in tracked:
            bad.add(path)
    return bad


def load_baseline():
    if not os.path.isfile(BASELINE):
        return None
    return set(json.load(open(BASELINE))['untracked_citations'])


def main(argv):
    now = violations(ROOT)

    if '--pin' in argv:
        json.dump({'untracked_citations': sorted(now),
                   'why': 'cited in a Check: line, present on disk, absent from git '
                          'ls-files. Accepted floor; a NEW one refuses (H182). Each '
                          'lane commits its own -- one lane committing all of them '
                          'is b529081 at scale.'},
                  open(BASELINE, 'w'), indent=1)
        print(f'trackcheck: pinned {len(now)} untracked citation(s)')
        return 0

    base = load_baseline()
    if base is None:
        print('trackcheck: no baseline -- run --pin once. REFUSING rather than reading '
              'an absent baseline as "nothing is untracked" (H30).')
        return 2

    new = sorted(now - base)
    healed = sorted(base - now)
    # PRINTED IN FULL EVERY RUN. A pinned floor that is not shown reads as coverage.
    print(f'trackcheck: floor {len(base)} untracked citation(s) · now {len(now)} · '
          f'committed since the pin {len(healed)} · NEW {len(new)}')
    if healed:
        print('  now tracked (debt shrank, always allowed): ' + ' '.join(healed[:10])
              + (' ...' if len(healed) > 10 else ''))
    if not new:
        print('trackcheck: no NEW citation names a file that exists here and in no commit')
        return 0
    for p in new:
        print(f'  NEW UNTRACKED CITATION {p}: cited as evidence, present on this disk, '
              f'absent from `git ls-files` -- a fresh clone cannot run it')
    print('\nREFUSE: a DONE row cites evidence that exists only on the author\'s disk.\n'
          '        §13: an uncommitted result is indistinguishable from one that was\n'
          '        never run. `git add -N <path>` then `git commit --only <path>`.')
    return 1


def selfcheck():
    """BOTH directions on a synthetic git repo. A gate whose refusing arm is never
    exercised is a coincidence, not a control (A15)."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, 'spikes')) as tmp:
        def git(*a):
            return subprocess.run(('git',) + a, cwd=tmp, capture_output=True, text=True)
        git('init', '-q')
        git('config', 'user.email', 't@t'); git('config', 'user.name', 't')
        os.makedirs(os.path.join(tmp, 'kitchen'))
        open(os.path.join(tmp, 'kitchen', 'test_a.py'), 'w').write('x')
        open(os.path.join(tmp, 'kitchen', 'test_b.py'), 'w').write('x')
        open(os.path.join(tmp, 'WORK_QUEUE.md'), 'w').write(
            'Check: `python3 kitchen/test_a.py`\n'
            'Check: `python3 kitchen/test_b.py`\n'
            'Check: `python3 kitchen/test_missing.py`\n'
            'Cites: `boinc/sched/credit.cpp`\n')
        git('add', 'WORK_QUEUE.md', 'kitchen/test_a.py')
        git('commit', '-qm', 'x')

        v = violations(tmp)
        if v != {'kitchen/test_b.py'}:
            print(f'SELFCHECK FAILED: expected {{kitchen/test_b.py}}, got {v}'); ok = False

        # a cited path that does not exist AT ALL is refcheck's job, not this one --
        # reporting it here would duplicate a gate and double-refuse one defect
        if 'kitchen/test_missing.py' in v:
            print('SELFCHECK FAILED: an absent file is refcheck\'s finding, not this one')
            ok = False

        # a path outside the repo must never be flagged (H14: no firing on known-good)
        if any('boinc' in p for p in v):
            print('SELFCHECK FAILED: upstream citation flagged'); ok = False

        # THE HEALING DIRECTION: committing it clears the violation
        git('add', 'kitchen/test_b.py'); git('commit', '-qm', 'y')
        if violations(tmp):
            print(f'SELFCHECK FAILED: committed file still counts: {violations(tmp)}')
            ok = False

        # THE REFUSING DIRECTION: a new untracked cited file appears
        open(os.path.join(tmp, 'kitchen', 'test_c.py'), 'w').write('x')
        open(os.path.join(tmp, 'WORK_QUEUE.md'), 'a').write('Check: `python3 kitchen/test_c.py`\n')
        if violations(tmp) != {'kitchen/test_c.py'}:
            print('SELFCHECK FAILED: a new untracked citation must be caught'); ok = False

        # a broken `git ls-files` REFUSES rather than reporting zero (H30)
        try:
            tracked_set(os.path.join(tmp, 'definitely', 'not', 'a', 'repo'))
            print('SELFCHECK FAILED: a broken git query must REFUSE'); ok = False
        except (SystemExit, FileNotFoundError, NotADirectoryError):
            pass

    print('trackcheck --selfcheck: ok' if ok else 'trackcheck --selfcheck: FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main(sys.argv[1:]))
