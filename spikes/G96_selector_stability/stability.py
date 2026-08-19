#!/usr/bin/env python3
"""G96 — is the per-key selector table STABLE, or is G95's aggregate hiding noise?

Run: python3 spikes/G96_selector_stability/stability.py

ATTACK ON MY OWN G95, ONE CYCLE OLD (MISSION_LOOP §2: self-authored data first).

G95 showed G88's valid-select argmax beats a multiset-preserving permutation
null 0/1000, +0.0212 above the null MAX. **That is an aggregate result and it
licenses no per-key claim.** A selector whose individual choices are validation
noise can still beat that null, because the null destroys the key-to-arm match
GLOBALLY while a weakly-informative selector retains a little of it everywhere.

And the distinction is not academic here: G88 publishes its selector as a FROZEN
PER-KEY TABLE with a `choice_sha256`, and a digest over a table reads as a claim
about the table. If the choice at a key would flip on different validation data,
that digest pins a sample, not a finding.

THE TEST. Shuffle the validation rows, split into two disjoint halves, fit
G88's own `freeze_dir_select` independently on each, and ask how often the two
halves choose the same arm for the same key.

A27 IS THIS LANE'S OWN GUARDRAIL AND IT APPLIES TO ME HERE: *a hold-out drawn
from one end of the key order is not a sample.* The rows are shuffled under a
pinned seed before splitting, so the halves cannot differ by predicate id.

THE CHANCE BASELINE MUST BE COMPUTED, NOT ASSUMED. The choice distribution is
heavily skewed -- 279 of 446 keys are distmult -- so two INDEPENDENT selectors
drawing from that marginal agree far more often than 1/5. Quoting agreement
against a naive 20% would make noise look like stability. The baseline used is
sum(p_i^2) over the observed marginal, which is the agreement rate of two
independent draws from it.
"""
from __future__ import annotations

import json, os, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)

# RE-EXEC BEFORE THE IMPORT, AND THE ORDER IS THE WHOLE POINT. `null.py` calls
# `os.execv(py, [py, <null.py>] + argv)` at MODULE level when numpy is missing,
# so importing it from a numpy-less interpreter REPLACES THIS PROCESS WITH G95'S
# OWN RUN. It printed G95's banner, G95's null, and `certify ok=True` -- G95's,
# not this spike's -- and that output is indistinguishable at a glance from this
# file having worked. A module whose import can execv is not importable; doing
# the re-exec here first means numpy exists by the time null.py is read and its
# own bootstrap returns immediately.
def _reexec():
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(sys.executable)
    for py in [os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")]:
        if os.path.isfile(py) and os.path.abspath(py) != here:
            os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.stderr.write("numpy required (S5 venv missing)\n")
    sys.exit(2)


_reexec()
sys.path.insert(0, os.path.join(SPIKES, "G95_selector_null"))

import null as G95                                            # noqa: E402  reuse the pipeline
_np = G95.np
G88MIX = G95.G88MIX
G59 = G95.G59
KEYS, DEFAULT = G95.KEYS, G95.DEFAULT
G88_HEADLINE = G95.G88_HEADLINE
SEED = 0xC0FFEE


def main() -> int:
    t0 = time.time()
    print("=== G96: is G88's per-key selector table stable? ===")
    valid_rows, test_rows, n_test = G95.build_rows()

    # Full-validation selector: the reproduction gate (C1/F3).
    full_mask, full_choice = G88MIX.freeze_dir_select(valid_rows, KEYS, default=DEFAULT)
    real = G88MIX.apply_dir(test_rows, full_choice, default=DEFAULT)["mrr"]
    print(f"\nfull-valid selector: {real:.4f} (published {G88_HEADLINE}) "
          f"sha={full_mask['sha256'][:12]}")

    dm_only = G59.metrics([r["ranks"]["distmult"] for r in test_rows])["mrr"]
    print(f"distmult everywhere: {dm_only:.4f}")

    # A27: SHUFFLE BEFORE SPLITTING. Splitting valid_rows as-laid-out would put
    # low predicate ids in one half and high in the other, and every key would
    # then be absent from one side -- a hold-out drawn from one end of the key
    # order, which is this lane's own A27 and was earned by exactly this mistake.
    rng = _np.random.default_rng(SEED)
    order = rng.permutation(len(valid_rows))
    half = len(order) // 2
    rows_a = [valid_rows[i] for i in order[:half]]
    rows_b = [valid_rows[i] for i in order[half:]]
    disjoint = set(order[:half].tolist()).isdisjoint(set(order[half:].tolist()))
    print(f"valid rows {len(valid_rows)} -> A {len(rows_a)} / B {len(rows_b)} "
          f"disjoint={disjoint}")

    mask_a, choice_a = G88MIX.freeze_dir_select(rows_a, KEYS, default=DEFAULT)
    mask_b, choice_b = G88MIX.freeze_dir_select(rows_b, KEYS, default=DEFAULT)
    mrr_a = G88MIX.apply_dir(test_rows, choice_a, default=DEFAULT)["mrr"]
    mrr_b = G88MIX.apply_dir(test_rows, choice_b, default=DEFAULT)["mrr"]
    print(f"half-A selector: {mrr_a:.4f}  counts={dict(mask_a['counts'])}")
    print(f"half-B selector: {mrr_b:.4f}  counts={dict(mask_b['counts'])}")

    # AGREEMENT over the keys BOTH halves scored. A key that fell to the default
    # on both sides agrees trivially and would inflate the rate, so it is
    # reported separately rather than folded in.
    shared = sorted(set(choice_a) & set(choice_b))
    agree = sum(1 for k in shared if choice_a[k] == choice_b[k])
    rate = agree / len(shared)

    # CHANCE, from the observed marginals rather than 1/5. Two independent draws
    # from distribution p agree with probability sum(p_i^2).
    ca, cb = Counter(choice_a[k] for k in shared), Counter(choice_b[k] for k in shared)
    n = len(shared)
    chance = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    print(f"\nkeys scored by both halves: {n}")
    print(f"  agree on the same arm : {agree}  ({rate:.4f})")
    print(f"  chance from marginals : {chance:.4f}   (naive 1/5 would be 0.2000)")
    print(f"  agreement above chance: {rate - chance:+.4f}")

    # The same question restricted to keys where at least one half departed from
    # the default -- the only keys the selector is actually making a claim about.
    nd = [k for k in shared if not (choice_a[k] == DEFAULT and choice_b[k] == DEFAULT)]
    nd_agree = sum(1 for k in nd if choice_a[k] == choice_b[k])
    nd_rate = nd_agree / len(nd) if nd else float('nan')
    # ITS OWN CHANCE RATE, or the number means nothing. Quoting 0.38 against the
    # 0.57 computed over ALL keys would be the naive-1/5 mistake at one remove:
    # this subset EXCLUDES the default-default agreements, so its marginals are
    # different and its chance rate is necessarily lower. A subset figure
    # compared to the whole set's baseline is E-family -- the number is real and
    # the model behind it is wrong.
    nda = Counter(choice_a[k] for k in nd)
    ndb = Counter(choice_b[k] for k in nd)
    m = len(nd)
    nd_chance = sum((nda[k] / m) * (ndb[k] / m)
                    for k in set(nda) | set(ndb)) if m else float('nan')
    print(f"  keys where either half left the default: {len(nd)}, "
          f"agree {nd_agree} ({nd_rate:.4f}) vs its OWN chance {nd_chance:.4f} "
          f"({nd_rate - nd_chance:+.4f})")

    c1 = G95.Control('reproduces_g88', 'nothing here is about G88 unless its '
                     'headline reproduces from its own instrument',
                     null_must_contain='a different mrr -- the pipeline is re-run '
                                       'from corpus and embeddings, so any drift '
                                       'in the arms or the split misses',
                     can_fail_because='a moved embedding, a changed miner, a '
                                      'different split')
    c1.observe(round(real, 4) == G88_HEADLINE,
               {'reproduced_mrr': round(real, 6), 'published': G88_HEADLINE,
                'selector_sha256': full_mask['sha256']},
               f'{real:.4f} vs {G88_HEADLINE}')

    c2 = G95.Control('halves_disjoint_and_shuffled', 'A27: a hold-out drawn from '
                     'one end of the key order is not a sample',
                     null_must_contain='an overlap, or an unshuffled split. Taking '
                                       'valid_rows[:half] instead would put low '
                                       'predicate ids in A and high in B and is '
                                       'reachable by deleting one line',
                     can_fail_because='the two index sets intersect, or the '
                                      'permutation is the identity')
    c2.observe(disjoint and len(rows_a) + len(rows_b) == len(valid_rows),
               {'n_valid': len(valid_rows), 'n_a': len(rows_a), 'n_b': len(rows_b),
                'disjoint': disjoint, 'shuffled_seed': SEED},
               f'A {len(rows_a)} / B {len(rows_b)}, disjoint={disjoint}')

    c3 = G95.Control('chance_computed_from_marginals', 'a skewed choice '
                     'distribution makes two independent selectors agree far '
                     'more than 1/5, so the baseline must come from the data',
                     null_must_contain='a value far from 0.20. distmult holds '
                                       '279/446 of the full table, so sum(p^2) '
                                       'must land well above a naive fifth -- if '
                                       'it did not, the marginals would be flat '
                                       'and the correction unnecessary',
                     can_fail_because='the marginals come out uniform, which '
                                      'would make the naive baseline correct '
                                      'after all')
    c3.observe(chance > 0.20, {'chance': round(chance, 6), 'naive': 0.2,
                               'marginal_a': dict(ca), 'marginal_b': dict(cb)},
               f'chance {chance:.4f} vs naive 0.2000')

    f1 = G95.Falsifier('F1_per_key_choice_is_noise',
                       'refutes any per-key reading of G88\'s frozen table and of '
                       'G95\'s aggregate verdict: the choice at a key would flip '
                       'on different validation data',
                       fires_when='half-A and half-B agree at or below the chance '
                                  'rate computed from the observed marginals',
                       null_must_contain='both answers -- agreement is measured '
                                         'and chance is measured, on the same keys')
    f1.observe(rate <= chance, {'agreement': round(rate, 6),
                                'chance': round(chance, 6), 'n_keys': n},
               f'agree {rate:.4f} vs chance {chance:.4f}')

    f2 = G95.Falsifier('F2_selector_needs_full_validation',
                       'refutes the mechanism reading: if HALF the validation set '
                       'cannot beat one arm, the published gain is partly a '
                       'data-budget effect and is optimistic for any smaller '
                       'validation set',
                       fires_when='neither half-fit selector beats DistMult on test',
                       null_must_contain='both answers -- the half-fit MRRs and '
                                         'the DistMult baseline are computed from '
                                         'the same test rows')
    f2.observe(not (mrr_a > dm_only or mrr_b > dm_only),
               {'mrr_a': round(mrr_a, 6), 'mrr_b': round(mrr_b, 6),
                'distmult': round(dm_only, 6)},
               f'A {mrr_a:.4f} / B {mrr_b:.4f} vs distmult {dm_only:.4f}')

    f3 = G95.Falsifier('F3_g88_not_reproduced',
                       'refutes the whole run',
                       fires_when='reproduced mrr != 0.3143 to 4 dp',
                       null_must_contain='both answers; C1 gates on the same '
                                         'comparison')
    f3.observe(round(real, 4) != G88_HEADLINE,
               {'reproduced': round(real, 6), 'published': G88_HEADLINE},
               f'{real:.4f}')

    out = os.path.join(HERE, 'stability.json')
    json.dump({'spike': 'G96', 'seed': SEED,
               'reproduced_mrr': round(real, 6), 'g88_published': G88_HEADLINE,
               'full_selector_sha256': full_mask['sha256'],
               # H233: G88 publishes the object; verified, not trusted. See
               # spikes/harness/opencheck.py verify_citation.
               'opens_at': {'full_selector_sha256':
                            'spikes/G88_5way_hybrid/result.json#/'},
               'distmult_only_mrr': round(dm_only, 6),
               'n_valid_rows': len(valid_rows), 'n_a': len(rows_a), 'n_b': len(rows_b),
               'half_a_mrr': round(mrr_a, 6), 'half_b_mrr': round(mrr_b, 6),
               'half_a_counts': dict(mask_a['counts']),
               'half_b_counts': dict(mask_b['counts']),
               'full_counts': dict(full_mask['counts']),
               'n_shared_keys': n, 'n_agree': agree,
               'agreement_rate': round(rate, 6),
               'chance_from_marginals': round(chance, 6),
               'agreement_above_chance': round(rate - chance, 6),
               'n_keys_either_left_default': len(nd),
               'n_agree_either_left_default': nd_agree,
               'agreement_rate_either_left_default': round(nd_rate, 6),
               'chance_either_left_default': round(nd_chance, 6),
               'above_chance_either_left_default': round(nd_rate - nd_chance, 6),
               'marginal_a_nondefault': dict(nda),
               'marginal_b_nondefault': dict(ndb),
               'elapsed_sec': round(time.time() - t0, 2)},
              open(out, 'w'), indent=1, sort_keys=True)

    ok, problems = G95.certify(
        HERE,
        deps=[os.path.join(SPIKES, 'G88_5way_hybrid'),
              os.path.join(SPIKES, 'G95_selector_null'),
              os.path.join(SPIKES, 'harness')],
        artifacts=[out], controls=[c1, c2, c3], falsifiers=[f1, f2, f3],
        allow_dirty=True,
        note='G96. G95 nulled the selector in AGGREGATE and G88 publishes it as a '
             'frozen PER-KEY table with a sha256. This fits the same selector '
             'independently on two disjoint shuffled halves of validation and '
             'measures how often they choose the same arm for the same key, '
             'against a chance rate computed from the observed marginals rather '
             'than assumed at 1/5.',
        falsifier='If the two halves agreed at or below the marginal chance rate, '
                  'the per-key table would be validation noise and neither G88\'s '
                  'choice_sha256 nor G95\'s aggregate verdict could be quoted '
                  'about any individual key.')
    print(f'\ncertify ok={ok}')
    for p in problems:
        print('  ' + p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
