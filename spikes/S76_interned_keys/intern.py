#!/usr/bin/env python3
"""S76 — S75 said the 18.4x was KEY LENGTH. Intern the symbols and find out.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If interning every symbol to a fixed-width id does NOT bring the pathmap /
    Python mean node-depth ratio for atom keys under 10x, then the cause of
    S75's 18.4x is NOT key length, and S75's mechanism claim is wrong.

S75 measured mean node depth 7.6 -> 139.1 (18.4x) on S73/S74's atom keys and
4.2 -> 10.3 (2.4x) on W2's 12-byte triple keys, threshold 10x fixed before
reading. It localised the difference to key length: `pathmap` stores a bounded
byte span per node, so an unbranched 1,155-byte run becomes ~1,148 nodes where
W2's trie spends one. That is a MECHANISM CLAIM, and the way to test one is to
change the variable it names and nothing else.

A THRESHOLD CROSSED ONCE IS ONE POINT (A18)
-------------------------------------------
"Under 10x" is a verdict on the falsifier and nothing more. If key length is
really the variable, then varying the id width should move the ratio WITH it, so
this sweeps four encodings over the same atom set and reports the relation --
including whether it is affine enough to be quoted as one, which `units` decides
rather than the author.

WHAT IS AND IS NOT CHANGED
--------------------------
Changed: symbols become `I` + an id of ID_BYTES instead of `S` + 2-byte length +
utf8. Unchanged: the expression framing (`E` + 2-byte arity + children), so the
encoding stays prefix-structured -- an expression's head is still a trie prefix
of everything beneath it, which is the property W2 showed makes non-membership
and completeness possible at all. Unchanged: the corpus, the atom set, the
triple set, and the probe binary.

THE PROBE IS S75's, UNMODIFIED AND UNREBUILT
--------------------------------------------
`pmprobe` reads `../keys_atoms.bin` and `../keys_triples.bin` relative to its
CWD, so this spike runs S75's committed binary from `probe_cwd/` and it reads
THIS directory's key files. Nothing in S75 is touched -- editing a committed
spike's instrument to extend it is how an artifact stops being the thing its
provenance describes (A24, family C). It also buys two controls: the ORIGINAL
encoding replayed through the probe now must reproduce S75's 139.1 exactly, and
the triples arm must reproduce S75's triple numbers exactly. If either moved,
the instrument moved and no comparison with S75 means anything.

INTERNING IS NOT FREE, AND THE COST IS NOT IN THE KEYS
------------------------------------------------------
A 4-byte id means nothing without the table that assigns it. Two parties
verifying the same proof must agree on the table or they are verifying different
statements, so the table has to be committed alongside the root or agreed out of
band. This spike MEASURES that table rather than waving at it, and ids are
assigned by SORTED symbol order so two parties holding the same symbol set
derive the same table without communicating.

  python3 intern.py        # builds S75's probe if needed, then measures
"""
import os, sys, json, struct, random, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from trie_witness import build, load, key                    # noqa: E402
import epoch as E                                            # noqa: E402
import units as U                                            # noqa: E402
from kfcheck import certify                                  # noqa: E402
from provenance import Control                               # noqa: E402

SEED = 20260817
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
PROBE = os.path.join(S75, 'pmprobe')
BIN = os.path.join(PROBE, 'target', 'release', 'pmprobe')
CWD = os.path.join(HERE, 'probe_cwd')
# S75's threshold, carried over unchanged. Re-picking it here would be fitting a
# knob to the answer it is meant to judge (A26), and the point of this spike is
# to be judged by the bar the previous one set.
NOT_A_CONSTANT_FACTOR = 10.0
HEADLINE = 4          # id width the verdict is stated at: 2 B is all this corpus
                      # needs, 4 B is the width that does not cap the symbol set


# --------------------------------------------------------------------------
# The encoding under test.
# --------------------------------------------------------------------------
def symbols(a, acc):
    if isinstance(a, list):
        for x in a:
            symbols(x, acc)
    else:
        acc.add(a)
    return acc


def build_table(atoms):
    """symbol -> id, assigned by SORTED symbol order.

    Sorted, not first-appearance: first-appearance ids depend on the order the
    corpus happened to be read in, so two parties with the same symbol set and
    different file orders would derive different tables and commit to different
    keys for the same atom. C_symbol_ids_are_canonical is that check.
    """
    acc = set()
    for a in atoms:
        symbols(a, acc)
    return {s: i for i, s in enumerate(sorted(acc))}


def encode_interned(a, tab, idb):
    """`E` + 2-byte arity + children, or `I` + idb-byte id. Injective given `tab`."""
    if isinstance(a, list):
        return b'E' + len(a).to_bytes(2, 'big') + \
               b''.join(encode_interned(x, tab, idb) for x in a)
    return b'I' + tab[a].to_bytes(idb, 'big')


def decode_interned(buf, inv, idb, i=0):
    """Inverse, so the round-trip control can fail rather than be asserted."""
    if buf[i:i + 1] == b'I':
        return inv[int.from_bytes(buf[i + 1:i + 1 + idb], 'big')], i + 1 + idb
    ar = int.from_bytes(buf[i + 1:i + 3], 'big')
    i += 3
    out = []
    for _ in range(ar):
        c, i = decode_interned(buf, inv, idb, i)
        out.append(c)
    return out, i


# --------------------------------------------------------------------------
# Measurement, reusing S75's instrument end to end.
# --------------------------------------------------------------------------
def dump_keys(path, keys):
    with open(path, 'wb') as f:
        f.write(struct.pack('<I', len(keys)))
        for k in keys:
            f.write(struct.pack('<H', len(k)))
            f.write(k)


def py_depths(keys):
    """(max node depth, mean node depth, nodes) for W2's trie. S75's function."""
    r = build(sorted(set(keys)))
    acc, st = [], [(r, 0)]
    while st:
        n, d = st.pop()
        acc.append(d)
        for b in n.children:
            st.append((n.children[b], d + 1))
    return max(acc), sum(acc) / len(acc), len(acc)


def run_probe(parse_probe, atom_keys, trip_keys):
    """One probe run over a given atom key set. Returns the parsed record."""
    dump_keys(os.path.join(HERE, 'keys_atoms.bin'), atom_keys)
    dump_keys(os.path.join(HERE, 'keys_triples.bin'), trip_keys)
    txt = subprocess.run([BIN], cwd=CWD, capture_output=True, text=True,
                         check=True).stdout
    return parse_probe(txt), txt


def measure(pm_rec, keys):
    pmax, pmean, pnodes = py_depths(keys)
    return {'keys': len(keys),
            'key_bytes_max': max(len(k) for k in keys),
            'key_bytes_mean': sum(len(k) for k in keys) / len(keys),
            'python': {'nodes': pnodes, 'max_node_depth': pmax,
                       'mean_node_depth': pmean},
            'pathmap': pm_rec,
            'depth_ratio_mean': pm_rec['mean_node_depth'] / pmean,
            'depth_ratio_max': pm_rec['max_node_depth'] / pmax,
            'node_ratio': pm_rec['nodes'] / pnodes}


def _freeze(a):
    return tuple(_freeze(x) for x in a) if isinstance(a, list) else a


def _thaw(a):
    return [_thaw(x) for x in a] if isinstance(a, tuple) else a


def main():
    sys.path.insert(0, S75)
    from compare import parse_probe                          # noqa: E402

    prev = json.load(open(os.path.join(S75, 'compare.json')))
    pa, pt = prev['sets']['atoms'], prev['sets']['triples']

    progs, _stats = E.load_corpus(E.CORPUS)
    atom_objs = [_thaw(a) for a in
                 sorted({_freeze(a) for _f, aa in progs for a in aa}, key=repr)]
    tab = build_table(atom_objs)
    inv = {i: s for s, i in tab.items()}

    tr, _NT, _NP, _NE = load(os.path.join(HERE, '..', 'S52_realkg', 'triples.bin'))
    trip = sorted(key(*t) for t in
                  sorted(tr, key=lambda x: (x[0], x[1], x[2]))[:4096])
    os.makedirs(CWD, exist_ok=True)
    if not os.path.exists(BIN):
        subprocess.run(['cargo', 'build', '--release'], cwd=PROBE, check=True)

    # Variants, ORIGINAL FIRST so its replay can be checked against S75 before
    # anything else is believed, and HEADLINE LAST so the committed key files and
    # probe_out.txt are the ones the verdict is stated at.
    variants = [('original', None)] + \
               [(f'id{n}', n) for n in sorted({2, 3, HEADLINE} - {None})]
    out = {'seed': SEED, 'threshold_carried_from_S75': NOT_A_CONSTANT_FACTOR,
           'headline_id_bytes': HEADLINE,
           'probe': 'S75/pmprobe, unmodified, run from S76/probe_cwd',
           'symbol_table': {
               'symbols': len(tab),
               'bytes_utf8': sum(len(s.encode()) for s in tab),
               'bytes_with_lengths': sum(len(s.encode()) + 2 for s in tab)},
           'variants': {}}
    txt = None
    for name, idb in variants:
        keys = sorted({E.encode(a) if idb is None else encode_interned(a, tab, idb)
                       for a in atom_objs})
        pm, txt = run_probe(parse_probe, keys, trip)
        out['variants'][name] = measure(pm['atoms'], keys)
        out['variants'][name]['id_bytes'] = idb
        if name == 'original':
            out['triples'] = measure(pm['triples'], trip)
    with open(os.path.join(HERE, 'probe_out.txt'), 'w') as f:
        f.write(txt)

    orig = out['variants']['original']
    head = out['variants'][f'id{HEADLINE}']
    t = out['triples']

    # THE RELATION, not the crossing. Points are (mean key bytes, depth ratio).
    pts = sorted((v['key_bytes_mean'], v['depth_ratio_mean'])
                 for v in out['variants'].values())
    affine_ok, affine_why = U.check_affine(pts)
    out['relation'] = {
        'points_mean_key_bytes_to_depth_ratio': pts,
        'affine': affine_ok, 'affine_verdict': affine_why,
        'quotable_as_a_rate': bool(affine_ok)}

    # ------------------------------------------------------------------ controls
    cs = []

    rt = [decode_interned(encode_interned(a, tab, HEADLINE), inv, HEADLINE)[0] == a
          for a in atom_objs]
    keyset = {encode_interned(a, tab, HEADLINE) for a in atom_objs}
    c = Control('C_interning_is_injective',
                'a shorter encoding that collides or drops information would '
                'produce exactly the depth improvement this spike claims, so '
                'soundness has to be established before the measurement is read',
                null_must_contain='a collision, which this encoding can express: '
                                  f'{len(tab)} symbols share a {HEADLINE}-byte id '
                                  'space and the arity field is fixed-width, so '
                                  'distinct atoms CAN be driven to one key',
                can_fail_because='any atom fails to round-trip, or two distinct '
                                 'atoms encode to one key (fewer keys than atoms)')
    c.observe(all(rt) and len(keyset) == len(atom_objs),
              {'atoms': len(atom_objs), 'distinct_keys': len(keyset),
               'round_trip_ok': sum(rt), 'round_trip_failed': rt.count(False)})
    cs.append(c)

    c = Control('C_original_replay_reproduces_S75',
                'the strongest available check that the instrument did not move: '
                "S75's own encoding, replayed through the same binary in this "
                'session, must land on the number S75 committed',
                null_must_contain="S75's committed 139.05 mean pathmap depth and "
                                  '83,210 nodes, recorded before this spike '
                                  'existed and not adjustable by it',
                can_fail_because='the replayed mean depth or node count differs '
                                 'from S75/compare.json by any amount')
    c.observe(orig['pathmap']['mean_node_depth'] == pa['pathmap']['mean_node_depth']
              and orig['pathmap']['nodes'] == pa['pathmap']['nodes']
              and orig['keys'] == pa['keys'],
              {'replay_mean': orig['pathmap']['mean_node_depth'],
               'S75_mean': pa['pathmap']['mean_node_depth'],
               'replay_nodes': orig['pathmap']['nodes'],
               'S75_nodes': pa['pathmap']['nodes'],
               'replay_keys': orig['keys'], 'S75_keys': pa['keys']})
    cs.append(c)

    c = Control('C_triples_arm_reproduces_S75',
                'the second half of the same instrument check, on the key set '
                'this spike does not touch at all',
                null_must_contain="S75's committed triple numbers (10.26 pathmap "
                                  'mean depth, 3,160 nodes), independent of '
                                  'anything this spike varies',
                can_fail_because='any triple-arm number differs from the value '
                                 'committed in S75/compare.json')
    c.observe(t['pathmap']['mean_node_depth'] == pt['pathmap']['mean_node_depth']
              and t['pathmap']['nodes'] == pt['pathmap']['nodes']
              and t['python']['mean_node_depth'] == pt['python']['mean_node_depth'],
              {'pm_mean': t['pathmap']['mean_node_depth'],
               'S75_pm_mean': pt['pathmap']['mean_node_depth'],
               'pm_nodes': t['pathmap']['nodes'],
               'S75_pm_nodes': pt['pathmap']['nodes'],
               'py_mean': t['python']['mean_node_depth'],
               'S75_py_mean': pt['python']['mean_node_depth']})
    cs.append(c)

    c = Control('C_key_length_actually_fell',
                'the mechanism claimed is key length, so key length must be '
                'observed falling before any depth result is attributed to it',
                null_must_contain='the original encoding measured in THIS run, '
                                  'which is free to come out shorter than the '
                                  'interned one -- 4-byte ids are longer than any '
                                  'symbol of 1 character',
                can_fail_because='interned keys are not shorter than the original '
                                 'encoding on both max and mean')
    c.observe(head['key_bytes_max'] < orig['key_bytes_max']
              and head['key_bytes_mean'] < orig['key_bytes_mean'],
              {'max_before': orig['key_bytes_max'], 'max_after': head['key_bytes_max'],
               'mean_before': orig['key_bytes_mean'],
               'mean_after': head['key_bytes_mean']})
    cs.append(c)

    c = Control('C_interning_brings_ratio_under_threshold',
                "this spike's declared falsifier: if it does not fire, key length "
                "is not the cause of S75's 18.4x and S75's mechanism claim is wrong",
                null_must_contain='the same instrument that produced 18.39x, so '
                                  'the scale can contain both outcomes and the '
                                  'threshold is reachable from either side',
                can_fail_because=f'the interned mean depth ratio reads at or above '
                                 f'{NOT_A_CONSTANT_FACTOR}x')
    c.observe(head['depth_ratio_mean'] < NOT_A_CONSTANT_FACTOR,
              {'ratio_before': orig['depth_ratio_mean'],
               'ratio_after': head['depth_ratio_mean'],
               'threshold': NOT_A_CONSTANT_FACTOR,
               'triples_reference': t['depth_ratio_mean']})
    cs.append(c)

    c = Control('C_ratio_moves_with_id_width',
                'one threshold crossing is one point (A18); if key length is the '
                'variable then narrowing the id must move the ratio in the same '
                'direction, and if it does not, something else is doing the work',
                null_must_contain='four encodings over ONE atom set, so a flat '
                                  'ratio across differing key lengths is an '
                                  'expressible outcome',
                can_fail_because='the depth ratio does not decrease monotonically '
                                 'as mean key bytes decrease across the four '
                                 'variants')
    c.observe(all(pts[i][1] <= pts[i + 1][1] for i in range(len(pts) - 1)),
              {'points_key_bytes_to_ratio': pts, 'affine': affine_ok,
               'affine_verdict': affine_why})
    cs.append(c)

    rng = random.Random(SEED)
    shuffled = list(atom_objs)
    rng.shuffle(shuffled)
    c = Control('C_symbol_ids_are_canonical',
                'an id assignment depending on read order makes two honest parties '
                'commit to different keys for the same atom set',
                null_must_contain='a shuffled atom order, which under a '
                                  'first-appearance assignment WOULD produce a '
                                  'different table -- the shuffle is a real '
                                  'perturbation, not a no-op',
                can_fail_because='rebuilding the table from the shuffled order '
                                 'yields any different id')
    tab2 = build_table(shuffled)
    c.observe(tab2 == tab,
              {'symbols': len(tab), 'identical_after_shuffle': tab2 == tab,
               'shuffle_changed_order': shuffled != atom_objs,
               'first_differing': next((s for s in tab if tab2.get(s) != tab[s]), None)})
    cs.append(c)

    out['controls'] = {c.name: c.as_dict() for c in cs}
    out['all_controls_fire'] = all(c.fired for c in cs)
    # compare.json is written BEFORE certify so the digest certify records is the
    # digest of the file that ships. A verdict appended afterwards would leave the
    # recorded hash describing a file that no longer exists (A24, family C); the
    # verdict lives in provenance.json, which is certify's own output.
    with open(os.path.join(HERE, 'compare.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)

    meas = [{'name': 'mean_key_bytes_to_depth_ratio', 'points': pts,
             'as_rate': bool(affine_ok)}]
    ok, problems = certify(
        HERE,
        deps=[HERE, os.path.join(HERE, '..', 'S57_hyperon_corpus')],
        artifacts=[os.path.join(HERE, 'intern.py'),
                   os.path.join(HERE, 'compare.json'),
                   os.path.join(HERE, 'probe_out.txt')],
        controls=cs, measurements=meas,
        captures=[('probe_stdout', txt),
                  ('headline_merkle_hash', head['pathmap']['merkle_hash'])],
        instrument_texts=[('pmprobe stdout', txt)],
        falsifier='if interning symbols to fixed-width ids does not bring the '
                  'pathmap/python mean node-depth ratio for atom keys under 10x, '
                  "the cause of S75's 18.4x is not key length and S75's mechanism "
                  'claim is wrong',
        note='S76: probe binary is S75/pmprobe unmodified, run from S76/probe_cwd '
             'so it reads this spike key files. Counts and digests only, no '
             'timings, so the result is valid while quiet.sh refuses.')

    print(f"{'variant':<9} {'id B':>4} {'key B max':>9} {'key B mean':>10} "
          f"{'py depth':>8} {'pm depth':>8} {'ratio':>7}")
    for n, v in out['variants'].items():
        print(f"{n:<9} {str(v['id_bytes']):>4} {v['key_bytes_max']:>9} "
              f"{v['key_bytes_mean']:>10.1f} {v['python']['mean_node_depth']:>8.1f} "
              f"{v['pathmap']['mean_node_depth']:>8.1f} "
              f"{v['depth_ratio_mean']:>6.2f}x")
    print(f"{'triples':<9} {'-':>4} {t['key_bytes_max']:>9} "
          f"{t['key_bytes_mean']:>10.1f} {t['python']['mean_node_depth']:>8.1f} "
          f"{t['pathmap']['mean_node_depth']:>8.1f} {t['depth_ratio_mean']:>6.2f}x")
    print(f"affine over the four variants: {affine_ok} — {affine_why}")
    print(f"symbol table {len(tab)} symbols, "
          f"{out['symbol_table']['bytes_with_lengths']} B to commit")
    for c in cs:
        print(f"  {'FIRES ' if c.fired else 'DEAD  '} {c.name}")
    print(f"certify ok={ok}")
    for p in problems:
        print('  PROBLEM ' + p)
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
