#!/usr/bin/env python3
"""S74 — binding the epoch SEQUENCE, which S73 proved its root does not.

WHAT S73 LEFT OPEN, IN ITS OWN WORDS
------------------------------------
S73's `C_root_is_state_not_history` groups the same 1,247 atoms into two different
epoch sequences and both reach `daf1d148…`. That is correct for a state
commitment and it was recorded as a control rather than a caveat because it is the
property most likely to be misread:

    "the root does not bind the path taken to it. Binding history needs the chain
     of (root, delta) pairs hashed together. NOT BUILT HERE."

Built here. The head is

    chain_0 = H('EPOCH0' || root_0)
    chain_N = H('EPOCHN' || chain_{N-1} || root_N || H(delta_N))

so an epoch's position, its resulting state, and the exact atom set that produced
it are all inside the digest. `delta_N` is committed as the trie root over the
sorted added keys, which reuses W2's canonical structure rather than inventing a
second encoding for the same job.

THE BOUNDARY, STATED UP FRONT
-----------------------------
The chain binds the SEQUENCE. It does not bind the STATE: a verifier holding only
chain heads cannot tell whether a prover's declared delta really produces the
declared root. That still needs S73's fold-forward delta proofs. The two are
complementary and neither substitutes for the other --
`C_chain_alone_cannot_catch_a_forged_delta` is that boundary as a control, because
a design that treated the chain head as sufficient would accept a forged epoch.

  python3 chain.py            # measurement + controls
  python3 chain.py --json
"""
import os, sys, json, hashlib, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
from trie_witness import build                      # noqa: E402
import epoch as E                                   # noqa: E402

SEED = 20260817
GENESIS = {b'\0'}          # same non-empty genesis space S73 uses


# ------------------------------------------------------------------- the chain
def delta_commit(added):
    """Commit an epoch's additions as a trie root over the sorted added keys.

    Reuses W2's canonical node hashing rather than adding a second encoding: two
    commitments for the same bytes is how two honest parties end up disagreeing.
    An empty delta is a distinct, explicit value -- not the same digest as
    'no epoch happened'.
    """
    if not added:
        return hashlib.sha256(b'EMPTY-DELTA').digest()
    return build(sorted(set(added))).h


def chain_genesis(root0):
    return hashlib.sha256(b'EPOCH0' + root0).digest()


def chain_step(prev_head, root_n, delta_n):
    """Position is inside the digest because prev_head is: an epoch lifted out of
    one sequence and dropped into another sees a different prev_head and therefore
    produces a different head."""
    return hashlib.sha256(b'EPOCHN' + prev_head + root_n + delta_commit(delta_n)).digest()


def build_chain(groups, genesis=GENESIS):
    """Fold a list of atom-key batches into (heads, roots, keys_after_each)."""
    keys = set(genesis)
    root = build(sorted(keys))
    heads, roots = [chain_genesis(root.h)], [root.h]
    for g in groups:
        added = sorted(set(g) - keys)
        keys |= set(added)
        root = build(sorted(keys))
        heads.append(chain_step(heads[-1], root.h, added))
        roots.append(root.h)
    return heads, roots, keys


def verify_chain(heads, roots, deltas, genesis_root):
    """Recompute every head from the declared (root, delta) pairs. Returns True
    only if the whole sequence reproduces the claimed heads, including the
    genesis. A verifier runs this without holding a single atom of the space
    beyond the deltas themselves."""
    if not heads or heads[0] != chain_genesis(genesis_root) or roots[0] != genesis_root:
        return False
    h = heads[0]
    for i, (r, d) in enumerate(zip(roots[1:], deltas), start=1):
        h = chain_step(h, r, d)
        if h != heads[i]:
            return False
    return len(heads) == len(roots) == len(deltas) + 1


def main():
    rnd = random.Random(SEED)
    progs, stats = E.load_corpus(E.CORPUS)
    prog_keys = [(f, sorted({E.encode(a) for a in atoms})) for f, atoms in progs]
    groups = [ks for _f, ks in prog_keys]
    all_atoms = sorted({k for g in groups for k in g})

    heads, roots, keys = build_chain(groups)
    deltas = []
    seen = set(GENESIS)
    for g in groups:
        add = sorted(set(g) - seen)
        seen |= set(add)
        deltas.append(add)

    out = {'seed': SEED,
           'corpus': {'programs': stats['files'], 'distinct_atoms': len(all_atoms)},
           'epochs': len(groups), 'final_atoms': len(keys),
           'final_trie_root': roots[-1].hex(),
           'chain_head': heads[-1].hex(),
           'bytes_per_epoch': 32,
           'chain_bytes_total': 32 * len(heads),
           'honest_chain_verifies': verify_chain(heads, roots, deltas, roots[0]),
           'controls': {}}
    C = out['controls']

    # ---- C_honest_chain_verifies (NEGATIVE control: bounds resolution).
    # FAILS IF the honest chain does not verify -- then every rejection below is
    # vacuous, which is the W1 failure mode.
    C['C_honest_chain_verifies'] = {
        'fires': out['honest_chain_verifies'],
        'fails_if': 'the honest chain does not reproduce its own heads -- then '
                    'every rejection below is vacuous',
        'can_fail': 'honest_chain_verifies reads false',
        'observed': {'epochs': len(groups), 'head': heads[-1].hex()[:16],
                     'verified': out['honest_chain_verifies']}}

    # ---- C_regrouping_detected. THE POINT OF THE SPIKE, and the exact
    # complement of S73's C_root_is_state_not_history: the same atoms in two
    # different epoch groupings must reach the SAME trie root and DIFFERENT
    # chain heads. FAILS IF the heads collide -- the chain would bind no more
    # than the root already did, and this spike would be pointless.
    ga = [all_atoms[:400], all_atoms[400:900], all_atoms[900:]]
    gb = [all_atoms[:150], all_atoms[150:1100], all_atoms[1100:]]
    ha, ra, _ = build_chain(ga)
    hb, rb, _ = build_chain(gb)
    C['C_regrouping_detected'] = {
        'fires': ra[-1] == rb[-1] and ha[-1] != hb[-1],
        'fails_if': 'two epoch groupings of one atom set share a chain head -- the '
                    'chain would add nothing to the root, which S73 already showed '
                    'is grouping-blind',
        'can_fail': 'head_a == head_b, or root_a != root_b (which would mean the '
                    'groupings were not equivalent in state and the test is void)',
        'observed': {'root_a': ra[-1].hex()[:16], 'root_b': rb[-1].hex()[:16],
                     'roots_equal': ra[-1] == rb[-1],
                     'head_a': ha[-1].hex()[:16], 'head_b': hb[-1].hex()[:16],
                     'heads_equal': ha[-1] == hb[-1]}}

    # ---- C_reorder_detected. Swap two adjacent epochs. Note the trie root is
    # UNCHANGED (same union), so the root cannot see this at all.
    sw = list(groups)
    sw[3], sw[4] = sw[4], sw[3]
    hs, rs, _ = build_chain(sw)
    C['C_reorder_detected'] = {
        'fires': rs[-1] == roots[-1] and hs[-1] != heads[-1],
        'fails_if': 'swapping two epochs leaves the chain head unchanged -- '
                    'order would not be committed',
        'can_fail': 'head_swapped == head_honest',
        'observed': {'final_root_unchanged': rs[-1] == roots[-1],
                     'head_honest': heads[-1].hex()[:16],
                     'head_swapped': hs[-1].hex()[:16]}}

    # ---- C_dropped_epoch_detected. Remove one epoch entirely. Its atoms are
    # gone too, so BOTH root and head must change; the head is what makes the
    # omission attributable to a position rather than merely visible.
    dr = groups[:10] + groups[11:]
    hd, rd, _ = build_chain(dr)
    C['C_dropped_epoch_detected'] = {
        'fires': hd[-1] != heads[-1] and len(hd) == len(heads) - 1,
        'fails_if': 'dropping an epoch leaves the chain head unchanged',
        'can_fail': 'head_dropped == head_honest',
        'observed': {'epochs_honest': len(heads) - 1, 'epochs_dropped': len(hd) - 1,
                     'head_dropped': hd[-1].hex()[:16]}}

    # ---- C_split_epoch_detected. Same atoms, same order, one epoch cut in two.
    # The finest possible regrouping, and the one a prover would reach for to
    # claim more epochs of "work" than it did.
    i = 20
    sp = groups[:i] + [groups[i][:len(groups[i]) // 2], groups[i][len(groups[i]) // 2:]] \
        + groups[i + 1:]
    hp, rp, _ = build_chain(sp)
    C['C_split_epoch_detected'] = {
        'fires': rp[-1] == roots[-1] and hp[-1] != heads[-1],
        'fails_if': 'splitting one epoch in two leaves the head unchanged -- a '
                    'prover could inflate its epoch count for free',
        'can_fail': 'head_split == head_honest',
        'observed': {'final_root_unchanged': rp[-1] == roots[-1],
                     'epochs_split': len(hp) - 1,
                     'head_split': hp[-1].hex()[:16]}}

    # ---- C_delta_content_bound. Keep every root and every delta SIZE, change
    # which atoms one delta names. FAILS IF the head is unchanged -- the chain
    # would commit to a shape rather than to content, which is S65's exact hole.
    bad = [list(d) for d in deltas]
    j = next(k for k, d in enumerate(bad) if len(d) >= 2)
    bad[j] = sorted(bad[j][:-1] + [E.encode(['NOT', 'IN', 'CORPUS'])])
    h2 = heads[0]
    for r, d in zip(roots[1:], bad):
        h2 = chain_step(h2, r, d)
    C['C_delta_content_bound'] = {
        'fires': h2 != heads[-1],
        'fails_if': 'substituting one atom inside a delta, at identical size and '
                    'identical roots, leaves the head unchanged -- the chain '
                    'would bind shape, not content (S65)',
        'can_fail': 'the recomputed head equals the honest head',
        'observed': {'epoch_tampered': j, 'delta_size': len(bad[j]),
                     'head_honest': heads[-1].hex()[:16],
                     'head_tampered': h2.hex()[:16]}}

    # ---- C_replayed_epoch_rejected. A CLEAN transplant: epoch 5's (root, delta)
    # pair copied verbatim over position 6, everything else left honest. The first
    # version of this control mangled two positions at once and fired for a
    # muddled reason -- a control that fires is not the same as a control that
    # tests what it says. FAILS IF verify_chain accepts the transplant.
    t = 5
    rr, dd = list(roots), list(deltas)
    rr[t + 1] = rr[t]                 # declared state after 6 == state after 5
    dd[t] = list(dd[t - 1])           # and epoch 6 replays epoch 5's delta
    accepted = verify_chain(heads, rr, dd, roots[0])
    C['C_replayed_epoch_rejected'] = {
        'fires': not accepted,
        'fails_if': "an epoch's (root, delta) pair verifies at a different "
                    'position -- epochs would be transplantable',
        'can_fail': 'verify_chain returns True on the transplanted sequence',
        'observed': {'transplanted_from': t, 'to': t + 1, 'accepted': accepted,
                     'honest_head': heads[-1].hex()[:16]}}

    # ---- C_chain_alone_cannot_catch_a_forged_delta. THE BOUNDARY, as a control.
    # A prover declares a delta and a root that the delta does not produce. The
    # chain verifies perfectly, because it commits to what it was TOLD; only
    # S73's fold-forward proof catches the lie. FAILS IF the chain does catch it,
    # which would mean this spike replaces the delta proofs -- it does not, and a
    # design that assumed so would accept a forged epoch.
    fk = set(GENESIS)
    f_roots, f_deltas = [build(sorted(fk)).h], []
    for g in groups[:5]:
        add = sorted(set(g) - fk)
        fk |= set(add)
        f_deltas.append(add)
        f_roots.append(build(sorted(fk)).h)
    lie_roots = list(f_roots)
    lie_roots[3] = build(sorted(set(all_atoms[:50]) | GENESIS)).h   # unrelated root
    f_heads = [chain_genesis(lie_roots[0])]
    for r, d in zip(lie_roots[1:], f_deltas):
        f_heads.append(chain_step(f_heads[-1], r, d))
    chain_ok = verify_chain(f_heads, lie_roots, f_deltas, lie_roots[0])
    # S73's fold-forward proof on the same epoch. Two things must hold, and the
    # SECOND is what stops this control being a tautology: the fold must produce
    # the HONEST root (proving the machinery works on this input at all), and that
    # root must differ from the lie. Checking only "folded != lie" would pass on a
    # broken fold that returned None, which is how the first version of this
    # control read as evidence while testing nothing.
    prev_keys = set(GENESIS) | set(f_deltas[0]) | set(f_deltas[1])
    prev = build(sorted(prev_keys))
    pfs = E.prove_epoch_delta(prev, prev_keys, f_deltas[2])
    folded = E.verify_epoch_delta(prev.h, pfs)
    honest3 = f_roots[3]
    C['C_chain_alone_cannot_catch_a_forged_delta'] = {
        'fires': chain_ok and folded == honest3 and folded != lie_roots[3],
        'fails_if': 'the chain alone rejects a root its declared delta does not '
                    'produce -- then it would subsume S73 and this boundary claim '
                    'is wrong. Also fails if the fold does not reproduce the '
                    'honest root, which would make the comparison vacuous',
        'can_fail': 'chain_ok reads false, or folded != honest3 (broken fold, '
                    'control void), or folded == the lied root',
        'observed': {'chain_accepts_the_lie': chain_ok,
                     'lied_root': lie_roots[3].hex()[:16],
                     'honest_root': honest3.hex()[:16],
                     'fold_forward_gives': (folded or b'').hex()[:16],
                     'fold_reproduces_honest': folded == honest3,
                     'fold_rejects_the_lie': folded != lie_roots[3]}}

    out['all_controls_fire'] = all(c['fires'] for c in C.values())

    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    with open(os.path.join(HERE, 'chain.json'), 'w') as f:
        json.dump(out, f, indent=1)
    provenance(out)
    return out


def report(o):
    print(f"S74 — binding the epoch SEQUENCE (seed {o['seed']})")
    print(f"{o['corpus']['programs']} programs, {o['corpus']['distinct_atoms']:,} "
          f"distinct atoms, {o['epochs']} epochs, {o['final_atoms']:,} final atoms")
    print(f"trie root  {o['final_trie_root'][:32]}…   (state)")
    print(f"chain head {o['chain_head'][:32]}…   (state + sequence)")
    print(f"cost: {o['bytes_per_epoch']} B per epoch, "
          f"{o['chain_bytes_total']:,} B for the whole chain\n")
    print('CONTROLS — each names the input that makes it fail')
    for n, c in o['controls'].items():
        print(f"  {'FIRES ' if c['fires'] else 'DEAD  '} {n:<44} {c['fails_if']}")
    print(f"\nall controls fire: {o['all_controls_fire']}")


def provenance(out):
    sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
    try:
        import kfcheck as KF
    except ImportError:
        return
    cs = [KF.Control(n, c['fails_if'],
                     null_must_contain='the regrouping/reorder/forgery injected',
                     can_fail_because=c['can_fail'])
          for n, c in out['controls'].items()]
    for ctl, (_n, c) in zip(cs, out['controls'].items()):
        ctl.observe(c['fires'], c['observed'])
    ok, problems = KF.certify(
        HERE, deps=(os.path.join(HERE, '..', 'S57_hyperon_corpus'),),
        artifacts=[os.path.join(HERE, 'chain.py'), os.path.join(HERE, 'chain.json')],
        controls=cs, allow_dirty=True,
        captures=[('chain_head', out['chain_head']),
                  ('final_trie_root', out['final_trie_root'])],
        falsifier='Exhibit two epoch SEQUENCES that differ in grouping, order, '
                  'count or delta content and share a chain head. Or show a '
                  'sequence the chain rejects that is in fact honest.',
        note='S74 epoch-chain commitment: binds sequence, explicitly does NOT '
             'bind state (that is S73 fold-forward). 32 B per epoch.')
    if not ok:
        print('\nPROVENANCE PROBLEMS:')
        for p in problems:
            print('  ' + p)


if __name__ == '__main__':
    main()
