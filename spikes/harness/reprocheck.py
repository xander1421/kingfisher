#!/usr/bin/env python3
"""Every load-bearing claim must name a command that re-runs it.

Two headline drivers broke silently and were only found by a sweep. The reason
they could break unnoticed is that no claim in the LEDGER names the command
that produces it -- the link from claim to reproducer lived in memory.

Convention: a row may carry `repro: <path> [args]` inside its evidence cell.
This checks that the path exists. It cannot check that the command still
produces the claimed number; only running it does that, which is the point.
"""
import os
import re
import sys

# The path must contain a '/' BEFORE any space. Without that, the regex matched
# its own prose in the LEDGER ("none named a repro: `->`") and reported a
# 12th annotation that was GONE -- a false positive in the tool whose whole job
# is auditing whether claims are reproducible.
REPRO = re.compile(r'repro:\s*`([^\s`]*/[^`]*)`')


def audit(ledger_path, root, grade='**A**'):
    rows = [l for l in open(ledger_path) if f'| {grade} |' in l]
    have, missing, broken, inert = [], [], [], []
    for l in rows:
        claim = l.split('|')[1].strip()
        if claim == grade:
            continue
        m = REPRO.search(l)
        if not m:
            missing.append(claim[:60])
            continue
        cmd = m.group(1)
        rel = cmd.split()[0]
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            broken.append((claim[:50], cmd))
        elif not rel.endswith(('.py', '.sh')):
            # EXISTENCE IS NOT RUNNABILITY. A `.md` cannot re-derive a number and
            # a prebuilt binary is an artifact, not a reproducer -- yet both
            # scored as "has a repro" because the path resolved. Three A-grade
            # claims were annotated this way, one of them by the same agent that
            # wrote this check, one cycle after writing it.
            inert.append((claim[:50], cmd))
        else:
            have.append((claim[:50], cmd))
    return have, missing, broken, inert


def main():
    root = os.path.expanduser('~/kingfisher')
    ledger = os.path.join(root, 'out/LEDGER.md')
    have, missing, broken, inert = audit(ledger, root)
    n = len(have) + len(missing) + len(broken) + len(inert)
    print(f'A-grade claims: {n}')
    print(f'  with a RUNNABLE repro       {len(have)}')
    print(f'  with a repro that is GONE   {len(broken)}')
    print(f'  with a NON-RUNNABLE repro   {len(inert)}   (.md or a binary)')
    print(f'  with NO repro:              {len(missing)}')
    for c, cmd in broken:
        print(f'  BROKEN  {c}  -> {cmd}')
    for c, cmd in inert:
        print(f'  INERT   {c}  -> {cmd}')
    return 1 if (broken or inert) else 0


def demo():
    import tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'sub'))
    open(os.path.join(d, 'sub', 'x.py'), 'w').write('')
    open(os.path.join(d, 'sub', 'note.md'), 'w').write('')
    led = os.path.join(d, 'L.md')
    # Paths MUST contain '/' — REPRO refuses a slash-less token (own-prose false positive).
    open(led, 'w').write(
        '| claim one | **A** | evidence repro: `sub/x.py 3` |\n'
        '| claim two | **A** | evidence with no reproducer |\n'
        '| claim three | **A** | evidence repro: `sub/gone.py` |\n'
        '| claim four | **B** | not audited at grade A |\n'
        '| claim five | **A** | evidence repro: `sub/note.md` |\n')
    have, missing, broken, inert = audit(led, d)
    assert len(have) == 1 and have[0][1] == 'sub/x.py 3', have
    assert missing == ['claim two'], missing
    assert len(broken) == 1 and broken[0][1] == 'sub/gone.py', broken
    assert len(inert) == 1 and inert[0][1] == 'sub/note.md', inert
    print('reprocheck: 4-tuple demo matches audit()')


if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
    else:
        sys.exit(main())
