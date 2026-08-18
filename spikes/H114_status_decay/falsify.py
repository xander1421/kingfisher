#!/usr/bin/env python3
"""H114 — the falsifier for statuscheck.py v1's own selfcheck.

Four properties, each broken on a copy, each expected to turn `--selfcheck` red
NAMING WHICH. Three of the four are other rows' findings turned into fixtures:

  * OFFER-FORM   the case that earned the row. The first rule shipped could see
                 only sentence assertions and found ZERO in prompts/ — F3 fired
                 against it before it went anywhere.
  * HISTORY      a journal's cycle entries are the past; gating them asks lanes
                 to rewrite history to keep a checker quiet.
  * H82          a row whose own field count is off has no readable status, and
                 counting it as a mismatch would report H82's defect as this
                 module's findings.
  * PATH-NOT-STATUS  `is in BLOCKED.log` is a filename. v1's first run reported
                 it as a status claim about H17.

usage:  python3 spikes/H114_status_decay/falsify.py   # exit 0 = all detected
"""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
SRC = os.path.join(ROOT, 'spikes', 'harness', 'statuscheck.py')

BREAKS = [
    ('OFFER-FORM   (sentence assertions only, as v1 before F3 fired)',
     lambda s: s.replace("    if base:\n", "    if False:\n"),
     'an offered DONE row must be caught'),
    ('HISTORY      (judge a journal whole, not only its NEXT blocks)',
     lambda s: s.replace(
         "    if re.fullmatch(r'HANDOFF(\\.[\\w.-]+)?\\.md', os.path.basename(path)):\n        out = []",
         "    if re.fullmatch(r'HANDOFF(\\.[\\w.-]+)?\\.md', os.path.basename(path)):\n"
         "        return [(0, text)]\n        out = []"),
     'a cycle entry is HISTORY and must not be gated'),
    ('H82          (the consumer stops skipping an unreadable row)',
     lambda s: s.replace(
         "            if actual is None or actual in ('NO-ROW', 'OTHER'):\n                continue",
         "            if actual in ('NO-ROW', 'OTHER'):\n                continue"),
     'an UNREADABLE row (H82) must not be reported as a mismatch'),
    ('PATH-NOT-STATUS (drop the filename guard)',
     lambda s: s.replace(r"r'\**(' + '|'.join(STATUSES) + r')\b(?!\.\w)', re.I)",
                         r"r'\**(' + '|'.join(STATUSES) + r')\b', re.I)"),
     '`BLOCKED.log` is a filename and must not read as a status'),
]


def run(label, mutate, marker):
    s = open(SRC).read()
    m = mutate(s)
    if m == s:
        print(f'  BAD      {label}: the break was a NO-OP — the anchor moved, so '
              f"this arm tested nothing (edits.py's whole subject)")
        return False
    live = SRC + '.h114tmp.py'
    open(live, 'w').write(m)
    try:
        p = subprocess.run([sys.executable, live, '--selfcheck'], cwd=ROOT,
                           capture_output=True, text=True)
    finally:
        os.remove(live)
    out = p.stdout + p.stderr
    ok = p.returncode != 0 and marker in out
    print(f'  {"DETECTED" if ok else "MISSED  "} {label}')
    if not ok:
        print(f'      rc={p.returncode}, marker not found: {marker!r}')
        print('      ' + (out.strip().replace('\n', '\n      ') or '(no output)'))
    return ok


print('H114 — falsifying statuscheck.py v1 by breaking one property at a time\n')
p = subprocess.run([sys.executable, SRC, '--selfcheck'], cwd=ROOT,
                   capture_output=True, text=True)
print(f'  {"OK      " if p.returncode == 0 else "BAD     "} '
      f'positive control: unbroken --selfcheck exits {p.returncode}, expected 0')
if p.returncode != 0:
    print('\nREFUSE: the selfcheck is already red, so nothing below is evidence.')
    sys.exit(2)

results = [run(*b) for b in BREAKS]
print()
if all(results):
    print("falsify: all four properties are DETECTED by v1's own --selfcheck.")
    sys.exit(0)
print('REFUSE: a broken property was not caught, so its fixture is decoration.')
sys.exit(1)
