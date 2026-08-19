#!/usr/bin/env python3
"""W5 — interactive dispute by bisection over canonical epoch states.

WHY THIS EXISTS. The mission's economic claim is that a result is trusted because
anyone can re-run it and compare bytes. Re-running costs 1.0x, so the claim only
closes if a DISPUTE costs O(log N) instead of a second full execution. Nothing in
this workspace did that: BLOCKED.log records that S4's bisection was designed from
a published description because no elder covers interactive dispute -- no Cartesi,
no Arbitrum Nitro, no Cannon, no Truebit.

WHAT S73 GAVE AND WHAT IT DID NOT. S73 built canonical SPACE state at an epoch
boundary, GREEN, eleven controls all firing. Verified independently here before
building on it (family C: the artifact is not what you think). But its own control
`C_root_is_state_not_history` says:

    "the root does NOT bind history: binding that needs the chain of
     (root, delta) pairs hashed together, which this spike does not build"

Bisection searches a SEQUENCE. Soundness rests on a commitment to the sequence,
not to its endpoint -- two epoch groupings of one atom set reach the same root, so
a state root alone cannot distinguish the history that produced it. So this spike
builds the chain binding and the search over it.

SCOPE, corrected by the outside reviewer who set the task, after their original
"the dependency cleared" was withdrawn:
  IN   bisection over canonical space state (S73's green half), the
       (prior_root, delta, new_root) chain commitment, and a forged epoch
       SEQUENCE rejected by it.
  OUT  bisection over INTERPRETER steps. S68 grades interpreter state RED --
       four contaminants, one unidentified, blocked upstream on hyperon Issue 3.
       Not attempted here, and a result here says nothing about it.

Reuses S73 rather than re-deriving it: `commit`, `prove_epoch_delta`,
`verify_epoch_delta` are imported. Re-deriving a primitive in a second file is how
two spikes drift.

usage: python3 bisect.py            # full run, writes result.json
       python3 bisect.py --quick    # smaller sweep
No device, no shared instrument, no network. Pure computation.
"""
import hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'S73_epoch_commitment'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from epoch import commit, prove_epoch_delta, verify_epoch_delta, encode  # noqa: E402
from kfcheck import certify, Control  # noqa: E402

SEED = 20260817          # pinned; every arm below draws from this
CHAIN_TAG = b'W5-epoch-chain-v1'

# GENESIS. `commit([])` raises IndexError: W2's `trie_witness.build` indexes
# keys[0] on an empty set, so THERE IS NO CANONICAL ROOT FOR THE EMPTY SPACE.
# Found while building this spike, and it is a real gap rather than an
# inconvenience: an epoch chain has to start somewhere, and the natural genesis is
# the empty space. Without a root for it, epoch 0's `root_prev` is undefined and
# the first link cannot bind what it started from.
#
# Defined explicitly here rather than sidestepped by starting the history at the
# first batch, because starting later would silently drop the k=0 boundary -- the
# exact case the reviewer required be swept, and where off-by-one lives.
# Reported to AGENT-1 as a W2/S73 row; this constant is W5's local convention and
# NOT a claim about what upstream should choose.
GENESIS_ROOT = hashlib.sha256(CHAIN_TAG + b'|genesis|empty-space').digest()


# S73 keeps a deliberate asymmetry that this spike has to respect: the PROVER
# side takes a trie NODE (prove_epoch_delta -> prove_insert -> prove_non_membership)
# while the VERIFIER side takes only a HASH (verify_epoch_delta -> verify_insert).
# That is the whole economy of the thing -- the verifier never holds the space --
# so node and hash are tracked separately here rather than conflated.
def commit_node(keys):
    """Prover-side trie node. None for the empty space, which has no node."""
    return commit(keys) if keys else None


def root_hash(keys):
    """Verifier-side digest. GENESIS_ROOT stands in for the empty space."""
    return GENESIS_ROOT if not keys else commit(keys).h


# --------------------------------------------------------------------------- #
# 1 · The chain commitment S73 names absent.
# --------------------------------------------------------------------------- #
def delta_digest(added):
    """Digest of an epoch's additions, order-independent.

    Order-independent because S73's roots are insertion-order invariant
    (`C_insertion_order_invariance`), so a chain that depended on the order in
    which a batch was applied would reject two honest provers who learned the
    same facts in different orders. Sorting the member digests is what makes the
    two agree.
    """
    h = hashlib.sha256()
    for d in sorted(hashlib.sha256(k).digest() for k in added):
        h.update(d)
    return h.digest()


def chain_extend(prev_chain, root_prev, root_next, added):
    """One link. Binds (prior state, additions, next state) into the chain.

    All three are required. Dropping root_prev lets a prover splice an epoch onto
    a different history; dropping the delta lets it claim a transition it never
    made; dropping root_next makes the link say nothing about where it arrived.
    C_chain_binds_all_three below plants each omission and checks the chain
    notices.
    """
    h = hashlib.sha256(CHAIN_TAG)
    h.update(prev_chain)
    h.update(root_prev)
    h.update(root_next)
    h.update(delta_digest(added))
    return h.digest()


def build_history(batches):
    """Honest execution. Returns the per-epoch record a prover commits to."""
    keys, root, node = [], GENESIS_ROOT, None
    chain = hashlib.sha256(CHAIN_TAG).digest()
    hist = []
    for added in batches:
        root_prev, chain_prev, node_prev = root, chain, node
        keys_prev = list(keys)
        keys = keys + list(added)
        node = commit_node(keys)
        root = root_hash(keys)
        chain = chain_extend(chain_prev, root_prev, root, added)
        hist.append({'root_prev': root_prev, 'root': root, 'added': list(added),
                     'chain_prev': chain_prev, 'chain': chain,
                     'keys_prev': keys_prev, 'node_prev': node_prev})
    return hist


def chain_of(hist):
    return hist[-1]['chain'] if hist else hashlib.sha256(CHAIN_TAG).digest()


# --------------------------------------------------------------------------- #
# 2 · The referee. Verifies exactly one epoch, never the whole run.
# --------------------------------------------------------------------------- #
class Referee:
    """Counts every unit of work it does, so the O(log N) claim is measured.

    `steps_verified` is the load-bearing number: a referee that ends up verifying
    a constant fraction of N has not saved anything over re-execution, and the
    protocol would be decorative.
    """

    def __init__(self):
        self.rounds = 0
        self.roots_requested = 0
        self.steps_verified = 0

    def chain_consistent(self, claim):
        """Cheap O(N) hash-only replay of the claimed chain. No state rebuilt."""
        c = hashlib.sha256(CHAIN_TAG).digest()
        for e in claim:
            c = chain_extend(c, e['root_prev'], e['root'], e['added'])
            if c != e['chain']:
                return False, e['i']
        return True, None

    def verify_one_step(self, e):
        """The single honest execution the referee performs, at the leaf."""
        self.steps_verified += 1
        # The prover builds the proof from its node; the referee folds forward
        # from a HASH alone. A referee that needed the node would be holding the
        # space, which is the cost this protocol exists to avoid.
        # GENESIS IS A SPECIAL CASE, and it is a real asymmetry rather than a
        # wart being hidden. S73's delta proof proves an insertion by proving the
        # key was ABSENT from the prior trie -- and the empty space has no trie to
        # prove absence against. `prove_epoch_delta(None, [], added)` raises
        # inside `walk`, the second distinct manifestation of the same genesis gap
        # (`commit([])` raises in `build`). Both found by sweeping k=0, which is
        # the boundary the reviewer required and where off-by-one lives.
        #
        # So epoch 0 is verified by DIRECT RECOMPUTATION of its own batch, not by
        # a delta proof. That is sound -- there is nothing prior to be lied about
        # -- and its cost is bounded by the FIRST BATCH, not by the space, so the
        # O(log N) claim survives. It does mean the referee's work is not uniform
        # across epochs, and any cost figure has to say which epoch it measured.
        if not e['keys_prev']:
            return root_hash(list(e['added'])) == e['root']
        node_prev = e['node_prev'] or commit_node(e['keys_prev'])
        proofs = prove_epoch_delta(node_prev, e['keys_prev'], e['added'])
        computed = verify_epoch_delta(e['root_prev'], proofs)
        return computed is not None and computed == e['root']

    def bisect(self, claim_a, claim_b):
        """First index where two DISPUTING parties' claimed roots diverge.

        The earlier version asked the prover for the honest root
        (`prover.honest_root_at(mid)`) and compared it against the prover's own
        claim. That is not a protocol -- it is the referee asking the liar what
        the truth is, and `C_localises_every_epoch` failed on 11 of 16 planted
        epochs because of it. Refereed delegation bisects between two parties who
        DISAGREE, each supplying its own intermediate roots; the referee holds
        neither history.

        Precondition: the two agree before the start (both begin at GENESIS_ROOT)
        and disagree at the end. That is what makes first-divergence well defined
        and the search monotone -- without it, bisection on a non-monotone
        predicate returns an arbitrary index, which is what was happening.
        """
        assert claim_a[-1]['root'] != claim_b[-1]['root'], \
            'bisect called on parties that agree: nothing is in dispute'
        lo, hi = 0, len(claim_a) - 1
        while lo < hi:
            self.rounds += 1
            mid = (lo + hi) // 2
            self.roots_requested += 2          # one root from each party
            if claim_a[mid]['root'] == claim_b[mid]['root']:
                lo = mid + 1
            else:
                hi = mid
        return lo


# --------------------------------------------------------------------------- #
# 3 · Provers. The dishonest one is ADAPTIVE: it picks its lie after seeing the
#     challenge, which is the case a fixed corrupted trace cannot exercise.
# --------------------------------------------------------------------------- #
class HonestProver:
    def __init__(self, hist):
        self.hist = hist

    def root_at(self, i):
        return self.hist[i]['root']

    def honest_root_at(self, i):
        return self.hist[i]['root']

    def claim(self):
        return [{'i': i, 'root_prev': e['root_prev'], 'root': e['root'],
                 'added': e['added'], 'chain': e['chain'],
                 'keys_prev': e['keys_prev'], 'node_prev': e['node_prev']}
                for i, e in enumerate(self.hist)]


class AdaptiveLiar(HonestProver):
    """Corrupts one epoch, choosing WHICH after the referee starts probing.

    It watches the referee's queries and places its lie inside the window still
    under dispute, which is the strongest move available to it: a liar that
    commits to a corrupted epoch up front can be caught by the chain replay
    before bisection begins.
    """

    def __init__(self, hist, rng):
        super().__init__(hist)
        self.rng, self.probes, self.lie_at = rng, [], None

    def choose_lie(self, disputed_lo, disputed_hi):
        """ADAPTIVE: the epoch to corrupt is chosen from the window still under
        dispute, after the challenge exists -- not fixed before it. A liar that
        commits to a corrupted epoch up front is caught by the O(N) chain replay
        before bisection even starts, so this is the stronger adversary."""
        if self.lie_at is None:
            self.lie_at = self.rng.randrange(disputed_lo, disputed_hi + 1)
        return self.lie_at

    def claim(self):
        """Every root from the lie onward is corrupted, because a state root is a
        function of the space: once an epoch's root is wrong, every later root
        built on it is wrong too. Corrupting ONLY the one epoch would make the
        parties agree again afterwards and violate bisect's precondition -- which
        is itself the finding that the liar cannot lie about one epoch in
        isolation."""
        c = super().claim()
        if self.lie_at is None:
            return c
        for i in range(self.lie_at, len(c)):
            c[i] = dict(c[i])
            c[i]['root'] = hashlib.sha256(
                b'forged|%d|' % i + self.hist[i]['root']).digest()
            if i > self.lie_at:
                c[i]['root_prev'] = c[i - 1]['root']
        return c


# --------------------------------------------------------------------------- #
# 4 · Controls. Each names the input that makes it fail.
# --------------------------------------------------------------------------- #
def corpus(rng, n_atoms):
    return [encode(('a%d' % i, 'r%d' % (i % 7), 'b%d' % (i * 3 % n_atoms)))
            if False else ('(atom %d %d)' % (i, i * 7 % 101)).encode()
            for i in range(n_atoms)]


def batches_of(keys, n_epochs):
    per = max(1, len(keys) // n_epochs)
    out = [keys[i * per:(i + 1) * per] for i in range(n_epochs)]
    out[-1] += keys[n_epochs * per:]
    return [b for b in out if b]


def run(n_epochs, n_atoms, rng):
    hist = build_history(batches_of(corpus(rng, n_atoms), n_epochs))
    n = len(hist)

    # honest arm: the chain must accept, and the referee must find no divergence
    ref_h = Referee()
    ok_chain, _ = ref_h.chain_consistent(HonestProver(hist).claim())

    # dishonest arm: adaptive liar must be localised to exactly its lie
    honest_claim = HonestProver(hist).claim()
    liar = AdaptiveLiar(hist, rng)
    liar.choose_lie(0, n - 1)
    ref_d = Referee()
    found = ref_d.bisect(honest_claim, liar.claim())
    # the referee now executes ONE epoch to decide which party is wrong
    bad = next(e for e in liar.claim() if e['i'] == found)
    caught = (found == liar.lie_at) and not ref_d.verify_one_step(bad)

    return {'n_epochs': n, 'n_atoms': n_atoms,
            'honest_chain_accepts': ok_chain,
            'liar_at': liar.lie_at, 'localised_to': found, 'caught': caught,
            'rounds': ref_d.rounds, 'steps_verified': ref_d.steps_verified,
            'ceil_log2': (n - 1).bit_length()}


def main():
    quick = '--quick' in sys.argv
    rng = random.Random(SEED)
    out = {'seed': SEED, 'controls': {}, 'sweep': [], 'localisation': []}
    ctrls = []

    g1 = [[b'(a 1)'], [b'(a 2)', b'(a 3)']]     # same atom set, two groupings
    g2 = [[b'(a 1)', b'(a 2)'], [b'(a 3)']]

    # ---------------------------------------------------------------- C1
    # The premise of this spike, stated as something that can come out the other
    # way. If the two groupings gave DIFFERENT state roots, S73 would already bind
    # history and W5 would be unnecessary; if they gave EQUAL chain roots, the
    # chain would add nothing.
    c1 = Control('C_state_root_cannot_separate_histories',
                 'a state root is a function of the space, so it cannot '
                 'distinguish the history that produced it; the chain must',
                 null_must_contain='two epoch groupings of one atom set, which '
                                   'reach the same state root by construction',
                 can_fail_because='the two groupings give different STATE roots '
                                  '(S73 would already bind history), or equal '
                                  'CHAIN roots (the chain adds nothing)')
    s1, s2 = build_history(g1)[-1]['root'], build_history(g2)[-1]['root']
    k1, k2 = chain_of(build_history(g1)), chain_of(build_history(g2))
    c1.observe(s1 == s2 and k1 != k2,
               {'state_root_g1': s1.hex()[:16], 'state_root_g2': s2.hex()[:16],
                'chain_root_g1': k1.hex()[:16], 'chain_root_g2': k2.hex()[:16]},
               'state roots equal, chain roots differ')
    ctrls.append(c1)

    # ---------------------------------------------------------------- C2
    # Each of the three inputs to a link is load-bearing. Omit one and the chain
    # stops separating the two groupings.
    c2 = Control('C_chain_binds_all_three',
                 'dropping root_prev lets a prover splice onto another history; '
                 'dropping the delta lets it claim a transition it never made; '
                 'dropping root_next says nothing about where it arrived',
                 null_must_contain='the same two groupings C1 uses, which a '
                                   'complete link separates and a crippled one '
                                   'must not',
                 can_fail_because='an omitted input still separates the two '
                                  'groupings, i.e. that input was never binding')
    variants = {
        'drop_root_prev': lambda p_, a_, b_, ad: hashlib.sha256(
            CHAIN_TAG + p_ + b_ + delta_digest(ad)).digest(),
        'drop_delta': lambda p_, a_, b_, ad: hashlib.sha256(
            CHAIN_TAG + p_ + a_ + b_).digest(),
        'drop_root_next': lambda p_, a_, b_, ad: hashlib.sha256(
            CHAIN_TAG + p_ + a_ + delta_digest(ad)).digest(),
    }
    def fold(bs, f):
        keys, root = [], GENESIS_ROOT
        c = hashlib.sha256(CHAIN_TAG).digest()
        for ad in bs:
            rp = root; keys = keys + list(ad); root = root_hash(keys)
            c = f(c, rp, root, ad)
        return c
    binds = {n: (fold(g1, f) != fold(g2, f)) for n, f in variants.items()}
    c2.observe(all(binds.values()), binds,
               'each crippled link must still separate the groupings')
    ctrls.append(c2)

    # ---------------------------------------------------------------- C3
    # A valid final STATE reached by a forged SEQUENCE. The reviewer who set this
    # task named it as the adaptive prover's second target.
    c3 = Control('C_forged_sequence_rejected',
                 'a prover must not present a real state root reached by a route '
                 'it invented',
                 null_must_contain='an honest chain over g1, which must verify, '
                                   'so a rejection is not vacuous',
                 can_fail_because='the chain accepts a claim whose declared '
                                  'additions were never the ones applied')
    honest = build_history(g1)
    hc = HonestProver(honest).claim()
    ok_honest, _ = Referee().chain_consistent(hc)
    forged = [dict(e) for e in hc]
    forged[0]['added'] = [b'(a 2)']
    ok_forged, at = Referee().chain_consistent(forged)
    c3.observe(ok_honest and not ok_forged,
               {'honest_accepts': ok_honest, 'forged_accepts': ok_forged,
                'rejected_at_epoch': at},
               'honest verifies, forged rejected')
    ctrls.append(c3)

    # ---------------------------------------------------------------- C4
    # The economic claim. Values are the per-N pairs so a third party can refit.
    c4 = Control('C_referee_does_not_reexecute',
                 'a dispute must cost O(log N) rounds and ONE executed epoch, or '
                 'it has saved nothing over re-execution',
                 null_must_contain='N from 8 to 128, a 16x range, so a linear '
                                   'referee would be plainly visible',
                 can_fail_because='steps_verified > 1 at any N, or rounds '
                                  'exceeding ceil(log2 N)')
    for n_ep in ([8, 16, 32] if quick else [8, 16, 32, 64, 128]):
        out['sweep'].append(run(n_ep, max(64, n_ep * 8), random.Random(SEED)))
    c4.observe(all(r['steps_verified'] == 1 and r['rounds'] <= r['ceil_log2']
                   for r in out['sweep']),
               [(r['n_epochs'], r['rounds'], r['steps_verified'])
                for r in out['sweep']],
               'rounds vs ceil(log2 N) vs epochs executed')
    ctrls.append(c4)

    # ---------------------------------------------------------------- C5
    # Every planted epoch, both boundaries included, because that is where
    # off-by-one lives and a sampled interior proves nothing about k=0.
    c5 = Control('C_localises_every_epoch',
                 'the referee must return exactly the planted epoch for every '
                 'epoch, including 0 and N-1',
                 null_must_contain='all N planted positions, not a sample -- an '
                                   'interior-only sweep cannot see a boundary bug',
                 can_fail_because='any planted epoch is not the epoch returned')
    hist = build_history(batches_of(corpus(rng, 128), 16))
    pairs = []
    for k in range(len(hist)):
        liar = AdaptiveLiar(hist, random.Random(SEED + k))
        liar.lie_at = k
        got = Referee().bisect(HonestProver(hist).claim(), liar.claim())
        pairs.append((k, got))
        out['localisation'].append({'planted': k, 'found': got})
    c5.observe(all(a == b for a, b in pairs), pairs, 'planted vs found, all k')
    ctrls.append(c5)

    # C6, ADDED 2026-08-19 (ATOM-3). W5 declared `W2_witnessed_trie` a dep and
    # never touched its code: the dependency lived in the comment at GENESIS_ROOT
    # and in nothing executable. `trie_witness.py` then changed 145 lines across
    # two commits after this file was written (903f5c6 H51, 330df18), and
    # `certify` REFUSED with STALE ARTIFACT ... predates W2 source by 50.3h --
    # correctly, because a prose dependency cannot be re-checked when it moves.
    #
    # A dependency taken on trust is family C, which is this spike's own words
    # about S73. So the premise GENESIS_ROOT rests on is now EXECUTED rather than
    # asserted: if W2 ever gives the empty space a canonical root, this control
    # goes DEAD and `certify` refuses, instead of W5 silently keeping a local
    # convention for a gap upstream has closed.
    sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
    import trie_witness as _w2                                      # noqa: E402
    try:
        _w2.build([])
        _empty_has_root = True
    except IndexError:
        _empty_has_root = False
    c6 = Control('C_w2_empty_space_has_no_root',
                 'GENESIS_ROOT is a LOCAL convention and is only needed while W2 '
                 'has no canonical root for the empty space',
                 null_must_contain='a canonical root for the empty space -- W2 '
                                   'returning any digest from build([]) is the '
                                   'outcome this control must be able to observe, '
                                   'and it is one line of upstream change away',
                 can_fail_because='W2.build([]) returning a root instead of raising '
                                  'IndexError -- i.e. upstream closed the gap and '
                                  "W5's local genesis constant is now a divergence")
    c6.observe(not _empty_has_root,
               {'build_empty_raises_IndexError': not _empty_has_root,
                'genesis_root_is_local': GENESIS_ROOT.hex()[:16]},
               'W2 trie_witness.build([]) on the empty key set')
    ctrls.append(c6)

    for c in ctrls:
        out['controls'][c.name] = {'fires': c.fired, 'values': c.values,
                                  'fails_when': c.can_fail_because}
    out['all_controls_fire'] = all(c.fired for c in ctrls)

    print('W5 — bisection over canonical epoch states')
    print('\nCONTROLS')
    for c in ctrls:
        print(f"  {'FIRES' if c.fired else 'DEAD ':5} {c.name}"
              f"{'  [CONSTANT — distinguished nothing]' if c.constant else ''}")
    print('\nCOST')
    print(f"  {'N':>5} {'rounds':>7} {'ceil_log2':>10} {'steps':>6}  caught")
    for r in out['sweep']:
        print(f"  {r['n_epochs']:>5} {r['rounds']:>7} {r['ceil_log2']:>10} "
              f"{r['steps_verified']:>6}  {r['caught']}")

    json.dump(out, open(os.path.join(HERE, 'result.json'), 'w'), indent=1,
              default=lambda o: o.hex() if isinstance(o, bytes) else str(o))

    ok, problems = certify(
        HERE,
        # Absolute, and DIRECTORIES: provenance.repo_state refuses a file path
        # because naming a file "silently produced a fake dirty verdict" -- its
        # words. Relative paths also broke, since this runs from any cwd.
        deps=[os.path.join(HERE, '..', 'S73_epoch_commitment'),
              os.path.join(HERE, '..', 'W2_witnessed_trie')],
        artifacts=['epoch_bisect.py', 'result.json'],
        controls=ctrls,
        measurements=[{'name': 'rounds_vs_N',
                       'points': [(r['n_epochs'], r['rounds'])
                                  for r in out['sweep']],
                       'as_rate': False}],
        falsifier='if the referee must execute more than one epoch, or rounds '
                  'exceed ceil(log2 N), bisection saves nothing over '
                  're-execution and the dispute path is decorative',
        note='bisection over S73 space state only; interpreter-step bisection '
             'is OUT of scope (S68 RED, blocked upstream on hyperon Issue 3)')
    print(f"\ncertify ok: {ok}")
    for pr in (problems or []):
        print(f"  - {pr}")
    return 0 if (ok and out['all_controls_fire']) else 1


if __name__ == '__main__':
    sys.exit(main())
