#!/usr/bin/env python3
"""G95 — null the SELECTOR, not the split.

Run: python3 spikes/G95_selector_null/null.py

THE QUESTION. G77/G87/G88 all report a gain from a valid-selected argmax over
4-5 arms, chosen per (predicate, direction) key. That selector has never been
nulled. G56 nulled a BINARY mask (1000 random same-size masks; 0/1000 reached
G54's 0.2313) and G81 located the mass (97.75% of G77's +0.0067 sits in
valid-picked DistMult keys) -- but locating where a gain sits is not evidence
that the mechanism placing it there carries information. An argmax over 5 arms
has strictly MORE freedom than a binary mask, so it needs a stronger null, not a
weaker one. A26, this lane's own guardrail: a knob is not a mechanism.

THE NULL, and why THIS one. Permuting the frozen choice vector ACROSS keys while
PRESERVING THE EXACT MULTISET {distmult 279, g64 85, complex 39, rotate 26,
prior 17} holds two things fixed that a naive null would destroy:

  * the marginal quality of the arms -- a "pick a uniformly random arm" null
    would be beaten trivially by any selector, because the arms are not equally
    good, and beating it would restate that DistMult is strong;
  * the selector's FREEDOM -- same number of keys, same number of departures
    from the default.

What it destroys is the only thing under test: the MATCH between a key and the
arm chosen for it. So a real gain must survive it, and A20 is satisfied by
construction -- the null CAN contain the effect, because a permutation that
happens to land the good arms on the right keys scores exactly what G88 scores.

THE INSTRUMENT IS G88'S OWN. `freeze_dir_select` and `apply_dir` are imported
from `spikes/G88_5way_hybrid/mix.py` and called unmodified; the per-arm test
ranks are the ones G88 computes. A third evaluator would make a disagreement
un-attributable (G94's own words: a spike that scores its own rules can move the
number twice and report it once).
"""
from __future__ import annotations

import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
G88 = os.path.join(SPIKES, "G88_5way_hybrid")


def _numpy_pythons():
    out = [os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")]
    parent = os.path.dirname(ROOT)
    try:
        names = os.listdir(parent)
    except OSError:
        names = []
    for name in names:
        out.append(os.path.join(parent, name, "spikes",
                                "S5_hdc_prototype", ".venv", "bin", "python"))
    return out


def _reexec_with_numpy():
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(sys.executable)
    for py in _numpy_pythons():
        if os.path.isfile(py) and os.path.abspath(py) != here:
            os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.stderr.write("numpy required (S5 venv missing)\n")
    sys.exit(2)


_reexec_with_numpy()

import numpy as np                                            # noqa: E402
sys.path.insert(0, os.path.join(SPIKES, "harness"))
for d in ("G51_bayesian_lift_scoring", "G59_official_split",
          "G64_bidirectional_topologies", "G72_complex_all_entity",
          "G75_complex_gate", "G76_distmult_min10", "G77_distmult_select",
          "G79_rotate_all_entity"):
    sys.path.insert(0, os.path.join(SPIKES, d))
sys.path.insert(0, G88)

import bayesian_lift as G51                                   # noqa: E402
import complex as G72                                         # noqa: E402
import distmult as G76                                        # noqa: E402
import official as G59                                        # noqa: E402
import rotate as G79                                          # noqa: E402
import run_g64 as G64                                         # noqa: E402
import mix as G88MIX                                          # noqa: E402  THE SUBJECT
from provenance import Control, Falsifier                     # noqa: E402
from kfcheck import certify                                   # noqa: E402

CORPUS = G59.CORPUS
# TAKEN FROM THE SUBJECT, NOT RETYPED. My first draft typed these three paths by
# eye and put ComplEx in G72 when G88 loads it from G75 -- §12.4's own defect
# ("a reference is resolved mechanically, never by eye") committed inside a
# spike that exists to check somebody else's mechanism. Reading them off the
# module also means a G88 that repoints an arm cannot silently diverge here.
CX_EMB, DM_EMB, ROT_EMB = G88MIX.CX_EMB, G88MIX.DM_EMB, G88MIX.ROT_EMB
KEYS = G88MIX.KEYS
DEFAULT = "distmult"
G88_HEADLINE = 0.3143
DRAWS = 1000
SEED = 0xC0FFEE


def build_rows():
    """G88's pipeline, verbatim in order, returning its valid/test rows."""
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"Official split: train={len(train)} valid={len(valid)} "
          f"test={len(test)} npred={npred} nent={nent}", flush=True)

    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    idx = G59.slim_index(train)

    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    for p, s, o in train:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)

    rules_by_head, _ = G64.mine_all_4_topologies_fast(train, out_adj, in_adj, npred)
    print(f"Mined {sum(len(r) for r in rules_by_head.values())} G64 rules.", flush=True)

    zc = np.load(CX_EMB); zd = np.load(DM_EMB); zr = np.load(ROT_EMB)

    def score(split):
        rows = G64.score_split_4topo(split, nent, rules_by_head, out_adj,
                                     in_adj, true_sp, true_po, idx)
        for r in rows:
            r["ranks"]["g64"] = r["ranks"].pop("g51")
        cx, cd, _ = G72.rank_complex(split, zc["E_re"], zc["E_im"],
                                     zc["R_re"], zc["R_im"], eval_sp, eval_po)
        G88MIX.attach_named(rows, split, cx, cd, "complex")
        dm, dd, _ = G76.rank_distmult(split, zd["E"], zd["R"], eval_sp, eval_po)
        G88MIX.attach_named(rows, split, dm, dd, "distmult")
        rt, rd, _ = G79.rank_rotate(split, zr["E_re"], zr["E_im"], zr["theta"],
                                    eval_sp, eval_po)
        G88MIX.attach_named(rows, split, rt, rd, "rotate")
        return rows

    print("Scoring VALID...", flush=True)
    valid_rows = score(valid)
    print("Scoring TEST...", flush=True)
    test_rows = score(test)
    return valid_rows, test_rows, len(test)


def main() -> int:
    t0 = time.time()
    print("=== G95: nulling the valid-select argmax (official FB15k-237) ===")
    valid_rows, test_rows, n_test = build_rows()

    # G88's OWN selector, unmodified.
    mask, choice = G88MIX.freeze_dir_select(valid_rows, KEYS, default=DEFAULT)
    real = G88MIX.apply_dir(test_rows, choice, default=DEFAULT)["mrr"]
    counts = dict(mask["counts"])
    print(f"\nreproduced G88 selector: counts={counts} sha={mask['sha256'][:12]}")
    print(f"reproduced G88 test MRR : {real:.4f}  (published {G88_HEADLINE})")

    # Single-arm comparands, from the same rows: what each arm scores ALONE.
    singles = {k: G59.metrics([r["ranks"][k] for r in test_rows])["mrr"]
               for k in KEYS}
    best_single = max(singles, key=singles.get)
    print("single arms:", {k: round(v, 4) for k, v in singles.items()})

    # THE NULL. Permute the choice VECTOR across keys; the multiset is carried,
    # so every draw makes exactly as many departures from the default as G88 did.
    keys = sorted(choice)
    vec = [choice[k] for k in keys]
    rng = np.random.default_rng(SEED)
    draws, multiset_ok = [], True
    from collections import Counter
    want = Counter(vec)
    for i in range(DRAWS):
        perm = list(vec)
        rng.shuffle(perm)
        if Counter(perm) != want:
            multiset_ok = False
        draws.append(G88MIX.apply_dir(
            test_rows, dict(zip(keys, perm)), default=DEFAULT)["mrr"])
        if (i + 1) % 200 == 0:
            print(f"  null draw {i + 1}/{DRAWS}", flush=True)
    draws = np.array(draws)
    med, p95, mx = float(np.median(draws)), float(np.percentile(draws, 95)), float(draws.max())
    ge = int((draws >= real).sum())
    print(f"\nNULL over {DRAWS} label-permuted selectors (multiset preserved):")
    print(f"  median {med:.4f}   p95 {p95:.4f}   max {mx:.4f}   min {draws.min():.4f}")
    ge_single = int((draws >= singles[best_single]).sum())
    print(f"  draws >= real {real:.4f}: {ge}/{DRAWS}")
    print(f"  draws >= best single arm {best_single} "
          f"{singles[best_single]:.4f}: {ge_single}/{DRAWS}")
    print(f"  real - null median = {real - med:+.4f}")

    c1 = Control('reproduces_g88', 'nothing downstream is about G88 unless its '
                 'headline reproduces from its own instrument',
                 null_must_contain='a DIFFERENT mrr. The pipeline is re-run from '
                                   'corpus and saved embeddings rather than read '
                                   'from result.json, so a drifted embedding, a '
                                   'changed rule miner or a moved split all '
                                   'produce a number that misses',
                 can_fail_because='any divergence in the arms, the corpus or the '
                                  'selector moves the 4th decimal')
    # A DICT, not a 2-list: `[0.3143, 0.3143]` is CONSTANT by construction when
    # the reproduction succeeds, and provenance.Control refuses constant
    # observations because they distinguished nothing. It was right to -- the
    # informative record is WHAT WAS COMPARED, including the selector digest,
    # which is the field that would move if the arms drifted while the rounded
    # MRR happened not to.
    c1.observe(round(real, 4) == G88_HEADLINE,
               {'reproduced_mrr': round(real, 6),
                'published_mrr': G88_HEADLINE,
                'reproduced_selector_sha256': mask['sha256'],
                'reproduced_counts': counts,
                'n_test_triples': n_test},
               f'reproduced {real:.4f} vs published {G88_HEADLINE}')

    c2 = Control('null_preserves_selection_budget', 'a draw that changes the arm '
                 'counts is a different experiment, not a null of this selector',
                 null_must_contain='a broken permutation. Counter(perm) is '
                                   'compared to Counter(vec) on EVERY draw, so a '
                                   'sampler that drew with replacement would be '
                                   'caught rather than assumed away',
                 can_fail_because='shuffling with replacement, or permuting the '
                                  'keys instead of the values')
    c2.observe(multiset_ok, [len(draws), len(keys)],
               f'{DRAWS} draws, each carrying {counts}')

    c3 = Control('null_is_non_degenerate', 'a null whose draws all score the same '
                 'cannot contain the effect and is not a null (A20)',
                 null_must_contain='spread. If the selector were irrelevant every '
                                   'permutation would score identically and the '
                                   'spread would be 0 -- that outcome is '
                                   'reachable and is exactly what a dead null '
                                   'looks like',
                 can_fail_because='every permutation scores identically, which '
                                  'would mean apply_dir ignores the choice')
    c3.observe(float(draws.std()) > 0,
               [float(draws.min()), float(draws.max()), float(draws.std())],
               f'spread {draws.max() - draws.min():.4f}, sd {draws.std():.4f}')

    f1 = Falsifier('F1_selector_carries_no_signal',
                   'refutes the ensemble thread: the argmax carries no '
                   'key-specific information and the 5-way gain is selection '
                   'freedom',
                   fires_when='real MRR is NOT above the null p95',
                   null_must_contain='both answers. The null max is a realisable '
                                     'permutation score, so real can land above '
                                     'or below it')
    f1.observe(not (real > p95), [real, p95, ge],
               f'real {real:.4f} vs null p95 {p95:.4f}, {ge}/{DRAWS} >= real')

    f2 = Falsifier('F2_random_assignment_beats_best_arm',
                   'refutes every mix row that argued from "beats DistMult": if '
                   'a RANDOM assignment of these arms already beats the best '
                   'single arm, that comparison was never about selection',
                   fires_when='null MEDIAN >= the best single-arm test MRR',
                   null_must_contain='both answers -- the median is a measured '
                                     'quantity and the single-arm scores come '
                                     'from the same rows')
    f2.observe(med >= singles[best_single], [med, singles[best_single]],
               f'null median {med:.4f} vs best single arm {best_single} '
               f'{singles[best_single]:.4f}')

    f3 = Falsifier('F3_g88_not_reproduced',
                   'refutes the whole run: if G88 does not reproduce, nothing '
                   'measured here is about G88',
                   fires_when='reproduced mrr != 0.3143 to 4 dp',
                   null_must_contain='both answers; C1 records the same '
                                     'comparison as a gating control')
    f3.observe(round(real, 4) != G88_HEADLINE,
               {'reproduced_mrr': round(real, 6), 'published_mrr': G88_HEADLINE,
                'selector_sha256': mask['sha256'],
                'delta': round(real - G88_HEADLINE, 6)},
               f'reproduced {real:.4f}')

    out = os.path.join(HERE, 'selector_null.json')
    json.dump({'spike': 'G95', 'seed': SEED, 'draws': DRAWS,
               'reproduced_mrr': round(real, 6),
               'g88_published_mrr': G88_HEADLINE,
               'selector_sha256': mask['sha256'], 'counts': counts,
               'n_keys': len(keys), 'n_test_triples': n_test,
               'single_arm_mrr': {k: round(v, 6) for k, v in singles.items()},
               'best_single_arm': best_single,
               'null_median': round(med, 6), 'null_p95': round(p95, 6),
               'null_max': round(mx, 6), 'null_min': round(float(draws.min()), 6),
               'null_sd': round(float(draws.std()), 6),
               'draws_ge_real': ge,
               'draws_ge_best_single_arm': ge_single,
               # THE DRAWS THEMSELVES, not only their summary. A null reported
               # as five statistics cannot be re-analysed against a question its
               # author did not ask -- and the first such question arrived
               # immediately (what fraction beats DistMult?) and was not
               # answerable from the summary I had written.
               'null_draws': [round(float(x), 6) for x in draws],
               'real_minus_null_median': round(real - med, 6),
               'elapsed_sec': round(time.time() - t0, 2)},
              open(out, 'w'), indent=1, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[G88, os.path.join(SPIKES, 'harness')],
        artifacts=[out],
        controls=[c1, c2, c3], falsifiers=[f1, f2, f3],
        allow_dirty=True,
        note='G95. The per-(predicate,direction) valid-select argmax behind '
             'G77/G87/G88 had never been nulled. G56 nulled a binary mask; an '
             'argmax over 5 arms has more freedom. The null permutes the frozen '
             'choice vector across keys preserving its exact multiset, so arm '
             'quality and selection budget are held fixed and only the key-to-arm '
             'MATCH is destroyed.',
        falsifier='If G88\'s 0.3143 were not above the p95 of 1000 '
                  'multiset-preserving label permutations of its own selector, '
                  'the 5-way gain would be selection freedom rather than a '
                  'mechanism, and the ensemble thread would be refuted.')
    print(f'\ncertify ok={ok}')
    for p in problems:
        print('  ' + p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
