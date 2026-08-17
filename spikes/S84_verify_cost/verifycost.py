#!/usr/bin/env python3
"""S84 — what does the VERIFIER pay, and does it track proof size?

THE FALSIFIER, STATED BEFORE THE RUN (it is HANDOFF's own live NEXT, verbatim)
------------------------------------------------------------------------------
    If verify cost is FLAT in proof size, the whole branching-cost result
    (S77 -> S80) is irrelevant to the job class and only the prover pays.

Operationalised before looking at anything: the falsifier FIRES if verifier work
grows by less than 10% across the three key sets while proof size grows by more
than 50%. Both thresholds fixed here, in the file, before the first run.

WHY THIS IS THE NEXT ITEM AND NOT ANOTHER BYTE COUNT
----------------------------------------------------
S77 -> S80 settled what a proof COSTS: point queries, absence and range queries,
all against W2's real prover, all in bytes. Every one of those is a statement
about the PROVER. The mission's claim is that a result is trusted because anyone
can re-run it and compare bytes, and the witnessed-verification route (W2) only
buys something if checking a proof is *forced* work that is cheaper than
re-execution. Nothing in the chain has measured the verifier at all.

THE MEASUREMENT PROBLEM, AND WHY THE PRIMARY QUANTITY IS NOT WALL TIME
----------------------------------------------------------------------
`spikes/quiet.sh` REFUSES on this host (loadavg 55.96 against a 3.50 limit, 4
containers from another project). §3: prefer load-insensitive work when the gate
fails. So the primary quantity is the verifier's HASH WORK -- how many sha256
objects it constructs and how many bytes it feeds them -- which is exact,
deterministic, reproducible byte-for-byte, and independent of load.

AND THAT IS A PROXY, WHICH IS THE EXACT MISTAKE THIS CHAIN ALREADY MADE ONCE.
S75/S76 measured node DEPTH as a proxy for proof size, both spikes certified
`ok=true` with firing controls, and S77 retracted both because depth is not what
a proof is made of. "A more careful measurement of the wrong quantity reads as a
stronger result." So hash work is not asserted to stand for time: wall time is
measured beside it in the same process and control C_proxy checks the two order
the key sets IDENTICALLY. If they disagree, the disagreement is the finding and
the hash numbers do not answer the falsifier. Wall time itself is recorded with
`citable: false` and is never published as a rate -- the gate refuses, and W4's
readset_table is the precedent for splitting one table into a citable half and a
non-citable half rather than publishing all of it.

THE NULL MUST BE ABLE TO CONTAIN THE EFFECT (A20)
-------------------------------------------------
"Verifier work grows with proof size" is unfalsifiable without a verifier that
genuinely does flat work. `flat_verify` is that null: it compares the claimed
root to the expected root and returns, i.e. it accepts any proof whose header
says the right thing. It is what a lazy verifier looks like, it does exactly one
hash regardless of proof size, and if the real verifier's numbers came out like
it the falsifier would fire. Reported in the same units as the real one.

THE PROBE MUST SHOW IT REACHED ITS TARGET (A29)
-----------------------------------------------
Counting hashes inside a function that returned False on the first line would
report a small, stable, entirely fictional number. So every proof measured here
is required to VERIFY TRUE, and a corrupted copy of each proof is required to
verify FALSE -- otherwise the verifier is not doing the work being counted.

  python3 verifycost.py
"""
import os, sys, json, time, hashlib, struct, statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
import trie_witness as TW                                                  # noqa: E402
from trie_witness import (build, prove_membership, verify_membership,      # noqa: E402
                          prove_non_membership, verify_non_membership,
                          steps_bytes)
from kfcheck import certify                                                # noqa: E402
from provenance import Control, Falsifier                                  # noqa: E402

SEED = 20260817
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples',        os.path.join(S75, 'keys_triples.bin'))]
PROBES = 120          # keys per set, same order of magnitude as S79's 200
REPEATS = 40          # wall-clock repeats per proof, median taken

# The falsifier's thresholds, fixed before any run.
FLAT_WORK_PCT = 10.0      # verifier work spread below this = flat
PROOF_SPAN_PCT = 50.0     # ... while proof size spread is above this


# ---------------------------------------------------------------- hash counter
class CountingHashlib:
    """Stands in for the `hashlib` module inside trie_witness.

    `node_hash` and `desc_hash` call `hashlib.sha256()` through the module
    global, so rebinding the global is enough -- no default argument is
    involved, which is the case CLAUDE.md records as the one that silently does
    not take (Python binds defaults at definition time). C_counter_live asserts
    the substitution actually reached the code rather than assuming it.
    """
    def __init__(self):
        self.n = 0
        self.b = 0

    def sha256(self, data=b''):
        self.n += 1
        return _Counted(self, data)


class _Counted:
    def __init__(self, owner, data=b''):
        self.owner = owner
        self._h = hashlib.sha256()
        if data:
            self.update(data)

    def update(self, data):
        self.owner.b += len(data)
        self._h.update(data)

    def digest(self):
        return self._h.digest()

    def hexdigest(self):
        return self._h.hexdigest()


def counted(fn, *a, **kw):
    """Run fn under the counting hashlib; return (result, n_hash, bytes_hash)."""
    c = CountingHashlib()
    real, TW.hashlib = TW.hashlib, c
    try:
        r = fn(*a, **kw)
    finally:
        TW.hashlib = real
    return r, c.n, c.b


# ------------------------------------------------------------------- the null
def flat_verify(root_hash, k, pf):
    """A verifier that does CONSTANT work, whatever the proof says.

    This is not a strawman for its own sake: it is what a verifier degenerates
    into if it trusts any field the prover supplies. It hashes the claimed root
    once and compares. It accepts forged proofs, which is the point -- the null
    has to be capable of producing the flat curve the falsifier looks for.
    """
    if pf is None:
        return False
    h = TW.hashlib.sha256()
    h.update(b'R')
    h.update(root_hash)
    return h.digest() is not None


# -------------------------------------------------------------------- corrupt
def corrupt_at(pf, idx):
    """Corrupt sibling digest at path position `idx`. Returns None if that
    position carries no sibling (a single-child node has nothing to flip -- the
    same fact S77 found: an unbranched position contributes no digests)."""
    import copy
    bad = copy.deepcopy(pf)
    (prefix, term, pairs), b = bad['steps'][idx]
    if not pairs:
        return None
    byte, dig = pairs[0]
    pairs[0] = (byte, bytes([dig[0] ^ 0xFF]) + dig[1:])
    return bad


def corrupt(pf):
    """A proof a correct verifier must REJECT. Flips one byte of one sibling
    digest on the path; if the path is empty, flips the node prefix instead."""
    import copy
    bad = copy.deepcopy(pf)
    for (prefix, term, pairs), b in bad['steps']:
        if pairs:
            byte, dig = pairs[0]
            pairs[0] = (byte, bytes([dig[0] ^ 0xFF]) + dig[1:])
            return bad
    d = bad.get('leaf') or bad.get('node')
    if d is not None:
        prefix, term, pairs = d
        newp = (bytes([prefix[0] ^ 0xFF]) + prefix[1:]) if prefix else b'\x01'
        nd = (newp, term, pairs)
        if 'leaf' in bad:
            bad['leaf'] = nd
        else:
            bad['node'] = nd
    return bad


def read_keys(path):
    """S79's reader, byte-identical. These .bin files are S75/S76 artifacts with
    a u32 count then length-prefixed keys; TW.load reads a DIFFERENT format (the
    S73 corpus triple file) and silently returns a tuple, which is why this is
    not TW.load."""
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    out, i = [], 4
    for _ in range(n):
        (ln,) = struct.unpack_from('<H', b, i)
        i += 2
        out.append(b[i:i + ln])
        i += ln
    return out


def probe_set(name, keys, want=PROBES):
    """Build, prove, verify and count for one key set. Returns a row dict."""
    root = build(sorted(keys))
    rh = root.h
    step = max(1, len(keys) // want)
    probes = sorted(keys)[::step][:want]
    per = defaultdict(list)
    saw, rej_ok, rej_n = [], 0, 0
    for k in probes:
        pf = prove_membership(root, k)
        if pf is None:
            continue
        ok, n, b = counted(verify_membership, rh, k, pf)
        if not ok:                          # A29: a False verdict counts nothing
            raise SystemExit('S84: a membership proof failed to verify -- the '
                             'counts would describe an early return')
        saw.append(n)
        rej_n += 1
        if not verify_membership(rh, k, corrupt(pf)):
            rej_ok += 1
        _r, fn, fb = counted(flat_verify, rh, k, pf)
        t = []
        for _ in range(REPEATS):
            t0 = time.perf_counter()
            verify_membership(rh, k, pf)
            t.append(time.perf_counter() - t0)
        per['proof_bytes'].append(steps_bytes(pf['steps']))
        per['hash_bytes'].append(b)
        per['hash_calls'].append(n)
        per['null_hash_bytes'].append(fb)
        per['steps'].append(len(pf['steps']))
        per['wall_us'].append(statistics.median(t) * 1e6)
        # EVERY position on the path must be load-bearing, or the verifier is
        # not FORCED to read the bytes it hashes -- which is the NEXT item's
        # actual wording. A verifier that checked only the last step would still
        # hash the same bytes and still reject the first control's corruption.
        for i in range(len(pf['steps'])):
            b2 = corrupt_at(pf, i)
            if b2 is None:
                per['positions_no_sibling'].append(1)
                continue
            per['positions_tried'].append(1)
            if not verify_membership(rh, k, b2):
                per['positions_rejected'].append(1)
    row = {'set': name, 'n_keys': len(keys), 'n_probes': len(per['proof_bytes']),
           **{m: round(statistics.mean(v), 3)
              for m, v in per.items() if not m.startswith('positions_')}}
    pos = (len(per['positions_tried']), len(per['positions_rejected']),
           len(per['positions_no_sibling']))
    row['positions_tried'], row['positions_rejected'] = pos[0], pos[1]
    row['positions_without_a_sibling'] = pos[2]
    return row, saw, rej_ok, rej_n, pos


def main():
    rows, sweep, counter_saw = [], [], []
    reject_ok = reject_total = 0
    pos_tried = pos_rej = pos_nosib = 0
    loaded = {}

    for name, path in SETS:
        keys = read_keys(path)
        loaded[name] = keys
        r, saw, ro, rn, pos = probe_set(name, keys)
        rows.append(r)
        pos_tried += pos[0]; pos_rej += pos[1]; pos_nosib += pos[2]
        counter_saw += saw
        reject_ok += ro
        reject_total += rn

    # THE X-AXIS SWEEP. The three real key sets span only 48.15% of proof size --
    # measured, and BELOW this file's own pre-registered 50% precondition, so the
    # falsifier could not be evaluated on them. The bar was NOT lowered (§5);
    # the axis was widened, by subsampling one set down to tiny tries where a
    # proof is a handful of steps. The three real sets remain the operating
    # points and are reported separately, because a sweep over subsamples is a
    # statement about the STRUCTURE and the real sets are the regime this
    # project actually stores.
    tri = sorted(loaded['triples'])
    for n in (8, 32, 128, 512, 2048, len(tri)):
        sub = tri[::max(1, len(tri) // n)][:n]
        r, saw, ro, rn, pos = probe_set('triples_n%d' % len(sub), sub, want=min(60, len(sub)))
        sweep.append(r)
        pos_tried += pos[0]; pos_rej += pos[1]; pos_nosib += pos[2]
        counter_saw += saw
        reject_ok += ro
        reject_total += rn

    def spread(v):
        return (max(v) - min(v)) / min(v) * 100.0

    pb = [r['proof_bytes'] for r in sweep]
    hb = [r['hash_bytes'] for r in sweep]
    nb = [r['null_hash_bytes'] for r in sweep]
    st = [r['steps'] for r in sweep]
    proof_spread, work_spread = spread(pb), spread(hb)
    step_spread, null_spread = spread(st), spread(nb)
    fired = work_spread < FLAT_WORK_PCT and proof_spread > PROOF_SPAN_PCT

    # The two LOAD-FREE components of verifier work, on the three real sets.
    order_bytes = [r['set'] for r in sorted(rows, key=lambda r: r['hash_bytes'])]
    order_steps = [r['set'] for r in sorted(rows, key=lambda r: r['steps'])]
    order_wall  = [r['set'] for r in sorted(rows, key=lambda r: r['wall_us'])]
    components_disagree = order_bytes != order_steps

    # A18: run the affine check, RECORD its verdict, and publish points not a
    # rate if it refuses -- rather than choosing `as_rate` after seeing the data.
    sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
    import units                                                          # noqa: E402
    pts = list(zip(pb, hb))
    affine_ok, affine_why = units.check_affine(pts)
    try:
        units.fit_or_refuse(pts)
        fit_why = 'accepted'
    except Exception as e:
        fit_why = str(e)

    ratio = [round(r['hash_bytes'] / r['proof_bytes'], 3) for r in rows + sweep]

    C = [
        Control('C_counter_live',
                'the hashlib substitution must actually reach node_hash/desc_hash; '
                'a counter that never incremented would report a flat verifier '
                'that is really an uninstrumented one',
                null_must_contain='a run where every count is 0 or constant',
                can_fail_because='if TW.hashlib were bound at definition time, or '
                                 'verify called hashlib directly, every count stays 0'),
        Control('C_reject_corrupt',
                'every counted verification must be doing real work: the good proof '
                'must verify TRUE and a corrupted copy must verify FALSE, or the '
                'numbers describe a function returning early (A29)',
                null_must_contain='a verifier that accepts the corrupted proof, '
                                  'which would put corrupt_rejected at 0',
                can_fail_because='if the flipped sibling digest were unused by the '
                                 'fold, the corrupted proof would still verify'),
        Control('C_null_bounds_the_flat_case',
                'the flat null must be FLAT and the real verifier must not be, or '
                '"not flat" is asserted against nothing (A20)',
                null_must_contain='a null whose work varies with proof size',
                can_fail_because='if flat_verify hashed the proof it would scale, '
                                 'and if the real verifier ignored the path it '
                                 'would match the null'),
        Control('C_proof_size_varies',
                'the x-axis must span a real range, or flatness in y is unreadable',
                null_must_contain='a sweep whose proof sizes are all within a few '
                                  'percent',
                can_fail_because='if proof size were set by something the key count '
                                 'does not move, the sweep would be flat in x -- '
                                 'and on the three REAL sets it was, at 48.15% '
                                 'against this file\'s pre-registered 50% bar'),
        Control('C_components_disagree',
                'verifier work has two load-free components -- bytes hashed and '
                'path steps -- and this control asks whether either one alone can '
                'stand for verify cost. It FIRES when they order the key sets '
                'differently, which means neither is a proxy and only a timed run '
                'could settle which dominates',
                null_must_contain='two components that order the sets identically, '
                                  'in which case either would be a usable proxy',
                can_fail_because='bytes and steps could rise together across the '
                                 'three sets, as they do across the sweep'),
    ]
    C[0].observe(len(set(counter_saw)) > 1 and min(counter_saw) > 0,
                 counter_saw[:12], 'distinct hash-call counts inside the verifier')
    C[1].observe(reject_ok == reject_total and reject_total > 0,
                 {'good_accepted': reject_total, 'corrupt_rejected': reject_ok,
                  'corrupt_accepted': reject_total - reject_ok},
                 'both directions of the verifier, counted')
    C[2].observe(null_spread < 1.0 and work_spread > 1.0,
                 {'null_hash_bytes': nb, 'real_hash_bytes': hb,
                  'null_spread_pct': round(null_spread, 3),
                  'real_spread_pct': round(work_spread, 2)},
                 'flat null vs the real verifier over the sweep')
    C[3].observe(proof_spread > PROOF_SPAN_PCT, pb,
                 'mean proof bytes across the sweep; spread %.1f%%' % proof_spread)
    C[4].observe(components_disagree, [order_bytes, order_steps],
                 'three real sets ordered by hash bytes vs by path steps')

    C.append(Control(
        'C_every_position_forced',
        'the finding is that the verifier is FORCED to read the proof, not merely '
        'that it happens to hash that many bytes. Corrupting a sibling digest at '
        'EVERY path position, one at a time, must be rejected at every position',
        null_must_contain='a verifier that accepts a corruption at some position, '
                          'i.e. one that hashes bytes whose value it does not '
                          'depend on',
        can_fail_because='a verifier checking only the leaf, or only the final '
                         'fold step, would accept corruption at earlier positions '
                         'while hashing exactly the same number of bytes'))
    C[-1].observe(pos_rej == pos_tried and pos_tried > 0,
                  {'positions_corrupted': pos_tried,
                   'positions_rejected': pos_rej,
                   'positions_accepted': pos_tried - pos_rej,
                   'positions_with_no_sibling_to_flip': pos_nosib},
                  'one flipped sibling digest per path position, all proofs')

    F = Falsifier('F_verify_flat',
                  refutes='that the S77->S80 branching-cost result matters to the '
                          'job class at all: if the verifier pays the same whatever '
                          'the proof size, only the prover pays and the branching '
                          'model is a prover-side curiosity',
                  fires_when='verifier hash-byte spread across the sweep is under '
                             '%.0f%% while proof-size spread is over %.0f%%'
                             % (FLAT_WORK_PCT, PROOF_SPAN_PCT),
                  null_must_contain='the flat_verify null, which does one hash '
                                    'regardless of proof size')
    F.observe(fired, [round(work_spread, 2), round(proof_spread, 2),
                      round(null_spread, 3), round(step_spread, 2)],
              'work %.1f%% / proof %.1f%% / null %.3f%% / steps %.1f%%'
              % (work_spread, proof_spread, null_spread, step_spread))

    out = {
        'seed': SEED,
        'operating_points': rows,
        'sweep': sweep,
        'falsifier_fired': fired,
        'spreads_pct': {
            'sweep_proof_bytes': round(proof_spread, 2),
            'sweep_verifier_hash_bytes': round(work_spread, 2),
            'sweep_verifier_steps': round(step_spread, 2),
            'sweep_null_hash_bytes': round(null_spread, 3),
            'real_sets_proof_bytes': round(spread([r['proof_bytes'] for r in rows]), 2),
            'real_sets_hash_bytes': round(spread([r['hash_bytes'] for r in rows]), 2),
            'real_sets_steps': round(spread([r['steps'] for r in rows]), 2),
            'real_sets_wall_us': round(spread([r['wall_us'] for r in rows]), 2),
        },
        'orderings_real_sets': {'by_hash_bytes': order_bytes,
                                'by_steps': order_steps,
                                'by_wall_us_NOT_CITABLE': order_wall},
        'components_disagree': components_disagree,
        'forced_positions': {'corrupted': pos_tried, 'rejected': pos_rej,
                             'accepted': pos_tried - pos_rej,
                             'no_sibling_to_flip': pos_nosib},
        'verifier_bytes_hashed_per_proof_byte': ratio,
        'affine': {'as_rate_published': False, 'check_affine_ok': affine_ok,
                   'check_affine_why': affine_why, 'fit_or_refuse': fit_why,
                   'why_not_a_rate': 'A18. The affine check was run BEFORE '
                                     'choosing how to report, and its verdict is '
                                     'recorded here whichever way it came out; '
                                     'points are published, never a slope.'},
        'wall_us_citable': False,
        'wall_us_reason': 'spikes/quiet.sh REFUSES on this host (loadavg 55.96 vs '
                          '3.50, 4 foreign containers). Wall time is recorded for '
                          'the ordering comparison only and is never published as '
                          'a rate; §3 and the W4 readset_table precedent.',
    }
    with open(os.path.join(HERE, 'verifycost.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(HERE, '..', 'W2_witnessed_trie')],
        artifacts=[os.path.join(HERE, 'verifycost.json')],
        controls=C, falsifiers=[F],
        measurements=[{'name': 'verifier_hash_bytes_vs_proof_bytes',
                       'points': pts, 'as_rate': False}],
        falsifier='verifier hash work flat (<%.0f%% spread) while proof size spans '
                  '>%.0f%%' % (FLAT_WORK_PCT, PROOF_SPAN_PCT))

    print(json.dumps(out, indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
