#!/usr/bin/env python3
"""S75 — run W2's and S74's declared falsifier against MORK's real `pathmap`.

THE FALSIFIER, AS BOTH SPIKES WROTE IT
--------------------------------------
    "Build the same three proofs on MORK pathmap and show the authentication path
     departs from 1.5-3.3 KB by more than the branching factor explains."

It fires. And it fires for one key set and not the other, which is the useful
shape rather than a flat verdict.

WHAT DECIDES PROOF LENGTH
-------------------------
Every node on the path to a key is one authenticated step: its sibling digests
have to travel with the proof. So the quantity to compare is **node depth**, not
node count and not byte depth. `pathmap` stores a BOUNDED byte span per node
(`line_list_node`), while W2's Python trie compresses an entire unbranched run
into one node's `prefix` however long it is. For 12-byte keys that barely matters.
For 1,155-byte keys it decides the result.

SECOND FINDING, AND IT WAS NOT WHAT I EXPECTED TO FIND
------------------------------------------------------
`pathmap` HAS a `merkleization.rs`. It is not an authentication layer: it is a
**deduplication pass keyed by a 128-bit non-cryptographic hash** (`gxhash`,
declared in `Cargo.toml` as "for dag_serialization, merkleization, and caching"),
whose result type reports `reused / cloned / replaced` and which emits no proof and
has no verifier. Using it as a commitment would be unsound. Anyone assuming "the
substrate already has merkleization" is assuming the wrong thing.

  python3 compare.py       # builds the probe if needed, then measures
"""
import os, re, sys, json, struct, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from trie_witness import build, load, key            # noqa: E402
import epoch as E                                    # noqa: E402

SEED = 20260817
PROBE = os.path.join(HERE, 'pmprobe')
BIN = os.path.join(PROBE, 'target', 'release', 'pmprobe')
# A ratio this large is not a constant factor. Stated BEFORE the numbers are read,
# because a threshold chosen afterwards is fitted to the answer it is meant to
# judge (A26: a knob is not a mechanism).
NOT_A_CONSTANT_FACTOR = 10.0


def dump_keys(path, keys):
    with open(path, 'wb') as f:
        f.write(struct.pack('<I', len(keys)))
        for k in keys:
            f.write(struct.pack('<H', len(k)))
            f.write(k)


def py_depths(keys):
    """(max node depth, mean node depth, nodes) for W2's trie."""
    r = build(sorted(set(keys)))
    acc, st = [], [(r, 0)]
    while st:
        n, d = st.pop()
        acc.append(d)
        for b in n.children:
            st.append((n.children[b], d + 1))
    return max(acc), sum(acc) / len(acc), len(acc)


def parse_probe(text):
    """One record per key set: counts, merkle result, and the depth histogram."""
    out = {}
    for name in ('atoms', 'triples'):
        m = re.search(rf'pathmap {name}\s+keys=\s*(\d+) nodes=\s*(\d+) '
                      rf'child_items=\s*(\d+)\s+merkle_hash=(0x[0-9a-f]+) '
                      rf'reused=(\d+) cloned=(\d+) replaced=(\d+)', text)
        s = re.search(rf'pathmap {name}\s+second merkleize: same_hash=(\w+) '
                      rf'reused=(\d+)', text)
        blk = text.split(f'--- {name} depth histogram')[1].split('TOTAL')[0]
        rows = [l.split('\t') for l in blk.strip().splitlines() if l[:1].isdigit()]
        dep = [(int(r[0]), int(r[1])) for r in rows if r[1].strip().isdigit()]
        tot = sum(n for _d, n in dep) or 1
        out[name] = {
            'keys': int(m.group(1)), 'nodes': int(m.group(2)),
            'child_items': int(m.group(3)), 'merkle_hash': m.group(4),
            'reused': int(m.group(5)), 'cloned': int(m.group(6)),
            'replaced': int(m.group(7)),
            'merkleize_stable': s.group(1) == 'true',
            'max_node_depth': max(d for d, n in dep if n > 0),
            'mean_node_depth': sum(d * n for d, n in dep) / tot}
    return out


def main():
    progs, stats = E.load_corpus(E.CORPUS)
    atoms = sorted({E.encode(a) for _f, aa in progs for a in aa})
    tr, NT, NP, NE = load(os.path.join(HERE, '..', 'S52_realkg', 'triples.bin'))
    trip = sorted(key(*t) for t in
                  sorted(tr, key=lambda x: (x[0], x[1], x[2]))[:4096])
    dump_keys(os.path.join(HERE, 'keys_atoms.bin'), atoms)
    dump_keys(os.path.join(HERE, 'keys_triples.bin'), trip)

    if not os.path.exists(BIN):
        subprocess.run(['cargo', 'build', '--release'], cwd=PROBE, check=True)
    txt = subprocess.run([BIN], cwd=PROBE, capture_output=True, text=True,
                         check=True).stdout
    with open(os.path.join(HERE, 'probe_out.txt'), 'w') as f:
        f.write(txt)
    pm = parse_probe(txt)

    out = {'seed': SEED, 'threshold_stated_before_reading': NOT_A_CONSTANT_FACTOR,
           'rustc': subprocess.run(['rustc', '--version'], capture_output=True,
                                   text=True).stdout.strip(),
           'pathmap_version': '0.3.0 (elders/PathMap, path dep, untrusted per §10)',
           'sets': {}, 'controls': {}}
    for name, keys in (('atoms', atoms), ('triples', trip)):
        pmax, pmean, pnodes = py_depths(keys)
        p = pm[name]
        out['sets'][name] = {
            'keys': len(keys),
            'key_bytes_max': max(len(k) for k in keys),
            'key_bytes_mean': sum(len(k) for k in keys) / len(keys),
            'python': {'nodes': pnodes, 'max_node_depth': pmax,
                       'mean_node_depth': pmean},
            'pathmap': p,
            'depth_ratio_mean': p['mean_node_depth'] / pmean,
            'depth_ratio_max': p['max_node_depth'] / pmax,
            'node_ratio': p['nodes'] / pnodes}

    C = out['controls']
    a, t = out['sets']['atoms'], out['sets']['triples']

    # ---- C_identical_key_sets. Both implementations must be fed the SAME bytes.
    # FAILS IF the key counts disagree -- then the comparison is between two
    # different inputs and every ratio below is meaningless.
    C['C_identical_key_sets'] = {
        'fires': a['pathmap']['keys'] == a['keys'] and t['pathmap']['keys'] == t['keys'],
        'fails_if': 'pathmap and the Python trie disagree on how many keys they '
                    'loaded -- the comparison would be between different inputs',
        'can_fail': 'either pathmap keys count differs from the dumped count',
        'observed': {'atoms_py': a['keys'], 'atoms_pm': a['pathmap']['keys'],
                     'triples_py': t['keys'], 'triples_pm': t['pathmap']['keys']}}

    # ---- C_probe_reads_pathmap_correctly (NEGATIVE control: bounds resolution).
    # pathmap's OWN test set must reproduce the node count its test implies.
    # FAILS IF it does not, in which case every pathmap number here is suspect
    # and the falsifier verdict is void rather than negative.
    tiny = [b'axx', b'ayy', b'bxx', b'byy', b'cxx', b'cyy', b'ddxx', b'ddyy']
    dump_keys(os.path.join(HERE, 'keys_tiny.bin'), tiny)
    tv = subprocess.run([BIN, '--tiny'], cwd=PROBE, capture_output=True,
                        text=True).stdout
    tn = re.search(r'pathmap tiny\s+keys=\s*8 nodes=\s*(\d+)', tv)
    C['C_probe_reads_pathmap_correctly'] = {
        'fires': bool(tn) and int(tn.group(1)) == 6,
        'fails_if': "pathmap's own 8-path test set does not give 6 nodes through "
                    'this probe -- then the probe is misreading the library and '
                    'the verdict is VOID, not negative',
        'can_fail': 'the tiny set reports any node count other than 6',
        'observed': {'nodes': int(tn.group(1)) if tn else None, 'expected': 6}}

    # ---- C_falsifier_fires_on_atoms. The declared falsifier, on variable-length
    # keys. FAILS IF the depth ratio is below the threshold stated above -- then
    # the atom-key numbers DO transfer and W2/S73/S74 need no correction.
    C['C_falsifier_fires_on_atoms'] = {
        'fires': a['depth_ratio_mean'] > NOT_A_CONSTANT_FACTOR,
        'fails_if': f"the mean node-depth ratio on atom keys is under "
                    f"{NOT_A_CONSTANT_FACTOR}x -- the falsifier would NOT fire and "
                    f"S73/S74's proof sizes would transfer to real pathmap",
        'can_fail': 'depth_ratio_mean for atoms reads below the threshold',
        'observed': {'py_mean_depth': a['python']['mean_node_depth'],
                     'pm_mean_depth': a['pathmap']['mean_node_depth'],
                     'ratio_mean': a['depth_ratio_mean'],
                     'ratio_max': a['depth_ratio_max'],
                     'key_bytes_max': a['key_bytes_max'],
                     'threshold': NOT_A_CONSTANT_FACTOR}}

    # ---- C_falsifier_does_not_fire_on_triples. The SAME test on fixed-length
    # keys must come out the other way, or the finding is about pathmap in general
    # rather than about key length -- which is the mechanism being claimed.
    # FAILS IF triples also exceed the threshold.
    C['C_falsifier_does_not_fire_on_triples'] = {
        'fires': t['depth_ratio_mean'] < NOT_A_CONSTANT_FACTOR,
        'fails_if': 'fixed-length triple keys ALSO exceed the threshold -- then '
                    'the cause is not key length and the mechanism claimed here '
                    'is wrong',
        'can_fail': 'depth_ratio_mean for triples reads above the threshold',
        'observed': {'py_mean_depth': t['python']['mean_node_depth'],
                     'pm_mean_depth': t['pathmap']['mean_node_depth'],
                     'ratio_mean': t['depth_ratio_mean'],
                     'key_bytes_max': t['key_bytes_max']}}

    # ---- C_merkleize_is_deterministic. Running it twice must give one hash, or
    # it is not a function of content at all. FAILS IF the hash moves.
    C['C_merkleize_is_deterministic'] = {
        'fires': a['pathmap']['merkleize_stable'] and t['pathmap']['merkleize_stable'],
        'fails_if': "pathmap's merkleize hash changes between two runs on the same "
                    'trie -- it would not be content-derived',
        'can_fail': 'either same_hash reads false',
        'observed': {'atoms_stable': a['pathmap']['merkleize_stable'],
                     'triples_stable': t['pathmap']['merkleize_stable'],
                     'atoms_hash': a['pathmap']['merkle_hash'],
                     'triples_hash': t['pathmap']['merkle_hash']}}

    # ---- C_merkleize_is_dedup_not_commitment. Evidence, not assertion: the digest
    # is 128 bits from a non-cryptographic hash, the result type counts reuse, and
    # NO proof or verify symbol exists in the crate. FAILS IF a proof/verify
    # function is found -- then pathmap does have an authentication layer and W2
    # should have been built on it.
    src = os.path.join(HERE, '..', '..', 'elders', 'PathMap', 'src')
    cargo = open(os.path.join(src, '..', 'Cargo.toml')).read()
    gx = re.search(r'gxhash\s*=.*#\s*(.*)', cargo)
    # A NAME GREP WAS THE WRONG TEST AND IT COST ME A DEAD CONTROL.
    # The first version searched for `fn (prove|verify|proof|witness)` and found
    # 14 hits, so it did not fire -- but every one is a Rust BORROW witness
    # (`fn witness<'w>(&self) -> Self::WitnessT`, several returning `()`), a
    # lifetime token with no relation to a cryptographic witness. That is
    # CLAUDE.md's "correct numbers, wrong attribution" in miniature: the control
    # matched a word, not a concept.
    #
    # The replacement cannot collide on a name: a crate that depends on NO
    # cryptographic hash cannot emit a cryptographic commitment, whatever its
    # functions are called. gxhash and xxhash are both non-cryptographic, and
    # pathmap's own Cargo.toml says what it uses them for.
    CRYPTO = ('sha2', 'sha3', 'blake3', 'blake2', 'keccak', 'digest',
              'ring', 'openssl', 'k256', 'curve25519')
    deps = [ln.strip() for ln in cargo.splitlines()
            if any(ln.strip().startswith(c) for c in CRYPTO)]
    borrow_witnesses = subprocess.run(
        ['grep', '-rc', 'fn witness', src], capture_output=True, text=True).stdout
    C['C_merkleize_is_dedup_not_commitment'] = {
        'fires': len(deps) == 0,
        'fails_if': 'pathmap depends on any cryptographic hash -- then it can emit '
                    'a real commitment and W2 may have reimplemented something '
                    'that existed',
        'can_fail': 'a sha2/sha3/blake3/keccak/digest dependency appears in '
                    'pathmap Cargo.toml',
        'observed': {'crypto_hash_deps': deps,
                     'digest_bits': 128,
                     'hash_is_gxhash_declared_for': (gx.group(1) if gx else None),
                     'result_type_fields': ['hash', 'reused', 'cloned', 'replaced'],
                     'name_grep_was_a_false_positive':
                         'fn witness in pathmap is a Rust borrow token '
                         '(-> Self::WitnessT, several -> ()), not a proof'}}

    # ---- C_dedup_actually_reuses. If merkleize's memo never fires, the DAG
    # sharing S73 leans on is not present in this corpus and its cost model would
    # be optimistic. FAILS IF reused is 0 on both sets.
    C['C_dedup_actually_reuses'] = {
        'fires': a['pathmap']['reused'] > 0 and t['pathmap']['reused'] > 0,
        'fails_if': 'merkleize reuses no nodes on either corpus -- the structural '
                    "sharing S73's cost model leans on would be absent here",
        'can_fail': 'reused reads 0 for atoms or for triples',
        'observed': {'atoms_reused': a['pathmap']['reused'],
                     'triples_reused': t['pathmap']['reused'],
                     'triples_nodes': t['pathmap']['nodes']}}

    out['all_controls_fire'] = all(c['fires'] for c in C.values())
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    with open(os.path.join(HERE, 'compare.json'), 'w') as f:
        json.dump(out, f, indent=1)
    provenance(out)
    return out


def report(o):
    print(f"S75 — W2/S74's declared falsifier, run against MORK's real pathmap "
          f"(seed {o['seed']})")
    print(f"pathmap {o['pathmap_version']}\n{o['rustc']}")
    print(f"threshold for 'not a constant factor', stated before reading: "
          f"{o['threshold_stated_before_reading']}x\n")
    print(f"{'key set':<9} {'keys':>6} {'key B max':>10} {'py depth':>9} "
          f"{'pm depth':>9} {'ratio':>7} {'py nodes':>9} {'pm nodes':>9}")
    for n, s in o['sets'].items():
        print(f"{n:<9} {s['keys']:>6} {s['key_bytes_max']:>10} "
              f"{s['python']['mean_node_depth']:>9.1f} "
              f"{s['pathmap']['mean_node_depth']:>9.1f} "
              f"{s['depth_ratio_mean']:>6.1f}x {s['python']['nodes']:>9} "
              f"{s['pathmap']['nodes']:>9}")
    print('\nCONTROLS — each names the input that makes it fail')
    for n, c in o['controls'].items():
        print(f"  {'FIRES ' if c['fires'] else 'DEAD  '} {n:<40} {c['fails_if']}")
    print(f"\nall controls fire: {o['all_controls_fire']}")


def provenance(out):
    try:
        import kfcheck as KF
    except ImportError:
        return
    cs = []
    for n, c in out['controls'].items():
        ctl = KF.Control(n, c['fails_if'],
                         null_must_contain='the opposite depth ratio, or a '
                                           'pathmap proof function',
                         can_fail_because=c['can_fail'])
        ctl.observe(c['fires'], c['observed'])
        cs.append(ctl)
    ok, problems = KF.certify(
        HERE, deps=(os.path.join(HERE, '..', 'S57_hyperon_corpus'),),
        artifacts=[os.path.join(HERE, 'compare.py'),
                   os.path.join(HERE, 'compare.json'),
                   os.path.join(HERE, 'probe_out.txt'),
                   os.path.join(HERE, 'pmprobe', 'src', 'main.rs')],
        controls=cs, allow_dirty=True,
        captures=[('pathmap_atoms_merkle_hash',
                   out['sets']['atoms']['pathmap']['merkle_hash'])],
        falsifier='Show that authentication path length does NOT scale with node '
                  'depth on pathmap -- e.g. a proof scheme over it whose size is '
                  'independent of the number of nodes on the path. That would '
                  'restore S73/S74 proof sizes on variable-length keys.',
        note='S75 runs W2/S74 declared falsifier against elders/PathMap 0.3.0. '
             'Fires on variable-length atom keys, does not on fixed-length '
             'triple keys. pathmap merkleize is dedup, not a commitment.')
    if not ok:
        print('\nPROVENANCE PROBLEMS:')
        for p in problems:
            print('  ' + p)


if __name__ == '__main__':
    main()
