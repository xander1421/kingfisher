#!/usr/bin/env python3
"""S77 — S75 and S76 turned node DEPTH into proof SIZE by multiplying. Wrong.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If the number of SIBLING digests along a pathmap path does not scale with
    node depth -- i.e. if the extra nodes on a long unbranched run are
    single-child and carry no siblings -- then depth was never a proxy for proof
    size, and S75's ~33 KB and S76's ~14 KB / ~9.9 KB are wrong in magnitude.

WHY DEPTH WAS THE WRONG QUANTITY
--------------------------------
An authentication path carries, at each position it passes, the digests of the
SIBLING subtries it did not take. A position with one child has no siblings, so
it costs the proof nothing but a step the verifier can recompute from key bytes
it already holds. Node count and sibling count are therefore different numbers
whenever a path contains long unbranched runs -- which is exactly what a
1,155-byte key is. S75 measured node depth, called it "one authenticated step",
and multiplied. S76 inherited that and measured the same wrong quantity more
precisely, over four encodings.

CLAUDE.md names this failure directly: "the right measurement of the wrong
question", and it is one of the three it says no tool will catch.

GROUNDED AGAINST AN IMPLEMENTED PROVER, NOT AGAINST ARITHMETIC
--------------------------------------------------------------
Sibling counts times a digest width is still arithmetic. So the same key sets go
through W2's `prove_membership`, which is a prover that exists, and its
`steps_bytes` is a byte count of a proof that was actually built. If pathmap's
sibling walk and W2's real proofs disagree about which key set is expensive, the
disagreement is the finding and neither number is published alone.

  python3 measure.py       # builds the probe if needed, then measures
"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
sys.path.insert(0, os.path.join(HERE, '..', 'S76_interned_keys'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from trie_witness import (build, load, key, prove_membership,          # noqa: E402
                          verify_membership, steps_bytes, desc_hash)
import epoch as E                                                      # noqa: E402
from intern import build_table, encode_interned                        # noqa: E402
from kfcheck import certify                                            # noqa: E402
from provenance import Control                                         # noqa: E402

SEED = 20260817
PROBE = os.path.join(HERE, 'pmproof')
BIN = os.path.join(PROBE, 'target', 'release', 'pmproof')
DIGEST = 32                     # sha256, the width W2's proofs actually carry
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')

# Sets are the COMMITTED key files of the two spikes under review, so the inputs
# are byte-identical to the ones whose depths were measured -- not re-derived.
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples', os.path.join(S75, 'keys_triples.bin'))]


def read_keys(path):
    import struct
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    out, i = [], 4
    for _ in range(n):
        (ln,) = struct.unpack_from('<H', b, i)
        i += 2
        out.append(b[i:i + ln])
        i += ln
    return out


def parse(text):
    """Rows kept as a LIST in emission order.

    Keyed by directory first, and two of the three key files live in the same
    spike directory, so the dict silently collapsed a row -- one key set would
    have vanished and the remaining two would have been mapped onto the wrong
    names by the positional zip below. Caught by the parser crashing on the
    field padding, which is luck, not method.
    """
    import re
    out = {'selfcheck': None, 'paths': []}
    for line in text.splitlines():
        f = dict(re.findall(r'(\w+)=\s*(\S+)', line))
        if line.startswith('selfcheck'):
            out['selfcheck'] = {'siblings': int(f['siblings']),
                                'steps': int(f['steps'])}
        elif line.startswith('path '):
            out['paths'].append({
                'file': line.split()[1],
                'keys': int(f['keys']),
                'mean_siblings': float(f['mean_siblings']),
                'max_siblings': int(f['max_siblings']),
                'mean_key_bytes': float(f['mean_key_bytes']),
                'branch_nodes_total': int(f['branch_nodes_total'])})
    return out


def w2_proof_bytes(keys, sample):
    """Real proof bytes from an implemented prover, on the same keys.

    Verified, not just measured: a proof whose verifier rejects is not a proof,
    and its size would be a number about nothing.
    """
    root = build(sorted(set(keys)))
    rh = root.h              # W2's Node carries its own digest; desc_hash takes a desc tuple
    tot, mx, verified = 0, 0, 0
    for k in sample:
        pf = prove_membership(root, k)
        b = steps_bytes(pf['steps'])
        tot += b
        mx = max(mx, b)
        verified += bool(verify_membership(rh, k, pf))
    return {'mean_bytes': tot / len(sample), 'max_bytes': mx,
            'verified': verified, 'sampled': len(sample)}


def main():
    if not os.path.exists(BIN):
        subprocess.run(['cargo', 'build', '--release'], cwd=PROBE, check=True)
    files = [p for _n, p in SETS]
    txt = subprocess.run([BIN] + files, cwd=HERE, capture_output=True,
                         text=True, check=True).stdout
    with open(os.path.join(HERE, 'probe_out.txt'), 'w') as f:
        f.write(txt)
    raw = parse(txt)
    # Map rows back onto set names by the FILE the probe echoed, not by position:
    # a positional zip is correct only until the probe reorders its output, and
    # nothing in the probe promises it will not.
    byfile = {r['file']: r for r in raw['paths']}
    assert len(byfile) == len(SETS), f'probe returned {len(byfile)} rows for {len(SETS)} sets'
    pm = {name: byfile[path] for name, path in SETS}

    s75 = json.load(open(os.path.join(S75, 'compare.json')))
    s76 = json.load(open(os.path.join(S76, 'compare.json')))
    depth = {'atoms_original': s75['sets']['atoms']['pathmap']['mean_node_depth'],
             'atoms_interned': s76['variants']['id4']['pathmap']['mean_node_depth'],
             'triples': s75['sets']['triples']['pathmap']['mean_node_depth']}

    out = {'seed': SEED, 'digest_bytes': DIGEST, 'sets': {},
           'depth_measured_by_S75_S76': depth,
           'selfcheck': raw['selfcheck']}
    for name, path in SETS:
        keys = read_keys(path)
        p = pm[name]
        # Every key walked in the probe; W2's prover is sampled deterministically
        # because building its trie for 4,096 keys and proving all of them is the
        # expensive half and the spread is what matters, not the tail.
        sample = keys[::max(1, len(keys) // 200)]
        w2 = w2_proof_bytes(keys, sample)
        out['sets'][name] = {
            'keys': p['keys'], 'mean_key_bytes': p['mean_key_bytes'],
            'pathmap_mean_siblings': p['mean_siblings'],
            'pathmap_max_siblings': p['max_siblings'],
            'pathmap_branch_nodes_total': p['branch_nodes_total'],
            'pathmap_auth_bytes_mean': p['mean_siblings'] * DIGEST,
            'pathmap_mean_node_depth': depth[name],
            'depth_implied_auth_bytes': depth[name] * DIGEST,
            'w2_real_proof': w2}

    a, i, t = (out['sets']['atoms_original'], out['sets']['atoms_interned'],
               out['sets']['triples'])

    # ------------------------------------------------------------------ controls
    cs = []

    c = Control('C_probe_reads_the_zipper_correctly',
                'a misread of child_count would produce a confident sibling '
                'count about nothing, and it is the only quantity this spike '
                'measures',
                null_must_contain='a hand-decidable trie: keys "aa" and "ab" '
                                  'branch exactly once, so the path to "aa" has '
                                  'exactly 1 sibling and any other answer is a '
                                  'misreading',
                can_fail_because='the two-key self-check reports any sibling '
                                 'count other than 1')
    c.observe(raw['selfcheck'] and raw['selfcheck']['siblings'] == 1,
              {'observed': raw['selfcheck'], 'expected_siblings': 1})
    cs.append(c)

    c = Control('C_same_key_files_as_S75_S76',
                'this is a review of two specific spikes, so it has to run on '
                'their committed key files rather than on re-derived ones',
                null_must_contain='the key counts S75 and S76 recorded (1,246 '
                                  'atoms, 4,096 triples), which this spike does '
                                  'not compute and cannot adjust',
                can_fail_because='any key count differs from the count in the '
                                 "reviewed spike's compare.json")
    c.observe(a['keys'] == s75['sets']['atoms']['keys']
              and i['keys'] == s76['variants']['id4']['keys']
              and t['keys'] == s75['sets']['triples']['keys'],
              {'atoms_original': a['keys'], 'atoms_interned': i['keys'],
               'triples': t['keys']})
    cs.append(c)

    # THE FALSIFIER. Depth and siblings must be shown to disagree, or S75/S76
    # were measuring a proxy that happened to work and nothing is retracted.
    depth_order = sorted(('atoms_original', 'atoms_interned', 'triples'),
                         key=lambda n: out['sets'][n]['pathmap_mean_node_depth'])
    sib_order = sorted(('atoms_original', 'atoms_interned', 'triples'),
                       key=lambda n: out['sets'][n]['pathmap_mean_siblings'])
    c = Control('C_depth_and_siblings_disagree',
                'S75 and S76 both converted depth into proof size by '
                'multiplication; that is only valid if the two quantities order '
                'the key sets the same way',
                null_must_contain='three key sets spanning 12 to 1,155 byte keys '
                                  'and 10.3 to 139.1 node depth, which is ample '
                                  'room for the two orderings to AGREE and for '
                                  'this control to come out negative',
                can_fail_because='depth and sibling count rank the three key sets '
                                 'in the same order, which would make depth a '
                                 'valid proxy and retract nothing')
    c.observe(depth_order != sib_order,
              {'by_depth_ascending': depth_order,
               'by_siblings_ascending': sib_order,
               'depths': {n: out['sets'][n]['pathmap_mean_node_depth']
                          for n in depth_order},
               'siblings': {n: out['sets'][n]['pathmap_mean_siblings']
                            for n in sib_order}})
    cs.append(c)

    # An implemented prover has to agree about WHICH set is expensive, or the
    # sibling walk is a model of nothing.
    w2_order = sorted(('atoms_original', 'atoms_interned', 'triples'),
                      key=lambda n: out['sets'][n]['w2_real_proof']['mean_bytes'])
    c = Control('C_real_prover_agrees_with_the_sibling_walk',
                'sibling count times 32 B is arithmetic; a prover that exists and '
                'a verifier that accepts are the check on it',
                null_must_contain="W2's own proof sizes on the same keys, "
                                  'produced by a prover written before this spike '
                                  'and free to rank the sets any way at all',
                can_fail_because='W2 real proof bytes rank the three key sets '
                                 'differently from the pathmap sibling walk')
    c.observe(w2_order == sib_order,
              {'by_w2_real_bytes': w2_order, 'by_pathmap_siblings': sib_order,
               'w2_mean_bytes': {n: out['sets'][n]['w2_real_proof']['mean_bytes']
                                 for n in w2_order},
               'pathmap_auth_bytes': {n: out['sets'][n]['pathmap_auth_bytes_mean']
                                      for n in sib_order}})
    cs.append(c)

    c = Control('C_every_sampled_proof_verifies',
                'a proof whose verifier rejects is not a proof and its size is a '
                'number about nothing -- W1 shipped four controls with no '
                'verification function at all',
                null_must_contain='a verifier that returns False, which W2 has '
                                  'and W1 did not',
                can_fail_because='any sampled membership proof fails '
                                 'verify_membership against the root hash')
    c.observe(all(out['sets'][n]['w2_real_proof']['verified']
                  == out['sets'][n]['w2_real_proof']['sampled'] for n in out['sets']),
              {n: out['sets'][n]['w2_real_proof'] for n in out['sets']})
    cs.append(c)

    # The mechanism, stated so it can be wrong: long keys are long UNBRANCHED
    # runs, so they add nodes without adding siblings.
    c = Control('C_long_keys_add_nodes_not_branches',
                'the reason depth fails as a proxy: the extra nodes a 1,155-byte '
                'key contributes are single-child and carry no digests',
                null_must_contain='the original atom keys, whose 139.1 mean depth '
                                  'gives them ample room to ALSO carry the most '
                                  'siblings if long runs were branchy',
                can_fail_because='the longest-key set does not have the fewest '
                                 'siblings per node on its path')
    per_node = {n: (out['sets'][n]['pathmap_mean_siblings']
                    / out['sets'][n]['pathmap_mean_node_depth'])
                for n in out['sets']}
    c.observe(per_node['atoms_original'] == min(per_node.values()),
              {'siblings_per_node_on_path': per_node,
               'mean_key_bytes': {n: out['sets'][n]['mean_key_bytes']
                                  for n in out['sets']}})
    cs.append(c)

    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    out['retracts'] = {
        'S75': 'the ~33 KB figure for S73 isolated insert proofs on real pathmap',
        'S76': 'the ~14 KB (id4) and ~9.9 KB (id2) figures, which inherit it',
        'ground': 'depth was multiplied by a digest width; the quantity that '
                  'buys digests is siblings on the path, and long keys add '
                  'nodes without adding siblings'}
    with open(os.path.join(HERE, 'measure.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[HERE],
        # OUTPUTS only. measure.py and main.rs are SOURCE in the dep tree, and
        # listing a source file as an artifact makes it its own staleness floor
        # -- E1 bug 5's shape, where `record` wrote provenance.json into the dir
        # it described and then reported everything older than itself.
        artifacts=[os.path.join(HERE, 'measure.json'),
                   os.path.join(HERE, 'probe_out.txt')],
        controls=cs, captures=[('probe_stdout', txt)],
        instrument_texts=[('pmproof stdout', txt)],
        falsifier='if the sibling count along a pathmap path scaled with node '
                  'depth, then depth was a valid proxy for proof size, S75 and '
                  "S76's multiplications would stand, and nothing here is "
                  'retracted',
        note='S77 reviews S75 and S76 on their own committed key files. It '
             'retracts their proof-size corrections and keeps their depth '
             'measurements, which reproduce. Counts and digests only, no '
             'timings, so valid while quiet.sh refuses.')
    for p in problems:
        print('  PROBLEM ' + p)

    print(f"{'set':<16} {'key B':>7} {'depth':>8} {'siblings':>9} "
          f"{'auth B':>9} {'depth-implied B':>16} {'W2 real B':>10}")
    for n, s in out['sets'].items():
        print(f"{n:<16} {s['mean_key_bytes']:>7.1f} "
              f"{s['pathmap_mean_node_depth']:>8.1f} "
              f"{s['pathmap_mean_siblings']:>9.1f} "
              f"{s['pathmap_auth_bytes_mean']:>9.0f} "
              f"{s['depth_implied_auth_bytes']:>16.0f} "
              f"{s['w2_real_proof']['mean_bytes']:>10.0f}")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(f"certify ok={ok}")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
