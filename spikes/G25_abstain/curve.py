#!/usr/bin/env python3
"""G25 — is 3.5% precision a limit of the evolved population, or of asking it
to answer everything?

G24 ended on an uncomfortable number. The evolved population reaches 4144
correct test triples at precision 0.0355; the un-evolved enumerated seed reaches
1127 at 0.2205. Six times more precise, from no evolution at all. I wrote that
the population "found recall, not truth", and left it there.

But that compares two systems at ONE operating point each, and the operating
point was never chosen -- it is just "assert everything any surviving rule
implies". A population can ABSTAIN. Withhold the predictions of rules that were
not confident on dev, and precision rises while coverage falls.

So the honest object is not a point, it is a CURVE, and the honest question is
whether the evolved population's curve lies above the seed's. Comparing two
systems at one arbitrary point each is how G15 got its headline.

    for each threshold t:
        the population asserts only predictions of rules with dev_conf >= t
        measure PRECISION and COVERAGE on test

THRESHOLD ON DEV, MEASURE ON TEST. Selecting the threshold on the set it is
scored against would be the same leak G22's three-way split exists to prevent:
the threshold is a parameter, and a parameter fitted on test makes the test
number meaningless.

WHAT WOULD FALSIFY "EVOLUTION HELPED". If the seed's curve lies above the
evolved population's anywhere the two overlap in coverage, then evolution bought
nothing that abstention could not buy more cheaply, and G24's coverage gain is
an artifact of a badly chosen operating point rather than a better population.
That is a real possible outcome of this script and it is the reason to run it.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G24_population"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G17_composition_redo"))
import evo as E  # noqa: E402
import redo as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
THRESHOLDS = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]


def curve(pop, idx, p_tr, p_dev, p_test, banned_heads=()):
    """Precision/coverage on TEST as a function of a dev-chosen threshold.

    `banned_heads` excludes the A15 planted predicate, and it MUST be excluded.
    The plant puts its conclusions in dev only (that is what makes it a
    held-out positive control), so the planted rule can never score on test --
    it contributes 568 predictions and 0 correct, by construction.

    Only the evolved arm ever discovers that rule, so leaving it in loads 568
    guaranteed-wrong assertions onto one side of the comparison. At threshold
    0.15 that is the difference between precision 0.2096 and 0.2418, which is
    the difference between losing to the seed and beating it.

    My own positive control was contaminating the primary measurement. Caught
    because the t=0.50 row read "1 rule, 568 predictions, 0 correct" -- a rule
    that survives the strictest filter while getting nothing right is not a
    good rule, it is a rule being scored against the wrong set.
    """
    scored = []
    for r in pop:
        if r["head"] in banned_heads:
            continue
        s = E.score(idx, r["body"], r["head"], p_tr, p_dev)
        if s:
            scored.append((s["conf"], r["head"], s["cand"]))
    out = []
    for t in THRESHOLDS:
        preds, correct = set(), set()
        kept = 0
        for conf, head, cand in scored:
            if conf < t:
                continue
            kept += 1
            for ac in cand:
                preds.add((head, ac))
                if head in p_test.get(ac, ()):
                    correct.add((head, ac))
        out.append({"t": t, "rules": kept, "preds": len(preds),
                    "correct": len(correct),
                    "prec": len(correct) / len(preds) if preds else 0.0})
    return out


def main():
    nt, npred, nent, tri = R.load()
    idx_ = list(range(nt))
    random.Random(E.SEED).shuffle(idx_)
    a, b = int(nt * 0.70), int(nt * 0.85)
    train = [tri[i] for i in idx_[:a]]
    dev = [tri[i] for i in idx_[a:b]]
    test = [tri[i] for i in idx_[b:]]
    ents = sorted({x for _, s_, o in train for x in (s_, o)})
    planted, ptr, pdev = E.plant(npred, nent, ents=ents,
                                 rng=random.Random(4242))
    train += ptr
    dev += pdev
    p_dev, p_test = E.Idx(dev).pair, E.Idx(test).pair
    idx = E.Idx(train)
    p_tr = idx.pair

    res = {}
    for arm in ("full", "no_variation"):
        print(f"running arm {arm} ...")
        _h, _c, pop = E.run(arm, train, p_dev, p_test, npred, planted,
                            log=False)
        res[arm] = {"pop": len(pop),
                    "curve": curve(pop, idx, p_tr, p_dev, p_test,
                                   banned_heads={planted[2]})}
        print(f"  {len(pop)} rules survived\n")

    print(f"{'thresh':>7}{'':4}{'EVOLVED (full)':>34}{'':4}"
          f"{'SEED (no_variation)':>34}")
    print(f"{'':7}{'':4}{'rules':>8}{'preds':>10}{'corr':>7}{'prec':>9}{'':4}"
          f"{'rules':>8}{'preds':>10}{'corr':>7}{'prec':>9}")
    for i, t in enumerate(THRESHOLDS):
        f = res["full"]["curve"][i]
        s = res["no_variation"]["curve"][i]
        print(f"{t:>7.2f}{'':4}{f['rules']:>8}{f['preds']:>10}"
              f"{f['correct']:>7}{f['prec']:>9.4f}{'':4}"
              f"{s['rules']:>8}{s['preds']:>10}{s['correct']:>7}"
              f"{s['prec']:>9.4f}")

    # Domination: at matched PRECISION, who covers more? Interpolating is
    # unjustified with 9 points, so compare only where a seed point has an
    # evolved point at >= its precision, and ask which covers more there.
    print("\nAT MATCHED-OR-BETTER PRECISION, WHO COVERS MORE:")
    verdict_rows = []
    for s in res["no_variation"]["curve"]:
        if s["preds"] == 0:
            continue
        better = [f for f in res["full"]["curve"]
                  if f["prec"] >= s["prec"] and f["preds"] > 0]
        if not better:
            print(f"   seed prec {s['prec']:.4f} (corr {s['correct']}): "
                  f"evolved NEVER reaches this precision")
            verdict_rows.append(("seed", s["prec"]))
            continue
        best = max(better, key=lambda f: f["correct"])
        win = "EVOLVED" if best["correct"] > s["correct"] else "SEED"
        verdict_rows.append((win, s["prec"]))
        print(f"   seed prec {s['prec']:.4f} corr {s['correct']:5d}   vs   "
              f"evolved prec {best['prec']:.4f} corr {best['correct']:5d}"
              f"   -> {win}")

    wins = sum(1 for w, _ in verdict_rows if w == "EVOLVED")
    tot = len(verdict_rows)
    if tot and wins == tot:
        v = ("EVOLVED DOMINATES — at every precision the seed reaches, the "
             "evolved population covers more")
    elif wins == 0:
        v = ("SEED DOMINATES — evolution bought nothing abstention could not "
             "buy more cheaply; G24's coverage gain was an operating-point "
             "artifact")
    else:
        v = (f"MIXED — evolved wins {wins}/{tot} of the seed's precision "
             f"levels; neither curve dominates")
    print(f"\nVERDICT: {v}")

    json.dump({"thresholds": THRESHOLDS, "arms": res, "verdict": v,
               "conditions": {"data": "real:FB15k-237+planted",
                              "split": "70/15/15", "split_seed": E.SEED,
                              "threshold_chosen_on": "dev",
                              "excluded": "A15 planted head predicate — its conclusions are dev-only by construction and cannot score on test",
                              "measured_on": "test",
                              "platforms": [["macos", "aarch64"]],
                              "concurrency": "single-process",
                              "swept": {"threshold": THRESHOLDS}},
               "cites": ["G24_population", "G17_composition_redo"]},
              open(os.path.join(HERE, "curve.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
