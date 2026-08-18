#!/usr/bin/env python3
"""H94 — the falsifier for recordloss.py v1's own selfcheck.

§12.3 asks for a check that FAILS when the component breaks, and a selfcheck
whose every fixture was written after the fix has a regression record and no
detection record. So this breaks v1 on a copy, one property at a time, and
asserts `--selfcheck` goes red NAMING WHICH.

The four properties are not one fix, and three of them are other lanes' findings
turned into fixtures rather than into prose:

  * INDEX-NOT-TREE   H35: two of pre-commit's three checkers judge the tree while
                     the commit carries a different blob.
  * KEY-NOT-LINE     ATOM-3's d278d01: a line-level deletion rule fires falsely
                     here, because CHANNEL lines are rewritten in place and grow.
  * WHOLE-FILE       deleting a document loses every record in it, and `git show`
                     of a deleted path errors — the same shape as "absent".
  * COMMIT-SCOPE     H72: a checker that reads every covered path lets one lane's
                     uncommitted deletion refuse every other lane's commits.

usage:  python3 spikes/H94_record_loss/falsify.py    # exit 0 = all four detected
"""
import os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
SRC = os.path.join(ROOT, 'spikes', 'harness', 'recordloss.py')

BREAKS = [
    ('INDEX-NOT-TREE (read the working tree, as refcheck/journalcheck do)',
     lambda s: s.replace(
         "        lost = compare(before, blob(f':{path}', cwd), covered(path))",
         "        _p = os.path.join(cwd or '.', path)\n"
         "        _t = open(_p).read() if os.path.exists(_p) else None\n"
         "        lost = compare(before, _t, covered(path))"),
     'clean staged blob must pass'),
    ('KEY-NOT-LINE  (whole log lines as keys, the rule d278d01 measured false)',
     lambda s: s.replace(
         "    return {f'{v} {i} {l}' for v, i, l in LOGLINE.findall(text)}",
         "    return {x for x in text.split(chr(10)) if LOGLINE.match(x)}"),
     'rewritten in place and grown must be QUIET'),
    ('WHOLE-FILE    (a deleted document loses nothing)',
     lambda s: s.replace(
         "    return keys(before, kind) - (keys(after, kind) if after is not None else set())",
         "    if after is None:\n        return set()\n"
         "    return keys(before, kind) - keys(after, kind)"),
     'deleting a journal outright must REFUSE'),
    ('COVERAGE      (journals not recognised, only CHANNEL.md)',
     lambda s: s.replace(
         "    if re.fullmatch(r'HANDOFF(\\.[\\w.-]+)?\\.md', base):\n        return 'cycle'\n",
         ""),
     'must REFUSE — the gate is inert'),
]

# WITHDRAWN ARM, kept with its reason (§5: no silent correction).
# ('COMMIT-SCOPE', staged -> git ls-files, "another lane's uncommitted deletion
#  must not refuse me") came back MISSED, and the arm was right: the break is a
# NO-OP. With an INDEX-vs-HEAD comparison, a covered path whose index copy equals
# HEAD has identical keys whether it is walked or not, so scoping to the commit's
# paths cannot change a verdict. recordloss.py v1's docstring claimed the scoping
# as the H72 defence; that claim is withdrawn there too. What defends H72 is
# reading the index. An arm that cannot fire is family A, in the falsifier.


def run(label, mutate, marker):
    s = open(SRC).read()
    m = mutate(s)
    if m == s:
        print(f'  BAD      {label}: the break was a NO-OP — the anchor moved, so '
              f"this arm tested nothing (edits.py's whole subject)")
        return False
    # The module resolves HERE from its own __file__ and writes its fixture under
    # it (§10), so run the broken copy IN PLACE under a different name.
    live = SRC + '.h94tmp.py'
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
        print(f'      rc={p.returncode}, expected marker not found: {marker!r}')
        print('      ' + (out.strip().replace('\n', '\n      ') or '(no output)'))
    return ok


print('H94 — falsifying recordloss.py v1 by breaking one property at a time\n')

# Positive control first. Without it a selfcheck red for an unrelated reason
# would score every arm DETECTED — H61's lesson, from this lane's own probe.
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
    print('falsify: all four properties are DETECTED by v1\'s own --selfcheck.')
    sys.exit(0)
print('REFUSE: a broken property was not caught, so its fixture is decoration.')
sys.exit(1)
