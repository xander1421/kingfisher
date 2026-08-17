#!/usr/bin/env python3
"""ATTACK cycle 4 — against the trie instrument W2 and S73 both rest on.

WHY THIS EXISTS
---------------
W2 and S73 share one implementation of `build`, `node_hash`, `walk` and `fold`.
I wrote the prover AND the verifier out of those same four functions. That is
A22 — a party supplying the input to a check on itself. If `node_hash` or `build`
is wrong, the prover and the verifier agree on the wrong answer and **every one of
the 20 controls across both spikes passes anyway**. Quorum cannot see this either:
three replicas running the same code agree byte-identically on a shared bug.

So the attacks are ordered instruments-first, and the first one is implementation
diversity: a SECOND, independently constructed trie, built by a different
algorithm, checked against the first on the real corpora.

  python3 attack.py
"""
import os, sys, json, hashlib, struct, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
from trie_witness import (build, node_hash, desc, walk, fold, load, key,
                          prove_membership, verify_membership,
                          prove_non_membership, verify_non_membership,
                          prove_completeness, verify_completeness,
                          steps_bytes, desc_bytes, COVER)

SEED = 20260817
FINDINGS = []


def finding(id_, verdict, text):
    FINDINGS.append({'id': id_, 'verdict': verdict, 'text': text})
    print(f"[{verdict:8}] {id_}: {text}")


# ===================================================================== A2
# Independent construction. `build` divides a SORTED key list on the longest
# common prefix, recursively. This inserts keys ONE AT A TIME into a mutable
# trie -- the classic algorithm -- then hashes bottom-up in a separate pass.
# Nothing is shared but the serialization format, which is the spec.
class MNode:
    __slots__ = ('prefix', 'kids', 'term')

    def __init__(self, prefix=b'', term=False):
        self.prefix, self.kids, self.term = prefix, {}, term


def ins(node, k):
    """Insert k (relative to this node) into a mutable trie."""
    P = node.prefix
    m = 0
    while m < len(P) and m < len(k) and P[m] == k[m]:
        m += 1
    if m < len(P):
        # split this node at m
        lower = MNode(P[m + 1:], node.term)
        lower.kids = node.kids
        node.prefix, node.kids, node.term = P[:m], {P[m]: lower}, False
    # node.prefix is now a prefix of k[:len(node.prefix)]
    r = k[len(node.prefix):]
    if not r:
        node.term = True
        return
    b = r[0]
    if b in node.kids:
        ins(node.kids[b], r[1:])
    else:
        node.kids[b] = MNode(r[1:], True)


def mhash(node):
    """Independently written serializer, from the format sentence in W2:
    'N', 2-byte prefix length, prefix, T or -, 2-byte child count, then each
    (byte, child digest) in ascending byte order."""
    parts = [b'N', struct.pack('>H', len(node.prefix)), node.prefix,
             b'T' if node.term else b'-', struct.pack('>H', len(node.kids))]
    for b in sorted(node.kids):
        parts.append(bytes([b]))
        parts.append(mhash(node.kids[b]))
    return hashlib.sha256(b''.join(parts)).digest()


def independent_root(keys):
    root = MNode(b'', False)
    ks = list(keys)
    if not ks:
        return None
    root.prefix = ks[0]
    root.term = True
    for k in ks[1:]:
        ins(root, k)
    return mhash(root)


def attack_a2():
    triples, NT, NP, NE = load(os.path.join(HERE, '..', 'S52_realkg', 'triples.bin'))
    srt = sorted(triples, key=lambda t: (t[0], t[1], t[2]))
    agree, disagree = 0, []
    for off, n in ((0, 4096), (136000, 4096), (0, 1024), (50000, 8192)):
        ks = sorted(key(*t) for t in srt[off:off + n])
        a, b = build(ks).h, independent_root(ks)
        (agree := agree + 1) if a == b else disagree.append((off, n, a.hex()[:16], b.hex()[:16]))
    # and on S73's variable-length atom keys, where the prefix logic is exercised
    import epoch as E
    progs, _st = E.load_corpus(E.CORPUS)
    ak = sorted({E.encode(x) for _f, atoms in progs for x in atoms})
    for n in (50, 300, len(ak)):
        a, b = build(ak[:n]).h, independent_root(ak[:n])
        (agree := agree + 1) if a == b else disagree.append(('atoms', n, a.hex()[:16], b.hex()[:16]))
    if disagree:
        finding('A2-independent-build', 'FATAL',
                f'two independently constructed tries disagree on {len(disagree)} '
                f'of {agree + len(disagree)} key sets: {disagree[:3]}')
    else:
        finding('A2-independent-build', 'SURVIVES',
                f'{agree}/{agree} key sets agree, across fixed-length triple keys '
                f'(4 shards) and variable-length atom keys (3 sizes, {len(ak)} atoms). '
                f'Insertion-order construction and sorted-divide construction reach '
                f'the same root, so the lcp logic in `build` is not carrying a bug '
                f'that the verifier would mirror.')
    return ak


# ===================================================================== A3
# W2's C_omit drops the LAST key of a non-empty answer. Three omission shapes it
# never tested: a middle key, a swap for another real key, and the extreme case
# -- claiming the answer is EMPTY when it is not.
def attack_a3():
    triples, NT, NP, NE = load(os.path.join(HERE, '..', 'S52_realkg', 'triples.bin'))
    srt = sorted(triples, key=lambda t: (t[0], t[1], t[2]))
    ks = sorted(key(*t) for t in srt[:4096])
    root = build(ks)
    R = root.h
    t = srt[2048]
    q = key(t[0], t[1], 0)[:8]
    good = prove_completeness(root, q)
    if len(good['keys']) < 4:
        finding('A3-omission-shapes', 'INCONCLUSIVE',
                'the probe prefix had fewer than 4 rows; cannot drop a middle one')
        return
    holes = {}
    mid = dict(good); mid['keys'] = good['keys'][:1] + good['keys'][2:]
    holes['drop_middle'] = verify_completeness(R, q, mid)
    swapped = dict(good)
    other = [k for k in ks if not k.startswith(q)][0]
    swapped['keys'] = sorted(good['keys'][:-1] + [other])
    holes['swap_for_real_key'] = verify_completeness(R, q, swapped)
    empty = dict(good); empty['keys'] = []
    holes['claim_empty'] = verify_completeness(R, q, empty)
    empty2 = dict(good); empty2['keys'] = []; empty2['kind'] = 'miss_byte'
    empty2['node'] = desc(root)
    holes['claim_empty_as_miss'] = verify_completeness(R, q, empty2)
    dup = dict(good); dup['keys'] = sorted(good['keys'] + [good['keys'][0]])
    holes['duplicate_row'] = verify_completeness(R, q, dup)
    accepted = [k for k, v in holes.items() if v]
    if accepted:
        finding('A3-omission-shapes', 'FATAL',
                f'verify_completeness ACCEPTED these cheats: {accepted} (rows in '
                f'honest answer: {len(good["keys"])})')
    else:
        finding('A3-omission-shapes', 'SURVIVES',
                f'all 5 untested cheat shapes rejected on a {len(good["keys"])}-row '
                f'answer: drop-middle, swap-for-another-real-key, claim-empty, '
                f'claim-empty-as-a-miss, duplicate-row. W2 only tested drop-last; '
                f'the gap was in its CONTROL SET, not in the verifier.')


# ===================================================================== A4
# S73 ships apply_insert cases 2 and 3 as UNREACHABLE code: the atom encoding is
# prefix-free, so no key ends inside another. Unreachable means untested, and it
# ships. Force them with synthetic prefix-nested keys.
def attack_a4():
    import epoch as E
    nested = [b'ab', b'abc', b'abd', b'abcd', b'b', b'bcd', b'xyz']
    hits = {2: 0, 3: 0}
    bad = []
    for i in range(len(nested)):
        base = set(nested[:i] + nested[i + 1:])
        if not base:
            continue
        rt = E.commit(base)
        kk = nested[i]
        pf = E.prove_insert(rt, kk)
        if pf is None:
            continue
        P, Rm = pf['node'][0], kk[pf['offset']:]
        m = 0
        while m < len(P) and m < len(Rm) and P[m] == Rm[m]:
            m += 1
        case = (1 if (m == len(P) and len(Rm) > len(P)) else
                2 if (m == len(P) and len(Rm) == len(P)) else
                3 if m == len(Rm) else 4)
        hits[case] = hits.get(case, 0) + 1
        got = E.verify_insert(rt.h, kk, pf)
        want = E.commit(base | {kk}).h
        if got != want:
            bad.append((kk, case, (got or b'').hex()[:12], want.hex()[:12]))
    if bad:
        finding('A4-unreachable-cases', 'FATAL',
                f'apply_insert is WRONG on prefix-nested keys: {bad}. Cases 2/3 are '
                f'dead only while the encoding stays prefix-free; committing '
                f'interior subexpressions would make them live.')
    elif not (hits.get(2) or hits.get(3)):
        # A probe that never reached its target must NOT report a clean null.
        # The first run of this attack did exactly that -- hits {2:0,3:0,1:3} and
        # a SURVIVES verdict -- which is W1's dead-control sin committed inside
        # an ATTACK cycle. Reaching the target is now a precondition of a verdict.
        finding('A4-unreachable-cases', 'PROBE-FAILED',
                f'case hits {hits}: neither case 2 nor case 3 was reached, so this '
                f'attack proves nothing about them. Do not read the absence of a '
                f'FATAL here as evidence.')
    else:
        finding('A4-unreachable-cases', 'SURVIVES',
                f'forced with prefix-nested synthetic keys, case hits {hits}, every '
                f'computed root matches a full rebuild. The two branches S73 could '
                f'not exercise are correct; that was luck, not evidence, until now.')


# ===================================================================== A1
# Encoding ceilings. Both encoders pack lengths into 2 bytes. Past 65,535 they
# raise rather than collide -- but a raise in a commitment path is a liveness
# failure, and "we never hit it" is not a bound unless it is measured.
def attack_a1(ak):
    import epoch as E
    progs, _ = E.load_corpus(E.CORPUS)
    max_sym, max_arity, max_enc = 0, 0, 0

    def scan(a):
        nonlocal max_sym, max_arity
        if isinstance(a, list):
            max_arity = max(max_arity, len(a))
            for x in a:
                scan(x)
        else:
            max_sym = max(max_sym, len(a.encode('utf-8')))
    for _f, atoms in progs:
        for a in atoms:
            scan(a)
    max_enc = max(len(k) for k in ak)
    # does it actually raise, or silently truncate?
    try:
        E.encode(['x' * 70000])
        raised = False
    except OverflowError:
        raised = True
    # and node_hash's own 2-byte prefix length
    try:
        node_hash(b'\0' * 70000, True, [])
        nh_raised = False
    except OverflowError:
        nh_raised = True
    hi = max(max_sym, max_arity)
    finding('A1-encoding-ceiling',
            'SURVIVES' if (raised and nh_raised) else 'FATAL',
            f'2-byte length fields cap symbols and arity at 65,535. Corpus '
            f'maxima: symbol {max_sym} B, arity {max_arity}, longest atom '
            f'encoding {max_enc} B -- headroom {65535 // max(hi, 1)}x. Overflow '
            f'RAISES rather than truncating (encode {raised}, node_hash '
            f'{nh_raised}), so it is a liveness limit, never a silent collision. '
            f'A single 64 KB string literal in a corpus would abort a commit.')


# ===================================================================== A5
# D6's own falsifier F2, re-measured after two cycles of my own work. If my
# spikes are the only ones that honour the spec I wrote, that is worth stating
# plainly rather than quoting the original 6/6.
def attack_a5():
    spikes = os.path.join(HERE, '..')
    cite, have, partial = [], [], []
    for d in sorted(os.listdir(spikes)):
        rp = os.path.join(spikes, d, 'RESULT.md')
        if not os.path.isfile(rp):
            continue
        txt = open(rp, errors='replace').read()
        if 'D6' not in txt:
            continue
        cite.append(d)
        # FILE PRESENCE IS NOT COMPLIANCE. The first version of this probe only
        # tested that provenance.json existed, and after the retro-fit it scored
        # W4/N1/S72 as passing while their records say ok:false. Read the verdict.
        pj = os.path.join(spikes, d, 'provenance.json')
        if os.path.isfile(pj):
            try:
                doc = json.load(open(pj))
            except Exception:
                continue
            if doc.get('ok'):
                have.append(d)
            else:
                partial.append((d, doc.get('d6_retrofit', {}).get('status'),
                                doc.get('d6_retrofit', {}).get('prose_only')))
    # And the inverse population, which the original F2 never counted: spikes
    # that HAVE a provenance record and do not cite D6 at all.
    silent = [d for d in sorted(os.listdir(spikes))
              if os.path.isfile(os.path.join(spikes, d, 'provenance.json'))
              and d not in cite]
    finding('A5-D6-F2-remeasured', 'HONEST-DEBT',
            f'{len(cite)} RESULT.md cite D6, {len(have)} are ok:true -- '
            f'still failing {len(cite) - len(have)}/{len(cite)}. '
            f'PARTIAL (record present, ok:false, controls that exist only in '
            f'prose): {partial}. Debt with no record at all: '
            f'{[d for d in cite if d not in have and d not in [x[0] for x in partial]]}. '
            f'My own two spikes this session '
            f'are in the OTHER population: {silent} carry a provenance record and '
            f'never mention D6, so F2 as written scores neither of them. F2 counts '
            f'citation without compliance and is blind to compliance without '
            f'citation; the falsifier needs both directions.')


# ===================================================================== A6
# My own provenance fix, attacked. The staleness floor is max(path-scoped HEAD
# time, newest dirty file). What if a dep tree has NEITHER?
def attack_a6():
    import tempfile, subprocess
    sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
    import provenance as P
    d = tempfile.mkdtemp()
    g = tempfile.mkdtemp()
    P._run(['git', 'init', '-q'], cwd=g)
    P._run(['git', 'config', 'user.email', 't@example.invalid'], cwd=g)
    P._run(['git', 'config', 'user.name', 'test'], cwd=g)
    # a dep tree with a commit that does NOT touch the dep subdir
    sub = os.path.join(g, 'dep')
    os.makedirs(sub)
    with open(os.path.join(g, 'elsewhere.txt'), 'w') as f:
        f.write('x')
    P._run(['git', 'add', 'elsewhere.txt'], cwd=g)
    P._run(['git', 'commit', '-qm', 'unrelated'], cwd=g)
    with open(os.path.join(sub, 'src.c'), 'w') as f:      # untracked source
        f.write('int main(void){return 0;}\n')
    ts, src = P.newest_source_mtime(sub)
    stale = os.path.join(d, 'old.bin')
    with open(stale, 'wb') as f:
        f.write(b'x')
    os.utime(stale, (1_600_000_000, 1_600_000_000))       # year 2020
    c = P.Control('probe', 'must fire', null_must_contain='an equal digest',
                  can_fail_because='record returns ok=True')
    c.observe(True, {'v': 1})
    ok, prov = P.record(d, deps=[sub], artifacts=[stale], controls=[c],
                        allow_dirty=True)
    caught = any('STALE' in x for x in prov['problems'])
    if caught:
        finding('A6-provenance-floor', 'SURVIVES',
                f'a dep subdir with no commits of its own and an UNTRACKED source '
                f'still raises the floor (ts={ts}, from={src!r}), and a year-2020 '
                f'artifact is caught.')
    else:
        finding('A6-provenance-floor', 'CONFIRMED-HOLE',
                f'floor collapsed to ts={ts} from={src!r} for a dep subdir with no '
                f'commit of its own; the year-2020 artifact was NOT flagged. '
                f'`git status --porcelain` collapses an untracked directory to '
                f'"dir/", so the newest file inside it never raises the floor -- '
                f'the fix I shipped this session is narrower than I claimed.')


def main():
    print('ATTACK cycle 4 — trie instrument, W2 + S73 + harness\n')
    ak = attack_a2()
    attack_a3()
    attack_a4()
    attack_a1(ak)
    attack_a5()
    attack_a6()
    print()
    n_fatal = sum(1 for f in FINDINGS if f['verdict'] == 'FATAL')
    print(f'{len(FINDINGS)} attacks, {n_fatal} FATAL, '
          f'{sum(1 for f in FINDINGS if f["verdict"] == "SURVIVES")} survived')
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump({'seed': SEED, 'findings': FINDINGS}, f, indent=1)
    return FINDINGS


if __name__ == '__main__':
    main()
