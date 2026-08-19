#!/usr/bin/env python3
"""A train/test leak control that intersects EXACT tuples cannot fire.

CLASS, not site. Nine files compute some form of

    len(set(train) & set(test)) == 0

and treat passing it as "no leakage". On WN18RR that control is unfalsifiable:
the dataset is CONSTRUCTED to have zero exact overlap, so the check passes on
any correctly-built split, under any amount of real leakage.

MEASURED on corpus/wn18rr, independently of the lane that reported it:

    test triples             3134
    EXACT (s,p,o) overlap       0     <- what the control checks
    REVERSED (o,p,s) leak    1086     34.7%   <- what it cannot see

The consequence, from ATOM-3's H165/H174 and reproduced here: RotatE scores
MRR 0.9831 on the leaked queries and 0.0214 on the clean ones. The headline
0.3546 is a blend, and the "10.0x lift over symbolic rules" INVERTS at one
operating point -- symbolic 0.0511 against RotatE 0.0214, 2.39x the other way.

This module refuses on the shape rather than on the number, so it stays true
for datasets whose leak rate is different or zero.

    python3 leakcheck.py                 # scan the repo for the weak control
    python3 leakcheck.py --selfcheck     # assert the checker itself works
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
WEAK = re.compile(r'set\(\s*train\s*\)\s*&\s*set\(\s*test\s*\)|set\(\s*test\s*\)\s*&\s*set\(\s*train\s*\)')
# A file is EXCUSED only if it also tests the reversed order somewhere.
REVERSED = re.compile(r'\(\s*o\s*,\s*p\s*,\s*s\s*\)|\(\s*t\s*,\s*r\s*,\s*h\s*\)|reversed_leak|rev_leak')


def leak_rates(train_path, test_path):
    """Both orders, so the number that matters is next to the number that hides it."""
    load = lambda f: [tuple(l.rstrip('\n').split('\t')) for l in open(f) if l.strip()]
    tr, te = set(load(train_path)), load(test_path)
    exact = sum(1 for t in te if t in tr)
    rev = sum(1 for s, p, o in te if (o, p, s) in tr)
    return {'n_test': len(te), 'exact': exact, 'reversed': rev,
            'reversed_pct': round(100.0 * rev / len(te), 2) if te else 0.0}


def scan():
    hits = []
    for dirpath, dirnames, files in os.walk(os.path.join(ROOT, 'spikes')):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'target', '__pycache__')]
        for fn in files:
            if not fn.endswith('.py'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                src = open(p, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            if WEAK.search(src):
                hits.append((os.path.relpath(p, ROOT), bool(REVERSED.search(src))))
    return hits


def selfcheck():
    """The checker must reject the weak form AND accept the fixed one, or it is
    the same unfireable-control defect one level up."""
    assert WEAK.search('c2 = len(set(train) & set(test)) == 0')
    assert WEAK.search('x = set(test) & set(train)')
    assert not WEAK.search('len(set(train) & set(valid))'), 'must not flag train/valid'
    assert REVERSED.search('rev = sum(1 for s,p,o in te if (o,p,s) in tr)')
    print('leakcheck: selfcheck passed (rejects weak form, accepts reversed-order fix)')


def main():
    if '--selfcheck' in sys.argv:
        selfcheck()
        return 0
    wn = os.path.join(ROOT, 'corpus', 'wn18rr')
    if os.path.isdir(wn):
        r = leak_rates(os.path.join(wn, 'train.txt'), os.path.join(wn, 'test.txt'))
        print(f"corpus/wn18rr: {r['n_test']} test triples, "
              f"EXACT overlap {r['exact']}, REVERSED leak {r['reversed']} ({r['reversed_pct']}%)")
        print()
    hits = scan()
    bad = [h for h, ok in hits if not ok]
    for h, ok in sorted(hits):
        print(f"  {'OK  ' if ok else 'WEAK'}  {h}")
    print(f"\n{len(hits)} file(s) use an exact-tuple leak control; {len(bad)} check only that order.")
    if bad:
        print("REFUSE: an exact-tuple intersection cannot detect a reversed-triple leak.")
        print("        On WN18RR it passes at 34.7% real leakage. Check both orders.")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
