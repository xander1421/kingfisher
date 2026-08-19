#!/usr/bin/env python3
"""S24 — when does checking a range-query proof stop being cheaper than doing
the query yourself?

WHY S85 DOES NOT ANSWER THIS
----------------------------
S85 settled verification against re-execution for MEMBERSHIP proofs. S20 then
measured the completeness verifier and found it REBUILDS THE ANSWER SUBTRIE
(`verify_completeness` calls `build(sorted(ks), pf['depth'])`), so its forced
work grows with the answer set -- 2,548 B hashed at 3.2 answers, 95,530 B at
1,943 -- while the authentication path SHRINKS over the same sweep, 2,304 B down
to 75 B. A cost that grows with the answer set has a crossover against doing the
work yourself; a cost that is flat in it does not.

WHAT "DOING IT YOURSELF" MEANS, STATED BEFORE MEASURING
--------------------------------------------------------
A client that does not take a proof must fetch the shard and CHECK IT, or it is
simply trusting the server and has bought nothing. Checking it means recomputing
the trie root from the keys and comparing to the committed root -- exactly
`build()` under the same counting hashlib. So both sides of this duel are sha256
work on the same instrument, in the same units, and neither is a wall time.
That matters here: `spikes/quiet.sh` REFUSES on this host and has all day, so a
seconds-denominated ratio would not be citable (§3, and W4's readset_table
precedent). **S85's published 238x-56,734x are wall-time ratios and nothing here
extends them.**

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If verifier work stays below the cost of rebuilding the whole shard across
    the entire reachable answer range, then a completeness proof is always
    cheaper than re-execution, S20's inversion is a curiosity rather than an
    operating constraint, and there is no crossover to publish.

Operationalised: the falsifier FIRES if `max(V(a)) < R` over the sweep, where
`R` is the bytes hashed to rebuild the whole key set's root.

THE PREDICTION, RECORDED SO IT CAN BE WRONG
-------------------------------------------
There is a crossover and it sits where the answer set approaches the shard,
because there the verifier rebuilds what the client would have rebuilt anyway,
plus an authentication path. The interesting number is not that it exists but
WHERE -- as a fraction of the shard, which is the form a client can act on.

  python3 range_crossover.py
"""
import os, sys, json, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
S20 = os.path.join(HERE, '..', 'S20_verify_kinds')
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
sys.path.insert(0, S20)
# S20 pins the COMMITTED trie_witness (blob 57d1a481) because the working-tree
# copy was uncommitted-modified; importing S20 inherits that pin, so this spike
# measures the same verifier S20 did rather than whatever is on disk now.
# DECLARED, not merely commented (H195): the flag is what `which_module.py`
# reads to tell a deliberate inheritance from a silent one.
import verify_kinds as S20M
USES_S20_PIN = True   # H195: deliberate, and machine-readable                                               # noqa: E402
from trie_witness import build, prove_completeness, verify_completeness    # noqa: E402
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402
from units import check_affine                                            # noqa: E402

SEED = 20260817
KEYS = os.path.join(S75, 'keys_triples.bin')
# Prefix lengths, not fractions: S20 measured that triple-key byte positions 8
# and 9 carry ONE distinct value each, so 8/9/10 are the same query and a
# fraction sweep silently duplicates points.
# Byte positions 0-2, 4-5 and 8-9 each carry ONE distinct value on this key set,
# so prefix lengths 1/2/3 are one query, 4/5/6 another and 8/9/10 a third. The
# lengths below are the DISTINCT ones, and 6/7/8/11 are exactly S20's so its
# operating points reproduce here rather than being approximated.
SWEEP = (1, 6, 7, 8, 11, 12)
PROBES = 60            # S20's count, so C1 compares equal things


def rebuild_cost(keys):
    """What a client pays to check the shard itself: recompute the root."""
    root, n, b = S20M.counted(build, sorted(set(keys)))
    return root, n, b


def measure(keys, root, prefix_len):
    rh = root.h
    stride = max(1, len(keys) // PROBES)
    qs = [k[:min(prefix_len, len(k))] for k in keys[::stride][:PROBES]]
    work, answers, wit, path, verified = [], [], [], [], 0
    for q in qs:
        pf = prove_completeness(root, q)
        ok, _n, b = S20M.counted(verify_completeness, rh, q, pf)
        if not ok:
            raise SystemExit('S24: a completeness proof failed to verify (A29)')
        verified += 1
        work.append(b)
        answers.append(len(pf.get('keys') or []))
        wit.append(S20M.witness_bytes(pf))
        path.append(S20M.auth_path_bytes(pf))
    return {'prefix_len': prefix_len, 'queries': len(qs), 'verified_true': verified,
            'answers': round(statistics.mean(answers), 3),
            'verify_hash_bytes': round(statistics.mean(work), 3),
            'witness_bytes': round(statistics.mean(wit), 3),
            'auth_path_bytes': round(statistics.mean(path), 3)}


def main():
    # S20 reads these .bin files with S84's reader (TW.load parses a DIFFERENT
    # format and silently returns a tuple), so the reader comes through S20's
    # own import of it rather than being written a third time.
    keys = S20M.S84M.read_keys(KEYS)
    root, rebuild_calls, rebuild_bytes = rebuild_cost(keys)
    shard_bytes = sum(len(k) for k in set(keys))

    rows = [measure(keys, root, L) for L in SWEEP]
    for r in rows:
        r['verify_per_rebuild'] = round(r['verify_hash_bytes'] / rebuild_bytes, 4)
        r['answers_frac_of_shard'] = round(r['answers'] / len(set(keys)), 5)
        r['bandwidth_frac_of_shard'] = round(r['witness_bytes'] / shard_bytes, 5)

    over = [r for r in rows if r['verify_hash_bytes'] >= rebuild_bytes]
    fired = not over

    out = {'seed': SEED, 'n_keys': len(set(keys)), 'shard_bytes': shard_bytes,
           'rebuild_hash_bytes': rebuild_bytes, 'rebuild_hash_calls': rebuild_calls,
           'rows': rows,
           'crossover': (None if fired else
                         {'first_prefix_len_at_or_above_rebuild': over[-1]['prefix_len'],
                          'answers_there': over[-1]['answers'],
                          'answers_frac_of_shard': over[-1]['answers_frac_of_shard']}),
           'falsifier_fired': fired}

    pts = [(r['answers'], r['verify_hash_bytes']) for r in rows]
    affine_ok, affine_why = check_affine(pts)
    out['affine'] = {'points_answers_vs_verify_bytes': pts,
                     'affine': bool(affine_ok), 'detail': affine_why}

    with open(os.path.join(HERE, 'range_crossover.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    # C1 -- GATING. S20's published operating point must reproduce here, on the
    # same instrument, before its extrapolation is priced against anything.
    prev = json.load(open(os.path.join(S20, 'verify_kinds.json')))
    prev_by_len = {r['prefix_len']: r for r in prev['answer_sweep']}
    deltas = {}
    for r in rows:
        p = prev_by_len.get(r['prefix_len'])
        if p:
            deltas['L%d' % r['prefix_len']] = {
                'answers_delta': round(r['answers'] - p['answer_keys'], 6),
                'verify_bytes_delta': round(r['verify_hash_bytes'] - p['hash_bytes'], 6),
                's24_probes': r['queries'], 's20_probes': p['n_proofs']}
    c = Control('C_S20_operating_points_reproduce',
                'S20 measured the completeness verifier at prefix lengths 6, 7, '
                '8 and 11 on this key set; those points must come back with the '
                'same answer sizes here before a crossover is drawn through them',
                null_must_contain='a different key file, prover or verifier '
                                  'would move the answer counts',
                can_fail_because='any shared prefix length disagrees on mean '
                                 'answer count (the probe counts differ by '
                                 'design -- 40 here against S20\'s 60 -- so the '
                                 'ANSWER means are what must agree)')
    c.observe(all(abs(v['answers_delta']) < 1e-6 for v in deltas.values()) and
              len(deltas) >= 3, deltas)
    C.append(c)

    # C2 -- the re-execution baseline must be the REAL alternative, not a
    # strawman: rebuilding must land on the prover's own root.
    root2, _n2, _b2 = rebuild_cost(keys)
    c = Control('C_rebuild_reaches_the_same_root',
                'the baseline is "fetch the shard and check it yourself", which '
                'is only the alternative if the rebuild reproduces the committed '
                'root -- otherwise it is a cheaper computation that proves '
                'nothing and the duel is rigged',
                null_must_contain='a rebuild that lands on a different root, '
                                  'which is what a client would see if the '
                                  'shard were tampered with',
                can_fail_because='the recomputed root differs from the prover\'s')
    c.observe(root2.h == root.h, {'root_prefix': root.h.hex()[:16],
                                  'rebuild_hash_bytes': rebuild_bytes,
                                  'rebuild_hash_calls': rebuild_calls,
                                  'shard_bytes': shard_bytes})
    C.append(c)

    # C3 -- A29. Every proof in the sweep verified TRUE.
    c = Control('C_every_proof_verified_true',
                'A29: counts taken inside a verifier that returned False on its '
                'first line would be small, stable and fictional',
                null_must_contain='a proof failing to verify, which raises '
                                  'SystemExit in the measurement loop',
                can_fail_because='any row has verified_true < queries')
    c.observe(all(r['verified_true'] == r['queries'] and r['queries'] > 0
                  for r in rows),
              {r['prefix_len']: [r['verified_true'], r['queries']] for r in rows})
    C.append(c)

    # C4 -- the two axes must move OPPOSITELY, or this is not the regime S20
    # found and the crossover is being drawn on the wrong curve.
    ordered = sorted(rows, key=lambda r: r['answers'])
    work_up = all(a['verify_hash_bytes'] <= b['verify_hash_bytes']
                  for a, b in zip(ordered, ordered[1:]))
    path_down = all(a['auth_path_bytes'] >= b['auth_path_bytes']
                    for a, b in zip(ordered, ordered[1:]))
    c = Control('C_inversion_present',
                'S20\'s inversion must be visible in this sweep: verifier work '
                'rising with answer size while the authentication path falls. If '
                'they moved together, the sweep is not the regime the crossover '
                'is about',
                null_must_contain='a sweep where both rise, which is what a '
                                  'verifier that only folded the path would give',
                can_fail_because='verify work is not monotone up in answer size, '
                                 'or the auth path is not monotone down')
    c.observe(work_up and path_down,
              {'by_answers': [(r['answers'], r['verify_hash_bytes'],
                               r['auth_path_bytes']) for r in ordered]})
    C.append(c)

    F = Falsifier('F_no_crossover',
                  refutes='this spike: if verifier work never reaches the cost '
                          'of rebuilding the shard, a range proof is always '
                          'cheaper to check than to redo and S20\'s inversion '
                          'is a curiosity, not an operating constraint',
                  fires_when='no swept answer size reaches the rebuild cost',
                  null_must_contain='a sweep whose largest answer set costs more '
                                    'to verify than the whole shard costs to '
                                    'rebuild')
    F.observe(fired, {'rebuild_hash_bytes': rebuild_bytes,
                      'max_verify_hash_bytes': max(r['verify_hash_bytes'] for r in rows),
                      'ratios': {r['prefix_len']: r['verify_per_rebuild'] for r in rows}})

    ok, problems = certify(
        HERE, deps=[S20],
        artifacts=[os.path.join(HERE, 'range_crossover.json')],
        controls=C, falsifiers=[F],
        measurements=[{'name': 'answers_vs_verify_hash_bytes', 'points': pts,
                       'as_rate': False}],
        falsifier='verifier work never reaching the cost of rebuilding the '
                  'shard, which would mean a range proof is always cheaper to '
                  'check than to redo')

    print(json.dumps({k: out[k] for k in ('n_keys', 'shard_bytes',
                                          'rebuild_hash_bytes', 'crossover',
                                          'falsifier_fired')},
                     indent=2, sort_keys=True))
    for r in rows:
        print('  L=%-3d answers=%8.1f (%.3f%% of shard)  verify=%9.1f B  '
              '= %.3f x rebuild   path=%7.1f B  witness=%9.1f B'
              % (r['prefix_len'], r['answers'], r['answers_frac_of_shard'] * 100,
                 r['verify_hash_bytes'], r['verify_per_rebuild'],
                 r['auth_path_bytes'], r['witness_bytes']))
    print('affine: %s (%s)' % (affine_ok, affine_why))
    print('falsifier F_no_crossover FIRED=%s' % fired)
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
