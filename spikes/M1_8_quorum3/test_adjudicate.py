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

assert adj([ok, ok, ok])[0]     == 'UNANIMOUS'
assert adj([ok, ok, bad])[0]    == 'MAJORITY'
assert adj([ok, bad, other])[0] == 'NO_QUORUM'
assert adj([None, None, None])[0] == 'NO_RESULTS'

# --- QUORUM SHRINKAGE. A worker that never answered did not agree; counting
# agreement over the survivors turns an availability failure into a clean
# verdict. That is craftable: hyperon panics above 1024 results, the threshold
# is result CARDINALITY, and the job author picks the program -- so a job can
# be authored to cross the limit on an honest device's shard but not on the
# attacker's, killing the honest workers. Q1's 72% capture assumed quorum SIZE
# was fixed. It is not.
v, k, n, disp, ret = adj([ok, ok, None])
assert v == 'REDUCED_QUORUM', v
assert (disp, ret) == (3, 2), (disp, ret)
assert v != 'UNANIMOUS' and v != 'MAJORITY', 'a short quorum must never read as agreement'
assert adj([ok, None, None])[0] == 'REDUCED_QUORUM'
# dispatched/returned are reported so the shrinkage is visible downstream
assert adj([ok, ok, ok])[3:] == (3, 3)
# two dispatched and two returned is a full quorum OF TWO -- different claim,
# and it is the caller's job to require 3 dispatched
assert adj([ok, ok])[0] == 'UNANIMOUS' and adj([ok, ok])[3:] == (2, 2)
# fuel is part of the key: same output, different fuel is a divergence (S57)
assert adj([ok, E(fuel='101'), E(fuel='102')])[0] == 'NO_QUORUM'
assert adj([ok, ok, E(fuel='999')])[0] == 'MAJORITY'
# status is part of the key: FUEL_EXHAUSTED != OK even at equal hash (S57 v1 bug)
assert adj([ok, ok, E(status='FUEL_EXHAUSTED')])[0] == 'MAJORITY'
assert adj([E(status='FUEL_EXHAUSTED'), E(status='FUEL_EXHAUSTED'), ok])[1][0] \
    == 'FUEL_EXHAUSTED'

# --- AGREED FAILURE is a fourth outcome, not a majority.
# `fuelrun` panics above 1024 results and exits 134 (SIGABRT) printing no
# fields, so the envelope has status CRASH and NO fuel_used. Three workers
# agreeing that a job died is deterministic and reproducible -- and it is still
# not a result. An earlier version returned MAJORITY here with CRASH in the key
# and expected the caller to notice; the caller did not, and `accepted` counted
# it. Formatting that None fuel_used also crashed the coordinator.
crash = E(status='CRASH', fuel=None, h=None)
assert adj([crash, crash, crash])[0] == 'AGREED_FAILURE'
assert adj([crash, crash, ok])[0]    == 'AGREED_FAILURE'
for st in ('CRASH', 'TIMEOUT', 'SHARD_MISSING', 'NO_PARSE'):
    e = E(status=st, fuel=None, h=None)
    assert adj([e, e, e])[0] == 'AGREED_FAILURE', st
# and a None fuel_used must not break the key
assert adj([crash, crash, crash])[1] == ('CRASH', None, None)
print('adjudicate: 24 assertions pass')
