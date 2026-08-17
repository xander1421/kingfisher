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

def E(status='OK', fuel='100', h='aa', domain='d1'):
    return {'status': status, 'fuel_used': fuel, 'sorted_hash': h,
            'domain': domain}


def D(n):
    """n envelopes agreeing, each in its own failure domain."""
    return [E(domain=f'dom{i}') for i in range(n)]

ok, bad, other = E(), E(h='bb'), E(h='cc')
q3.MIN_DOMAINS = 1  # most cases below are about agreement, not independence

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
v, k, n, disp, ret, _ = adj([ok, ok, None])
assert v == 'REDUCED_QUORUM', v
assert (disp, ret) == (3, 2), (disp, ret)
assert v != 'UNANIMOUS' and v != 'MAJORITY', 'a short quorum must never read as agreement'
assert adj([ok, None, None])[0] == 'REDUCED_QUORUM'
# dispatched/returned are reported so the shrinkage is visible downstream
assert adj([ok, ok, ok])[3:5] == (3, 3)
# two dispatched and two returned is a full quorum OF TWO -- different claim,
# and it is the caller's job to require 3 dispatched
assert adj([ok, ok])[0] == 'UNANIMOUS' and adj([ok, ok])[3:5] == (2, 2)
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
# --- INDEPENDENCE. A worker that never had an independent failure mode did not
# provide an independent check. Two workers on one binary and one host share
# libm, clock, page tables and the 1024-result panic, so their agreement is
# nearly free. REDUCED_QUORUM cannot see this: dispatched=3, returned=3, and the
# domain count is 1.
q3.MIN_DOMAINS = 3

def W(wid, **axes):
    """Register a worker's COORDINATOR-OBSERVED domain vector and return an
    envelope for it. The adjudicator reads OBSERVED, never the envelope -- a
    test that sets a `domain` field on the envelope exercises a path the code
    does not take, and will pass on {None} collapsing to one domain."""
    base = dict(binary='b1', manifest='m1', host='h1', os='o1', isa='i1',
                operator='UNATTESTED')
    base.update(axes)
    q3.OBSERVED[wid] = base
    return E(domain=wid) | {'worker': wid}

q3.OBSERVED.clear()
same = [W('a'), W('b'), W('c')]                       # identical on every axis
v, k, n, disp, ret, dom = adj(same)
assert v == 'INSUFFICIENT_DOMAINS', v
assert (disp, ret, dom) == (3, 3, 1), (disp, ret, dom)
assert v != 'UNANIMOUS', 'three seats in one domain must not read as unanimous'

# the real M1 setup: 2 host workers on one binary + 1 phone.
# host/os/isa give 2 domains; operator and manifest give 1, and the WEAKEST
# axis binds -- which is the whole reason the count is a vector.
q3.OBSERVED.clear()
mixed = [W('a'), W('b'), W('p', binary='b2', host='h2', os='o2')]
v2, _, _, _, _, dom2 = adj(mixed)
assert v2 == 'INSUFFICIENT_DOMAINS', v2
assert dom2 == 1, f'operator/manifest are shared, so the weakest axis is 1, got {dom2}'
pc = mixed[0]['_per_class']
assert pc['host'] == 2 and pc['os'] == 2 and pc['binary'] == 2, pc
assert pc['operator'] == 1 and pc['manifest'] == 1, pc

# three genuinely independent domains on EVERY axis
q3.OBSERVED.clear()
indep = [W(f'w{i}', binary=f'b{i}', manifest=f'm{i}', host=f'h{i}',
           os=f'o{i}', isa=f'i{i}', operator=f'op{i}') for i in range(3)]
v3, _, _, _, _, dom3 = adj(indep)
assert v3 == 'UNANIMOUS' and dom3 == 3, (v3, dom3)

# a shared MANIFEST alone caps it: same feature set means the same
# feature-induced fault, whatever the digests say
q3.OBSERVED.clear()
shared_man = [W(f'w{i}', binary=f'b{i}', host=f'h{i}', os=f'o{i}',
                isa=f'i{i}', operator=f'op{i}') for i in range(3)]
assert adj(shared_man)[0] == 'INSUFFICIENT_DOMAINS'
assert adj(shared_man)[5] == 1, 'one manifest is one domain on that axis'

q3.OBSERVED.clear()
# domains are counted among AGREEING workers only -- a dissenter in a third
# domain does not lend independence to the majority
q3.MIN_DOMAINS = 2
q3.OBSERVED.clear()
a1, a2 = W('x', host='h1'), W('y', host='h1')
dis = W('z', host='h9', binary='b9', manifest='m9', os='o9', isa='i9', operator='op9')
dis['sorted_hash'] = 'zz'                      # disagrees
split = [a1, a2, dis]
assert adj(split)[0] == 'INSUFFICIENT_DOMAINS', adj(split)[0]
assert adj(split)[5] == 1, 'the dissenter must not be counted as a domain'
q3.MIN_DOMAINS = 1
q3.OBSERVED.clear()

print('adjudicate: 36 assertions pass')

# --- SOUNDNESS: an empty result member must never read as agreement. -----------
# Reported by a fresh reviewer 2026-08-17 and reproduced before the fix: key()
# guarded results_text for ABSENCE and not EMPTINESS, so canon('') -> '' ->
# sha256('') = e3b0c442..., and three workers returning an empty results block
# keyed IDENTICALLY and adjudicated UNANIMOUS -- agreement on nothing. Because
# key() prefers results_text when present, an empty block also silently DISCARDED
# the worker's own sorted_hash. Masked in production only by MIN_DOMAINS under
# operator=1, i.e. it would have activated the day an attestation root landed.
#
# These assertions fail if the guard is reverted.
_ok  = {'status': 'OK', 'fuel_used': 100, 'sorted_hash': 'abc123', 'results_text': '(A B)'}
def _with(**kw):
    e = dict(_ok); e.update(kw); return e

for _label, _e in [('empty results_text', _with(results_text='')),
                   ('blank results_text', _with(results_text='   ')),
                   ('empty sorted_hash',  _with(results_text=None, sorted_hash='')),
                   ('null  sorted_hash',  _with(results_text=None, sorted_hash=None))]:
    assert key(_e) is None, f'{_label}: an empty result member produced an agreement key'
    assert adj([_with(**{}), _e, _e])[0] != 'UNANIMOUS', f'{_label}: adjudicated UNANIMOUS'
    assert adj([_e, _e, _e])[0] in ('NO_RESULTS', 'REDUCED_QUORUM'), _label

# The empty-hash CONSTANT arriving as if it were a result is refused too.
assert key(_with(results_text=None,
                 sorted_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')) is None

# A FAILED worker legitimately has no result member, and agreement that a job
# failed is a different verdict from agreement on a result. The first version of
# the guard omitted this and turned three crashes into NO_RESULTS; line 62 caught
# it. This pins the boundary so the fix cannot be widened back over it.
_crash = {'status': 'CRASH', 'fuel_used': None, 'sorted_hash': None, 'results_text': None}
assert adj([_crash, _crash, _crash])[0] == 'AGREED_FAILURE'

# ARITY. Every path returns 6; NO_RESULTS returned 5 while the only production
# caller unpacks 6, so total quorum loss crashed the coordinator instead of
# recording the verdict. Asserting [0] alone is what let it through.
for _envs in ([None, None, None], [_ok, _ok, _ok], [_crash, _crash, _crash]):
    assert len(adj(_envs)) == 6, f'arity {len(adj(_envs))} != 6 for {_envs[0]}'

print('soundness: empty result member cannot agree; arity uniform at 6')
