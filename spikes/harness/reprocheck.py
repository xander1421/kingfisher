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
    have, missing, broken = [], [], []
    for l in rows:
        claim = l.split('|')[1].strip()
        if claim == grade:
            continue
        m = REPRO.search(l)
        if not m:
            missing.append(claim[:60])
            continue
        cmd = m.group(1)
        path = os.path.join(root, cmd.split()[0])
        (have if os.path.exists(path) else broken).append((claim[:50], cmd))
    return have, missing, broken


def main():
    root = os.path.expanduser('~/kingfisher')
    ledger = os.path.join(root, 'out/LEDGER.md')
    have, missing, broken = audit(ledger, root)
    n = len(have) + len(missing) + len(broken)
    print(f'A-grade claims: {n}')
    print(f'  with a repro: that EXISTS   {len(have)}')
    print(f'  with a repro: that is GONE  {len(broken)}')
    print(f'  with NO repro:              {len(missing)}')
    for c, cmd in broken:
        print(f'  BROKEN  {c}  -> {cmd}')
    return 1 if broken else 0


def demo():
    import tempfile
    d = tempfile.mkdtemp()
    open(os.path.join(d, 'x.py'), 'w').write('')
    led = os.path.join(d, 'L.md')
    open(led, 'w').write(
        '| claim one | **A** | evidence repro: `x.py 3` |\n'
        '| claim two | **A** | evidence with no reproducer |\n'
        '| claim three | **A** | evidence repro: `gone.py` |\n'
        '| claim four | **B** | not audited at grade A |\n')
    have, missing, broken = audit(led, d)
    assert len(have) == 1 and have[0][1] == 'x.py 3', have
    assert missing == ['claim two'], missing
    assert len(broken) == 1 and broken[0][1] == 'gone.py', broken
    print('reprocheck: 3 assertions pass')


if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
    else:
        sys.exit(main())
