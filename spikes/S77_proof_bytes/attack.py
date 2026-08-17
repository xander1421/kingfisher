#!/usr/bin/env python3
"""ATTACK on S77's own instrument, by the lane that wrote it, one cycle later.

S77 retracted two published spikes on the strength of ONE self-authored
measurement: a Rust walk calling `child_count()` at each byte position. Its only
validation was a two-key self-check and a 5-7% agreement with W2's prover -- and
that second one is weaker than it looks, because if `child_count` systematically
under-reported branching, W2's own trie would still rank the sets the same way
and the agreement would be preserved. A22: the party supplying the measurement
supplied the check on it.

THREE ATTACKS, each stated with what result would kill S77:

  A1  INDEPENDENT RECOUNT. Compute siblings from the KEY SETS ALONE in Python --
      no pathmap, no zipper, no Rust. For each key, at each byte position, count
      the distinct next-bytes among the keys sharing that prefix, minus the one
      taken. If pathmap's walk and this disagree by more than rounding, S77's
      numbers are wrong and its retraction of S75/S76 is unfounded.

  A2  PREFIX KEYS. C4 of this project found a soundness bug where a key ending
      INSIDE another key's span was mishandled by exactly this kind of walk. If
      any key is a proper prefix of another, the terminal position is both an end
      and a branch, and the walk may count it as neither.

  A3  THE ROOT POSITION. S77 counts child_count BEFORE descending each byte,
      which includes the root. If the root's children should NOT be charged to a
      proof -- the root digest is the commitment, and a verifier holds it -- then
      every set is overcharged by (root children - 1), and the triples set, with
      the widest root, is overcharged most. That is the direction that would
      REVERSE S77's inversion finding.

  python3 attack.py
"""
import os, sys, json, struct, subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                   # noqa: E402
from provenance import Control                                # noqa: E402

S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples', os.path.join(S75, 'keys_triples.bin'))]


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


def independent_siblings(keys):
    """Siblings per key, computed from the key set alone.

    The logical byte trie is fully determined by the key set: at a prefix p, the
    children are the distinct bytes following p among keys that start with p. No
    trie is built and no library is called, so a bug in pathmap's zipper, in the
    Rust walk, or in this project's trie code cannot reach this number.

    Charged the same way S77 charges: at each position, (children - 1), counted
    only where children > 1. Root included, so A3 can be measured as a delta
    rather than argued.
    """
    kids = defaultdict(set)
    for k in keys:
        for i in range(len(k)):
            kids[k[:i]].add(k[i])
    tot, root_charge, per_key = 0, 0, []
    rootn = len(kids[b''])
    for k in keys:
        s = 0
        for i in range(len(k)):
            c = len(kids[k[:i]])
            if c > 1:
                s += c - 1
        per_key.append(s)
        tot += s
    root_charge = (rootn - 1) if rootn > 1 else 0
    return {'mean_siblings': tot / len(keys), 'max_siblings': max(per_key),
            'root_children': rootn, 'root_charge_per_key': root_charge}


def main():
    prev = json.load(open(os.path.join(HERE, 'measure.json')))
    out = {'attacks': {}, 'sets': {}}
    cs = []

    # ---- A1 INDEPENDENT RECOUNT ------------------------------------------
    worst = 0.0
    for name, path in SETS:
        keys = read_keys(path)
        ind = independent_siblings(keys)
        pm = prev['sets'][name]['pathmap_mean_siblings']
        rel = abs(ind['mean_siblings'] - pm) / pm
        worst = max(worst, rel)
        out['sets'][name] = {
            'pathmap_mean_siblings': pm,
            'independent_mean_siblings': ind['mean_siblings'],
            'relative_difference': rel,
            'pathmap_max_siblings': prev['sets'][name]['pathmap_max_siblings'],
            'independent_max_siblings': ind['max_siblings'],
            'root_children': ind['root_children'],
            'root_charge_per_key': ind['root_charge_per_key'],
            'mean_siblings_excluding_root':
                ind['mean_siblings'] - ind['root_charge_per_key']}

    c = Control('A1_independent_recount_agrees',
                "S77's sibling counts come from one self-authored Rust walk; this "
                'recomputes them from the key sets alone, with no pathmap, no '
                'zipper and no trie code of this project in the path',
                null_must_contain='the same three key files S77 measured, so a '
                                  'disagreement is expressible and would land on '
                                  'the exact numbers the retraction rests on',
                can_fail_because='any set differs by more than 1% between the '
                                 'pathmap walk and the independent recount')
    c.observe(worst < 0.01,
              {n: {'pathmap': v['pathmap_mean_siblings'],
                   'independent': v['independent_mean_siblings'],
                   'rel_diff': v['relative_difference']}
               for n, v in out['sets'].items()})
    cs.append(c)

    # ---- A2 PREFIX KEYS ---------------------------------------------------
    # C4 of this project found a real soundness bug of exactly this shape: a key
    # ending inside another key's compressed span was reported present. If this
    # corpus contains no such pair, the walk was never exercised on the case and
    # THAT is the finding -- an untested branch, not a passing one.
    prefix_pairs = {}
    for name, path in SETS:
        keys = sorted(read_keys(path))
        n = sum(1 for i in range(len(keys) - 1) if keys[i + 1].startswith(keys[i]))
        prefix_pairs[name] = n
    out['attacks']['A2_prefix_keys'] = prefix_pairs
    c = Control('A2_prefix_key_exposure_is_known',
                'a key that is a proper prefix of another makes a position both a '
                'terminal and a branch; C4 found a real soundness bug of that '
                'shape in this project, so whether the corpus contains the case '
                'has to be a recorded fact rather than an assumption',
                null_must_contain='three key sets totalling 6,588 keys, any pair '
                                  'of which could be prefix-related; the encodings '
                                  'are claimed prefix-free but nothing had checked',
                can_fail_because='any set contains a key that is a proper prefix '
                                 'of another, which would put S77 on an untested '
                                 'and historically buggy path')
    c.observe(all(v == 0 for v in prefix_pairs.values()), prefix_pairs)
    cs.append(c)

    # ---- A3 THE ROOT POSITION --------------------------------------------
    # The attack that could REVERSE the finding: if the root's children should not
    # be charged, the widest-root set is overcharged most, and triples have the
    # widest root. Recompute the ordering with the root charge removed.
    order_with = sorted(out['sets'], key=lambda n: out['sets'][n]['independent_mean_siblings'])
    order_without = sorted(out['sets'],
                           key=lambda n: out['sets'][n]['mean_siblings_excluding_root'])
    depth_order = sorted(out['sets'],
                         key=lambda n: prev['sets'][n]['pathmap_mean_node_depth'])
    out['attacks']['A3_root_charge'] = {
        'order_with_root': order_with, 'order_without_root': order_without,
        'order_by_depth': depth_order,
        'excluding_root': {n: out['sets'][n]['mean_siblings_excluding_root']
                           for n in out['sets']}}
    c = Control('A3_finding_survives_dropping_the_root_charge',
                "S77's inversion is the whole retraction; if it depends on charging "
                'a proof for the root node, whose digest the verifier already '
                'holds, then the retraction is an artefact of the accounting',
                # WRITTEN WRONG AND CORRECTED BY THE RUN: this said "the triples
                # set, whose root is the widest of the three". Measured, the
                # triples root has ONE child (every triple key shares a leading
                # byte) and the atom sets have two. So the attack's premise was
                # backwards -- there was no root charge worth removing anywhere,
                # and least of all on the set I expected it to sink. Kept visible
                # because an attack whose stated mechanism is wrong is exactly
                # what this project keeps finding in its own controls.
                null_must_contain='a root charge of (root children - 1) per key, '
                                  'which is free to be large enough to reorder the '
                                  'sets -- 256 children at the root would swamp '
                                  'every other position on a short key',
                can_fail_because='dropping the root charge makes the sibling '
                                 'ordering agree with the depth ordering, which '
                                 'would restore depth as a valid proxy')
    c.observe(order_without != depth_order,
              {'with_root': order_with, 'without_root': order_without,
               'by_depth': depth_order,
               'excluding_root': out['attacks']['A3_root_charge']['excluding_root']})
    cs.append(c)

    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    out['verdict'] = ('S77 SURVIVES' if out['all_controls_fire']
                      else 'S77 IS DAMAGED — see the controls that did not fire')
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[HERE],
        artifacts=[os.path.join(HERE, 'attack.json')],
        controls=cs,
        falsifier='an independent recount of siblings from the key sets alone '
                  "disagreeing with S77's pathmap walk, or the inversion "
                  'disappearing once the root charge is removed, would make S77 '
                  'wrong and its retraction of S75/S76 unfounded',
        # H49, 2026-08-17: BESIDE S77's record, not on top of it. As written
        # this certified into S77's own directory with artifacts=[attack.json],
        # so re-running it replaced S77's six controls and its measure.json
        # digest with this attack's. Latent rather than live -- S77's record was
        # regenerated afterwards and survived by luck of ordering -- and found by
        # the §12.2 sweep when the same defect went LIVE in S79.
        record_name='provenance.attack.json',
        note='ATTACK cycle on S77, by its own author, one cycle after it '
             'retracted two spikes on a single self-authored measurement (A22).')
    for p in problems:
        print('  PROBLEM ' + p)

    print(f"{'set':<16} {'pathmap sib':>12} {'independent':>12} {'rel diff':>9} "
          f"{'root kids':>10} {'sib no root':>12}")
    for n, v in out['sets'].items():
        print(f"{n:<16} {v['pathmap_mean_siblings']:>12.3f} "
              f"{v['independent_mean_siblings']:>12.3f} "
              f"{v['relative_difference']:>8.2%} {v['root_children']:>10} "
              f"{v['mean_siblings_excluding_root']:>12.3f}")
    print(f"prefix-related key pairs: {prefix_pairs}")
    print(f"order by depth       : {depth_order}")
    print(f"order by siblings    : {order_with}")
    print(f"order without root   : {order_without}")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(f"{out['verdict']}   certify ok={ok}")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
