#!/usr/bin/env python3
"""One runnable check on the only non-trivial logic in M1.8.
The adjudicator decides what counts as agreement; every attack in Q1 lands here."""
import importlib.util, os, sys
spec = importlib.util.spec_from_loader('q3', loader=None)
q3 = importlib.util.module_from_spec(spec)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'q3.py')).read()
q3.__dict__['__file__'] = 'q3.py'
exec(src.split('def main()')[0], q3.__dict__)   # load helpers, skip main
adj = q3.adjudicate

def E(status='OK', fuel='100', h='aa'):
    return {'status': status, 'fuel_used': fuel, 'sorted_hash': h}

ok, bad, other = E(), E(h='bb'), E(h='cc')

assert adj([ok, ok, ok])[:1]    == ('UNANIMOUS',)
assert adj([ok, ok, bad])[:1]   == ('MAJORITY',)
assert adj([ok, bad, other])[0] == 'NO_QUORUM'
assert adj([None, None, None])[0] == 'NO_RESULTS'
# a missing replica must not manufacture a majority from one survivor
assert adj([ok, None, None])[0] == 'NO_QUORUM'
assert adj([ok, ok, None])[:1]  == ('MAJORITY',)
# fuel is part of the key: same output, different fuel is a divergence (S57)
assert adj([ok, E(fuel='101'), E(fuel='102')])[0] == 'NO_QUORUM'
assert adj([ok, ok, E(fuel='999')])[:1] == ('MAJORITY',)
# status is part of the key: FUEL_EXHAUSTED != OK even at equal hash (S57 v1 bug)
assert adj([ok, ok, E(status='FUEL_EXHAUSTED')])[:1] == ('MAJORITY',)
assert adj([E(status='FUEL_EXHAUSTED'), E(status='FUEL_EXHAUSTED'), ok])[1][0] \
    == 'FUEL_EXHAUSTED'
# two crashes agreeing are NOT an accepted result they are an agreed failure;
# the verdict says MAJORITY and the key carries CRASH. Caller must read the key.
assert adj([E(status='CRASH'), E(status='CRASH'), ok])[1][0] == 'CRASH'
print('adjudicate: 11 assertions pass')
