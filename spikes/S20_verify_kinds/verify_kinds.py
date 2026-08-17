#!/usr/bin/env python3
"""S20 — what does the VERIFIER pay for ABSENCE and COMPLETENESS proofs?

WHY THIS ID IS S20 AND NOT S86
------------------------------
`sh spikes/harness/allocid.sh S` answers with the lowest free number, and after
H57 widened its seed to the filesystem that answer is S20. Hand-picking a higher
one to keep the numbers chronological is the "grep more carefully" habit H57
removed. The claim line in `CHANNEL.md` precedes this directory (§13.3).

THE FALSIFIER, STATED BEFORE THE RUN AND FIXED IN THIS FILE
-----------------------------------------------------------
    If absence and completeness verifier work lands inside the MEMBERSHIP band
    S84 measured -- 1.06x to 1.16x the proof's own bytes -- on all three key
    sets, then S84 extends by inspection and this cycle buys nothing.

Operationalised below as `BAND = (1.06, 1.16)`: the falsifier FIRES if all six
(2 kinds x 3 key sets) ratios fall inside it.

THE PREDICTION, RECORDED SO IT CAN BE WRONG
-------------------------------------------
It will not, for completeness. `verify_completeness` calls
`build(sorted(ks), pf['depth'])` -- the verifier REBUILDS THE WHOLE ANSWER
SUBTRIE -- so its forced work should be set by ANSWER SIZE, which is the axis
W2's published "auth path is independent of answer size" is silent about and
which S80 deliberately kept separate from proof size. Absence should stay near
membership, because `verify_non_membership` folds one path and then does a set
membership test on the divergence node's children.

WHY THE ITEM EXISTS AT ALL
--------------------------
S79 and S80 both measured the PROVER for these two kinds and both said the
verifier does not follow by inspection: S79 found absence orders the three key
sets identically to membership, S80 found completeness orders them DIFFERENTLY,
so "the verifier is forced to hash the proof" (S84) is a statement about one of
three proof kinds. The mission's claim is that verification beats re-execution;
S85 priced that duel on membership. A range query is the query a real client
asks, and nothing has priced its verifier.

THE DENOMINATOR IS `witness_bytes`, NOT `steps_bytes`
-----------------------------------------------------
H51: `witness_bytes` = auth path + the terminal descriptor, and for absence that
descriptor is the DIVERGENCE CHILD SET while for completeness it is the ANSWER
SET. `steps_bytes` is the auth path alone. S84 used `steps_bytes` because
`witness_bytes` raised `KeyError: 'kind'` on a membership proof until H51 fixed
it; comparing three kinds on the auth path alone would charge completeness
nothing for the answer set it must transmit. Both are recorded per row so the
S84 comparison is still available, and the S84 reproduction control uses S84's
own quantity.

THE PROBE MUST SHOW IT REACHED ITS TARGET (A29)
-----------------------------------------------
Every proof measured here must verify TRUE, and for every proof a corrupted twin
must verify FALSE. Counting hashes inside a verifier that returned False on its
first line would report a small, stable, entirely fictional number -- and this
chain has already published two careful measurements of the wrong quantity.

Beyond that, each kind gets a control aimed at the part of the proof that kind
alone carries: the divergence child set for absence, the answer set for
completeness. A verifier that folds the path but ignores those would hash almost
the same bytes and pass every path-position control.

  python3 verify_kinds.py
"""
import os, sys, json, copy, struct, statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
S79 = os.path.join(HERE, '..', 'S79_absence_bytes')
S80 = os.path.join(HERE, '..', 'S80_completeness_bytes')
S84 = os.path.join(HERE, '..', 'S84_verify_cost')
W2 = os.path.join(HERE, '..', 'W2_witnessed_trie')

# WHICH COPY OF THE INSTRUMENT, AND WHY IT IS PINNED
# --------------------------------------------------
# `spikes/W2_witnessed_trie/trie_witness.py` was UNCOMMITTED-MODIFIED while this
# spike ran -- another lane wrapping the three verifiers in try/except, 145 lines
# changed, mtime 15:31, no CHANNEL claim naming it. `certify` refused the first
# run on exactly that (DIRTY TREE ... 2 modified), which is the A24 gate doing
# its job: the numbers would have described a version of the verifier that
# exists in no commit and that nobody could re-run.
#
# So the published run imports `w2_head/trie_witness.py`, a byte-pin of blob
# 57d1a481feb0f94fa392d80a048aeeda3f0f4379 taken with `git show HEAD:...` at
# commit 6d81a45, and the WORKING-TREE copy becomes a control:
# `C_worktree_agrees` re-runs the whole measurement in a subprocess against it
# and every published figure must be identical. The dirty-tree refusal is
# ANSWERED WITH EVIDENCE rather than bypassed with `allow_dirty` -- the S76
# precedent. Set KF_W2_WORKTREE=1 to run that side directly.
PIN = os.path.join(HERE, 'w2_head')
WORKTREE_RUN = os.environ.get('KF_W2_WORKTREE') == '1'
INSTRUMENT = W2 if WORKTREE_RUN else PIN
# INSTRUMENT goes on the path FIRST and `trie_witness` is imported before
# anything that imports it, so `verifycost` and `absence` -- both of which
# insert the W2 directory themselves -- get the pinned module from sys.modules.
sys.path.insert(0, INSTRUMENT)
import trie_witness as _TW_FIRST                                           # noqa: E402,F401
for p in (os.path.join(HERE, '..', 'harness'), S79, S80, S84):
    sys.path.insert(0, p)

import trie_witness as TW                                                  # noqa: E402
from trie_witness import (build, prove_membership, verify_membership,      # noqa: E402
                          prove_non_membership, verify_non_membership,
                          prove_completeness, verify_completeness,
                          witness_bytes, auth_path_bytes)
from kfcheck import certify                                                # noqa: E402
from provenance import Control, Falsifier                                  # noqa: E402
from units import check_affine                                             # noqa: E402
# IMPORTED, NOT REIMPLEMENTED. C1 reproduces S84's committed numbers with S84's
# own probe function; C27's attack on S79 made that a gating control rather than
# a habit, after a reimplemented `base()` gave a 450x discrepancy that looked
# like a finding. `verifycost` and `absence` guard their mains with __main__.
import verifycost as S84M                                                  # noqa: E402
from absence import absent_probes, child_map                               # noqa: E402

SEED = 20260817
BAND = (1.06, 1.16)       # S84's measured membership ratio, corrected by C27
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples',        os.path.join(S75, 'keys_triples.bin'))]
PROBES = 60               # per set per kind; S79 used 200, S80 120, S84 120
FRACTION = 0.75           # S80's query prefix fraction, kept so the two compare
# THE ANSWER-SIZE AXIS, by PREFIX LENGTH and not by fraction. The first draft
# swept fractions (0.60, 0.75, 0.90, 0.98) and produced a DUPLICATE POINT:
# triple keys are 12 B and byte positions 8 and 9 carry ONE distinct value each
# (measured: 1, 1, 1, 3, 1, 1, 55, 225, 1, 1, 55, 256 distinct values by
# position), so prefixes of length 8, 9 and 10 select identical answer sets.
# Two points at the same x is not a wider axis, and `check_affine` would have
# been fitting a duplicated observation.
ANSWER_SWEEP_LENGTHS = (6, 7, 8, 11)


def counted(fn, *a, **kw):
    """S84's counter, imported. Returns (result, n_hash_calls, bytes_hashed)."""
    return S84M.counted(fn, *a, **kw)


# ------------------------------------------------------------------ tampering
def tamper_path(pf, idx):
    """Flip one sibling digest at path position `idx`. None if that position
    carries no sibling (an unbranched position has no digest -- S77)."""
    bad = copy.deepcopy(pf)
    (prefix, term, pairs), b = bad['steps'][idx]
    if not pairs:
        return None
    byte, dig = pairs[0]
    pairs[0] = (byte, bytes([dig[0] ^ 0xFF]) + dig[1:])
    return bad


def drop_divergence_child(pf):
    """Absence only: remove one child from the DIVERGENCE node's descriptor.

    This is the attack absence exists to stop. The verifier concludes "k is
    absent" from "the next byte is not among this node's children", so a prover
    that hides the child holding k would prove a false absence. It is invisible
    to every path-position control, because the divergence node is not on the
    path -- it is the terminal descriptor.
    """
    bad = copy.deepcopy(pf)
    prefix, term, pairs = bad['node']
    if not pairs:
        return None
    bad['node'] = (prefix, term, pairs[1:])
    return bad


def add_divergence_child(pf, k):
    """Absence only: ADD the queried byte as a child of the divergence node.

    The mirror of the above and the one a verifier could get right by accident:
    if it accepts, a prover can deny a key it holds; if the fold is checked, the
    forged child changes the node digest and the fold fails.
    """
    bad = copy.deepcopy(pf)
    prefix, term, pairs = bad['node']
    have = {b for b, _h in pairs}
    i = 0
    for (p2, _t, _p), _b in bad['steps']:
        i += len(p2) + 1
    i += min(len(prefix), max(0, len(k) - i))
    if i >= len(k) or k[i] in have:
        return None
    bad['node'] = (prefix, term,
                   sorted(list(pairs) + [(k[i], b'\x11' * 32)]))
    return bad


def drop_answer_key(pf):
    """Completeness only: omit one answer key. The anti-omission check."""
    if not pf.get('keys') or len(pf['keys']) < 2:
        return None
    bad = copy.deepcopy(pf)
    bad['keys'] = bad['keys'][1:]
    return bad


def tamper_answer_key(pf):
    """Completeness only: alter one answer key's LAST byte, keeping the count."""
    if not pf.get('keys'):
        return None
    bad = copy.deepcopy(pf)
    k = bad['keys'][-1]
    if not k:
        return None
    bad['keys'] = bad['keys'][:-1] + [k[:-1] + bytes([k[-1] ^ 0x01])]
    return bad


# ------------------------------------------------------------------ measuring
def measure_absence(name, keys):
    root = build(sorted(set(keys)))
    rh = root.h
    kids = child_map(keys)
    probes, depths = absent_probes(keys, kids, PROBES)
    per = defaultdict(list)
    tam = {'path_tried': 0, 'path_rejected': 0, 'no_sibling': 0,
           'drop_child_tried': 0, 'drop_child_rejected': 0,
           'add_child_tried': 0, 'add_child_rejected': 0}
    verified = 0
    for q in probes:
        pf = prove_non_membership(root, q)
        if pf is None:                      # probe is present: not an absence case
            continue
        ok, n, b = counted(verify_non_membership, rh, q, pf)
        if not ok:
            raise SystemExit('S20: an absence proof failed to verify -- the '
                             'counts would describe an early return (A29)')
        verified += 1
        _r, _fn, fb = counted(S84M.flat_verify, rh, q, pf)
        per['witness_bytes'].append(witness_bytes(pf))
        per['auth_path_bytes'].append(auth_path_bytes(pf))
        per['hash_bytes'].append(b)
        per['hash_calls'].append(n)
        per['null_hash_bytes'].append(fb)
        per['steps'].append(len(pf['steps']))
        per['answer_keys'].append(0)
        for i in range(len(pf['steps'])):
            bad = tamper_path(pf, i)
            if bad is None:
                tam['no_sibling'] += 1
                continue
            tam['path_tried'] += 1
            tam['path_rejected'] += 0 if verify_non_membership(rh, q, bad) else 1
        bad = drop_divergence_child(pf)
        if bad is not None:
            tam['drop_child_tried'] += 1
            tam['drop_child_rejected'] += 0 if verify_non_membership(rh, q, bad) else 1
        bad = add_divergence_child(pf, q)
        if bad is not None:
            tam['add_child_tried'] += 1
            tam['add_child_rejected'] += 0 if verify_non_membership(rh, q, bad) else 1
    return _row(name, 'absence', per, len(keys), verified), tam


def measure_completeness(name, keys, fraction=FRACTION, prefix_len=None):
    root = build(sorted(set(keys)))
    rh = root.h
    stride = max(1, len(keys) // PROBES)
    sampled = keys[::stride][:PROBES]
    if prefix_len is None:
        qs = [k[:max(1, int(len(k) * fraction))] for k in sampled]
    else:
        qs = [k[:min(prefix_len, len(k))] for k in sampled]
    per = defaultdict(list)
    tam = {'path_tried': 0, 'path_rejected': 0, 'no_sibling': 0,
           'drop_key_tried': 0, 'drop_key_rejected': 0,
           'tamper_key_tried': 0, 'tamper_key_rejected': 0}
    verified = 0
    for q in qs:
        pf = prove_completeness(root, q)
        ok, n, b = counted(verify_completeness, rh, q, pf)
        if not ok:
            raise SystemExit('S20: a completeness proof failed to verify -- the '
                             'counts would describe an early return (A29)')
        verified += 1
        _r, _fn, fb = counted(S84M.flat_verify, rh, q, pf)
        per['witness_bytes'].append(witness_bytes(pf))
        per['auth_path_bytes'].append(auth_path_bytes(pf))
        per['hash_bytes'].append(b)
        per['hash_calls'].append(n)
        per['null_hash_bytes'].append(fb)
        per['steps'].append(len(pf['steps']))
        per['answer_keys'].append(len(pf.get('keys') or []))
        for i in range(len(pf['steps'])):
            bad = tamper_path(pf, i)
            if bad is None:
                tam['no_sibling'] += 1
                continue
            tam['path_tried'] += 1
            tam['path_rejected'] += 0 if verify_completeness(rh, q, bad) else 1
        bad = drop_answer_key(pf)
        if bad is not None:
            tam['drop_key_tried'] += 1
            tam['drop_key_rejected'] += 0 if verify_completeness(rh, q, bad) else 1
        bad = tamper_answer_key(pf)
        if bad is not None:
            tam['tamper_key_tried'] += 1
            tam['tamper_key_rejected'] += 0 if verify_completeness(rh, q, bad) else 1
    return _row(name, 'completeness', per, len(keys), verified), tam


def _row(name, kind, per, n_keys, verified):
    row = {'set': name, 'kind': kind, 'n_keys': n_keys,
           'n_proofs': len(per['witness_bytes']), 'verified_true': verified}
    for m, v in per.items():
        row[m] = round(statistics.mean(v), 3) if v else 0.0
    row['work_per_witness_byte'] = round(
        row['hash_bytes'] / row['witness_bytes'], 3) if row['witness_bytes'] else 0.0
    row['work_per_auth_path_byte'] = round(
        row['hash_bytes'] / row['auth_path_bytes'], 3) if row['auth_path_bytes'] else 0.0
    return row


def main():
    out = {'seed': SEED, 'band_from_S84': list(BAND), 'probes_per_set': PROBES,
           'query_prefix_fraction': FRACTION, 'rows': [], 'answer_sweep': []}
    loaded = {name: S84M.read_keys(path) for name, path in SETS}
    tam_abs = defaultdict(int)
    tam_comp = defaultdict(int)

    for name, _path in SETS:
        keys = loaded[name]
        r, t = measure_absence(name, keys)
        out['rows'].append(r)
        for k, v in t.items():
            tam_abs[k] += v
        r, t = measure_completeness(name, keys)
        out['rows'].append(r)
        for k, v in t.items():
            tam_comp[k] += v

    # THE ANSWER-SIZE AXIS. A range query's answer set is what the verifier
    # rebuilds, so the axis that decides its cost is not which key set it is but
    # how much of the key the query pins. Reported as points; `check_affine` is
    # run BEFORE choosing how to report, per S84's method.
    for L in ANSWER_SWEEP_LENGTHS:
        r, _t = measure_completeness('triples', loaded['triples'], prefix_len=L)
        r['prefix_len'] = L
        out['answer_sweep'].append(r)

    if WORKTREE_RUN:
        # The control side: same measurement, working-tree instrument, no
        # certification. Written under its own name so it cannot overwrite the
        # published artifact -- H49, an attack that recorded into its target.
        with open(os.path.join(HERE, 'verify_kinds.worktree.json'), 'w') as f:
            json.dump(out, f, indent=2, sort_keys=True)
        print('worktree run written (no certification on this side)')
        return 0

    # ---------------------------------------------------------------- verdict
    ratios = {(r['set'], r['kind']): r['work_per_witness_byte'] for r in out['rows']}
    inside = {k: (BAND[0] <= v <= BAND[1]) for k, v in ratios.items()}
    out['work_per_witness_byte'] = {'%s/%s' % k: v for k, v in ratios.items()}
    out['inside_S84_band'] = {'%s/%s' % k: v for k, v in inside.items()}
    fired = not all(inside.values())

    sweep_pts = [(r['answer_keys'], r['hash_bytes']) for r in out['answer_sweep']]
    affine_ok, affine_why = check_affine(sweep_pts)
    out['answer_axis'] = {'points_answer_keys_vs_hash_bytes': sweep_pts,
                          'affine': bool(affine_ok), 'affine_detail': affine_why}

    with open(os.path.join(HERE, 'verify_kinds.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    # C1 -- GATING. S84's own probe function, S84's own quantity, S84's own key
    # files, compared against its committed artifact. If this moves, every
    # number below is being produced by a different instrument than the one the
    # band came from, and the comparison is meaningless.
    prev = json.load(open(os.path.join(S84, 'verifycost.json')))
    prev_by_set = {r['set']: r for r in prev['operating_points']}
    repro, deltas = {}, []
    for name, _path in SETS:
        r, _saw, _ro, _rn, _pos = S84M.probe_set(name, loaded[name])
        d_h = r['hash_bytes'] - prev_by_set[name]['hash_bytes']
        d_p = r['proof_bytes'] - prev_by_set[name]['proof_bytes']
        repro[name] = {'hash_bytes_now': r['hash_bytes'],
                       'hash_bytes_committed': prev_by_set[name]['hash_bytes'],
                       'delta_hash_bytes': round(d_h, 6),
                       'delta_proof_bytes': round(d_p, 6)}
        deltas += [abs(d_h), abs(d_p)]
    c = Control('C_S84_reproduces',
                'the membership band this spike compares against is reproduced '
                'here with S84\'s own probe function on S84\'s own key files, '
                'before any new number is computed',
                null_must_contain='any drift in trie_witness, the key files or '
                                  'the counting hashlib would move these means',
                can_fail_because='S84.probe_set returns hash_bytes or proof_bytes '
                                 'differing from the committed verifycost.json')
    c.observe(max(deltas) == 0.0, repro)
    C.append(c)

    # C2 -- A29. Every proof verified TRUE, or the hash counts describe an early
    # return rather than the work of checking a proof.
    all_true = all(r['verified_true'] == r['n_proofs'] and r['n_proofs'] > 0
                   for r in out['rows'])
    c = Control('C_every_proof_verified_true',
                'A29: a probe that cannot show it reached its target has '
                'produced no evidence. A verifier returning False on line one '
                'hashes almost nothing and reports a small stable number',
                null_must_contain='a proof that fails to verify, which raises '
                                  'SystemExit in the measurement loop',
                can_fail_because='any row has verified_true < n_proofs, or zero '
                                 'proofs were built for a set')
    c.observe(all_true, {'%s/%s' % (r['set'], r['kind']):
                         [r['verified_true'], r['n_proofs']] for r in out['rows']})
    C.append(c)

    # C3 -- every PATH position is load-bearing, for both kinds.
    pf_ok = (tam_abs['path_tried'] > 0 and tam_comp['path_tried'] > 0 and
             tam_abs['path_rejected'] == tam_abs['path_tried'] and
             tam_comp['path_rejected'] == tam_comp['path_tried'])
    c = Control('C_every_path_position_forced',
                'a sibling digest flipped at EACH path position independently '
                'must be rejected, or the verifier hashes bytes it does not '
                'actually check and the ratio prices nothing',
                null_must_contain='a verifier that checks only the last step '
                                  'would accept a corruption at position 0',
                can_fail_because='any single-position corruption verifies TRUE, '
                                 'or no position had a sibling to flip')
    c.observe(pf_ok, {'absence': dict(tam_abs), 'completeness': dict(tam_comp)})
    C.append(c)

    # C4 -- the part ABSENCE alone carries. Not on the path: the divergence node.
    ab_ok = (tam_abs['drop_child_tried'] > 0 and
             tam_abs['drop_child_rejected'] == tam_abs['drop_child_tried'] and
             tam_abs['add_child_tried'] > 0 and
             tam_abs['add_child_rejected'] == tam_abs['add_child_tried'])
    c = Control('C_divergence_child_set_forced',
                'absence is the claim "the next byte is not among this node\'s '
                'children", so a prover hiding the child that holds the key '
                'would prove a false absence. Both directions driven: a child '
                'removed, and the queried byte forged in',
                null_must_contain='a verifier that folds the path and trusts the '
                                  'terminal descriptor accepts both edits',
                can_fail_because='either tampered absence proof verifies TRUE, or '
                                 'neither edit was constructible on any probe')
    c.observe(ab_ok, dict(tam_abs))
    C.append(c)

    # C5 -- the part COMPLETENESS alone carries: the answer set.
    co_ok = (tam_comp['drop_key_tried'] > 0 and
             tam_comp['drop_key_rejected'] == tam_comp['drop_key_tried'] and
             tam_comp['tamper_key_tried'] > 0 and
             tam_comp['tamper_key_rejected'] == tam_comp['tamper_key_tried'])
    c = Control('C_answer_set_forced',
                'completeness is the anti-omission claim, so an omitted answer '
                'key and an altered answer key must both be rejected -- this is '
                'the work that makes the verifier rebuild the subtrie',
                null_must_contain='a verifier that folds the path and takes the '
                                  'key list on trust accepts both edits',
                can_fail_because='either tampered completeness proof verifies '
                                 'TRUE, or no proof carried two or more keys')
    c.observe(co_ok, dict(tam_comp))
    C.append(c)

    # C6 -- the null must be able to contain the flat effect (A20).
    nulls = sorted({r['null_hash_bytes'] for r in out['rows']})
    c = Control('C_null_is_flat',
                'A20: "verifier work tracks proof size" is unfalsifiable without '
                'a verifier that genuinely does constant work. S84\'s '
                'flat_verify is that null and it must stay flat across both new '
                'kinds and all three sets',
                null_must_contain='the real verifier, whose bytes hashed differ '
                                  'by set and by kind',
                can_fail_because='flat_verify\'s bytes hashed differ across rows, '
                                 'which would mean the null is reading the proof')
    c.observe(len(nulls) == 1, {'distinct_null_hash_bytes': nulls,
                                'real_hash_bytes': sorted(
                                    {r['hash_bytes'] for r in out['rows']})})
    C.append(c)

    # C7 -- the instrument is the COMMITTED one, and the in-flight edit to it
    # does not move a number. This is the A24 gate answered with evidence.
    import subprocess
    env = dict(os.environ, KF_W2_WORKTREE='1')
    sub = subprocess.run([sys.executable, os.path.abspath(__file__)],
                         cwd=HERE, env=env, capture_output=True, text=True)
    wt_path = os.path.join(HERE, 'verify_kinds.worktree.json')
    wt = json.load(open(wt_path)) if os.path.exists(wt_path) else {}
    same = (sub.returncode == 0 and wt.get('rows') == out['rows'] and
            wt.get('answer_sweep') == out['answer_sweep'])
    c = Control('C_worktree_agrees',
                'the published numbers come from a byte-pin of the COMMITTED '
                'trie_witness.py (blob 57d1a481, HEAD 6d81a45) because the '
                'working-tree copy was uncommitted-modified while this ran. The '
                'same measurement against the working-tree copy must give '
                'identical rows, or the two verifiers are not the same verifier',
                null_must_contain='the in-flight edit rewrites all three verify '
                                  'functions, so a behavioural change in any of '
                                  'them lands in these rows',
                can_fail_because='any row or sweep point differs between the '
                                 'pinned and working-tree instruments, or the '
                                 'subprocess fails to run at all')
    c.observe(same, {'subprocess_rc': sub.returncode,
                     'rows_identical': wt.get('rows') == out['rows'],
                     'sweep_identical': wt.get('answer_sweep') == out['answer_sweep'],
                     'pinned_instrument': os.path.relpath(PIN, HERE),
                     'stderr_tail': sub.stderr[-300:]})
    C.append(c)

    F = Falsifier('F_S84_band_extends',
                  refutes='this spike: if both new kinds sit inside the '
                          'membership band, the verifier model extends by '
                          'inspection and the cycle bought nothing',
                  fires_when='any of the six (kind x set) ratios falls OUTSIDE '
                             '[%.2f, %.2f]' % BAND,
                  null_must_contain='six ratios inside the band, which is what '
                                    'the membership rows already look like')
    F.observe(fired, {'ratios': out['work_per_witness_byte'],
                      'inside_band': out['inside_S84_band']})

    ok, problems = certify(
        HERE,
        deps=[S84],
        artifacts=[os.path.join(HERE, 'verify_kinds.json'),
                   os.path.join(PIN, 'trie_witness.py')],
        controls=C, falsifiers=[F],
        measurements=[{'name': 'answer_keys_vs_verifier_hash_bytes',
                       'points': sweep_pts, 'as_rate': False}],
        falsifier='absence and completeness verifier work inside S84\'s '
                  'membership band [%.2f, %.2f] on all three key sets, which '
                  'would mean the verifier model extends by inspection' % BAND)

    print(json.dumps({k: out[k] for k in
                      ('work_per_witness_byte', 'inside_S84_band', 'answer_axis')},
                     indent=2, sort_keys=True))
    for r in out['rows']:
        print('  %-16s %-13s witness=%9.1f auth=%8.1f work=%9.1f  x%.3f  answers=%.1f'
              % (r['set'], r['kind'], r['witness_bytes'], r['auth_path_bytes'],
                 r['hash_bytes'], r['work_per_witness_byte'], r['answer_keys']))
    print('falsifier F_S84_band_extends FIRED=%s' % fired)
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
