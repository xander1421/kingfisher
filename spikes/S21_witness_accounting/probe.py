#!/usr/bin/env python3
"""S21 — H51 fixed the accounting function and left every consumer on the broken one.

ATTACKER-1, 2026-08-17, cycle 15.  Run: `python3 spikes/S21_witness_accounting/probe.py`

THE ROW UNDER ATTACK
--------------------
H51 (AGENT-1, DONE, `903f5c6`) diagnosed that `witness_bytes()` raised
`KeyError: 'kind'` on a membership proof, so four spikes -- S77, S79, S80, S84 --
"reached for `steps_bytes` instead, which is the AUTHENTICATION PATH ONLY, and
nothing said the two differed."  Its fix corrected `witness_bytes` and
deliberately kept `steps_bytes` unchanged, "because five spikes call it and every
number they published is a number it returned."

VERIFIED BY GREP, NOT BY READING: `S77/measure.py:114`, `S79/absence.py:158`,
`S80/completeness.py:125`, `S84/verifycost.py:231` all still call `steps_bytes`.
Only AGENT-1's in-flight S20 calls `witness_bytes`.  So the row's

    "Additive: every existing caller of `steps_bytes` keeps its behaviour, so no
     recorded number moves by installing this."

is true of INSTALLING it, and is the opposite of reassuring: the four published
figures are still the accounting H51 says is wrong, under a DONE that reads as
though the confusion is resolved.  §12.2 inverted -- the site (the function) was
fixed and the class (four spikes publishing the auth path as the proof size) was
left standing.

SCOPE: S77's headline, because it is a LEDGER-chain claim -- "interning makes
proofs 22% BIGGER, 1,568 -> 1,917 B".

FALSIFIERS, POSTED TO CHANNEL.md BEFORE THIS FILE EXISTED
---------------------------------------------------------
  F1  THE KILL.  If `witness_bytes(pf) == steps_bytes(pf['steps'])` on S77's
      membership proofs, no published number moves and this row is cosmetic.
      `desc_bytes` has a 5-byte floor by inspection, so I expect it to fail --
      running it anyway, because inspection is not a measurement.
  F2  THE SCOPE BOUND, and it decides evidence vs conclusion.  If the absolute
      byte counts move but S77's RATIO does not, S77's CONCLUSION survives and
      only its absolute figures die.  Say which one is being killed.
  F3  If S77's own `measure.py` does not reproduce its published 1,568 / 1,917 /
      2,350 under an unmodified re-run, no delta can be attributed to the
      accounting and the NUMBER is withdrawn -- irreproducibility is not a kill.

CONTROLS
  C0  S77's numbers must reproduce EXACTLY before any recomputation is believed.
      This is B2's lesson from this same hour: a reconstructed instrument's first
      output must be the original's published figures.  Nothing here is
      reimplemented -- S77's own module is imported and its own function called.
      FAILS IF: any mean differs from measure.json at all.
  C1  Every sampled proof must still VERIFY.  A proof whose verifier rejects is
      not a proof and its size is a number about nothing (S77's own control).
      FAILS IF: any sampled proof fails verify_membership against the root hash.
  C2  The two accountings must be measured on THE SAME PROOF OBJECTS in one pass,
      never differenced across two runs.  "Never subtract a separately-measured
      overhead" -- a 59% became 41% exactly that way.
      FAILS IF: the pairing is broken, detected by requiring delta == desc_bytes
      of that proof's own leaf for every single proof, not on the mean.
  C3  MECHANISM, stated so it can be wrong, because "correct numbers pointing at
      the wrong cause" is one of the three failure modes no tool catches.  The
      omitted term is `desc_bytes(leaf)`, whose only variable part is the leaf's
      UNCONSUMED KEY TAIL -- so it must be largest exactly where S77's own
      explanation says the trie has the longest unbranched runs, and it must rank
      the three key sets the same way the mean leaf tail does.
      FAILS IF: the ranking by omitted bytes differs from the ranking by mean
      leaf-prefix length, in which case the term varies for some other reason and
      the attribution is withdrawn even though the bytes are right.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
S77 = os.path.join(ROOT, 'spikes', 'S77_proof_bytes')
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))


def load(path, name):
    """Import S77's module rather than reimplementing it (C0)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


s77 = load(os.path.join(S77, 'measure.py'), 's77_measure')
from trie_witness import (build, prove_membership, verify_membership,   # noqa: E402
                          steps_bytes, witness_bytes, desc_bytes)

published = json.load(open(os.path.join(S77, 'measure.json')))['sets']

problems = []
rows = {}

print('S21 — the same proofs, both accountings, one pass\n')
print(f"{'key set':18s} {'n':>4s} {'steps_bytes':>12s} {'witness_bytes':>14s} "
      f"{'delta B':>9s} {'delta %':>8s} {'published':>11s}")

for name, path in s77.SETS:
    keys = s77.read_keys(path)
    # S77's own sampling, copied from measure.py:153 so the population is identical.
    sample = keys[::max(1, len(keys) // 200)]
    root = build(sorted(set(keys)))
    rh = root.h

    n_steps = n_wit = 0
    verified = 0
    pairing_ok = True
    tail_len = 0                 # C3: the leaf's unconsumed key tail
    for k in sample:
        pf = prove_membership(root, k)
        sb = steps_bytes(pf['steps'])
        wb = witness_bytes(pf)
        # C2: the two accountings on ONE proof object, and the per-proof
        # difference must be exactly that proof's own terminal descriptor.
        if wb - sb != desc_bytes(pf['leaf']):
            pairing_ok = False
        n_steps += sb
        n_wit += wb
        tail_len += len(pf['leaf'][0])
        verified += bool(verify_membership(rh, k, pf))

    m_steps = n_steps / len(sample)
    m_wit = n_wit / len(sample)
    pub = published[name]['w2_real_proof']

    rows[name] = {'sampled': len(sample), 'verified': verified,
                  'steps_bytes_mean': m_steps, 'witness_bytes_mean': m_wit,
                  'delta_bytes': m_wit - m_steps,
                  'delta_pct': 100.0 * (m_wit - m_steps) / m_steps,
                  'published_mean': pub['mean_bytes'],
                  'published_sampled': pub['sampled'],
                  'pairing_exact': pairing_ok,
                  'mean_leaf_tail_bytes': tail_len / len(sample)}

    print(f"{name:18s} {len(sample):4d} {m_steps:12.2f} {m_wit:14.2f} "
          f"{m_wit - m_steps:9.2f} {100.0 * (m_wit - m_steps) / m_steps:7.2f}% "
          f"{pub['mean_bytes']:11.2f}")

    # ---- C0: exact reproduction, or nothing below is attributable ------------
    if m_steps != pub['mean_bytes']:
        problems.append(f'C0 {name}: re-run {m_steps!r} != published '
                        f'{pub["mean_bytes"]!r} — F3 FIRES, number withdrawn')
    if len(sample) != pub['sampled']:
        problems.append(f'C0 {name}: sampled {len(sample)} != published '
                        f'{pub["sampled"]} — different population, A15')
    # ---- C1 ------------------------------------------------------------------
    if verified != len(sample):
        problems.append(f'C1 {name}: {verified}/{len(sample)} verified')
    # ---- C2 ------------------------------------------------------------------
    if not pairing_ok:
        problems.append(f'C2 {name}: per-proof delta != desc_bytes(leaf) — the '
                        'two accountings are not paired on the same object')

print()

# ---------------------------------------------------------------- F1 ----------
deltas = [r['delta_bytes'] for r in rows.values()]
f1_fires = all(d == 0 for d in deltas)
print(f"F1 {'FIRES — no published number moves, row is cosmetic' if f1_fires else 'DOES NOT FIRE'}: "
      f"per-set delta {[round(d, 2) for d in deltas]} B "
      f"({min(deltas):.2f}–{max(deltas):.2f})")

# ---------------------------------------------------------------- F2 ----------
# S77's conclusion is a RATIO ACROSS SETS: interning (atoms_interned) costs more
# proof bytes than not interning (atoms_original). Recompute it under both.
o, i = rows['atoms_original'], rows['atoms_interned']
r_steps = i['steps_bytes_mean'] / o['steps_bytes_mean']
r_wit = i['witness_bytes_mean'] / o['witness_bytes_mean']
print(f"F2 S77's headline ratio, interned/original:  "
      f"steps_bytes {r_steps:.4f} ({100 * (r_steps - 1):+.1f}%)   "
      f"witness_bytes {r_wit:.4f} ({100 * (r_wit - 1):+.1f}%)")
f2_fires = abs(r_wit - r_steps) < 0.005
print(f"F2 {'FIRES' if f2_fires else 'DOES NOT FIRE'}: the ratio moves by "
      f"{abs(r_wit - r_steps):.4f} — S77's CONCLUSION "
      f"{'survives; only its absolute figures die' if f2_fires else 'moves too'}")

# ---- the ranking, which is what S77 actually concluded ----------------------
order_steps = sorted(rows, key=lambda n: rows[n]['steps_bytes_mean'])
order_wit = sorted(rows, key=lambda n: rows[n]['witness_bytes_mean'])
print(f"   set ranking by steps_bytes  : {order_steps}")
print(f"   set ranking by witness_bytes: {order_wit}"
      f"  {'UNCHANGED' if order_steps == order_wit else 'REORDERED'}")

# ---------------------------------------------------------------- C3 ----------
order_delta = sorted(rows, key=lambda n: rows[n]['delta_bytes'])
order_tail = sorted(rows, key=lambda n: rows[n]['mean_leaf_tail_bytes'])
print(f"C3 mechanism — omitted bytes vs mean leaf key tail:")
for n in rows:
    print(f"   {n:18s} omitted {rows[n]['delta_bytes']:7.2f} B   "
          f"mean leaf tail {rows[n]['mean_leaf_tail_bytes']:7.2f} B")
if order_delta != order_tail:
    problems.append(f'C3: omitted-bytes ranking {order_delta} != leaf-tail '
                    f'ranking {order_tail} — the attribution is withdrawn')
print(f"   ranking by omitted bytes {order_delta} vs by leaf tail {order_tail}: "
      f"{'SAME — attribution holds' if order_delta == order_tail else 'DIFFERENT'}")

out = {'spike': 'S21', 'atom': 'ATTACKER-1',
       'question': 'H51 fixed witness_bytes and left S77/S79/S80/S84 calling '
                   'steps_bytes; how big is the term they omit?',
       'falsifiers': {'F1_no_number_moves': f1_fires,
                      'F2_ratio_unchanged': f2_fires,
                      'F3_reproduction_failed': any(p.startswith('C0') for p in problems)},
       'sets': rows,
       's77_headline_ratio': {'steps_bytes': r_steps, 'witness_bytes': r_wit},
       'ranking': {'steps_bytes': order_steps, 'witness_bytes': order_wit,
                   'omitted_bytes': order_delta, 'leaf_tail': order_tail},
       'call_sites_still_on_steps_bytes': [
           'spikes/S77_proof_bytes/measure.py:114',
           'spikes/S79_absence_bytes/absence.py:158',
           'spikes/S80_completeness_bytes/completeness.py:125',
           'spikes/S84_verify_cost/verifycost.py:231']}
json.dump(out, open(os.path.join(HERE, 'result.json'), 'w'), indent=1, sort_keys=True)

print()
if problems:
    print('REFUSE — a control failed, so no number above is attributable:')
    for p in problems:
        print('  ' + p)
    sys.exit(1)
print(f'{len(rows)} key sets, all controls held (C0 exact reproduction, '
      f'C1 {sum(r["verified"] for r in rows.values())} proofs verified, '
      f'C2 per-proof pairing exact). result.json written.')
