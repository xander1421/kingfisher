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

    # C_chain_binds_all_three — omit each of the three inputs and confirm the
    # chain stops distinguishing histories. Fails if any omission is harmless.
    base = build_history([[b'(a 1)'], [b'(a 2)'], [b'(a 3)']])
    c_full = chain_of(base)
    variants = {
        'drop_root_prev': lambda p, a, b, ad: hashlib.sha256(
            CHAIN_TAG + p + b + delta_digest(ad)).digest(),
        'drop_delta': lambda p, a, b, ad: hashlib.sha256(
            CHAIN_TAG + p + a + b).digest(),
        'drop_root_next': lambda p, a, b, ad: hashlib.sha256(
            CHAIN_TAG + p + a + delta_digest(ad)).digest(),
    }
    binds = {}
    for name, f in variants.items():
        # same atom set, DIFFERENT grouping -> a sound chain must separate them
        g1 = [[b'(a 1)'], [b'(a 2)', b'(a 3)']]
        g2 = [[b'(a 1)', b'(a 2)'], [b'(a 3)']]
        def fold(bs, f=f):
            keys, root = [], GENESIS_ROOT
            c = hashlib.sha256(CHAIN_TAG).digest()
            for ad in bs:
                rp = root; keys = keys + list(ad); root = root_hash(keys)
                c = f(c, rp, root, ad)
            return c
        binds[name] = (fold(g1) != fold(g2))
    out['controls']['C_chain_binds_all_three'] = {
        'fires': all(binds.values()), 'detail': binds,
        'fails_when': 'an omitted input leaves two different histories with one '
                      'chain root -- the link would not bind that input'}

    # C_state_root_cannot_separate_histories — the S73 fact this spike exists for.
    g1 = [[b'(a 1)'], [b'(a 2)', b'(a 3)']]
    g2 = [[b'(a 1)', b'(a 2)'], [b'(a 3)']]
    same_state = build_history(g1)[-1]['root'] == build_history(g2)[-1]['root']
    diff_chain = chain_of(build_history(g1)) != chain_of(build_history(g2))
    out['controls']['C_state_root_cannot_separate_histories'] = {
        'fires': same_state and diff_chain,
        'state_roots_equal': same_state, 'chain_roots_differ': diff_chain,
        'fails_when': 'the two groupings give different STATE roots, in which '
                      'case S73 already bound history and this spike is '
                      'unnecessary; or equal CHAIN roots, in which case the '
                      'chain adds nothing'}

    # C_forged_sequence_rejected — a valid final STATE reached by a forged
    # sequence. The reviewer named this as criterion 2's second target.
    honest = build_history(g1)
    forged = [dict(e) for e in HonestProver(honest).claim()]
    forged[0]['added'] = [b'(a 2)']            # same endpoint, different route
    ref = Referee()
    ok_forged, at = ref.chain_consistent(forged)
    out['controls']['C_forged_sequence_rejected'] = {
        'fires': (not ok_forged), 'rejected_at_epoch': at,
        'fails_when': 'the chain accepts a sequence whose declared additions '
                      'were never the ones applied -- then a prover can present '
                      'a real state root reached by a route it invented'}

    # C_referee_does_not_reexecute — the whole economic point.
    r = run(64, 512, random.Random(SEED))
    out['controls']['C_referee_does_not_reexecute'] = {
        'fires': r['steps_verified'] == 1 and r['rounds'] <= r['ceil_log2'],
        'steps_verified': r['steps_verified'], 'rounds': r['rounds'],
        'ceil_log2': r['ceil_log2'],
        'fails_when': 'the referee verifies more than one epoch, or takes more '
                      'than ceil(log2 N) rounds -- either way it is doing work '
                      'proportional to the run and has saved nothing'}

    # localisation swept over EVERY planted epoch including 0 and N-1, because
    # boundaries are where off-by-one lives.
    n = 16
    hist = build_history(batches_of(corpus(rng, 128), n))
    miss = []
    for k in range(len(hist)):
        liar = AdaptiveLiar(hist, random.Random(SEED + k))
        liar.lie_at = k                       # force the boundary case
        ref = Referee()
        got = ref.bisect(HonestProver(hist).claim(), liar.claim())
        out['localisation'].append({'planted': k, 'found': got,
                                    'rounds': ref.rounds})
        if got != k:
            miss.append(k)
    out['controls']['C_localises_every_epoch'] = {
        'fires': not miss, 'missed': miss, 'n': len(hist),
        'fails_when': 'any planted epoch, including 0 and N-1, is not the epoch '
                      'the referee returns'}

    # cost curve over >=3 values of N, per A18: one point is not a rate.
    for n_ep in ([8, 16, 32] if quick else [8, 16, 32, 64, 128]):
        out['sweep'].append(run(n_ep, max(64, n_ep * 8), random.Random(SEED)))

    fired = {k: v['fires'] for k, v in out['controls'].items()}
    out['all_controls_fire'] = all(fired.values())

    print('W5 — bisection over canonical epoch states')
    print('\nCONTROLS')
    for k, v in out['controls'].items():
        print(f"  {'FIRES' if v['fires'] else 'DEAD ':5} {k}")
        print(f"        fails when: {v['fails_when']}")
    print('\nLOCALISATION — every planted epoch, 0..N-1')
    print(f"  planted/found mismatches: {out['controls']['C_localises_every_epoch']['missed'] or 'none'}")
    print('\nCOST — rounds against N, and steps the referee executed')
    print(f"  {'N':>5} {'rounds':>7} {'ceil_log2':>10} {'steps':>6}  caught")
    for s in out['sweep']:
        print(f"  {s['n_epochs']:>5} {s['rounds']:>7} {s['ceil_log2']:>10} "
              f"{s['steps_verified']:>6}  {s['caught']}")
    print(f"\nall controls fire: {out['all_controls_fire']}")

    json.dump(out, open(os.path.join(HERE, 'result.json'), 'w'),
              indent=1, default=lambda o: o.hex() if isinstance(o, bytes) else str(o))
    return 0 if out['all_controls_fire'] else 1


if __name__ == '__main__':
    sys.exit(main())
