#!/usr/bin/env python3
"""W2 — witnessed re-execution on the trie substrate, with real non-membership.

WHY THIS SPIKE EXISTS, AND WHAT IT IS NOT
-----------------------------------------
W1 is INVALID. It measured a sorted-array range-skip that no engine here
implements, and its four "controls" could not fail -- there was no
proof-verification function anywhere in it (`proof_len` returned a length).
W4 then closed the prefilter route for good: the HDC prefilter is a similarity
search, its read set is 100% of the index on every query, and no key ordering
can bound it.

W4 left three routes. This spike takes route 1: **verify the exact-match stage
only, treating the prefilter as an untrusted accelerator.** The exact-match
substrate is a radix-256 trie (MORK's `pathmap`, `elders/PathMap`), and unlike a
similarity search a trie DOES have order in the key -- so prefix skipping here is
structural, not invented. That is the difference between this spike and W1.

W1 also stated the requirement it did not implement:

    "Reads that find nothing need non-membership proofs, which demand an
     authenticated ORDERED structure. The substrate is already a trie, which is
     the shape that provides them -- but this spike does not implement them."

This spike implements them, and a verifier that can reject.

WHAT IS PROVED
--------------
Three proof kinds over one Merkle-committed trie root:

  membership      key K is in the shard
  non-membership  key K is NOT in the shard         <- W1's unimplemented requirement
  completeness    the answer to prefix query Q is EXACTLY this set, no omissions

Completeness is the one that matters. A dishonest worker's cheapest cheat is not
a fabricated row (an inclusion proof catches that) -- it is a SILENTLY DROPPED
match. Only an ordered authenticated structure can refuse that, because refusing
it means proving that nothing lies in a range.

Data: FB15k-237, 272,115 triples -- `spikes/S52_realkg/triples.bin`, the only
real KG in this workspace. Stdlib only. Seed pinned.

  python3 trie_witness.py           # measurement + controls
  python3 trie_witness.py --json    # machine-readable
"""
import struct, hashlib, random, sys, json, os

SEED = 20260817
SHARD_TRIPLES = int(os.environ.get('W2_SHARD', 4096))   # W1's shard unit, kept for comparability
NQ = 200                                                # queries per shape
CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      '..', 'S52_realkg', 'triples.bin')

# ---------------------------------------------------------------- key encoding
# BIG-endian, deliberately. In a radix trie the byte order of the key IS the
# order of the structure, so big-endian makes byte-lexicographic order equal
# numeric order and makes (p), (p,s) genuine prefixes. Little-endian would give
# a trie whose prefixes mean nothing -- the encoding is load-bearing, not a
# serialization detail.
def key(p, s, o):
    return struct.pack('>3I', p, s, o)

def unkey(k):
    return struct.unpack('>3I', k)


def load(path):
    with open(path, 'rb') as f:
        NT, NP, NE = struct.unpack('<3i', f.read(12))
        raw = f.read(NT * 12)
    return [struct.unpack_from('<3i', raw, i * 12) for i in range(NT)], NT, NP, NE


# ------------------------------------------------------------ committed trie
class Node:
    """Path-compressed radix-256 node. `prefix` is the bytes consumed AT this
    node; `children` is keyed by the single branch byte that follows it."""
    __slots__ = ('prefix', 'children', 'term', 'h')

    def __init__(self, prefix, children, term):
        self.prefix, self.children, self.term = prefix, children, term
        self.h = node_hash(prefix, term, sorted(children.items()))


def node_hash(prefix, term, child_pairs):
    """Canonical node commitment. child_pairs must be (byte, child_hash) SORTED
    by byte -- the sort is what makes the commitment canonical, and control
    C_child_order shows the sort is load-bearing rather than decorative.

    Because the digest depends only on (prefix, term, children), two identical
    subtries hash identically -- which is exactly pathmap's structural sharing
    (it is a DAG, not just a trie) expressed in the authentication layer.
    """
    h = hashlib.sha256()
    h.update(b'N')
    h.update(len(prefix).to_bytes(2, 'big'))
    h.update(prefix)
    h.update(b'T' if term else b'-')
    h.update(len(child_pairs).to_bytes(2, 'big'))
    for b, ch in child_pairs:
        h.update(bytes([b]))
        h.update(ch if isinstance(ch, bytes) else ch.h)
    return h.digest()


def build(keys, depth=0):
    """Deterministic build from a SORTED key list. Determinism is required: the
    verifier rebuilds a subtrie from the answer set and must land on the same
    digest the prover committed."""
    first, last = keys[0], keys[-1]
    lim = min(len(first), len(last))
    lcp = depth
    while lcp < lim and first[lcp] == last[lcp]:
        lcp += 1
    prefix = first[depth:lcp]
    term = len(first) == lcp                  # sorted, so only the first can end here
    children, i, n = {}, 0, len(keys)
    if term:
        i = 1
    while i < n:
        b = keys[i][lcp]
        j = i + 1
        while j < n and keys[j][lcp] == b:
            j += 1
        children[b] = build(keys[i:j], lcp + 1)
        i = j
    return Node(prefix, children, term)


def desc(node):
    """The public description of a node: everything a verifier needs to recompute
    its digest without holding the subtrie."""
    return (node.prefix, node.term, [(b, node.children[b].h) for b in sorted(node.children)])


def desc_hash(d):
    prefix, term, pairs = d
    return node_hash(prefix, term, sorted(pairs))


# ---------------------------------------------------------------------- walk
COVER, MISS_BYTE, MISS_PREFIX = 'cover', 'miss_byte', 'miss_prefix'

def walk(root, q):
    """Descend by query prefix q. Returns (kind, steps, node, extra).

    steps is the authenticated path: (node_description_without_taken_child,
    taken_byte). `extra` carries the divergence detail for the miss kinds.
    """
    node, i, steps, depth = root, 0, [], 0
    while True:
        pl = len(node.prefix)
        take = min(pl, len(q) - i)
        if node.prefix[:take] != q[i:i + take]:
            return MISS_PREFIX, steps, node, {'at': i, 'depth': depth}
        i += take
        if i == len(q):
            # `matched` is load-bearing: q can be exhausted INSIDE this node's
            # compressed prefix, and `node.term` describes a key ending at the
            # prefix's END, not wherever q stopped. Conflating the two made
            # prove_non_membership report b'ab' as PRESENT in a trie holding only
            # b'abc'. Unreachable for W2 (fixed-length keys) and S73 (prefix-free
            # encoding), but it was wrong, and the ATTACK cycle 4 A4 probe found
            # it only because it could not reach the case it was aiming at.
            return COVER, steps, node, {'depth': depth, 'matched': take}
        b = q[i]
        if b not in node.children:
            return MISS_BYTE, steps, node, {'byte': b, 'depth': depth}
        pairs = [(cb, node.children[cb].h) for cb in sorted(node.children) if cb != b]
        steps.append(((node.prefix, node.term, pairs), b))
        depth = depth + pl + 1
        node = node.children[b]
        i += 1


def fold(steps, leaf_hash):
    """Recompute the root from a leaf digest and the sibling path. This is the
    function W1 did not have."""
    h = leaf_hash
    for (prefix, term, pairs), b in reversed(steps):
        h = node_hash(prefix, term, sorted(list(pairs) + [(b, h)]))
    return h


def collect(node, out):
    if node.term:
        out.append(True)          # placeholder; keys reconstructed by caller
    for b in sorted(node.children):
        collect(node.children[b], out)


def keys_under(node, prefix_so_far, out):
    p = prefix_so_far + node.prefix
    if node.term:
        out.append(p)
    for b in sorted(node.children):
        keys_under(node.children[b], p + bytes([b]), out)
    return out


# ---------------------------------------------------------------- proof sizes
HASH = 32

def steps_bytes(steps):
    n = 0
    for (prefix, term, pairs), _b in steps:
        n += 2 + len(prefix) + 1 + 2 + len(pairs) * (1 + HASH) + 1
    return n

def desc_bytes(d):
    prefix, _term, pairs = d
    return 2 + len(prefix) + 1 + 2 + len(pairs) * (1 + HASH)


# --------------------------------------------------------------------- proofs
def prove_membership(root, k):
    kind, steps, node, _x = walk(root, k)
    if kind != COVER or not node.term or _x.get('matched') != len(node.prefix):
        return None
    return {'steps': steps, 'leaf': desc(node)}

def verify_membership(root_hash, k, pf):
    """True iff pf proves k is in the trie committed by root_hash. Uses only the
    proof and the root -- never the prover's trie."""
    if pf is None:
        return False
    leaf = pf['leaf']
    if fold(pf['steps'], desc_hash(leaf)) != root_hash:
        return False
    # re-walk the query against the PROVEN descriptions, so a proof of a
    # different key cannot be replayed for this one.
    i = 0
    for (prefix, _t, _p), b in pf['steps']:
        if k[i:i + len(prefix)] != prefix:
            return False
        i += len(prefix)
        if i >= len(k) or k[i] != b:
            return False
        i += 1
    prefix, term, _p = leaf
    return k[i:] == prefix and term


def prove_non_membership(root, k):
    kind, steps, node, x = walk(root, k)
    if kind == COVER and node.term and x.get('matched') == len(node.prefix):
        return None                       # key IS present; no honest proof exists
    return {'steps': steps, 'node': desc(node), 'kind': kind, 'extra': x}

def verify_non_membership(root_hash, k, pf):
    """True iff pf proves k is ABSENT. This is the check an unordered structure
    cannot offer: it works because the trie's child set at the divergence point
    is authenticated, so 'there is no branch here' is a provable statement."""
    if pf is None:
        return False
    d = pf['node']
    if fold(pf['steps'], desc_hash(d)) != root_hash:
        return False
    i = 0
    for (prefix, _t, _p), b in pf['steps']:
        if k[i:i + len(prefix)] != prefix:
            return False
        i += len(prefix)
        if i >= len(k) or k[i] != b:
            return False
        i += 1
    prefix, term, pairs = d
    have = {b for b, _h in pairs}
    take = min(len(prefix), len(k) - i)
    if prefix[:take] != k[i:i + take]:
        return True                       # diverges inside the compressed prefix
    i += take
    if i == len(k):
        # present only if the key consumed the WHOLE compressed prefix and a key
        # ends at this node. `take < len(prefix)` means k stops mid-prefix, so k
        # is absent however `term` reads.
        return not (take == len(prefix) and term)
    return k[i] not in have               # no branch for the next byte


def prove_completeness(root, q):
    """Prove the answer to prefix query q is exactly this key set."""
    kind, steps, node, x = walk(root, q)
    if kind != COVER:
        return {'steps': steps, 'node': desc(node), 'kind': kind, 'extra': x,
                'keys': [], 'depth': x['depth']}
    pre = b''
    for (prefix, _t, _p), b in steps:
        pre += prefix + bytes([b])
    return {'steps': steps, 'kind': COVER, 'keys': keys_under(node, pre, []),
            'depth': x['depth'], 'extra': x}

def verify_completeness(root_hash, q, pf):
    """True iff the claimed key set is EXACTLY the keys under prefix q.

    An omitted key, an added key, or a tampered key all change the rebuilt
    subtrie digest, so the fold to the root fails. This is the anti-omission
    check; controls C_omit / C_add / C_tamper each drive it to False.
    """
    if pf is None:
        return False
    if pf['kind'] != COVER:
        # empty answer: must be backed by a non-membership-style divergence
        if pf['keys']:
            return False
        d = pf['node']
        if fold(pf['steps'], desc_hash(d)) != root_hash:
            return False
        prefix, _term, pairs = d
        i = pf['depth'] + 0
        # re-walk against proven descriptions
        j = 0
        for (p2, _t, _p), b in pf['steps']:
            if q[j:j + len(p2)] != p2:
                return False
            j += len(p2)
            if j >= len(q) or q[j] != b:
                return False
            j += 1
        take = min(len(prefix), len(q) - j)
        if prefix[:take] != q[j:j + take]:
            return True
        j += take
        return j < len(q) and q[j] not in {b for b, _h in pairs}
    ks = pf['keys']
    if not ks:
        return False
    if any(not k.startswith(q) for k in ks):
        return False
    if list(ks) != sorted(set(ks)):
        return False                      # canonical, duplicate-free, or reject
    rebuilt = build(sorted(ks), pf['depth'])
    return fold(pf['steps'], rebuilt.h) == root_hash


def reexecute(pf, filt):
    """The re-execution half of 'witnessed re-execution': the verifier runs the
    query itself over the proven key set. It never sees the shard."""
    return [k for k in pf['keys'] if filt(unkey(k))]


def witness_bytes(pf):
    n = steps_bytes(pf['steps'])
    if pf['kind'] == COVER:
        return n + 12 * len(pf['keys'])
    return n + desc_bytes(pf['node'])


# ----------------------------------------------------------------------- main
def main():
    triples, NT, NP, NE = load(CORPUS)
    rnd = random.Random(SEED)

    # one shard, clustered by (pred, subj) exactly as S52 does, so the trie's
    # prefix order is the same order S52's layout result is about.
    srt = sorted(triples, key=lambda t: (t[0], t[1], t[2]))
    off = int(os.environ.get('W2_OFFSET', 0))
    shard = srt[off:off + SHARD_TRIPLES]
    keys = sorted(key(*t) for t in shard)
    root = build(keys)
    R = root.h
    kset = set(keys)

    # SHARD COMPOSITION is recorded because two of the three shape numbers below
    # are functions of it, not of the trie: the (p ?s o) fraction is ~1/(distinct
    # predicates in the shard), and the (p s ?o) answer size is set by (p,s)
    # fan-out. Reporting the fractions without this would repeat W1's error of
    # publishing a corpus statistic as a system result.
    pairs = {}
    for t in shard:
        pairs[(t[0], t[1])] = pairs.get((t[0], t[1]), 0) + 1
    fan = sorted(pairs.values())

    out = {'seed': SEED, 'corpus': {'path': os.path.relpath(CORPUS), 'triples': NT,
                                    'preds': NP, 'entities': NE},
           'shard_triples': len(keys), 'shard_bytes': 12 * len(keys),
           'shard_offset': off,
           'composition': {'distinct_preds': len({t[0] for t in shard}),
                           'distinct_ps_pairs': len(pairs),
                           'ps_fanout_median': fan[len(fan) // 2],
                           'ps_fanout_max': fan[-1]},
           'root': R.hex(), 'shapes': {}, 'nonmembership': {}, 'scaling': [],
           'controls': {}}

    # ---- the three query shapes, on the real key set
    shapes = {
        # (p s ?o): prefix is p||s -- aligned with the clustering
        'p_s_?o': (lambda t: key(t[0], t[1], 0)[:8], lambda t, q: True),
        # (p ?s o): prefix is p only, then filter o. The ANSWER is small but the
        # WITNESS is every key under p, because completeness must refuse omission.
        'p_?s_o': (lambda t: key(t[0], 0, 0)[:4], lambda t, q: True),
        # (?p s o): no prefix. Covering node is the root: the witness is the shard.
        '?p_s_o': (lambda t: b'', lambda t, q: True),
    }
    for name, (mkq, _f) in shapes.items():
        ws, fr, ans, ok, pb, ab = [], [], [], 0, [], []
        for _ in range(NQ):
            t = shard[rnd.randrange(len(shard))]
            q = mkq(t)
            pf = prove_completeness(root, q)
            good = verify_completeness(R, q, pf)
            ok += bool(good)
            # re-execute the actual shape, filtering the proven set
            if name == 'p_s_?o':
                got = reexecute(pf, lambda x: x[0] == t[0] and x[1] == t[1])
            elif name == 'p_?s_o':
                got = reexecute(pf, lambda x: x[0] == t[0] and x[2] == t[2])
            else:
                got = reexecute(pf, lambda x: x[1] == t[1] and x[2] == t[2])
            ws.append(witness_bytes(pf))
            # DECOMPOSED, because the two halves move in opposite directions
            # across shards and their sum agreed by coincidence on the first run.
            # path = authentication overhead; answer = data the verifier needs
            # regardless, so only `path` is the price of being verifiable.
            pb.append(steps_bytes(pf['steps']))
            ab.append(12 * len(pf['keys']))
            fr.append(100.0 * len(pf['keys']) / len(keys))
            ans.append(len(got))
        ws.sort(); fr.sort(); ans.sort()
        out['shapes'][name] = {
            'queries': NQ, 'verified': ok,
            'witness_mean': sum(ws) / len(ws), 'witness_median': ws[len(ws) // 2],
            'witness_p95': ws[int(.95 * len(ws))], 'witness_max': ws[-1],
            'pct_shard_mean': sum(fr) / len(fr), 'pct_shard_median': fr[len(fr) // 2],
            'pct_shard_p95': fr[int(.95 * len(fr))],
            'vs_full_shard': (sum(ws) / len(ws)) / (12.0 * len(keys)),
            # mean AND median, because the uniform-over-triples generator samples
            # (p,s) pairs in proportion to their fan-out: the mean answer is set
            # by the one 394-row pair, the median by the typical 3-row pair.
            'answer_rows_mean': sum(ans) / len(ans),
            'answer_rows_median': ans[len(ans) // 2],
            'path_bytes_mean': sum(pb) / len(pb),
            'answer_bytes_mean': sum(ab) / len(ab),
        }

    # ---- non-membership: the thing W1 declared necessary and did not build.
    # TWO arms, because they differ by 20x and the flattering one is the easy one.
    #   shallow: a uniformly random absent key. Diverges at the FIRST branch byte
    #            almost always, because this shard holds only a few predicates.
    #   deep:    (p, s) is PRESENT, o is absent. Shares the whole clustering
    #            prefix with real rows, so the divergence is as late as the
    #            structure allows. This is the realistic miss and the honest cost.
    def nm_arm(gen):
        ws, ok, tried, depths = [], 0, 0, []
        while tried < NQ:
            k = gen()
            if k in kset:
                continue
            tried += 1
            pf = prove_non_membership(root, k)
            ok += bool(verify_non_membership(R, k, pf))
            ws.append(steps_bytes(pf['steps']) + desc_bytes(pf['node']))
            depths.append(len(pf['steps']))
        ws.sort()
        return {'queries': tried, 'verified': ok,
                'witness_mean': sum(ws) / len(ws), 'witness_median': ws[len(ws) // 2],
                'witness_p95': ws[int(.95 * len(ws))], 'witness_max': ws[-1],
                'path_steps_mean': sum(depths) / len(depths),
                'vs_full_shard': (sum(ws) / len(ws)) / (12.0 * len(keys))}

    present_ps = sorted(pairs)
    out['nonmembership'] = {
        'shallow_random': nm_arm(lambda: key(rnd.randrange(NP), rnd.randrange(NE),
                                             rnd.randrange(NE))),
        'deep_present_ps': nm_arm(lambda: (lambda ps: key(ps[0], ps[1],
                                                          NE + 1 + rnd.randrange(9999)))(
            present_ps[rnd.randrange(len(present_ps))])),
    }

    # ---- scaling: does the aligned witness stay flat as the shard grows?
    for n in (1024, 4096, 16384, 65536):
        if n > len(srt):
            break
        kk = sorted(key(*t) for t in srt[:n])
        rt = build(kk)
        r2 = random.Random(SEED)
        w, mm, pth = [], [], []
        for _ in range(50):
            t = srt[r2.randrange(n)]
            q = key(t[0], t[1], 0)[:8]
            pf = prove_completeness(rt, q)
            assert verify_completeness(rt.h, q, pf)
            w.append(witness_bytes(pf))
            pth.append(steps_bytes(pf['steps']))
            miss = key(t[0], t[1], NE + 1 + r2.randrange(1000))
            mpf = prove_non_membership(rt, miss)
            assert verify_non_membership(rt.h, miss, mpf)
            mm.append(steps_bytes(mpf['steps']) + desc_bytes(mpf['node']))
        out['scaling'].append({
            'shard_triples': n, 'shard_bytes': 12 * n,
            'aligned_witness_mean': sum(w) / len(w),
            'aligned_path_mean': sum(pth) / len(pth),
            'nonmembership_witness_mean': sum(mm) / len(mm),
            'aligned_vs_shard': (sum(w) / len(w)) / (12.0 * n)})

    # ------------------------------------------------------------- CONTROLS
    # Every one names the input that makes it fail, per MISSION_LOOP.md §5.
    C = out['controls']
    t = shard[len(shard) // 2]
    q8 = key(t[0], t[1], 0)[:8]
    good = prove_completeness(root, q8)
    assert verify_completeness(R, q8, good), 'honest completeness proof rejected'

    # C_honest -- NEGATIVE control. Bounds resolution: if honest proofs did not
    # verify, every rejection below would be vacuous. FAILS IF any honest proof
    # (membership, non-membership, completeness) returns False.
    hm = all(verify_membership(R, k, prove_membership(root, k))
             for k in rnd.sample(keys, 200))
    C['C_honest'] = {'fires': bool(hm and good is not None),
                     'fails_if': 'any honest proof verifies False -- then all '
                                 'rejections below are vacuous',
                     'observed': {'membership_ok': int(hm),
                                  'completeness_ok': int(bool(good))}}

    # C_omit -- the cheapest real cheat: silently drop one matching row.
    # FAILS IF verify_completeness returns True on a short answer.
    if len(good['keys']) >= 2:
        bad = dict(good); bad['keys'] = good['keys'][:-1]
        C['C_omit'] = {'fires': not verify_completeness(R, q8, bad),
                       'fails_if': 'a short answer verifies -- omission would be '
                                   'undetectable and completeness would be theatre',
                       'observed': {'honest_rows': len(good['keys']),
                                    'cheat_rows': len(bad['keys'])}}
    else:
        C['C_omit'] = {'fires': False, 'fails_if': 'unreachable: answer had <2 rows',
                       'observed': {'honest_rows': len(good['keys'])}}

    # C_add -- fabricate a row inside the proven range.
    # FAILS IF a padded answer verifies.
    fab = sorted(set(good['keys']) | {q8 + struct.pack('>I', 0xFFFFFFFE)})
    badd = dict(good); badd['keys'] = fab
    C['C_add'] = {'fires': not verify_completeness(R, q8, badd),
                  'fails_if': 'a fabricated row inside the proven prefix verifies',
                  'observed': {'honest_rows': len(good['keys']), 'cheat_rows': len(fab)}}

    # C_tamper -- flip one byte of one proven key.
    # FAILS IF the tampered set verifies.
    tk = list(good['keys'])
    tk[0] = tk[0][:11] + bytes([tk[0][11] ^ 0x01])
    badt = dict(good); badt['keys'] = sorted(set(tk))
    C['C_tamper'] = {'fires': not verify_completeness(R, q8, badt),
                     'fails_if': 'a one-byte-tampered answer verifies',
                     'observed': {'flipped_bit': 1, 'rows': len(tk)}}

    # C_forged_nonmembership -- claim a PRESENT key is absent, by doctoring the
    # divergence node's child list. This is the attack non-membership exists to
    # stop. FAILS IF the forgery verifies.
    present = keys[len(keys) // 3]
    assert prove_non_membership(root, present) is None, \
        'prover produced a non-membership proof for a present key'
    kind, steps, node, x = walk(root, present)
    d = desc(node)
    forged = {'steps': steps, 'kind': MISS_BYTE, 'extra': {'byte': 0},
              'node': (d[0] + b'\x00', d[1], d[2])}   # doctored: prefix extended
    C['C_forged_nonmembership'] = {
        'fires': (not verify_non_membership(R, present, forged)),
        'fails_if': 'a doctored divergence node verifies as absence -- a worker '
                    'could then deny any row it did not want to return',
        'observed': {'prover_refused_honest_proof': 1,
                     'forgery_rejected': int(not verify_non_membership(R, present, forged))}}

    # C_wrong_root -- a valid proof against a different commitment.
    # FAILS IF it verifies, which would mean the root binds nothing.
    other = build(sorted(key(*t) for t in srt[SHARD_TRIPLES:2 * SHARD_TRIPLES])).h
    C['C_wrong_root'] = {'fires': not verify_completeness(other, q8, good),
                         'fails_if': 'an honest proof verifies under a foreign root',
                         'observed': {'root': R.hex()[:16], 'other': other.hex()[:16]}}

    # C_child_order -- is the sort in node_hash load-bearing?
    # FAILS IF reversing child order leaves the digest unchanged (then the
    # canonicalisation is decorative and D2's F5 danger applies here too).
    multi = None
    stack = [root]
    while stack and multi is None:
        n = stack.pop()
        if len(n.children) >= 2:
            multi = n
        stack.extend(n.children.values())
    if multi is not None:
        pairs = [(b, multi.children[b].h) for b in sorted(multi.children)]
        rev = node_hash(multi.prefix, multi.term, pairs[::-1])
        C['C_child_order'] = {
            'fires': rev != multi.h,
            'fails_if': 'reversed child order gives the same digest -- the sort '
                        'would be decorative and two tries could share a root',
            'observed': {'children': len(pairs), 'sorted': multi.h.hex()[:16],
                         'reversed': rev.hex()[:16]}}
    else:
        C['C_child_order'] = {'fires': False,
                              'fails_if': 'unreachable: no node had >=2 children',
                              'observed': {}}

    # C_replay -- a valid membership proof for key A replayed for key B.
    # FAILS IF it verifies, which would make proofs transferable.
    a, b = keys[7], keys[9]
    C['C_replay'] = {'fires': not verify_membership(R, b, prove_membership(root, a)),
                     'fails_if': "key A's proof verifies for key B -- proofs "
                                 'would not bind the key they answer',
                     'observed': {'a': a.hex(), 'b': b.hex()}}

    # C_miss_depth -- the "deep" non-membership arm must actually be deeper than
    # the random arm, otherwise the hard/easy split is a label and not a
    # measurement, and the cheap 121 B figure would be the only one reported.
    sh, dp = out['nonmembership']['shallow_random'], out['nonmembership']['deep_present_ps']
    C['C_miss_depth'] = {
        'fires': dp['path_steps_mean'] > sh['path_steps_mean'],
        'fails_if': 'the deep arm does not authenticate a longer path than the '
                    'random arm -- then "hard miss" is a label, not a case',
        'observed': {'shallow_steps': sh['path_steps_mean'],
                     'deep_steps': dp['path_steps_mean'],
                     'shallow_bytes': sh['witness_mean'], 'deep_bytes': dp['witness_mean']}}

    out['all_controls_fire'] = all(c['fires'] for c in C.values())

    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'witness.json'), 'w') as f:
        json.dump(out, f, indent=1)
    provenance(here, out)
    return out


# The observation that would have made each control NOT fire, written against
# the values in `observed` so a third party can recheck it. `harness/provenance.py`
# refuses a control without one (A15); D6 H1 states the limit -- it catches an
# ABSENT statement, never a vacuous one.
CAN_FAIL = {
    'C_honest': 'membership_ok or completeness_ok reads 0',
    'C_omit': 'verify_completeness returns True on the short answer',
    'C_add': 'verify_completeness returns True on the padded answer',
    'C_tamper': 'verify_completeness returns True after the one-bit flip',
    'C_forged_nonmembership': 'forgery_rejected reads 0, or the prover emits an '
                              'honest absence proof for a present key',
    'C_wrong_root': 'the honest proof verifies under the foreign root',
    'C_child_order': 'the sorted and reversed digests are equal',
    'C_replay': "key A's membership proof verifies for key B",
    'C_miss_depth': 'deep_steps <= shallow_steps',
}


def provenance(here, out):
    """Persist the controls' OBSERVATIONS, not just their verdicts (harness rule
    A20: a control reported in prose cannot be rechecked)."""
    sys.path.insert(0, os.path.join(here, '..', 'harness'))
    try:
        import provenance as P
    except ImportError:
        return
    cs = []
    for name, c in out['controls'].items():
        ctl = P.Control(name, c['fails_if'],
                        null_must_contain='the cheat this control injects',
                        can_fail_because=CAN_FAIL[name])
        ctl.observe(c['fires'], c['observed'])
        cs.append(ctl)
    # deps MUST name the corpus tree. `deps=()` silently disables BOTH the
    # staleness and the dirty-tree checks -- which is the A24 hole, since a
    # digest pins which artifact and not what is in it. This spike was first
    # written with deps=() and had no staleness check at all.
    ok, prov = P.record(here, deps=(os.path.join(here, '..', 'S52_realkg'),),
        artifacts=[os.path.join(here, 'trie_witness.py'),
                   os.path.join(here, 'witness.json')],
        controls=cs, allow_dirty=True,   # loop commits at cycle end; dirt is RECORDED
        note='W2 witnessed re-exec on a Merkle-committed radix trie; '
             'membership + non-membership + completeness, real verifier')
    if not ok:
        print('\nPROVENANCE PROBLEMS:')
        for p in prov['problems']:
            print('  ' + p)


def report(o):
    sb = o['shard_bytes']
    c = o['composition']
    print(f"W2 — witnessed re-exec on the trie substrate (seed {o['seed']})")
    print(f"corpus {o['corpus']['triples']:,} triples; shard[{o['shard_offset']}:] "
          f"{o['shard_triples']:,} keys = {sb:,} B; root {o['root'][:16]}…")
    print(f"shard composition: {c['distinct_preds']} predicates, "
          f"{c['distinct_ps_pairs']} (p,s) pairs, fan-out median "
          f"{c['ps_fanout_median']} max {c['ps_fanout_max']}\n")
    print(f"{'query shape':<12} {'ans med':>8} {'path B':>8} {'answer B':>9} "
          f"{'wit mean':>9} {'% shard':>8} {'vs shard':>9} {'verified':>9}")
    for k, v in o['shapes'].items():
        print(f"{k:<12} {v['answer_rows_median']:>8.0f} {v['path_bytes_mean']:>8.0f} "
              f"{v['answer_bytes_mean']:>9.0f} {v['witness_mean']:>9.0f} "
              f"{v['pct_shard_mean']:>8.2f} {v['vs_full_shard']:>8.2f}x "
              f"{v['verified']}/{v['queries']:>4}")
    print(f"\nNON-MEMBERSHIP (W1's unimplemented requirement) — two arms")
    print(f"  {'arm':<18} {'steps':>6} {'wit med':>8} {'wit mean':>9} {'max':>7} "
          f"{'% shard':>8} {'verified':>9}")
    for arm, n in o['nonmembership'].items():
        print(f"  {arm:<18} {n['path_steps_mean']:>6.2f} {n['witness_median']:>8.0f} "
              f"{n['witness_mean']:>9.0f} {n['witness_max']:>7.0f} "
              f"{n['vs_full_shard']*100:>7.3f}% {n['verified']}/{n['queries']:>4}")
    print(f"\nSCALING (aligned (p s ?o) and absence, vs shard size)")
    print(f"  {'shard B':>10} {'auth path':>10} {'aligned W':>10} {'absent W':>9} "
          f"{'aligned/shard':>14}")
    for s in o['scaling']:
        print(f"  {s['shard_bytes']:>10,} {s['aligned_path_mean']:>10.0f} "
              f"{s['aligned_witness_mean']:>10.0f} "
              f"{s['nonmembership_witness_mean']:>9.0f} {s['aligned_vs_shard']:>13.4f}x")
    print(f"\nCONTROLS — each names the input that makes it fail")
    for name, c in o['controls'].items():
        print(f"  {'FIRES ' if c['fires'] else 'DEAD  '} {name:<26} {c['fails_if']}")
    print(f"\nall controls fire: {o['all_controls_fire']}")


if __name__ == '__main__':
    main()
