#!/usr/bin/env python3
"""S79 — S77 measured MEMBERSHIP only. Absence is the proof this project sells.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If non-membership proof cost does NOT track branching the way membership
    does, then "proof size is set by branching, not key length" is a
    membership-only statement and S77 must say so.

WHY THIS ONE MATTERS MORE THAN MEMBERSHIP
-----------------------------------------
W2's whole contribution over W1 was that absence is provable at all: W1 had no
verification function, so its four controls were dead. The verifiable job class
is trie-only queries, and the query that needs a proof is the one that returns
nothing. So the number that carries weight is W2's published **~2.0 KB on the
realistic miss**, and S75 restated it as "~3.6-5.8 KB on real pathmap" -- which
S77 retracted along with everything else derived from depth, WITHOUT putting a
corrected figure in its place. This closes that.

THE MODEL, AND WHERE IT DIFFERS FROM MEMBERSHIP
-----------------------------------------------
A membership proof charges (children - 1) at each branching position on the path:
the siblings not taken. An ABSENCE proof charges the same along the shared
prefix, and then at the DIVERGENCE position it must carry **every** child of that
node -- all `children` digests, not children - 1 -- because the claim is that the
byte it needs is not among them. Showing a subset would let a prover hide the
child that makes the key present. That +1 is the entire structural difference and
it is stated here before the numbers.

THE INSTRUMENT IS THE ONE C14 VALIDATED
---------------------------------------
The sibling walk is computed in Python from the key sets alone. That is not a
shortcut around Rust: C14 attacked S77 by recomputing its pathmap walk this exact
way and got 0.00% relative difference on all three sets, so the Python recount IS
the validated instrument, and using it here means no new unvalidated code sits
under the number. W2's real prove_non_membership runs beside it and every proof
is verified.

  python3 absence.py
"""
import os, sys, json, struct
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from trie_witness import (build, prove_membership, prove_non_membership,   # noqa: E402
                          verify_non_membership, steps_bytes)
from kfcheck import certify                                                # noqa: E402
from provenance import Control                                             # noqa: E402

SEED = 20260817
DIGEST = 32
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
S77 = os.path.join(HERE, '..', 'S77_proof_bytes')
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples', os.path.join(S75, 'keys_triples.bin'))]
PROBES = 200


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


def absent_probes(keys, kids, n):
    """Absent keys built by perturbing REAL keys deep in the trie.

    A27: a probe drawn from one end of the key order is not a sample of the key
    space, and S73 published a flat 293 B because its probes all diverged at the
    root. These diverge as DEEP as the key allows -- the last position where the
    trie still has the prefix -- which is the realistic miss W2's ~2.0 KB is
    about, and the expensive case rather than the cheap one.

    A random-byte probe would diverge at the root and produce a small, true,
    useless number; C_probes_are_deep_misses is what stops that being reported.
    """
    out, depths = [], []
    stride = max(1, len(keys) // n)
    for k in keys[::stride][:n]:
        # walk to the deepest position still in the trie, then take a byte that
        # is NOT a child there -- absence by construction, not by hope
        pos = 0
        while pos < len(k) and k[:pos] in kids and k[pos] in kids[k[:pos]]:
            pos += 1
        d = max(0, pos - 1)
        present = kids.get(k[:d], set())
        alt = next((b for b in range(256) if b not in present), None)
        if alt is None:
            continue
        out.append(k[:d] + bytes([alt]))
        depths.append(d)
    return out, depths


def absence_siblings(probe, kids):
    """Digests an absence proof carries, under the model stated in the docstring.

    (children - 1) along the shared prefix, then ALL children at the divergence
    position. Returns (digests, divergence_depth).
    """
    s, i = 0, 0
    while i < len(probe):
        p = probe[:i]
        c = kids.get(p)
        if c is None:
            break                       # prefix itself left the trie
        if probe[i] not in c:
            s += len(c)                 # divergence: EVERY child must be shown
            return s, i
        if len(c) > 1:
            s += len(c) - 1
        i += 1
    return s, i


def main():
    prev = json.load(open(os.path.join(S77, 'measure.json')))
    out = {'seed': SEED, 'digest_bytes': DIGEST, 'probes_per_set': PROBES,
           'model': 'membership charges (children-1) per branching position; '
                    'absence charges the same along the shared prefix and ALL '
                    'children at the divergence position, because a subset would '
                    'let a prover hide the child that makes the key present',
           'sets': {}}
    cs = []

    for name, path in SETS:
        keys = read_keys(path)
        kids = child_map(keys)
        probes, depths = absent_probes(keys, kids, PROBES)
        sib = [absence_siblings(p, kids) for p in probes]
        mean_sib = sum(s for s, _d in sib) / len(sib)

        root = build(sorted(set(keys)))
        rh = root.h
        real, verified, rejected_membership = [], 0, 0
        for p in probes:
            pf = prove_non_membership(root, p)
            if pf is None:
                continue
            real.append(steps_bytes(pf['steps']))
            verified += bool(verify_non_membership(rh, p, pf))
            # the probe must genuinely be absent, or "absence proof" is a
            # membership proof wearing another name
            rejected_membership += (prove_membership(root, p) is None)
        out['sets'][name] = {
            'probes': len(probes),
            'mean_divergence_depth': sum(depths) / len(depths),
            'mean_key_bytes': prev['sets'][name]['mean_key_bytes'],
            'membership_siblings': prev['sets'][name]['pathmap_mean_siblings'],
            'absence_digests_mean': mean_sib,
            'absence_auth_bytes_mean': mean_sib * DIGEST,
            'membership_auth_bytes_mean': prev['sets'][name]['pathmap_auth_bytes_mean'],
            'absence_over_membership': mean_sib / prev['sets'][name]['pathmap_mean_siblings'],
            'w2_real_absence_bytes_mean': sum(real) / len(real) if real else None,
            'w2_proofs_built': len(real), 'w2_verified': verified,
            'probes_absent': rejected_membership}

    a = out['sets']

    c = Control('C_probes_are_absent_and_proofs_verify',
                'an "absence proof" for a key that is present, or one the verifier '
                'rejects, is a number about nothing -- W1 shipped four controls '
                'with no verification function at all',
                null_must_contain='W2\'s prove_membership, which is free to find '
                                  'any probe present, and verify_non_membership, '
                                  'which is free to return False',
                can_fail_because='any probe is found present by prove_membership, '
                                 'or any absence proof fails verification')
    c.observe(all(v['probes_absent'] == v['probes'] and v['w2_verified'] == v['w2_proofs_built']
                  for v in a.values()),
              {n: {'probes': v['probes'], 'absent': v['probes_absent'],
                   'built': v['w2_proofs_built'], 'verified': v['w2_verified']}
               for n, v in a.items()})
    cs.append(c)

    c = Control('C_probes_are_deep_misses',
                'A27: probes that diverge at the root measure the CHEAP miss and '
                "S73 published a flat 293 B that way; W2's ~2.0 KB is about the "
                'realistic deep miss',
                null_must_contain='a divergence depth free to come out at 0 or 1, '
                                  'which is exactly what a random-byte probe would '
                                  'give on these key sets',
                can_fail_because='mean divergence depth is below 2 for any set, '
                                 'i.e. the probes leave the trie immediately')
    c.observe(all(v['mean_divergence_depth'] >= 2 for v in a.values()),
              {n: v['mean_divergence_depth'] for n, v in a.items()})
    cs.append(c)

    # THE FALSIFIER: absence must order the sets the same way membership does, or
    # "proof size is set by branching" is membership-only.
    mem_order = sorted(a, key=lambda n: a[n]['membership_auth_bytes_mean'])
    abs_order = sorted(a, key=lambda n: a[n]['absence_auth_bytes_mean'])
    w2_order = sorted(a, key=lambda n: a[n]['w2_real_absence_bytes_mean'])
    c = Control('C_absence_tracks_branching_like_membership',
                "S77 generalised to 'proof size is set by branching, not key "
                "length' from membership alone; if absence orders the sets "
                'differently, that sentence is membership-only and S77 overreached',
                null_must_contain='three key sets whose absence proofs are built '
                                  'independently of the membership measurement and '
                                  'are free to rank in any of six orders',
                can_fail_because='the absence ordering differs from the membership '
                                 'ordering on these three sets')
    c.observe(abs_order == mem_order,
              {'by_membership': mem_order, 'by_absence': abs_order,
               'absence_bytes': {n: a[n]['absence_auth_bytes_mean'] for n in a},
               'membership_bytes': {n: a[n]['membership_auth_bytes_mean'] for n in a}})
    cs.append(c)

    c = Control('C_real_prover_agrees_on_absence_ordering',
                'the model charges ALL children at the divergence point, which is '
                'a claim about what a proof must carry; a prover that exists is '
                'the check on it',
                null_must_contain="W2's prove_non_membership, written before this "
                                  'spike and free to rank the sets any way',
                can_fail_because="W2's real absence bytes rank the sets differently "
                                 'from the modelled digest counts')
    c.observe(w2_order == abs_order,
              {'by_w2_real': w2_order, 'by_model': abs_order,
               'w2_bytes': {n: a[n]['w2_real_absence_bytes_mean'] for n in a}})
    cs.append(c)

    c = Control('C_absence_costs_more_than_membership',
                'the model says absence carries every child at the divergence '
                'point where membership carries all but one, so absence must be '
                'strictly dearer -- if it is not, the model is wrong about what an '
                'absence proof has to show',
                null_must_contain='membership digest counts measured in S77, which '
                                  'this spike does not recompute and cannot adjust',
                can_fail_because='any set shows absence costing no more than '
                                 'membership')
    c.observe(all(v['absence_over_membership'] > 1.0 for v in a.values()),
              {n: v['absence_over_membership'] for n, v in a.items()})
    cs.append(c)

    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    with open(os.path.join(HERE, 'absence.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[HERE], artifacts=[os.path.join(HERE, 'absence.json')],
        controls=cs,
        falsifier='if non-membership proof cost does not track branching the way '
                  'membership does -- i.e. if the absence ordering differs from '
                  "the membership ordering -- then S77's \"proof size is set by "
                  'branching, not key length" is membership-only and overreached',
        note='S79 uses the Python sibling recount that C14 validated against the '
             'pathmap walk at 0.00%, so no new unvalidated instrument sits under '
             'the number. Counts and digests only, no timings.')
    for p in problems:
        print('  PROBLEM ' + p)

    print(f"{'set':<16} {'div depth':>10} {'mem B':>8} {'abs B':>8} {'x mem':>7} "
          f"{'W2 real abs B':>14}")
    for n, v in a.items():
        print(f"{n:<16} {v['mean_divergence_depth']:>10.1f} "
              f"{v['membership_auth_bytes_mean']:>8.0f} "
              f"{v['absence_auth_bytes_mean']:>8.0f} "
              f"{v['absence_over_membership']:>6.2f}x "
              f"{v['w2_real_absence_bytes_mean']:>14.0f}")
    print(f"order by membership: {mem_order}")
    print(f"order by absence   : {abs_order}")
    print(f"order by W2 real   : {w2_order}")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(f"certify ok={ok}")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
