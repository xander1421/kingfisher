#!/usr/bin/env python3
"""S36 — witnessed verification, driven as a JOB, on the case replication cannot reach.

M1-DEMO (§8) item 6 is *"witnessed verification demonstrated on at least one job
class"*. The W2 -> S20 -> S24 -> S27 chain was built for that line and has never
been driven end to end as a job: proofs were measured, never adjudicated.

THE JOB CLASS
-------------
A prefix range query over the real-KG key set S24 and S27 already measure. Two
envelope shapes for the same job:

  REPLICATION -- a worker returns the answer set; a second worker's bytes are
                 compared to it. This is M1.8's quorum, in miniature.
  WITNESSED   -- one worker returns the answer PLUS a completeness proof against
                 the shard root; a single verifier decides alone.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If a single witnessed verifier cannot reject a cheat that a 2-of-2
    replication check would catch, the witnessed route buys nothing over plain
    replication and the honest recommendation for this job class is quorum alone.

THE CASE THAT DECIDES IT, AND IT IS NOT THE HONEST ONE
-------------------------------------------------------
Replication catches a lying member only when the members are INDEPENDENT. M1.8's
own verdict on the real run is `INSUFFICIENT_DOMAINS` -- 50 of 64 jobs -- and
S26 measured the other half: a WRONG REPLICA is caught 0/64, because two copies
of the same wrong computation agree. So the demonstration drives three worlds:

  1. honest pair                  -> both routes accept, and must AGREE
  2. one liar, honest peer        -> both routes reject
  3. two non-independent liars    -> replication ACCEPTS (they agree with each
                                     other), the witnessed verifier REJECTS

World 3 is the whole argument for witnessing, and it is the one no amount of
quorum size fixes.

COST IS NOT RE-DERIVED. S24 measured the verify-vs-rebuild crossover on this key
set and it is cited, not recomputed.

  python3 witnessed_job.py
"""
import os, sys, json, copy, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
S20 = os.path.join(HERE, '..', 'S20_verify_kinds')
S24 = os.path.join(HERE, '..', 'S24_range_crossover')
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
sys.path.insert(0, S20)
# S20's pin of the COMMITTED trie_witness, inherited by importing it.
import verify_kinds as S20M                                               # noqa: E402
from trie_witness import build, prove_completeness, verify_completeness    # noqa: E402
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402

SEED = 20260817
KEYS = os.path.join(S75, 'keys_triples.bin')
PREFIX_LEN = 8            # S24's operating point: ~97 answers, 2.4% of the shard
JOBS = 40


def answer_bytes(keys):
    """The canonical result envelope a replicating worker returns: the answer set
    in sorted order, length-prefixed, hashed. This is M1.8's `sorted_hash` in the
    shape a range job needs -- byte-comparable, order-independent by
    construction."""
    b = b''.join(len(k).to_bytes(2, 'big') + k for k in sorted(keys))
    return b, hashlib.sha256(b).hexdigest()


def replicate(env_a, env_b):
    """M1.8's adjudication in miniature: agreement is byte equality of the
    result member. Returns (verdict, agree)."""
    return ('AGREE', True) if env_a['hash'] == env_b['hash'] else ('DISAGREE', False)


def witness_verify(root_hash, q, env):
    """One verifier, no peers: the proof must verify AND its answer set must be
    exactly the answer the envelope reports."""
    pf = env.get('proof')
    if pf is None:
        return False
    if not verify_completeness(root_hash, q, pf):
        return False
    _b, h = answer_bytes(pf['keys'])
    return h == env['hash']


def make_env(root, q, keys, cheat=None):
    """A worker's envelope for one job. `cheat` mutates the ANSWER, and the proof
    is then built to match the worker's claim -- which is what a lying worker
    would do, and is the only version of the test that means anything: a liar
    who ships an honest proof of the honest answer has not lied."""
    ans = list(keys)
    if cheat == 'omit':
        ans = ans[1:]
    elif cheat == 'add':
        ans = ans + [b'\xff' * len(ans[0])]
    elif cheat == 'alter':
        k = ans[-1]
        ans = ans[:-1] + [k[:-1] + bytes([k[-1] ^ 0x01])]
    b, h = answer_bytes(ans)
    pf = prove_completeness(root, q)
    if cheat is not None:
        # the liar rewrites the proof's key list to match its claim; the
        # authentication path is the honest one it received from the store.
        pf = copy.deepcopy(pf)
        pf['keys'] = sorted(ans)
    return {'answer_bytes': len(b), 'hash': h, 'proof': pf, 'n': len(ans)}


def main():
    keys = S20M.S84M.read_keys(KEYS)
    root = build(sorted(set(keys)))
    rh = root.h
    ks = sorted(set(keys))
    stride = max(1, len(ks) // JOBS)
    queries = [k[:PREFIX_LEN] for k in ks[::stride][:JOBS]]

    worlds = {'honest_pair': {'replication': [], 'witnessed': []},
              'one_liar_honest_peer': {'replication': [], 'witnessed': []},
              'two_non_independent_liars': {'replication': [], 'witnessed': []}}
    skipped = 0
    for q in queries:
        true_pf = prove_completeness(root, q)
        answer = true_pf.get('keys') or []
        if len(answer) < 3:
            skipped += 1
            continue

        honest = make_env(root, q, answer)
        liar = make_env(root, q, answer, cheat='omit')
        liar2 = copy.deepcopy(liar)           # a second worker running the SAME
                                              # wrong computation: not independent

        # world 1 -- honest pair
        v, agree = replicate(honest, make_env(root, q, answer))
        worlds['honest_pair']['replication'].append(agree)
        worlds['honest_pair']['witnessed'].append(witness_verify(rh, q, honest))

        # world 2 -- one liar, honest peer
        v, agree = replicate(honest, liar)
        worlds['one_liar_honest_peer']['replication'].append(not agree)
        worlds['one_liar_honest_peer']['witnessed'].append(
            not witness_verify(rh, q, liar))

        # world 3 -- two non-independent liars, and nobody honest in the quorum
        v, agree = replicate(liar, liar2)
        worlds['two_non_independent_liars']['replication'].append(not agree)
        worlds['two_non_independent_liars']['witnessed'].append(
            not witness_verify(rh, q, liar))

    def rate(v):
        return {'n': len(v), 'correct': sum(1 for x in v if x),
                'rate': round(sum(1 for x in v if x) / len(v), 4) if v else None}

    out = {'seed': SEED, 'prefix_len': PREFIX_LEN, 'jobs': len(queries),
           'skipped_small_answers': skipped,
           'worlds': {w: {r: rate(v) for r, v in d.items()}
                      for w, d in worlds.items()}}

    # each tamper class, against the single verifier
    tampers = {}
    for c in ('omit', 'add', 'alter'):
        rejected = 0
        n = 0
        for q in queries:
            pf = prove_completeness(root, q)
            if len((pf.get('keys') or [])) < 3:
                continue
            n += 1
            env = make_env(root, q, pf['keys'], cheat=c)
            rejected += 0 if witness_verify(rh, q, env) else 1
        tampers[c] = {'n': n, 'rejected': rejected}
    out['tamper_classes'] = tampers

    # cost, cited not recomputed
    s24 = json.load(open(os.path.join(S24, 'range_crossover.json')))
    row = next(r for r in s24['rows'] if r['prefix_len'] == PREFIX_LEN)
    out['cost_cited_from_S24'] = {
        'verify_hash_bytes': row['verify_hash_bytes'],
        'rebuild_hash_bytes': s24['rebuild_hash_bytes'],
        'verify_per_rebuild': row['verify_per_rebuild'],
        'answers': row['answers'], 'shard_bytes': s24['shard_bytes'],
        'witness_bytes': row['witness_bytes']}

    w = out['worlds']
    fired = not (w['two_non_independent_liars']['witnessed']['rate'] == 1.0 and
                 w['two_non_independent_liars']['replication']['rate'] == 0.0)
    out['falsifier_fired'] = fired

    with open(os.path.join(HERE, 'witnessed_job.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    c = Control('C_honest_jobs_accepted_by_both',
                'both routes must ACCEPT the honest job, or the comparison is '
                'between a verifier and a broken verifier rather than between '
                'two ways of deciding the same question',
                null_must_contain='a verifier that rejects everything would '
                                  'score perfectly on the cheat worlds and fail '
                                  'here',
                can_fail_because='any honest job is rejected by either route')
    c.observe(w['honest_pair']['replication']['rate'] == 1.0 and
              w['honest_pair']['witnessed']['rate'] == 1.0,
              w['honest_pair'])
    C.append(c)

    c = Control('C_replication_works_when_independent',
                'replication must CATCH the liar when the peer is honest -- '
                'otherwise world 3 proves nothing, because the baseline would be '
                'broken rather than blind',
                null_must_contain='a replication check that cannot see a '
                                  'differing answer at all',
                can_fail_because='the honest-peer world is not caught at 100%')
    c.observe(w['one_liar_honest_peer']['replication']['rate'] == 1.0,
              w['one_liar_honest_peer'])
    C.append(c)

    c = Control('C_all_three_tampers_rejected',
                'the single verifier must reject an OMITTED, an ADDED and an '
                'ALTERED answer -- one tamper class rejected could be an '
                'accident of encoding',
                null_must_contain='a verifier that only checks the answer count, '
                                  'which would accept the altered key',
                can_fail_because='any tamper class has rejected < n')
    c.observe(all(v['rejected'] == v['n'] and v['n'] > 0 for v in tampers.values()),
              tampers)
    C.append(c)

    c = Control('C_jobs_have_real_answers',
                'a job whose answer is one or two keys makes omission trivial '
                'and the demonstration vacuous; jobs below three answers are '
                'skipped and the count is reported',
                null_must_contain='a query set that returns single keys, which '
                                  'is what a long prefix would give',
                can_fail_because='fewer than 10 jobs survived the filter')
    c.observe(len(queries) - skipped >= 10,
              {'jobs': len(queries), 'skipped': skipped,
               'answers_at_this_prefix': out['cost_cited_from_S24']['answers']})
    C.append(c)

    F = Falsifier('F_witnessing_buys_nothing',
                  refutes='the witnessed route for this job class: if one '
                          'verifier cannot reject what a 2-of-2 replication '
                          'check catches, quorum alone is the honest '
                          'recommendation',
                  fires_when='the witnessed verifier fails to reject the '
                             'non-independent liars, or replication catches them',
                  null_must_contain='two identical wrong answers, which is '
                                    'exactly what replication reads as agreement')
    F.observe(fired, {'two_non_independent_liars': w['two_non_independent_liars'],
                      'one_liar_honest_peer': w['one_liar_honest_peer']})

    ok, problems = certify(
        HERE, deps=[S20, S24],
        artifacts=[os.path.join(HERE, 'witnessed_job.json')],
        controls=C, falsifiers=[F],
        falsifier='a single witnessed verifier failing to reject a cheat that '
                  '2-of-2 replication catches, which would make the witnessed '
                  'route redundant for this job class')

    print(json.dumps(out, indent=2, sort_keys=True)[:1400])
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
