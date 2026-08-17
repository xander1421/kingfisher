#!/usr/bin/env python3
"""H41 — does refcheck v5's selfcheck go RED when v5 is reverted?  (§12.3)

The claim in v5's header is "revert either half on a copy and --selfcheck goes
red naming which". This runs it. Three reverts, each restoring exactly one of
v5's three changes, plus an unmodified CONTROL — because if every copy were
rubble all three reverts would "fire" and read as a perfect score.

Never touches the live module: `pre-commit.hook` gates refcheck for every lane,
so reverting it in place would refuse the fleet's commits for as long as the run
takes. Same rule test_loop_gate.sh states for itself.

usage: python3 spikes/H41_fenced_paths/falsify.py
exit 0 = every revert is detected by the selfcheck and the control is green.
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'spikes', 'harness'))
from edits import anchored_replace, AnchorMissing              # noqa: E402

SRC = os.path.join(REPO, 'spikes', 'harness', 'refcheck.py')

REVERTS = [
    ('R1  the fence half',
     'v4 read only inline backticks, so a path inside a ```sh fence — the form '
     'a lane copies and runs — was never checked',
     "            if rel.endswith('.md'):\n"
     "                for blk in re.findall(r'^```[^\\n]*\\n(.*?)^```', text, re.M | re.S):\n"
     "                    cited |= set(re.findall(r'[^\\s`\\'\"|;()]+/[^\\s`\\'\"|;()]*', blk))\n",
     '',
     'MISSES  absent path inside a ```sh fence'),

    ('R2  the dot-slash half',
     "v4's first-segment rule skipped `./x` because the first segment of a "
     'dot-slash token is `.`, which is not a listdir entry',
     "            if not tok.startswith('./') and body.split('/')[0] not in top:",
     "            if body.split('/')[0] not in top:",
     'MISSES  absent dot-slash path'),

    ('R3  the journal scope',
     'without it a broken path in a single-writer journal (H10) refuses every '
     "lane's commit, and only the one lane forbidden to be tripped by it may fix it",
     "        if not re.match(r'HANDOFF\\..+\\.md$', rel):",
     '        if True:',
     'FALSE-POSITIVE on a broken path in a per-lane JOURNAL'),
]


def selfcheck(text):
    """Run this refcheck source's --selfcheck in a scratch dir; return (rc, out)."""
    tmp = tempfile.mkdtemp(prefix='h41_')
    try:
        p = os.path.join(tmp, 'refcheck.py')
        open(p, 'w').write(text)
        r = subprocess.run([sys.executable, p, '--selfcheck'],
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    base = open(SRC).read()
    problems = []

    rc, out = selfcheck(base)
    print(f'  CONTROL  unmodified refcheck --selfcheck: '
          f'{"green" if rc == 0 else "RED"}')
    if rc != 0:
        problems.append('CONTROL: the unmodified module does not pass its own '
                        'selfcheck, so no revert below is evidence')
        print(out)

    for rid, why, old, new, want in REVERTS:
        try:
            reverted = anchored_replace(base, old, new)
        except AnchorMissing as e:
            # Loud, because the silent version is a green report over no test:
            # the anchor moved, the revert changed nothing, and the selfcheck
            # would have gone green on an unmodified module.
            problems.append(f'{rid}: anchor gone, revert tested NOTHING ({e})')
            print(f'  {rid}  ANCHOR MISSING — cannot falsify')
            continue
        rc, out = selfcheck(reverted)
        if rc == 0:
            problems.append(f'{rid}: reverted and the selfcheck still passed — '
                            f'"{want}" is INERT')
            print(f'  {rid}  INERT   defect restored and the selfcheck passed')
        elif want not in out:
            problems.append(f'{rid}: selfcheck failed but not on "{want}"')
            print(f'  {rid}  WRONG   red, but not on the expected line')
            print('\n'.join('           ' + l for l in out.splitlines()
                            if 'MISSES' in l or 'FALSE-POSITIVE' in l))
        else:
            print(f'  {rid}  FIRES   {want}')
            print(f'           defect: {why}')

    print()
    if problems:
        print(f'H41: {len(problems)} revert(s) are not detected by the selfcheck')
        for p in problems:
            print(f'  - {p}')
        return 1
    print(f'H41: all {len(REVERTS)} of v5\'s changes are load-bearing — reverting '
          f'any one is caught by refcheck --selfcheck')
    return 0


if __name__ == '__main__':
    sys.exit(main())
