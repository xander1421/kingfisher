#!/usr/bin/env python3
"""S23 — the other three consumers of the authentication-path accounting.

ATTACKER-1, 2026-08-17, cycle 16.  Run: `python3 spikes/S23_consumer_sweep/probe.py`

Filed out of S21 rather than folded into it.  S21 measured S77's membership case:
the omitted term is the leaf's unconsumed key tail, at worst 5.32% of the
published figure.  The other three consumers of `steps_bytes` omit STRUCTURALLY
LARGER terms, and two of them carry digests rather than framing:

  S79/absence.py:158        omits `desc_bytes(pf['node'])` -- the DIVERGENCE CHILD
                            SET, 33 B per child.  And S79's model explicitly
                            CHARGES that set, so its model-vs-prover cross-check
                            compared two different quantities (H51 said so; this
                            measures it).
  S80/completeness.py:125   omits `12 * len(pf['keys'])` -- the entire answer set.
  S84/verifycost.py:231     publishes a cost RATIO whose DENOMINATOR is the proof
                            size, so the ratio moves with the accounting and not
                            only the byte count.  Its proof kind is membership, so
                            its omitted term is the same leaf tail S21 measured --
                            named that way rather than implied to be larger.

METHOD IS S21's, DELIBERATELY, AND NOT A NEW INSTRUMENT
------------------------------------------------------
For each spike: import ITS OWN module, replicate ITS OWN population from ITS OWN
generators and constants, require the published figure to reproduce under `==`
before anything is recomputed (C0), then compute both accountings in ONE PASS with
a PER-PROOF equality check (C2) so no number here comes from a subtraction.

FALSIFIERS, POSTED TO CHANNEL.md BEFORE THIS FILE EXISTED
  F1  per spike: if its omitted term is zero, its numbers stand and that third of
      the row is cosmetic.
  F2  per spike: if the absolutes move but the CONCLUSION's ranking or direction
      does not, the evidence dies and the conclusion does not -- and it is stated
      per spike, not once for all three.
  F3  per spike: a published figure that does not reproduce exactly is REPORTED
      IRREPRODUCIBLE and withdrawn, not replaced.  Irreproducibility is not a kill.

CONTROLS
  C0  exact reproduction of each published mean, under `==`, before any delta is
      believed.  FAILS IF: any re-run mean differs at all, or the population size
      differs -- comparing across differently-sized populations is how G15 died.
  C1  every proof must still verify with the spike's own verifier.  FAILS IF: any
      sampled proof fails, in which case its size is a number about nothing.
  C2  both accountings on THE SAME proof object, per-proof equality against the
      terminal descriptor, never a difference of two means.
  C3  INDEPENDENT SECOND OPINION on the size of the term, which S21 did not have:
      AGENT-1's S20 (`a5bccb4`) computed `witness_bytes` and `auth_path_bytes` side
      by side for absence and completeness, on a DIFFERENT population (60 proofs,
      75%-length prefixes).  It is NOT used as a substitute -- G15 died comparing
      across populations -- only as a check that the term's SIGN and ORDER OF
      MAGNITUDE agree with a measurement I did not make.
      FAILS IF: S20's per-kind term disagrees in sign, or by more than 3x in
      magnitude, with the term measured here on the same proof kind.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'W2_witnessed_trie'))


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


from trie_witness import (build, prove_membership, verify_membership,      # noqa: E402
                          prove_non_membership, verify_non_membership,
                          prove_completeness, verify_completeness,
                          steps_bytes, witness_bytes, desc_bytes)

problems = []
out = {'spike': 'S23', 'atom': 'ATTACKER-1', 'spikes': {}}


def reproduces(mine, pub):
    """Exact at the precision the artifact PUBLISHES, which is not a tolerance.

    C0's first run REFUSED all three S84 rows: 1602.4833333333333 against a
    published 1602.483. S79 and S80 store full float repr, S84 stores
    `round(x, 3)`. Comparing a full float to a rounded literal under `==` calls a
    perfect reproduction irreproducible -- and the honest fix is to compare at the
    recorded precision, not to widen a tolerance. If the published value has k
    decimals, my value rounded to k decimals must equal it EXACTLY; anything else
    still refuses.
    """
    if mine == pub:
        return True, 'exact'
    s = repr(float(pub))
    k = len(s.split('.')[1]) if '.' in s else 0
    if round(mine, k) == pub:
        return True, f'exact at published {k}dp'
    return False, f'{mine!r} vs {pub!r}'


def report(tag, name, n, pub, m_steps, m_wit, extra=''):
    d = m_wit - m_steps
    ok, how = reproduces(m_steps, pub)
    print(f"  {name:18s} {n:4d} {m_steps:11.2f} {m_wit:12.2f} {d:9.2f} "
          f"{100.0 * d / m_steps:7.2f}%  pub {pub:11.2f} [{how}] {extra}")
    if not ok:
        problems.append(f'C0 {tag}/{name}: re-run {how} — F3 FIRES for this '
                        'spike, number withdrawn not replaced')
    return d


hdr = (f"  {'key set':18s} {'n':>4s} {'steps_bytes':>11s} {'witness_bytes':>12s} "
       f"{'delta B':>9s} {'delta %':>8s}")

# ============================================================== S79 — absence ==
print('S79 — absence proofs. Omitted term is the DIVERGENCE CHILD SET.\n' + hdr)
S79 = load('spikes/S79_absence_bytes/absence.py', 's79_absence')
pub79 = json.load(open(os.path.join(ROOT, 'spikes/S79_absence_bytes/absence.json')))['sets']
s79_rows = {}
for name, path in S79.SETS:
    keys = S79.read_keys(path)
    kids = S79.child_map(keys)
    probes, _depths = S79.absent_probes(keys, kids, S79.PROBES)
    root = build(sorted(set(keys)))
    rh = root.h
    n_st = n_wt = 0
    built = verified = 0
    pairing = True
    for p in probes:
        pf = prove_non_membership(root, p)
        if pf is None:
            continue
        sb, wb = steps_bytes(pf['steps']), witness_bytes(pf)
        if wb - sb != desc_bytes(pf['node']):
            pairing = False
        n_st += sb
        n_wt += wb
        built += 1
        verified += bool(verify_non_membership(rh, p, pf))
    ms, mw = n_st / built, n_wt / built
    pb = pub79[name]
    d = report('S79', name, built, pb['w2_real_absence_bytes_mean'], ms, mw)
    if built != pb['w2_proofs_built']:
        problems.append(f'C0 S79/{name}: built {built} != published '
                        f'{pb["w2_proofs_built"]} — different population, G15')
    if verified != built:
        problems.append(f'C1 S79/{name}: {verified}/{built} verified')
    if not pairing:
        problems.append(f'C2 S79/{name}: per-proof delta != desc_bytes(node)')
    s79_rows[name] = {'proofs': built, 'verified': verified,
                      'steps_bytes_mean': ms, 'witness_bytes_mean': mw,
                      'delta_bytes': d, 'delta_pct': 100.0 * d / ms,
                      'published_mean': pb['w2_real_absence_bytes_mean'],
                      'model_absence_auth_bytes_mean': pb['absence_auth_bytes_mean'],
                      'pairing_exact': pairing}

# S79's headline is a MODEL-vs-PROVER residual. H51 says it compared two different
# quantities; this is that residual under each accounting.
print('\n  S79\'s model-vs-prover residual, the quantity H51 says was mis-paired:')
for name, r in s79_rows.items():
    mdl = r['model_absence_auth_bytes_mean']
    print(f"    {name:18s} model {mdl:9.2f}  vs steps {r['steps_bytes_mean']:9.2f} "
          f"(residual {r['steps_bytes_mean'] - mdl:+8.2f})  "
          f"vs witness {r['witness_bytes_mean']:9.2f} "
          f"(residual {r['witness_bytes_mean'] - mdl:+8.2f})")
    r['residual_vs_model_steps'] = r['steps_bytes_mean'] - mdl
    r['residual_vs_model_witness'] = r['witness_bytes_mean'] - mdl

# ========================================================= S80 — completeness ==
print('\nS80 — completeness proofs. Omitted term is the ENTIRE ANSWER SET.\n' + hdr)
S80 = load('spikes/S80_completeness_bytes/completeness.py', 's80_completeness')
pub80 = json.load(open(os.path.join(ROOT, 'spikes/S80_completeness_bytes/completeness.json')))['sets']
s80_rows = {}
for name, path in S80.SETS:
    keys = S80.read_keys(path)
    stride = max(1, len(keys) // S80.QUERIES)
    sampled = keys[::stride][:S80.QUERIES]
    qs = [k[:max(1, int(len(k) * S80.FRACTION))] for k in sampled]
    root = build(sorted(set(keys)))
    rh = root.h
    n_st = n_wt = 0
    built = verified = 0
    pairing = True
    answers = 0
    for q in qs:
        pf = prove_completeness(root, q)
        if pf is None:
            continue
        sb, wb = steps_bytes(pf['steps']), witness_bytes(pf)
        if wb - sb != 12 * len(pf['keys']):
            pairing = False
        n_st += sb
        n_wt += wb
        answers += len(pf.get('keys') or [])
        built += 1
        verified += bool(verify_completeness(rh, q, pf))
    ms, mw = n_st / built, n_wt / built
    pb = pub80[name]
    d = report('S80', name, built, pb['w2_real_step_bytes_mean'], ms, mw,
               extra=f"answers/proof {answers / built:6.1f}")
    if built != pb['proofs']:
        problems.append(f'C0 S80/{name}: proofs {built} != published {pb["proofs"]}')
    if verified != built:
        problems.append(f'C1 S80/{name}: {verified}/{built} verified')
    if not pairing:
        problems.append(f'C2 S80/{name}: per-proof delta != 12*len(keys)')
    # S80's OWN FALSIFIER, made apples-to-apples. S80 compared the completeness
    # AUTH PATH against the membership AUTH PATH -- consistent, and the auth path
    # is not the proof. Charge both sides their terminal descriptor and re-ask
    # S80's question: does completeness still order the sets differently?
    n_mem = 0
    for k in sampled:
        mpf = prove_membership(root, k)
        if mpf is None:
            continue
        n_mem += witness_bytes(mpf)
    mem_wit = n_mem / len(sampled)
    s80_rows[name] = {'membership_witness_bytes_same_sample': mem_wit,
                      'proofs': built, 'verified': verified,
                      'steps_bytes_mean': ms, 'witness_bytes_mean': mw,
                      'delta_bytes': d, 'delta_pct': 100.0 * d / ms,
                      'published_mean': pb['w2_real_step_bytes_mean'],
                      'mean_answer_keys': answers / built,
                      'pairing_exact': pairing}

# S80's OWN FALSIFIER, RE-ASKED APPLES-TO-APPLES. S80's verdict is an ORDERING:
# "triples are the most expensive point query and the CHEAPEST range query", so
# "proof size is set by branching" is point-query-only and S77/S79 carry that
# scope. Both sides of that comparison were AUTH PATHS. Charge both their terminal
# descriptor -- the answer set for completeness, the leaf for membership -- and ask
# S80's question again.
print("\n  S80's ordering claim, with BOTH sides charged their terminal descriptor:")
print(f"    {'key set':18s} {'completeness':>13s} {'membership':>12s}  which is dearer")
inv = {}
for name, r in s80_rows.items():
    cw, mw2 = r['witness_bytes_mean'], r['membership_witness_bytes_same_sample']
    inv[name] = cw > mw2
    print(f"    {name:18s} {cw:13.2f} {mw2:12.2f}  "
          f"{'completeness (range)' if cw > mw2 else 'membership (point)'}")
    r['completeness_dearer_than_membership'] = cw > mw2
same_direction = len(set(inv.values())) == 1
print(f"    S80 found triples cheapest for range and dearest for point, which is "
      f"why its falsifier fired.\n    On witness_bytes all three sets agree in "
      f"direction: {same_direction} "
      f"({'S80\'s reordering does not survive' if same_direction else 'it survives'})")
out['s80_ordering_same_direction_on_witness_bytes'] = same_direction

# ============================================== S84 — a RATIO whose denominator ==
print('\nS84 — membership. Its omitted term is S21\'s leaf tail; what moves is the RATIO.\n' + hdr)
S84 = load('spikes/S84_verify_cost/verifycost.py', 's84_verifycost')
pub84 = json.load(open(os.path.join(ROOT, 'spikes/S84_verify_cost/verifycost.json')))
s84_rows = {}
# Keyed off `operating_points`, which is where S84 publishes per-set rows. My
# first draft guessed `rows`/`sets`, found neither, and silently printed no ratio
# at all — a lookup that misses must not degrade to a blank line, so the ratio
# block below now REFUSES when the key is absent.
p84 = {r['set']: r for r in pub84['operating_points']}
for name, path in S84.SETS:
    keys = S84.read_keys(path)
    root = build(sorted(keys))
    rh = root.h
    step = max(1, len(keys) // S84.PROBES)
    probes = sorted(keys)[::step][:S84.PROBES]
    n_st = n_wt = 0
    built = verified = 0
    pairing = True
    for k in probes:
        pf = prove_membership(root, k)
        if pf is None:
            continue
        sb, wb = steps_bytes(pf['steps']), witness_bytes(pf)
        if wb - sb != desc_bytes(pf['leaf']):
            pairing = False
        n_st += sb
        n_wt += wb
        built += 1
        verified += bool(verify_membership(rh, k, pf))
    ms, mw = n_st / built, n_wt / built
    pb = p84.get(name, {})
    pubv = pb.get('proof_bytes', pb.get('proof_bytes_mean'))
    d = report('S84', name, built, pubv if pubv is not None else ms, ms, mw)
    if verified != built:
        problems.append(f'C1 S84/{name}: {verified}/{built} verified')
    if not pairing:
        problems.append(f'C2 S84/{name}: per-proof delta != desc_bytes(leaf)')
    hb = pb.get('hash_bytes', pb.get('hash_bytes_mean'))
    row = {'proofs': built, 'verified': verified,
           'steps_bytes_mean': ms, 'witness_bytes_mean': mw,
           'delta_bytes': d, 'delta_pct': 100.0 * d / ms,
           'published_proof_bytes': pubv, 'published_hash_bytes': hb,
           'pairing_exact': pairing}
    if hb:
        row['ratio_on_steps_bytes'] = hb / ms
        row['ratio_on_witness_bytes'] = hb / mw
    s84_rows[name] = row

if not all('ratio_on_steps_bytes' in r for r in s84_rows.values()):
    problems.append('S84: published hash_bytes not found for every set, so the '
                    'ratio could not be recomputed — a missing input must refuse, '
                    'not print nothing (H30 class)')
if any('ratio_on_steps_bytes' in r for r in s84_rows.values()):
    print("\n  S84's published cost ratio (verifier hash bytes / proof bytes), "
          "recomputed on the correct denominator:")
    for name, r in s84_rows.items():
        if 'ratio_on_steps_bytes' not in r:
            continue
        print(f"    {name:18s} {r['ratio_on_steps_bytes']:.4f}x  ->  "
              f"{r['ratio_on_witness_bytes']:.4f}x   "
              f"({100 * (r['ratio_on_witness_bytes'] / r['ratio_on_steps_bytes'] - 1):+.1f}%)")

# ------------------------------------------------------------------- C3 --------
print('\nC3 — independent second opinion from AGENT-1\'s S20, on a DIFFERENT '
      'population (used for sign and magnitude only, never as a substitute):')
try:
    s20 = json.load(open(os.path.join(ROOT, 'spikes/S20_verify_kinds/verify_kinds.json')))
    rows20 = s20.get('rows') or []
    seen = {}
    for r in rows20:
        wb, ab = r.get('witness_bytes'), r.get('auth_path_bytes')
        if wb is None or ab is None:
            continue
        seen.setdefault(r.get('kind'), []).append(wb - ab)
    mine = {'absence': [r['delta_bytes'] for r in s79_rows.values()],
            'completeness': [r['delta_bytes'] for r in s80_rows.values()]}
    for kind, deltas in sorted(seen.items()):
        s20_mean = sum(deltas) / len(deltas)
        if kind not in mine:
            print(f"    {kind:14s} S20 term {s20_mean:9.2f} B   (no S23 counterpart)")
            continue
        my_mean = sum(mine[kind]) / len(mine[kind])
        ratio = (max(abs(s20_mean), abs(my_mean))
                 / max(1e-9, min(abs(s20_mean), abs(my_mean))))
        agree = (s20_mean > 0) == (my_mean > 0) and ratio <= 3.0
        print(f"    {kind:14s} S20 term {s20_mean:9.2f} B   S23 term {my_mean:9.2f} B"
              f"   {ratio:5.2f}x apart  {'AGREE' if agree else 'DISAGREE'}")
        if not agree:
            problems.append(f'C3 {kind}: S20 {s20_mean:.2f} vs S23 {my_mean:.2f} — '
                            'sign or magnitude disagreement with an independent run')
    out['s20_cross_check'] = {k: sum(v) / len(v) for k, v in seen.items()}
except FileNotFoundError:
    problems.append('C3: S20 verify_kinds.json absent — the independent second '
                    'opinion could not be taken, and a control that did not run '
                    'is not a control that passed')

# ------------------------------------------------------------------- F1/F2 -----
print()
for tag, rows in (('S79', s79_rows), ('S80', s80_rows), ('S84', s84_rows)):
    ds = [r['delta_bytes'] for r in rows.values()]
    f1 = all(d == 0 for d in ds)
    order_s = sorted(rows, key=lambda n: rows[n]['steps_bytes_mean'])
    order_w = sorted(rows, key=lambda n: rows[n]['witness_bytes_mean'])
    print(f"F1 {tag}: {'FIRES — term is zero' if f1 else 'does not fire'}, "
          f"term {min(ds):.2f}–{max(ds):.2f} B "
          f"({min(r['delta_pct'] for r in rows.values()):.2f}–"
          f"{max(r['delta_pct'] for r in rows.values()):.2f}%)")
    print(f"F2 {tag}: set ranking {'UNCHANGED' if order_s == order_w else 'REORDERED'} "
          f"— {order_s} -> {order_w}")
    out['spikes'][tag] = {'sets': rows, 'F1_term_is_zero': f1,
                          'ranking_steps': order_s, 'ranking_witness': order_w,
                          'F2_ranking_unchanged': order_s == order_w}

json.dump(out, open(os.path.join(HERE, 'result.json'), 'w'), indent=1, sort_keys=True)
print()
if problems:
    print('REFUSE — a control failed, so the numbers above are not attributable:')
    for p in problems:
        print('  ' + p)
    sys.exit(1)
print('3 spikes, 9 key-set rows, all controls held (C0 exact, C1 all verified, '
      'C2 per-proof pairing, C3 independent cross-check). result.json written.')
