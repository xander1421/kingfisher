#!/usr/bin/env python3
"""H85 — ATTACK (§2) on the loop (§12.8). Target: `refcheck.py` v6 check 6,
which I shipped one hour before this ran. Self-authored data first.

THE READING, taken from the source before anything was run: check 6's body sits
under `if rel in BASELINE_ROW_SHAPE:` and that dict has exactly one key, so the
check cannot execute for any file except `WORK_QUEUE.md` — while `refcheck` still
prints "every §N, guardrail and path citation in 53 harness files resolves".

FALSIFIERS, STATED BEFORE THE FIRST RUN (posted to CHANNEL.md at claim time):

  FA  a malformed row planted in a harness `.md` OTHER than WORK_QUEUE.md IS
      reported -> the reading is wrong, withdraw the attack
  FB  the SAME row planted in WORK_QUEUE.md is NOT reported -> the check is
      broken outright rather than mis-scoped, and the row is worse than filed
  FC  measured BEFORE any repair: widening the scope naively (the shipped rule,
      every file) flags rows in existing harness content -> that is the repair's
      real cost, and it decides whether the fix ships as a gate, as a baseline,
      or not at all. A fix that refuses every lane's commits on live content is
      H33, and this lane has shipped that once already
  FD  the header-derived rule does not report EVERY row the shipped rule reports
      in WORK_QUEUE.md -> it is not a narrowing of the false positives, it is a
      different check that has traded them for false NEGATIVES, and the
      comparison below is not evidence for it.
      **v2 of this file, and FD as first written was too weak: it fired only if
      the derived rule reported MORE, so a rule reporting 2 of 10 real defects
      passed it — and the verdict line then printed "both rules report the same
      2 rows", which is not what was measured. A falsifier stated in the wrong
      direction is not a falsifier.**

usage:  python3 spikes/H85_check6_scope/attack.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import refcheck                                                    # noqa: E402

# A row that is malformed under any reading: three cells of text, an unescaped
# pipe in the third, in a table whose header declares three columns.
PLANT = ('\n| ZZ9 | planted by H85 | DONE — `grep -c . x | wc -l` says so |\n')
HEADER = '\n| id | item | status |\n|---|---|---|\n'


def run_refcheck(tree):
    p = subprocess.run([sys.executable, 'spikes/harness/refcheck.py'],
                       cwd=tree, capture_output=True, text=True)
    return p.stdout + p.stderr


def build():
    """A scratch copy of every file refcheck reads."""
    t = tempfile.mkdtemp(prefix='h85_')
    for rel in refcheck.harness_files():
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(t, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    # refcheck resolves paths against ROOT, so the scratch tree needs the
    # top-level entries its path check reads. Copy the directory NAMES only.
    for fn in sorted(os.listdir(ROOT)):
        p = os.path.join(t, fn)
        if not os.path.exists(p):
            if os.path.isdir(os.path.join(ROOT, fn)):
                os.makedirs(p, exist_ok=True)
            else:
                open(p, 'w').write('')
    return t


def arm(name, rel):
    t = build()
    try:
        p = os.path.join(t, rel)
        open(p, 'a').write(HEADER + PLANT)
        out = run_refcheck(t)
        seen = 'ZZ9' in out
        print(f'  {name:<44} planted in {rel:<20} reported: '
              f'{"YES" if seen else "NO"}')
        return seen
    finally:
        shutil.rmtree(t, ignore_errors=True)


def scan_all(rule):
    """Every harness file, under `rule(text) -> [(id, n), ...]`."""
    hits = {}
    for rel in refcheck.harness_files():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        bad = rule(open(p, errors='replace').read())
        if bad:
            hits[rel] = [b[0] for b in bad]
    return hits


DELIM = re.compile(r'^\|(?:\s*:?-{2,}:?\s*\|)+\s*$')
CELL = re.compile(r'(?<!\\)\|')


def header_derived(text, end_on_blank_only=False):
    """Rows whose field count differs from THEIR OWN table's header width.

    The shipped rule hard-codes 5 fields, which is WORK_QUEUE.md's shape. A
    two-column table is not malformed for having two columns.

    `end_on_blank_only` is the difference between the two candidate repairs, and
    it is worth 8 of WORK_QUEUE.md's 10 defects: a row whose own text contains an
    unescaped newline-free pipe still starts with `|`, but a row that has been
    WRAPPED or that follows a non-table line loses its table if the width is
    dropped at every non-`|` line. GFM terminates a table at a BLANK line, so
    that is the correct reset point.
    """
    out, width = [], None
    for line in text.splitlines():
        if DELIM.match(line):
            width = len(CELL.split(line))
            continue
        if not line.startswith('|'):
            if not end_on_blank_only or not line.strip():
                width = None
            continue
        cell = line.split('|')[1].strip().strip('*`').strip()
        if not (refcheck.ID_CELL.match(cell) and
                (any(c.isdigit() for c in cell) or '-' in cell)):
            continue
        if width is None:
            continue
        n = len(CELL.split(line))
        if n != width:
            out.append((cell, n))
    return out


print('H85 — ATTACK on refcheck.py v6 check 6, one hour after I shipped it\n')
fb = arm('FB positive control: the keyed file', 'WORK_QUEUE.md')
fa = arm('FA the same row, another harness file', 'MISSION_LOOP.md')
fa2 = arm('   and a third', 'CLAUDE.md')
print()

naive = scan_all(refcheck.malformed_rows)
derived = scan_all(header_derived)
blank = scan_all(lambda t: header_derived(t, end_on_blank_only=True))
print('FC — what a WIDENED check 6 would say about live content today:')
for rel in sorted(set(naive) | set(derived) | set(blank)):
    print(f'    {rel:<26} shipped: {len(naive.get(rel, [])):<3} '
          f'header-derived: {len(derived.get(rel, [])):<3} '
          f'header-derived/blank-terminated: {len(blank.get(rel, [])):<3}')
print()

# --- verdicts, and FB/FD before anything is concluded from the rest
if not fb:
    print('  PROBLEM  FB FIRED: check 6 does not report a planted row even in the '
          'one file it is keyed to. It is broken outright, not mis-scoped, and '
          'nothing else here is evidence about scope.')
    sys.exit(2)
print('FB ok: the planted row IS reported in WORK_QUEUE.md, so the check works '
      'where it is keyed and the arms below are about SCOPE.')

if fa or fa2:
    print('FA FIRED: a planted row IS reported outside WORK_QUEUE.md. The reading '
          'is wrong and the attack is withdrawn.')
    sys.exit(1)
print('FA did not fire: the SAME row is invisible in MISSION_LOOP.md and '
      'CLAUDE.md. **Check 6 cannot fire for any file but one**, and refcheck '
      'prints its all-clear over the gap — A15, and H30\'s class in the module '
      'whose own v5 header names H30\'s class.')

wq_naive = set(naive.get('WORK_QUEUE.md', []))
for label, got in (('header-derived', set(derived.get('WORK_QUEUE.md', []))),
                   ('header-derived/blank-terminated',
                    set(blank.get('WORK_QUEUE.md', [])))):
    missed = wq_naive - got
    verdict = ('MISSES ' + ','.join(sorted(missed))) if missed else 'reports all'
    print(f'FD  {label:<34} {len(got)}/{len(wq_naive)} of the shipped rule\'s '
          f'rows — {verdict}')
if wq_naive - set(blank.get('WORK_QUEUE.md', [])):
    print('  FD FIRED on BOTH candidate rules: a repair that trades false '
          'positives for false negatives on the file the check exists for does '
          'not ship. Nothing below is a recommendation.')
    sys.exit(1)
print('FD did not fire for the blank-terminated rule: it reports every row the '
      'shipped rule reports on WORK_QUEUE.md, so it differs from it only where '
      'the shipped one was wrong.')

fp = {k: sorted(set(v) - set(blank.get(k, [])))
      for k, v in naive.items() if set(v) - set(blank.get(k, []))}
print()
if fp:
    print('FC — AND THE OBVIOUS REPAIR WOULD HAVE BEEN WRONG. Deleting the '
          '`if rel in BASELINE_ROW_SHAPE` guard, which is the one-line fix this '
          'attack was going to make, files these accusations against live '
          'content:')
    for rel, ids in fp.items():
        print(f'    {rel}: {ids} — flagged by the shipped rule, NOT by the '
              'blank-terminated header-derived one')
    print('  `analysis/GUARDRAILS.md:700` declares a TWO-column table '
          '(`| | the instrument cannot |`). A two-column row is not malformed '
          'for having two columns; the shipped rule hard-codes WORK_QUEUE.md\'s '
          'width. So check 6 was inert AND wrong, and the inertness is the only '
          'reason it never filed a false accusation.')
else:
    print('FC: widening the scope flags nothing new, so the repair is free.')
