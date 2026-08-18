#!/usr/bin/env python3
"""H85 — the falsifier for refcheck.py v7's own selfcheck.

§12.3 asks for a check that FAILS when the component breaks, and a selfcheck
whose every fixture was written after the fix has a regression record and no
detection record. So this reverts v7 on a COPY, one half at a time, and asserts
`--selfcheck` goes red naming which half.

The two halves are not one fix. v7 removes a SCOPE defect (check 6 ran only for
files keyed in BASELINE_ROW_SHAPE) and a WIDTH defect (the expected width was the
constant 5, i.e. WORK_QUEUE.md's). Reverting either alone must be caught, because
shipping only the scope half -- the one-line fix this row was going to make --
would have accused `analysis/GUARDRAILS.md`'s four-field rows on every run.

usage:  python3 spikes/H85_check6_scope/falsify.py     # exit 0 = both halves detected
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
SRC = os.path.join(ROOT, 'spikes', 'harness', 'refcheck.py')

# (label, what the revert restores, expected marker in the red output)
REVERTS = [
    ('SCOPE  (v6: check 6 keyed to BASELINE_ROW_SHAPE)',
     lambda s: s.replace(
         '        known = BASELINE_ROW_SHAPE.get(rel, ())\n'
         '        for rid, n, want in malformed_rows(text):',
         '        if rel not in BASELINE_ROW_SHAPE:\n'
         '            continue\n'
         '        known = BASELINE_ROW_SHAPE.get(rel, ())\n'
         '        for rid, n, want in malformed_rows(text):'),
     'MISSES  THE SAME row in a file check 6 could not reach'),
    ('WIDTH  (v6: expected width hard-coded to 5)',
     lambda s: s.replace(
         '        want = declared if declared is not None else modal\n',
         '        want = 5\n'),
     'FALSE-POSITIVE on a FOUR-field table'),
]


def run(label, mutate, marker):
    t = tempfile.mkdtemp(prefix='h85f_')
    try:
        dst = os.path.join(t, 'refcheck.py')
        s = open(SRC).read()
        m = mutate(s)
        if m == s:
            print(f'  BAD  {label}: the revert was a NO-OP -- the anchor moved, so '
                  f'this arm tested nothing (edits.py\'s whole subject)')
            return False
        open(dst, 'w').write(m)
        # The module resolves ROOT from its own __file__, so a copy outside
        # spikes/harness/ would scan the wrong tree. Run it in place under a
        # different NAME instead, and restore the original unconditionally.
        live = SRC + '.h85tmp.py'
        shutil.copy2(dst, live)
        try:
            p = subprocess.run([sys.executable, live, '--selfcheck'],
                               cwd=ROOT, capture_output=True, text=True)
        finally:
            os.remove(live)
        out = p.stdout + p.stderr
        ok = p.returncode != 0 and marker in out
        print(f'  {"DETECTED" if ok else "MISSED  "} {label}')
        if not ok:
            print(f'      rc={p.returncode}, expected marker not found: {marker!r}')
        return ok
    finally:
        shutil.rmtree(t, ignore_errors=True)


print('H85 — falsifying refcheck.py v7 by reverting each half on a copy\n')

# Positive control first: unmutated, the selfcheck must PASS. Without it a
# selfcheck that is red for an unrelated reason would score both arms DETECTED.
p = subprocess.run([sys.executable, SRC, '--selfcheck'], cwd=ROOT,
                   capture_output=True, text=True)
print(f'  {"OK      " if p.returncode == 0 else "BAD     "} '
      f'positive control: unmutated --selfcheck exits {p.returncode}, expected 0')
if p.returncode != 0:
    print('\nREFUSE: the selfcheck is already red, so nothing below is evidence '
          'about the reverts.')
    sys.exit(2)

results = [run(*r) for r in REVERTS]
print()
if all(results):
    print('falsify: both halves of v7 are DETECTED by its own --selfcheck. '
          'Reverting either goes red and names which.')
    sys.exit(0)
print('REFUSE: a revert of v7 was not caught by the selfcheck, so the fixture '
      'for it is decoration.')
sys.exit(1)
