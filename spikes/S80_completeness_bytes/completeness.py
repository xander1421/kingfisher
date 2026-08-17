#!/usr/bin/env python3
"""S80 — the third proof kind. S79 said it does not follow by inspection.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If completeness proof cost does NOT order the three key sets the way
    membership and absence do, then "proof size is set by branching" is a claim
    about POINT queries only, and S77/S79 must say so.

WHY IT DOES NOT FOLLOW FROM S79
-------------------------------
Membership and absence both terminate at a point: one path, one divergence. A
completeness proof answers a RANGE -- "these are exactly the keys under prefix q"
-- so it has two parts with different scaling:

  * the AUTH PATH to q, which is siblings, exactly like the other two, and which
    W2 measured as 1.5-2.4 KB and called "independent of answer size";
  * the ANSWER ITSELF, which is every key under q and has nothing to do with
    branching on the way there.

So the honest question is not "does completeness track branching" but "which
PART does", and reporting a single total would hide it. That is A18's shape --
one number standing for two mechanisms -- and this spike separates them before
measuring rather than after.

QUERIES ARE PREFIXES OF REAL KEYS, TAKEN AT A FIXED FRACTION OF KEY LENGTH,
because a query drawn at a fixed BYTE depth would sit near the root of the
1,155-byte atom keys and near the leaf of the 12-byte triple keys -- comparing
two different regimes and calling it a comparison (A27's shape, one step up).

  python3 completeness.py
"""
import os, sys, json, struct
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from trie_witness import (build, prove_completeness, verify_completeness,   # noqa: E402
                          steps_bytes)
from kfcheck import certify                                                 # noqa: E402
from provenance import Control, Falsifier                                   # noqa: E402

SEED = 20260817
DIGEST = 32
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
S77 = os.path.join(HERE, '..', 'S77_proof_bytes')
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples', os.path.join(S75, 'keys_triples.bin'))]
QUERIES = 120
FRACTION = 0.75          # query prefix length as a fraction of the key's length


def read_keys(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    out, i = [], 4
    for _ in range(n):
        (ln,) = struct.unpack_from('<H', b, i)
        i += 2
        out.append(b[i:i + ln])
        i += ln
    return out


def child_map(keys):
    kids = defaultdict(set)
    for k in keys:
        for i in range(len(k)):
            kids[k[:i]].add(k[i])
    return kids


def path_siblings(q, kids):
    """Digests on the auth path to q -- the same charge S77 measured and C14
    validated at 0.00%, applied to a prefix instead of a whole key."""
    s = 0
    for i in range(len(q)):
        c = kids.get(q[:i])
        if c is None:
            break
        if len(c) > 1:
            s += len(c) - 1
    return s


def main():
    prev = json.load(open(os.path.join(S77, 'measure.json')))
    out = {'seed': SEED, 'digest_bytes': DIGEST, 'queries_per_set': QUERIES,
           'query_prefix_fraction': FRACTION, 'sets': {}}
    cs = []

    for name, path in SETS:
        keys = read_keys(path)
        kids = child_map(keys)
        stride = max(1, len(keys) // QUERIES)
        sampled = keys[::stride][:QUERIES]
        qs = [k[:max(1, int(len(k) * FRACTION))] for k in sampled]
        # Scale is checked against the SAMPLE's own mean key length, not the
        # population's. The first run compared the sampled query mean against
        # S77's whole-corpus mean_key_bytes -- two different populations -- and
        # C_queries_are_scale_matched correctly refused the run as VOID. Fixed
        # rather than loosened: widening the tolerance would have made a real
        # mismatch invisible on the next corpus.
        sample_mean_key_bytes = sum(len(k) for k in sampled) / len(sampled)

        # Membership recomputed on the SAME sampled keys. S77's figure is a mean
        # over ALL keys, and comparing it against a 120-key sample mean is the
        # population mismatch that already made C_queries_are_scale_matched refuse
        # this run once. Fixed in both places rather than only where it was caught.
        mem_sample = sum(path_siblings(k, kids) for k in sampled) / len(sampled) * DIGEST

        root = build(sorted(set(keys)))
        rh = root.h
        auth, answers, real_total, verified, covers = [], [], [], 0, 0
        for q in qs:
            auth.append(path_siblings(q, kids) * DIGEST)
            pf = prove_completeness(root, q)
            if pf is None:
                continue
            covers += (pf.get('kind') == 'cover')
            answers.append(len(pf.get('keys') or []))
            real_total.append(steps_bytes(pf['steps']))
            verified += bool(verify_completeness(rh, q, pf))
        n = len(auth)
        out['sets'][name] = {
            'queries': n,
            'mean_query_bytes': sum(len(q) for q in qs) / len(qs),
            'sample_mean_key_bytes': sample_mean_key_bytes,
            'mean_answer_keys': sum(answers) / len(answers),
            'max_answer_keys': max(answers),
            'auth_path_bytes_mean': sum(auth) / n,
            'w2_real_step_bytes_mean': sum(real_total) / len(real_total),
            'membership_auth_bytes_corpus': prev['sets'][name]['pathmap_auth_bytes_mean'],
            'membership_auth_bytes_same_sample': mem_sample,
            'covers': covers, 'verified': verified, 'proofs': len(real_total)}

    a = out['sets']

    c = Control('C_completeness_proofs_verify',
                'a completeness proof that its own verifier rejects is a number '
                'about nothing, and this is the proof kind whose verifier is the '
                'anti-omission check -- W2 drives it to False with C_omit / C_add '
                '/ C_tamper',
                null_must_contain="W2's verify_completeness, which returns False "
                                  'on an omitted, added or tampered key and is '
                                  'free to reject every proof here',
                can_fail_because='any completeness proof fails verification, or '
                                 'any query fails to cover')
    c.observe(all(v['verified'] == v['proofs'] and v['covers'] == v['proofs']
                  for v in a.values()),
              {n: {'proofs': v['proofs'], 'verified': v['verified'],
                   'covers': v['covers']} for n, v in a.items()})
    cs.append(c)

    # THE FALSIFIER, on the AUTH PATH half only -- which is the half the claim is
    # about. Stating it on the total would let the answer set decide the verdict.
    mem_order = sorted(a, key=lambda n: a[n]['membership_auth_bytes_same_sample'])
    auth_order = sorted(a, key=lambda n: a[n]['auth_path_bytes_mean'])
    tracks = auth_order == mem_order

    # A CONTROL IS AN INSTRUMENT CHECK; A FALSIFIER IS A VERDICT. Conflating them
    # was a defect in the first draft of this file, and `certify` exposed it: the
    # falsifier fired -- a real negative result -- and certify could only report
    # "DID NOT FIRE, run is VOID". That is A21 exactly: a test that cannot express
    # its verdict. `Control` is documented as "a positive control that MUST fire",
    # so a control whose failure IS the finding makes every negative result
    # indistinguishable from a broken run.
    #
    # This is NOT weakening a gate to pass it (§5). The gate now asserts something
    # strictly checkable that the previous version never checked: that the
    # comparison was CAPABLE of coming out either way -- three sets, real verified
    # proofs, and auth-path values far enough apart to order without a tie. The
    # verdict itself is published in out['verdict'], where a reader cannot mistake
    # it for a passing check.
    spread = (max(v['auth_path_bytes_mean'] for v in a.values())
              / min(v['auth_path_bytes_mean'] for v in a.values()))
    # H20 LANDED: the verdict is now a Falsifier, recorded with its outcome and
    # NOT gating `ok`. This spike is what found that `Control` could not express a
    # negative -- it fired, and certify called the run VOID -- so it is the right
    # place to prove the fix end to end. The decidability control below STAYS: it
    # is an instrument check and belongs in the gate, which is exactly the
    # distinction H20 is about.
    fal = Falsifier(
        'F_branching_rule_is_point_query_only',
        refutes="S77's \"proof size is set by branching, not key length\" as a "
                'statement about key sets rather than about point queries',
        fires_when='the completeness auth-path ordering differs from the '
                   'membership ordering on these three key sets',
        null_must_contain='three key sets free to rank in any of six orders '
                          'under either measure, so agreement and disagreement '
                          'are both expressible')
    fal.observe(not tracks,
                {'by_membership': mem_order, 'by_auth_path': auth_order,
                 'auth_bytes': {n: a[n]['auth_path_bytes_mean'] for n in a},
                 'membership_bytes_same_sample':
                     {n: a[n]['membership_auth_bytes_same_sample'] for n in a}})

    c = Control('C_auth_path_comparison_is_decisive',
                "the falsifier here is an ORDERING, so what has to be checked is "
                'that the ordering was decidable at all: three sets, real verified '
                'proofs, and values far enough apart that the ranking is not noise',
                null_must_contain='auth-path values free to tie or to sit within '
                                  'rounding of each other, in which case no '
                                  'ordering claim could be made in either direction',
                can_fail_because='fewer than three sets produced proofs, or the '
                                 'largest and smallest auth-path means are within '
                                 '5% of each other, making the ranking noise')
    c.observe(len(a) == 3 and spread > 1.05,
              {'auth_bytes': {n: a[n]['auth_path_bytes_mean'] for n in a},
               'membership_bytes_same_sample':
                   {n: a[n]['membership_auth_bytes_same_sample'] for n in a},
               'spread_max_over_min': spread,
               'by_membership': mem_order, 'by_auth_path': auth_order,
               'VERDICT_auth_path_tracks_branching': tracks})
    cs.append(c)

    # THE SEPARATION, which is the reason this spike is not a footnote to S79: the
    # answer half must be shown to vary independently, or "two parts with
    # different scaling" is a story rather than a measurement.
    ans = {n: a[n]['mean_answer_keys'] for n in a}
    ans_order = sorted(a, key=lambda n: ans[n])
    c = Control('C_answer_size_is_a_separate_axis',
                'if the answer set ordered the sets the same way the auth path '
                'does, a single total would be safe to publish and the separation '
                'this spike insists on would be decoration',
                null_must_contain='answer sizes free to correlate with the auth '
                                  'path -- nothing in the construction forces the '
                                  'two orderings apart, and on a different corpus '
                                  'they could coincide',
                can_fail_because='the answer-size ordering matches the auth-path '
                                 'ordering, making the two axes indistinguishable '
                                 'on this corpus')
    c.observe(ans_order != auth_order,
              {'by_answer_keys': ans_order, 'by_auth_path': auth_order,
               'mean_answer_keys': ans,
               'max_answer_keys': {n: a[n]['max_answer_keys'] for n in a}})
    cs.append(c)

    c = Control('C_queries_are_scale_matched',
                'a query taken at a fixed BYTE depth sits near the root of a '
                '1,155-byte atom key and near the leaf of a 12-byte triple key, '
                'which compares two regimes and calls it a comparison',
                null_must_contain='the key lengths themselves, which differ by '
                                  '90x across these sets and would produce wildly '
                                  'unmatched query depths under a fixed-byte rule',
                can_fail_because='mean query length is not close to FRACTION of '
                                 'mean key length for every set')
    ok_scale = all(abs(v['mean_query_bytes'] / v['sample_mean_key_bytes'] - FRACTION)
                   < 0.05 for v in a.values())
    c.observe(ok_scale,
              {n: {'mean_query_bytes': v['mean_query_bytes'],
                   'sample_mean_key_bytes': v['sample_mean_key_bytes'],
                   'ratio': v['mean_query_bytes'] / v['sample_mean_key_bytes'],
                   'corpus_mean_key_bytes': prev['sets'][n]['mean_key_bytes']}
               for n, v in a.items()})
    cs.append(c)

    out['verdict'] = {
        'auth_path_tracks_branching': tracks,
        'by_membership': mem_order, 'by_auth_path': auth_order,
        'finding': ('the completeness auth path orders the key sets DIFFERENTLY '
                    'from membership, so "proof size is set by branching" is a '
                    'POINT-QUERY claim and S77/S79 must carry that scope')
                   if not tracks else
                   ('the completeness auth path orders the key sets the same way '
                    'membership does, so the branching rule extends to range '
                    'queries')}
    out['falsifier'] = fal.as_dict()
    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    with open(os.path.join(HERE, 'completeness.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[HERE], artifacts=[os.path.join(HERE, 'completeness.json')],
        controls=cs, falsifiers=[fal],
        falsifier='if the completeness AUTH PATH orders the three key sets '
                  'differently from membership, then "proof size is set by '
                  'branching" is a claim about point queries only and S77/S79 '
                  'overreached',
        note='S80 separates the auth path from the answer set BEFORE measuring, '
             'because a single total would let the answer size decide a verdict '
             'about branching (A18). Counts and digests only, no timings.')
    for p in problems:
        print('  PROBLEM ' + p)

    print(f"{'set':<16} {'query B':>8} {'answers':>8} {'auth B':>8} "
          f"{'mem B':>8} {'W2 step B':>10}")
    for n, v in a.items():
        print(f"{n:<16} {v['mean_query_bytes']:>8.1f} {v['mean_answer_keys']:>8.2f} "
              f"{v['auth_path_bytes_mean']:>8.0f} "
              f"{v['membership_auth_bytes_same_sample']:>8.0f} "
              f"{v['w2_real_step_bytes_mean']:>10.0f}")
    print(f"order by membership : {mem_order}")
    print(f"order by auth path  : {auth_order}")
    print(f"order by answer size: {ans_order}")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(f"  {'FIRED ' if fal.fired else 'quiet '} {fal.name} -- {fal.as_dict()['verdict']}")
    print(f"certify ok={ok}  (a fired falsifier no longer voids the run -- H20)")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
