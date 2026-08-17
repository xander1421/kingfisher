#!/usr/bin/env python3
"""S78 — S77's own caveat, run rather than left standing.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If a commitment over pathmap's PHYSICAL nodes reorders the three key sets,
    S77's inversion is specific to the logical byte view and its retraction of
    S75/S76 needs qualifying.

S77 counts siblings at LOGICAL byte positions -- the trie a Merkle proof commits
to and the one W2 proves over. pathmap's own `merkleize` hashes PHYSICAL nodes
instead, and the atom trie has 83,210 of them against 3,160 for triples. If a
physical commitment charged a proof per physical node, that 26x would swamp the
1,461 vs 2,246 B of sibling digests and the ordering would flip straight back.

WHAT THE SOURCE SAYS, AND IT IS DECISIVE
----------------------------------------
`elders/PathMap/src/merkleization.rs:53` states the composition in its own
comment, and the loop below it implements exactly that:

    // hash = (value, [(path, child_hash)])

So to recompute a physical node's hash a verifier needs the node's value and,
for EVERY child, that child's path segment and its hash. For a node with k
children that is k-1 sibling digests. **For a single-child node it is zero** --
the one path segment is key bytes the verifier already holds, and the one child
hash is the value it computed from below. A long unbranched run therefore costs a
physical commitment no digests either, exactly as it costs the logical one none.

WHAT IS LEFT IS FRAMING, AND FRAMING IS A THRESHOLD
---------------------------------------------------
A verifier walking physical nodes must know where the segment boundaries fall,
which the key bytes alone do not say. Call that F bytes per physical node on the
path. Then the question is arithmetic on numbers already measured, and the
deliverable is the F at which the ordering flips.

GRADE, STATED UP FRONT (out/LEDGER.md): this is **D** -- composed from measured
parts plus arithmetic -- with one **E** input read from source. It is published
as a threshold and a source reading, never as a measured byte count. The whole
S75->S76->S77 arc is what happens when a D is written in a verdict line that
reads like a B.

  python3 threshold.py
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                    # noqa: E402
from provenance import Control                                 # noqa: E402

S77 = os.path.join(HERE, '..', 'S77_proof_bytes')
MERK = os.path.join(HERE, '..', '..', 'elders', 'PathMap', 'src', 'merkleization.rs')
DIGEST = 32
# A framing field is a length or a tag. Below 1 B there is no field at all; above
# 32 B a "framing field" is larger than the digest it frames, which is not a
# framing scheme anyone would build. Outside this window the threshold answers
# nothing, and that is what makes the control able to fail.
PLAUSIBLE_F = (1.0, 32.0)


def main():
    m = json.load(open(os.path.join(S77, 'measure.json')))
    sets = {n: {'siblings': v['pathmap_mean_siblings'],
                'physical_nodes_on_path': v['pathmap_mean_node_depth'],
                'logical_auth_bytes': v['pathmap_auth_bytes_mean']}
            for n, v in m['sets'].items()}

    # The pair that decides the inversion: the set with the fewest sibling digests
    # and the most physical nodes, against the set with the most siblings and the
    # fewest nodes. If F flips any pair it flips this one first.
    lo = min(sets, key=lambda n: sets[n]['siblings'])
    hi = max(sets, key=lambda n: sets[n]['siblings'])
    d_sib = sets[hi]['logical_auth_bytes'] - sets[lo]['logical_auth_bytes']
    d_nodes = (sets[lo]['physical_nodes_on_path']
               - sets[hi]['physical_nodes_on_path'])
    flip_F = d_sib / d_nodes if d_nodes > 0 else float('inf')

    src = open(MERK).read()
    # PROPERTY, not vocabulary (A30): the composition comment AND the loop that
    # implements it must both be present. A grep for the word "hash" in a file
    # named merkleization.rs cannot distinguish a commitment from a dedup key --
    # that mistake is S75's, and it cost a control there.
    says_pairs = bool(re.search(r'//\s*hash\s*=\s*\(value,\s*\[\(path,\s*child_hash\)\]\)', src))
    hashes_each_child = ('path.hash(&mut hasher);' in src
                         and 'child_hash.hash(&mut hasher);' in src)
    per_child_iteration = 'next_items(it)' in src

    out = {'sets': sets, 'digest_bytes': DIGEST,
           'deciding_pair': {'fewest_siblings': lo, 'most_siblings': hi,
                             'sibling_byte_gap': d_sib,
                             'physical_node_gap': d_nodes},
           'flip_threshold_bytes_per_physical_node': flip_F,
           'plausible_framing_window': PLAUSIBLE_F,
           'minimal_framing_is': 'a segment length, 1-2 B; the segment BYTES are '
                                 'key bytes the verifier already holds and the '
                                 'child hash is the value it computed from below',
           'source': {'file': 'elders/PathMap/src/merkleization.rs',
                      'composition_comment': says_pairs,
                      'hashes_path_and_child_hash_per_child': hashes_each_child,
                      'iterates_children': per_child_iteration},
           'grade': 'D (arithmetic over measured inputs) with one E input '
                    '(composition read from source, not measured)'}

    cs = []

    c = Control('C_single_child_physical_node_carries_no_digest',
                "the whole question is whether a physical commitment charges per "
                'NODE or per SIBLING; the source states the composition and the '
                'loop implements it, so this is decidable without a measurement',
                null_must_contain='merkleization.rs, which is equally free to '
                                  'hash a fixed child array, a 256-slot map, or '
                                  'every node on the path -- any of which would '
                                  'charge a digest per node and flip this',
                can_fail_because='the composition comment is absent, or the loop '
                                 'does not hash a (path, child_hash) pair per '
                                 'child, i.e. the node hash is not built from its '
                                 "children's digests one at a time")
    c.observe(says_pairs and hashes_each_child and per_child_iteration,
              out['source'])
    cs.append(c)

    c = Control('C_inputs_are_the_committed_ones',
                'this spike computes rather than measures, so its inputs must be '
                "the reviewed spikes' committed numbers and not retyped prose -- "
                'retyping a number out of a page is D6 hole H5 performed on '
                'purpose',
                null_must_contain="S77's measure.json, whose values this spike "
                                  'reads and cannot adjust',
                can_fail_because='any set is missing from S77/measure.json or any '
                                 'sibling/depth value is absent or non-numeric')
    c.observe(len(sets) == 3 and all(
        isinstance(v['siblings'], float) and isinstance(v['physical_nodes_on_path'], float)
        for v in sets.values()), sets)
    cs.append(c)

    c = Control('C_threshold_is_decision_relevant',
                'a threshold outside any framing anyone would build answers '
                'nothing in either direction, and publishing it would be a number '
                'with no decision attached',
                null_must_contain='a computed F free to land anywhere: below 1 B '
                                  '(even a length field flips the ordering, so '
                                  "S77 needs qualifying) or above 32 B (a full "
                                  'digest per node would not flip it, so the '
                                  'caveat was never a risk)',
                can_fail_because=f'the flip threshold falls outside '
                                 f'{PLAUSIBLE_F[0]}-{PLAUSIBLE_F[1]} B per node')
    c.observe(PLAUSIBLE_F[0] <= flip_F <= PLAUSIBLE_F[1],
              {'flip_threshold': flip_F, 'window': PLAUSIBLE_F,
               'deciding_pair': out['deciding_pair']})
    cs.append(c)

    c = Control('C_inversion_survives_minimal_framing',
                "S77's inversion is the retraction; if a 1-2 B segment length per "
                'physical node undoes it, the retraction is specific to the '
                'logical view and must say so',
                null_must_contain='the atom trie\'s 139.1 physical nodes per path '
                                  'against the triples\' 10.3 -- a 13x gap with '
                                  'ample room to overturn a 785 B sibling gap',
                can_fail_because='the flip threshold is at or below 2 B per '
                                 'physical node')
    c.observe(flip_F > 2.0, {'flip_threshold': flip_F,
                             'minimal_framing_upper_bound': 2.0,
                             'margin': flip_F / 2.0})
    cs.append(c)

    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    out['verdict'] = (
        f'the ordering flips only if a physical-node commitment costs more than '
        f'{flip_F:.1f} B of framing per node on the path; minimal framing is a '
        f'segment length at 1-2 B, so S77 survives with a {flip_F / 2.0:.1f}x '
        f'margin' if flip_F > 2.0 else
        f'the ordering flips at {flip_F:.1f} B per node, within minimal framing: '
        f"S77's inversion is specific to the logical view")
    with open(os.path.join(HERE, 'threshold.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[HERE], artifacts=[os.path.join(HERE, 'threshold.json')],
        controls=cs,
        falsifier='a physical-node commitment that charges a digest per node '
                  'rather than per sibling, or a framing cost above the computed '
                  'threshold, would reorder the key sets and make S77 a statement '
                  'about the logical view only',
        note='S78 is GRADE D: arithmetic over inputs measured in S77, plus one E '
             'input read from pathmap source. Published as a threshold, never as '
             'a measured byte count.')
    for p in problems:
        print('  PROBLEM ' + p)

    print(f"deciding pair: {lo} (fewest siblings, {sets[lo]['physical_nodes_on_path']:.1f} "
          f"nodes) vs {hi} ({sets[hi]['physical_nodes_on_path']:.1f} nodes)")
    print(f"sibling byte gap {d_sib:.0f} B over a physical node gap of {d_nodes:.1f}")
    print(f"FLIP THRESHOLD: {flip_F:.2f} B of framing per physical node on the path")
    print(f"source composition (value, [(path, child_hash)]): {says_pairs}")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(out['verdict'])
    print(f"certify ok={ok}")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
