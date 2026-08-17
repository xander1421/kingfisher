#!/usr/bin/env python3
"""S73 — canonical SPACE state at an epoch boundary, with verifiable deltas.

WHAT THIS IS, AND THE HALF IT DELIBERATELY DOES NOT TOUCH
---------------------------------------------------------
"Canonical state serialization at an epoch boundary" is two problems wearing one
name, and S68 already settled which half is reachable:

  INTERPRETER state (the plan stack)  -- S68 is RED. Four contaminants, one
      unidentified, ~50% divergence after masking three. Blocked upstream on
      hyperon Issue 3. Bisection needs this and cannot have it.
  SPACE state (the atom set)          -- reachable today. This spike.

So this does NOT unblock optimistic-execution/bisection; that stays gated on S68.
It unblocks the other dependant: **verifiable adaptation across epochs** — a
learner adds atoms, and a verifier checks the transition without holding the space.

WHAT S65 GOT WRONG, AND THE STANDARD THAT SETS
----------------------------------------------
S65 committed to `current_results()` — emitted output, not state — and 100% of
its leaf content was `"()\\n"` repeated, so the root was forgeable in 6 lines of
Python without running hyperon. A state commitment must therefore bind CONTENT,
not shape. Two spaces with the same atom count and different atoms must differ.

WHAT IS BUILT
-------------
1. A canonical byte encoding of MeTTa atoms, read from the real corpus.
2. An epoch commitment: the W2 Merkle-committed radix trie over that atom set.
3. A **fold-forward delta proof**: from `root_N`, the k added atoms, and one
   proof each, a verifier *computes* `root_N+1`. It never sees the space.
4. A **null that is not a straw man**: XOR-of-hashes, which also gives O(k)
   epoch deltas — and is then shown to be forgeable, which is the point.

Corpus: `../S57_hyperon_corpus/corpus/*.metta`, 67 real MeTTa programs — the same
corpus M1's admission gate and the 65-CID quorum chain run on.
Trie primitives are imported from W2, not reimplemented.

  python3 epoch.py            # measurement + controls
  python3 epoch.py --json
"""
import os, sys, json, hashlib, random, struct
from functools import reduce

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
from trie_witness import (build, node_hash, desc, desc_hash, walk, fold,
                          prove_non_membership, verify_non_membership,
                          steps_bytes, desc_bytes, COVER, MISS_BYTE, MISS_PREFIX)

SEED = 20260817
CORPUS = os.path.join(HERE, '..', 'S57_hyperon_corpus', 'corpus')


# ------------------------------------------------------------------ MeTTa read
def tokenize(src):
    """Parens, quoted strings with backslash escapes, `;` line comments, symbols.

    All three matter on this corpus: 50 of 67 files carry `;` comments, and
    `builtin_mods__catalog.metta` has `\\"list\\"` nested inside a string. A reader
    that mishandles either produces a different atom set, and then every digest
    below commits to the wrong thing.
    """
    i, n, out = 0, len(src), []
    while i < n:
        c = src[i]
        if c in ' \t\r\n':
            i += 1
        elif c == ';':
            while i < n and src[i] != '\n':
                i += 1
        elif c in '()':
            out.append(c)
            i += 1
        elif c == '"':
            j, buf = i + 1, ['"']
            while j < n:
                if src[j] == '\\' and j + 1 < n:
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                buf.append(src[j])
                if src[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(''.join(buf))
            i = j
        else:
            j = i
            while j < n and src[j] not in ' \t\r\n();':
                if src[j] == '"':
                    break
                j += 1
            out.append(src[i:j])
            i = j
    return out


def parse(tokens):
    """Top-level atoms only. Unbalanced trailing input is dropped and counted --
    silently repairing it would let a reader bug look like a clean corpus."""
    atoms, stack, cur, dropped = [], [], None, 0
    for t in tokens:
        if t == '(':
            new = []
            if cur is None:
                cur = new
            else:
                stack.append(cur)
                cur.append(new)
                cur = new
        elif t == ')':
            if cur is None:
                dropped += 1
                continue
            if stack:
                cur = stack.pop()
            else:
                atoms.append(cur)
                cur = None
        else:
            if cur is None:
                atoms.append(t)          # bare top-level symbol
            else:
                cur.append(t)
    if cur is not None or stack:
        dropped += 1
    return atoms, dropped


# ------------------------------------------------------- canonical atom bytes
def encode(a):
    """Canonical, injective, PREFIX-structured byte encoding of an atom.

    `E` + 2-byte arity + children, or `S` + 2-byte length + utf8. Prefix-structured
    on purpose: an expression's head becomes a trie prefix of everything beneath
    it, so order in the key is order in the structure — the property W2 showed is
    what makes non-membership and completeness possible at all. Arity is
    length-prefixed rather than delimited so no symbol can forge a boundary.
    """
    if isinstance(a, list):
        return b'E' + len(a).to_bytes(2, 'big') + b''.join(encode(x) for x in a)
    b = a.encode('utf-8')
    return b'S' + len(b).to_bytes(2, 'big') + b


def decode(buf, i=0):
    """Inverse of `encode`, so the round-trip control can actually fail."""
    if buf[i:i + 1] == b'S':
        ln = int.from_bytes(buf[i + 1:i + 3], 'big')
        return buf[i + 3:i + 3 + ln].decode('utf-8'), i + 3 + ln
    ar = int.from_bytes(buf[i + 1:i + 3], 'big')
    i += 3
    out = []
    for _ in range(ar):
        c, i = decode(buf, i)
        out.append(c)
    return out, i


def load_corpus(path):
    progs, stats = [], {'files': 0, 'dropped': 0, 'expr_nodes': 0}
    for f in sorted(os.listdir(path)):
        if not f.endswith('.metta'):
            continue
        atoms, dropped = parse(tokenize(open(os.path.join(path, f)).read()))
        stats['files'] += 1
        stats['dropped'] += dropped
        stats['expr_nodes'] += sum(count_exprs(a) for a in atoms)
        progs.append((f, atoms))
    return progs, stats


def count_exprs(a):
    return 1 + sum(count_exprs(x) for x in a) if isinstance(a, list) else 0


# ------------------------------------------------------- epoch commitment
def commit(keys):
    return build(sorted(set(keys)))


def all_digests(node, out=None):
    """Every node digest in the trie. Set-differencing two epochs gives exactly
    the nodes that had to be recomputed, because structural sharing means an
    unchanged subtrie keeps its digest."""
    if out is None:
        out = set()
    out.add(node.h)
    for b in sorted(node.children):
        all_digests(node.children[b], out)
    return out


# ------------------------------------- fold-forward single-insert delta proof
def prove_insert(root, k):
    """A proof that k is absent from `root`, which is also everything needed to
    compute the root that results from inserting it."""
    pf = prove_non_membership(root, k)
    if pf is None:
        return None                       # already present; no insertion to prove
    j = 0
    for (prefix, _t, _p), _b in pf['steps']:
        j += len(prefix) + 1
    pf['offset'] = j
    return pf


def apply_insert(d, R):
    """Given the PROVEN description of the divergence node and the key's
    remaining bytes, return the digest of the node that replaces it.

    Four cases, all reachable on variable-length keys. Any of them wrong and
    C_incremental_equals_full fires -- that control is what decides whether this
    function is right, not inspection.
    """
    P, term, pairs = d[0], d[1], list(d[2])
    m = 0
    while m < len(P) and m < len(R) and P[m] == R[m]:
        m += 1
    if m == len(P) and len(R) > len(P):
        # 1. hang a new leaf off an absent branch byte
        b = R[m]
        leaf = node_hash(R[m + 1:], True, [])
        return node_hash(P, term, sorted(pairs + [(b, leaf)]))
    if m == len(P) and len(R) == len(P):
        # 2. the node exists but is not terminal; make it terminal
        return node_hash(P, True, pairs)
    if m == len(R):
        # 3. the key ends inside the compressed prefix; split, new part terminal
        tail = node_hash(P[m + 1:], term, pairs)
        return node_hash(R, True, [(P[m], tail)])
    # 4. prefixes diverge mid-way; split into a fork with two children
    tail = node_hash(P[m + 1:], term, pairs)
    leaf = node_hash(R[m + 1:], True, [])
    return node_hash(P[:m], False, sorted([(P[m], tail), (R[m], leaf)]))


def verify_insert(root_hash, k, pf):
    """Return the root that MUST result from inserting k, or None if the proof
    does not establish that k was absent from root_hash. The verifier computes
    the new root; it never receives it."""
    if pf is None or not verify_non_membership(root_hash, k, pf):
        return None
    return fold(pf['steps'], apply_insert(pf['node'], k[pf['offset']:]))


def prove_epoch_delta(root_prev, prev_keys, added):
    """k additions, proved one at a time in canonical order against the
    intermediate roots. No batch multiproof: W1/W3 died on a mis-counted one,
    and k sequential paths are correct by construction."""
    cur_keys, cur, proofs = set(prev_keys), root_prev, []
    for kk in sorted(added):
        if kk in cur_keys:
            continue
        pf = prove_insert(cur, kk)
        proofs.append((kk, pf))
        cur_keys.add(kk)
        cur = commit(cur_keys)
    return proofs


def verify_epoch_delta(root_prev, proofs):
    """Fold root_prev forward through every proof. Returns the final root or None.
    A verifier that gets root_N+1 and this list can check the transition without
    holding a single atom of the space beyond the additions themselves."""
    cur = root_prev
    for kk, pf in proofs:
        nxt = verify_insert(cur, kk, pf)
        if nxt is None:
            return None
        cur = nxt
    return cur


# ------------------------------------------------- the null, and why it fails
def xor_digest(keys):
    """XOR-of-hashes: the unordered commitment. It DOES give O(k) epoch deltas,
    which is what makes it a real null rather than a straw man -- it passes the
    cheap test the trie passes. C_xor_forgeable then shows what it costs."""
    return reduce(lambda a, b: bytes(x ^ y for x, y in zip(a, b)),
                  (hashlib.sha256(k).digest() for k in keys), b'\0' * 32)


def main():
    rnd = random.Random(SEED)
    progs, stats = load_corpus(CORPUS)
    out = {'seed': SEED, 'corpus': {'path': os.path.relpath(CORPUS, HERE), **stats},
           'epochs': [], 'controls': {}}

    prog_keys = [(f, sorted({encode(a) for a in atoms})) for f, atoms in progs]
    allk = sorted({k for _f, ks in prog_keys for k in ks})
    out['corpus']['distinct_atoms'] = len(allk)
    out['corpus']['atom_bytes'] = sum(len(k) for k in allk)

    # ---- the epoch chain: each program is one epoch's additions
    seen, root, digs = set(), commit([b'\0']), None
    seen_keys = {b'\0'}                      # a non-empty genesis space
    root = commit(seen_keys)
    digs = all_digests(root)
    chain_ok = True
    for f, ks in prog_keys:
        added = [k for k in ks if k not in seen_keys]
        if not added:
            continue
        proofs = prove_epoch_delta(root, seen_keys, added)
        # `root.h`, not `root`: the verifier gets a DIGEST, never the prover's
        # node. Passing the Node made every fold compare a hash to an object and
        # silently return None, and C_incremental_equals_full is what caught it.
        computed = verify_epoch_delta(root.h, proofs)
        seen_keys |= set(added)
        nxt = commit(seen_keys)
        ndigs = all_digests(nxt)
        agreed = computed == nxt.h
        chain_ok = chain_ok and agreed
        pbytes = sum(steps_bytes(pf['steps']) + desc_bytes(pf['node']) + len(kk)
                     for kk, pf in proofs)
        out['epochs'].append({
            'program': f, 'added': len(added), 'space_atoms': len(seen_keys),
            'space_bytes': sum(len(k) for k in seen_keys),
            'nodes_total': len(ndigs),
            'nodes_recomputed': len(ndigs - digs),
            'proof_bytes': pbytes,
            'proof_bytes_per_add': pbytes / len(added),
            'verifier_agreed': agreed,
            'xor_root': xor_digest(sorted(seen_keys)).hex()[:16],
            'trie_root': nxt.h.hex()[:16]})
        root, digs = nxt, ndigs

    # ---- how does a SINGLE insert's cost grow with the space? The per-epoch
    # table cannot answer this: its `frac` column falls only because the
    # denominator grows, which says nothing about the cost of one addition.
    # This is the number that decides deployability, so it is measured, not
    # extrapolated from the last row.
    # MATCHED HOLD-OUT. The first version drew a fresh set of probe atoms for
    # each space size, so the rows differed in BOTH space size and which atoms
    # were inserted -- and the proof bytes came out non-monotonic (433 / 279 /
    # 952), which is a confound reported as a rate (A18). The same 25 held-out
    # atoms are now inserted into every space, so only the space size varies.
    # ...and the matched hold-out needed a SECOND fix. Taking the probe as the
    # lexicographic tail `ks_all[-25:]` and the base as `pool[:n]` made every
    # probe diverge at or near the root, because a sorted prefix of the key space
    # contains nothing adjacent to a sorted suffix of it. The result was 293 B
    # flat across a 10x space range -- the cost of inserting OUTSIDE the occupied
    # range, not the cost of an insert. Shuffle first so both probe and base are
    # spread across the key space and the probes land surrounded.
    out['scaling'] = []
    ks_all = sorted(seen_keys)
    shuf = list(ks_all)
    random.Random(SEED).shuffle(shuf)
    probe = shuf[:25]
    pool = shuf[25:]
    for n in (100, 300, 1000, len(pool)):
        if n > len(pool):
            break
        base = set(pool[:n])
        rt = commit(base)
        pb, rh, dg = [], [], all_digests(rt)
        for kk in probe:
            pf = prove_insert(rt, kk)
            assert verify_insert(rt.h, kk, pf) == commit(base | {kk}).h
            pb.append(steps_bytes(pf['steps']) + desc_bytes(pf['node']) + len(kk))
            rh.append(len(all_digests(commit(base | {kk})) - dg))
        out['scaling'].append({
            'space_atoms': n, 'nodes': len(dg), 'inserts_sampled': len(pb),
            'probe_is_matched': True,
            'proof_bytes_mean': sum(pb) / len(pb),
            'proof_bytes_max': max(pb),
            'new_digests_per_insert': sum(rh) / len(rh)})

    out['final'] = {'atoms': len(seen_keys), 'trie_root': root.h.hex(),
                    'xor_root': xor_digest(sorted(seen_keys)).hex(),
                    'nodes': len(digs), 'epochs': len(out['epochs']),
                    'chain_verified': chain_ok}

    # -------------------------------------------------------------- CONTROLS
    C = out['controls']
    ks = sorted(seen_keys)

    # C_reader_roundtrip -- decode(encode(a)) must reproduce the atom, and a
    # re-encode must be byte-identical. FAILS IF the reader loses or invents
    # structure; a corpus that parses "cleanly" into the wrong atom set commits
    # every digest here to the wrong thing.
    bad = 0
    for k in rnd.sample(ks, min(500, len(ks))):
        a, used = decode(k)
        if used != len(k) or encode(a) != k:
            bad += 1
    C['C_reader_roundtrip'] = {
        'fires': bad == 0 and stats['dropped'] == 0,
        'fails_if': 'any atom fails to round-trip, or the reader dropped an '
                    'unbalanced form -- the atom set would not be the corpus',
        'observed': {'sampled': min(500, len(ks)), 'roundtrip_failures': bad,
                     'dropped_forms': stats['dropped'],
                     'expr_nodes_parsed': stats['expr_nodes']}}

    # C_incremental_equals_full -- the verifier's fold-forward root must equal a
    # full rebuild, over every epoch. FAILS IF any epoch disagrees, which is what
    # a wrong case in apply_insert looks like.
    C['C_incremental_equals_full'] = {
        'fires': chain_ok and len(out['epochs']) > 0,
        'fails_if': 'a computed root differs from the rebuilt root in any epoch '
                    '-- apply_insert would have a wrong case and the delta proof '
                    'would be unsound',
        'observed': {'epochs': len(out['epochs']),
                     'agreed': sum(1 for e in out['epochs'] if e['verifier_agreed'])}}

    # C_apply_insert_cases -- all four apply_insert branches must actually be
    # exercised. FAILS IF any case count is 0: an unexercised branch is an
    # untested one, and C_incremental_equals_full would be silent about it.
    cases = {1: 0, 2: 0, 3: 0, 4: 0}
    probe = commit(ks[:200])
    for kk in ks[200:600]:
        pf = prove_insert(probe, kk)
        if pf is None:
            continue
        P, R = pf['node'][0], kk[pf['offset']:]
        m = 0
        while m < len(P) and m < len(R) and P[m] == R[m]:
            m += 1
        cases[1 if (m == len(P) and len(R) > len(P)) else
              2 if (m == len(P) and len(R) == len(P)) else
              3 if m == len(R) else 4] += 1
    # Cases 2 and 3 need one atom's encoding to be a proper PREFIX of another's,
    # and `encode` is self-delimiting, so it is prefix-free and they cannot occur.
    # That is checked rather than asserted: if the encoding ever stops being
    # prefix-free (interior subexpressions as keys would do it), `prefix_free`
    # goes False and those two branches become live, untested code.
    prefix_free = not any(ks[i + 1].startswith(ks[i]) for i in range(len(ks) - 1))
    C['C_apply_insert_cases'] = {
        'fires': cases[1] > 0 and cases[4] > 0 and prefix_free
                 and cases[2] == 0 and cases[3] == 0,
        'fails_if': 'the branch-add (1) or mid-prefix fork (4) case is never '
                    'reached, OR cases 2/3 fire while the encoding is still '
                    'prefix-free, OR prefix_free goes False -- in which case '
                    'cases 2 and 3 are live code that nothing here tests',
        'observed': {**{f'case_{k_}': v for k_, v in cases.items()},
                     'encoding_prefix_free': prefix_free,
                     'cases_2_3_unreachable_by_construction': prefix_free}}

    # C_wrong_prior_root -- fold a valid delta from the WRONG prior root.
    # FAILS IF it still produces a root; the chain would not bind history.
    e0 = prog_keys[0][1][:5]
    g = commit({b'\0'})
    pfs = prove_epoch_delta(g, {b'\0'}, e0)
    wrong = commit({b'\1'})
    C['C_wrong_prior_root'] = {
        'fires': verify_epoch_delta(wrong.h, pfs) is None,
        'fails_if': 'a delta verifies against a prior root it was not built on '
                    '-- epochs would not chain',
        'observed': {'genesis': g.h.hex()[:16], 'wrong': wrong.h.hex()[:16],
                     'adds': len(pfs)}}

    # C_smuggled_extra_atom -- the prover slips in an atom the delta did not
    # declare. FAILS IF the computed root still matches the prover's new root.
    smug = commit(set(e0) | {b'\0', b'SMUGGLED'})
    C['C_smuggled_extra_atom'] = {
        'fires': verify_epoch_delta(g.h, pfs) != smug.h,
        'fails_if': "an undeclared atom leaves the computed root unchanged -- the "
                    'delta would bound additions it does not name',
        'observed': {'declared_root': (verify_epoch_delta(g.h, pfs) or b'').hex()[:16],
                     'smuggled_root': smug.h.hex()[:16]}}

    # C_content_not_shape -- S65's exact hole. Two spaces, SAME atom count,
    # different atoms. FAILS IF the roots collide, i.e. the commitment binds
    # shape rather than content and is forgeable without running anything.
    a_set, b_set = set(ks[:300]), set(ks[:299]) | {encode(['NOT', 'IN', 'CORPUS'])}
    C['C_content_not_shape'] = {
        'fires': len(a_set) == len(b_set) and commit(a_set).h != commit(b_set).h,
        'fails_if': 'two spaces of equal size with different atoms share a root '
                    '-- this is S65, where 100% of leaves were "()" and the root '
                    'was forged in 6 lines without running hyperon',
        'observed': {'n_a': len(a_set), 'n_b': len(b_set),
                     'root_a': commit(a_set).h.hex()[:16],
                     'root_b': commit(b_set).h.hex()[:16]}}

    # C_insertion_order_invariance -- the same atom set committed in 20 random
    # insertion orders must give one root. FAILS IF any differs: two honest
    # replicas that learned the same facts in different orders would disagree,
    # which would make the whole commitment unusable for adaptation.
    sub = ks[:400]
    roots = set()
    for _ in range(20):
        p = list(sub)
        rnd.shuffle(p)
        roots.add(commit(p).h)
    C['C_insertion_order_invariance'] = {
        'fires': len(roots) == 1,
        'fails_if': 'two insertion orders of one atom set give two roots -- '
                    'replicas that learned the same facts in different orders '
                    'would never agree',
        'observed': {'orders': 20, 'distinct_roots': len(roots)}}

    # C_sharing_real -- structural sharing must make an epoch cost far less than
    # a rebuild. FAILS IF the recomputed fraction approaches 1, i.e. sharing buys
    # nothing and every epoch rehashes the whole space.
    fr = [e['nodes_recomputed'] / e['nodes_total'] for e in out['epochs']]
    C['C_sharing_real'] = {
        'fires': bool(fr) and sum(fr) / len(fr) < 0.5 and min(fr) < 0.1,
        'fails_if': 'the mean recomputed-node fraction reaches 0.5 -- structural '
                    'sharing would buy nothing and an epoch would cost a rebuild',
        'observed': {'mean_fraction': sum(fr) / len(fr) if fr else None,
                     'min': min(fr) if fr else None, 'max': max(fr) if fr else None}}

    # C_xor_forgeable -- THE NULL, and it is not a straw man: XOR-of-hashes gives
    # O(k) epoch deltas too, so it passes the cheap test. It is broken anyway,
    # constructively: a^a = 0, so declaring any atom TWICE returns the digest to
    # its previous value while the space has changed. FAILS IF no such collision
    # can be built -- then XOR would suffice and the trie is unjustified.
    base = set(ks[:300])
    extra = encode(['FORGED', 'PAIR'])
    forged = sorted(list(base) + [extra, extra])       # multiset, atom twice
    C['C_xor_forgeable'] = {
        'fires': (xor_digest(sorted(base)) == xor_digest(forged)
                  and commit(set(forged)).h != commit(base).h),
        'fails_if': 'no equal-digest different-space can be built -- XOR would be '
                    'a sound set commitment and the trie would be unjustified',
        'observed': {'xor_base': xor_digest(sorted(base)).hex()[:16],
                     'xor_forged': xor_digest(forged).hex()[:16],
                     'trie_base': commit(base).h.hex()[:16],
                     'trie_forged': commit(set(forged)).h.hex()[:16]}}

    # C_xor_cannot_prove_absence -- the null's second failure, stated as a
    # measurement rather than an appeal to intuition: the XOR digest is 32 bytes
    # and carries no path, so absence proofs have no bytes to be made of. The
    # trie's do. FAILS IF the trie's absence proof is not larger than 32 bytes,
    # which would mean it carries no structure either.
    absent = encode(['DEFINITELY', 'ABSENT', 'ATOM'])
    apf = prove_non_membership(commit(base), absent)
    nm_bytes = steps_bytes(apf['steps']) + desc_bytes(apf['node'])
    C['C_xor_cannot_prove_absence'] = {
        'fires': (verify_non_membership(commit(base).h, absent, apf)
                  and nm_bytes > 32),
        'fails_if': 'the trie absence proof is not larger than the 32-byte XOR '
                    'digest -- it would carry no structure the digest lacks',
        'observed': {'xor_bytes': 32, 'trie_absence_proof_bytes': nm_bytes,
                     'verified': True}}

    # C_root_is_state_not_history -- the same atoms grouped into DIFFERENT epoch
    # sequences must reach the SAME final root. Fires if equal. This is stated as
    # a control rather than a caveat because it is the property most likely to be
    # misread: the root commits to the SPACE, never to the path taken to it. A
    # reader who assumes it binds history would accept a forged epoch sequence.
    # FAILS IF the roots differ -- then it is not a state commitment at all.
    grp = sorted(seen_keys)
    r_a, ka = commit({b'\0'}), {b'\0'}
    for chunk in (grp[:400], grp[400:900], grp[900:]):
        ka |= set(chunk)
        r_a = commit(ka)
    r_b, kb = commit({b'\0'}), {b'\0'}
    for chunk in (grp[:150], grp[150:1100], grp[1100:]):
        kb |= set(chunk)
        r_b = commit(kb)
    C['C_root_is_state_not_history'] = {
        'fires': r_a.h == r_b.h == root.h,
        'fails_if': 'two epoch groupings of one atom set reach different roots -- '
                    'then the root is not a state commitment. It also means the '
                    'root does NOT bind history: binding that needs the chain of '
                    '(root, delta) pairs hashed together, which this spike does '
                    'not build',
        'observed': {'grouping_a': r_a.h.hex()[:16], 'grouping_b': r_b.h.hex()[:16],
                     'chain_root': root.h.hex()[:16]}}

    out['all_controls_fire'] = all(c['fires'] for c in C.values())

    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    with open(os.path.join(HERE, 'epoch.json'), 'w') as f:
        json.dump(out, f, indent=1)
    provenance(out)
    return out


def report(o):
    c, f = o['corpus'], o['final']
    print(f"S73 — canonical SPACE state at an epoch boundary (seed {o['seed']})")
    print(f"corpus {c['files']} programs, {c['expr_nodes']:,} expression nodes, "
          f"{c['distinct_atoms']:,} distinct top-level atoms "
          f"= {c['atom_bytes']:,} B encoded")
    print(f"final space {f['atoms']:,} atoms / {f['nodes']:,} trie nodes over "
          f"{f['epochs']} epochs; chain verified {f['chain_verified']}")
    print(f"trie root {f['trie_root'][:32]}…\n")
    print(f"{'epoch':<38} {'added':>6} {'atoms':>6} {'nodes':>6} {'rehash':>7} "
          f"{'frac':>6} {'proof B/add':>12} {'ok':>3}")
    es = o['epochs']
    for e in es[:6] + ([None] if len(es) > 9 else []) + es[-3:]:
        if e is None:
            print(f"{'  … %d more epochs …' % (len(es) - 9):<38}")
            continue
        print(f"{e['program'][:38]:<38} {e['added']:>6} {e['space_atoms']:>6} "
              f"{e['nodes_total']:>6} {e['nodes_recomputed']:>7} "
              f"{e['nodes_recomputed']/e['nodes_total']:>6.3f} "
              f"{e['proof_bytes_per_add']:>12.0f} "
              f"{'Y' if e['verifier_agreed'] else 'N':>3}")
    if o.get('scaling'):
        print(f"\nSINGLE-INSERT COST vs SPACE SIZE (25 inserts each)")
        print(f"  {'atoms':>7} {'nodes':>7} {'proof B':>9} {'max':>7} "
              f"{'new digests/insert':>19}")
        for s_ in o['scaling']:
            print(f"  {s_['space_atoms']:>7} {s_['nodes']:>7} "
                  f"{s_['proof_bytes_mean']:>9.0f} {s_['proof_bytes_max']:>7} "
                  f"{s_['new_digests_per_insert']:>19.2f}")
    print(f"\nCONTROLS — each names the input that makes it fail")
    for name, ct in o['controls'].items():
        print(f"  {'FIRES ' if ct['fires'] else 'DEAD  '} {name:<30} {ct['fails_if']}")
    print(f"\nall controls fire: {o['all_controls_fire']}")


# The observation that would have made each control NOT fire, stated as a value
# in `observed` rather than as a sentiment. `harness/provenance.py` refuses a
# control without one (A15), and D6 H1 is explicit that this catches an ABSENT
# statement and not a vacuous one -- so these are written against the recorded
# numbers, where a third party can check them.
CAN_FAIL = {
    'C_reader_roundtrip':
        'roundtrip_failures > 0 or dropped_forms > 0. Mishandling `;` inside a '
        'string literal, or `\\"` inside one, produces exactly that.',
    'C_incremental_equals_full':
        'agreed < epochs. A wrong branch in apply_insert shows up here and '
        'nowhere else.',
    'C_apply_insert_cases':
        'case_1 or case_4 reads 0, i.e. the equality control never drove that '
        'branch at all.',
    'C_wrong_prior_root':
        'verify_epoch_delta returns a root instead of None under the wrong '
        'genesis.',
    'C_smuggled_extra_atom':
        'declared_root equals smuggled_root.',
    'C_content_not_shape':
        'root_a equals root_b while n_a == n_b. This is the S65 outcome.',
    'C_insertion_order_invariance':
        'distinct_roots > 1 across the 20 shuffles.',
    'C_sharing_real':
        'mean_fraction reaches 0.5 -- every epoch rehashing half the trie.',
    'C_xor_forgeable':
        'xor_base != xor_forged, i.e. no duplicate-atom collision exists and '
        'XOR is a sound set commitment after all.',
    'C_xor_cannot_prove_absence':
        'trie_absence_proof_bytes <= 32, i.e. the trie proof carries no '
        'structure the bare digest lacks.',
    'C_root_is_state_not_history':
        'grouping_a != grouping_b, i.e. the root depends on how the atoms were '
        'batched into epochs.',
}


def provenance(out):
    sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
    try:
        import provenance as P
        import kfcheck as KF
    except ImportError:
        return
    cs = []
    for name, c in out['controls'].items():
        ctl = P.Control(name, c['fails_if'],
                        null_must_contain='the failure this control injects',
                        can_fail_because=CAN_FAIL[name])
        ctl.observe(c['fires'], c['observed'])
        cs.append(ctl)
    # kfcheck.certify, not provenance.record: CLAUDE.md's entry point runs
    # families B and E too and REFUSES a run with no declared falsifier.
    # Family E fires on the scaling rows -- units.check_affine refuses an affine
    # model (adjacent slopes span 203% of tolerance) -- so "12x the space costs
    # 2.27x the proof" is an ENDPOINT RATIO over measured points and no rate may
    # be fitted to it.
    ok, problems = KF.certify(
        HERE, deps=(os.path.join(HERE, '..', 'S57_hyperon_corpus'),),
        artifacts=[os.path.join(HERE, 'epoch.py'),
                   os.path.join(HERE, 'epoch.json')],
        controls=cs, allow_dirty=True,
        captures=[('final_trie_root', out['final']['trie_root']),
                  ('final_xor_root', out['final']['xor_root'])],
        measurements=[{'name': 'insert_proof_bytes_vs_space_atoms',
                       'points': [(s['space_atoms'], s['proof_bytes_mean'])
                                  for s in out['scaling']],
                       'as_rate': False}],
        falsifier='Exhibit an epoch delta this verifier folds to the prover\'s '
                  'new root while the added atom set differs from the one it '
                  'declares -- that refutes the delta proof. Or: show two epoch '
                  'groupings of one atom set reaching different roots, which '
                  'refutes it as a state commitment at all.',
        note='S73 canonical space state at an epoch boundary; fold-forward delta '
             'proofs, XOR null shown forgeable. Scaling rows are MEASURED POINTS, '
             'not a rate: units.check_affine refuses an affine fit.')
    prov = {'problems': problems}
    if not ok:
        print('\nPROVENANCE PROBLEMS:')
        for p in prov['problems']:
            print('  ' + p)


if __name__ == '__main__':
    main()
