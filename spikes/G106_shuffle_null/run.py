#!/usr/bin/env python3
"""G106 — the null on the 70/15/15 shuffle, the one split config.json marks
"NEVER MEASURED", and the leak re-expressed as LIFT instead of as raw MRR.

Run: PYTHONUNBUFFERED=1 python3 spikes/G106_shuffle_null/run.py   (~10 s)

WHY THIS IS NOT A LICENCE FOR 0.2648
  The shuffle split carries 30.01% same-pair leakage (G46/G48). Nothing measured
  on it should be gated on and `config.json` says so. What the null buys is the
  leak in the units the loop reports:

      leak-free lift  = 0.1358 - 0.1732      = -0.0374   (G49, G104)
      shuffle   lift  = 0.2648 - N           = measured here
      the leak, as lift = shuffle lift - leak-free lift

  The only leak figure quotable today is a raw MRR gap (+0.1290, G102), which
  compares two SYSTEMS. A system and its null are both inflated by a leak, and
  possibly by different amounts; the difference of the differences is what says
  how much of the headline was the leak rather than the method.

THE RANKER IS G104's, REUSED AND NOT RETYPED
  `rank_of` and `evaluate_prior` are imported from G104 rather than copied, and
  F3 re-runs them on the PAIR-DISJOINT split in this same process: they must
  return 0.1732. G104 shipped an internally consistent, fully green, TRANSPOSED
  model -- `for s, p, o` where this repo's tuple is `(p, s, o)` -- and no
  invariant computable from the measurement itself could see it. So the check
  here is a cross-split reproduction against a number produced by other code,
  not another self-consistency test.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
G34 = os.path.join(SPIKES, "G34_length1_and_constants")
G48 = os.path.join(SPIKES, "G48_pairdisjoint_split")
G104 = os.path.join(SPIKES, "G104_null_in_the_loop")

for d in (os.path.join(SPIKES, "harness"), G34, G48, G104):
    sys.path.insert(0, d)

import kfcheck                                            # noqa: E402
import length1_constants as L                             # noqa: E402
from provenance import Control, Falsifier                 # noqa: E402
from split import pair_disjoint_split, leak_count         # noqa: E402
from run import prior_scores, evaluate_prior              # noqa: E402  (G104's)

PAIR_DISJOINT_NULL = 0.1732     # G49, reproduced by G104 to six places
LEAK_FREE_SYSTEM = 0.1358       # G48/G49 full_system, same split
SHUFFLE_SYSTEM = 0.2648067492241375   # G34 arm, the withdrawn headline
TOL = 0.0005


def same_pair_leak(train, test):
    """Test triples whose (s, o) pair already appears in train under any p."""
    pairs = {(s, o) for _p, s, o in train} | {(o, s) for _p, s, o in train}
    return sum(1 for _p, s, o in test if (s, o) in pairs)


def main() -> int:
    t0 = time.time()
    _nt, _npred, nent, tri, train, _dev, test = L.load_dataset()
    true_sp, true_po = L.build_filter_index(tri)

    head, tail = prior_scores(train, None)
    shuffle_null = evaluate_prior(test, head, tail, true_sp, true_po, nent)
    leak = same_pair_leak(train, test)
    print(f"shuffle  null mrr {shuffle_null['mrr']:.6f}  hits10 "
          f"{shuffle_null['hits10']:.4f}  n_queries {shuffle_null['n_queries']}",
          flush=True)
    print(f"shuffle  same-pair leaked test triples {leak} of {len(test)} "
          f"({100.0 * leak / len(test):.2f}%)", flush=True)

    # F3 — the same ranker, in this same process, on the leak-free split.
    pd_train, _pd_dev, pd_test, _n = pair_disjoint_split(tri, L.SEED)
    pd_head, pd_tail = prior_scores(pd_train, None)
    pd_null = evaluate_prior(pd_test, pd_head, pd_tail, true_sp, true_po, nent)
    print(f"pairdisj null mrr {pd_null['mrr']:.6f}  (must be "
          f"{PAIR_DISJOINT_NULL})", flush=True)

    # A second, independently derived shuffle null: rebuild the split from
    # scratch under the same pinned seed. Two runs of one function is not a
    # reproduction, so this re-derives the SPLIT rather than re-calling the
    # scorer on the same lists.
    import random
    rng = random.Random(L.SEED)
    idx = list(range(len(tri)))
    rng.shuffle(idx)
    a, b = int(len(tri) * 0.70), int(len(tri) * 0.85)
    train2 = [tri[i] for i in idx[:a]]
    test2 = [tri[i] for i in idx[b:]]
    h2, t2 = prior_scores(train2, None)
    null2 = evaluate_prior(test2, h2, t2, true_sp, true_po, nent)

    shuffle_lift = SHUFFLE_SYSTEM - shuffle_null["mrr"]
    leakfree_lift = LEAK_FREE_SYSTEM - PAIR_DISJOINT_NULL
    leak_as_lift = shuffle_lift - leakfree_lift

    controls = [
        Control("C1_split_is_the_one_the_headline_came_from",
                why="the null must be on the same split as 0.2648 or it bounds "
                    "nothing; that split is L.load_dataset()'s own 70/15/15",
                can_fail_because="the split is not 70/15/15, or n_test moves",
                null_must_contain="the three split sizes"),
        Control("C2_this_split_really_does_leak",
                why="the whole reason its number is not gatable; a null on a "
                    "split that turned out clean would be a different row",
                can_fail_because="same-pair leaked test triples == 0",
                null_must_contain="the leak count and rate"),
        Control("C3_both_query_directions_scored",
                why="a half-scored null compared against a fully scored system "
                    "is not a comparison",
                can_fail_because="n_queries != 2 * n_test",
                null_must_contain="n_queries and n_test"),
        Control("C4_the_split_rebuilds_to_the_same_null",
                why="re-calling one scorer on one list is not a reproduction; "
                    "the SPLIT is re-derived from the pinned seed",
                can_fail_because="the rebuilt split gives a different null",
                null_must_contain="both values"),
    ]
    controls[0].observe(
        abs(len(train) / len(tri) - 0.70) < 0.001 and len(test) > 0,
        {"n_train": len(train), "n_dev": len(_dev), "n_test": len(test),
         "n_total": len(tri)})
    controls[1].observe(leak > 0, {"leaked_test_triples": leak,
                                   "n_test": len(test),
                                   "rate": round(leak / len(test), 4)})
    controls[2].observe(shuffle_null["n_queries"] == 2 * len(test),
                        {"n_queries": shuffle_null["n_queries"],
                         "n_test": len(test)})
    controls[3].observe(abs(null2["mrr"] - shuffle_null["mrr"]) < 1e-12,
                        {"first": shuffle_null["mrr"], "rebuilt": null2["mrr"]})

    falsifiers = [
        Falsifier("F2_the_leak_does_not_survive_the_null_subtraction",
                  refutes="that the leak inflated the LIFT and not merely both "
                          "numbers equally",
                  fires_when="|shuffle lift - leak-free lift| <= 0.005",
                  null_must_contain="both lifts and their difference"),
        Falsifier("F3_the_ranker_disagrees_with_itself_across_splits",
                  refutes="that the shuffle number is comparable to G49/G104",
                  fires_when=f"|pair-disjoint null - {PAIR_DISJOINT_NULL}| > {TOL}",
                  null_must_contain="the recomputed value and the published one"),
    ]
    falsifiers[0].observe(abs(leak_as_lift) <= 0.005,
                          {"shuffle_lift": round(shuffle_lift, 6),
                           "leakfree_lift": round(leakfree_lift, 6),
                           "leak_as_lift": round(leak_as_lift, 6)})
    falsifiers[1].observe(abs(pd_null["mrr"] - PAIR_DISJOINT_NULL) > TOL,
                          {"recomputed": round(pd_null["mrr"], 6),
                           "published": PAIR_DISJOINT_NULL})

    res = {"spike": "G106",
           "shuffle_split": {
               "null": {k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in shuffle_null.items()},
               "n_train": len(train), "n_dev": len(_dev), "n_test": len(test),
               "same_pair_leaked_test_triples": leak,
               "same_pair_leak_rate": round(leak / len(test), 4),
               "system_mrr_withdrawn_headline": SHUFFLE_SYSTEM,
               "lift": round(shuffle_lift, 6)},
           "pair_disjoint_split": {
               "null_recomputed_here": round(pd_null["mrr"], 6),
               "null_published": PAIR_DISJOINT_NULL,
               "system_mrr": LEAK_FREE_SYSTEM,
               "lift": round(leakfree_lift, 6)},
           "the_leak_expressed_as_lift": round(leak_as_lift, 6),
           "note": "the shuffle number is NOT gatable; the null is measured to "
                   "size the leak in the units the loop reports, not to license "
                   "0.2648",
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "shuffle_null.json"), "w"),
              indent=1, sort_keys=True)

    print(f"\nshuffle   {SHUFFLE_SYSTEM:.4f} - {shuffle_null['mrr']:.4f} = "
          f"{shuffle_lift:+.4f}")
    print(f"leak-free {LEAK_FREE_SYSTEM:.4f} - {PAIR_DISJOINT_NULL:.4f} = "
          f"{leakfree_lift:+.4f}")
    print(f"the leak, as lift: {leak_as_lift:+.4f}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G34, G48, G104],
        artifacts=[os.path.join(HERE, "shuffle_null.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the shuffle null makes the leaky lift indistinguishable from "
                  "the leak-free one, OR the ranker fails to reproduce the "
                  "pair-disjoint null in this same process",
        note="G106: the null on the 70/15/15 shuffle, and the leak re-expressed "
             "as lift rather than as a raw MRR gap.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
