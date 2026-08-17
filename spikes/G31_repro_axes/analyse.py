#!/usr/bin/env python3
"""G31 — did fitness-proportional reproduction pay? Paired, three seeds.

PRE-REGISTERED FALSIFIER, written into sweep.py before any of these runs
existed and quoted here verbatim so it cannot be softened after the fact:

    if the prediction ratio straddles 1.0 across seeds, or precision does not
    improve consistently, repro selection is inert on these axes too and G24's
    verdict stands as written.

PRIMARY AXES ARE PREDICTIONS AND PRECISION, not coverage. G24 measured this
mechanism on coverage at one seed and called it "worth approximately nothing" —
on the axis I had told AGENT-2-LANE, an hour earlier, was too noisy to headline.
Their six accidentally-paired runs then showed coverage inert (3/6 up) while
predictions fell 6/6 and precision rose 6/6.

PAIRING: each (seed, death-setting) contributes one repro-ON/repro-OFF pair
differing in nothing else. 3 seeds x 2 death settings = 6 pairs. A paired sign
test over 6 pairs floors at 1/64 = 0.016, and that floor is only quoted if all
six point the same way — otherwise the count is reported as it falls.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = [777, 1234, 31337]
PAIRS = [("full", "uniform_parents", "death ON"),
         ("no_death", "no_death+uniform_parents", "death OFF")]


def load(arm, seed):
    p = os.path.join(HERE, "runs", f"{arm.replace('+', '_')}_s{seed}.json")
    if not os.path.exists(p):
        return None
    h = json.load(open(p))["hist"]
    if not h:
        return None
    last = h[-1]
    return {"pop": last["pop"], **last["test"]}


def main():
    print(f"{'pair':<12}{'seed':>7}{'repro':>7}{'pop':>6}{'correct':>9}"
          f"{'preds':>10}{'prec':>9}")
    rows = []
    for on, off, label in PAIRS:
        for s in SEEDS:
            a, b = load(on, s), load(off, s)
            if not a or not b:
                print(f"  MISSING {on}/{off} s{s}")
                continue
            rows.append((label, s, a, b))
            print(f"{label:<12}{s:>7}{'ON':>7}{a['pop']:>6}{a['solved']:>9}"
                  f"{a['predicted']:>10}{a['precision']:>9.4f}")
            print(f"{'':<12}{'':>7}{'OFF':>7}{b['pop']:>6}{b['solved']:>9}"
                  f"{b['predicted']:>10}{b['precision']:>9.4f}")

    if not rows:
        print("\nNO PAIRS LOADED — nothing was measured. Not a verdict.")
        return 2

    print(f"\n{'pair':<12}{'seed':>7}{'d(correct)':>12}{'pred ratio':>12}"
          f"{'prec ratio':>12}")
    dcov, rpred, rprec = [], [], []
    for label, s, a, b in rows:
        dc = a["solved"] - b["solved"]
        rp = a["predicted"] / b["predicted"] if b["predicted"] else float("nan")
        rq = a["precision"] / b["precision"] if b["precision"] else float("nan")
        dcov.append(dc)
        rpred.append(rp)
        rprec.append(rq)
        print(f"{label:<12}{s:>7}{dc:>+12}{rp:>12.3f}{rq:>12.3f}")

    n = len(rows)
    cov_up = sum(1 for d in dcov if d > 0)
    pred_down = sum(1 for r in rpred if r < 1.0)
    prec_up = sum(1 for r in rprec if r > 1.0)
    print(f"\nCOVERAGE     {cov_up}/{n} up     range {min(dcov):+d} to "
          f"{max(dcov):+d}")
    print(f"PREDICTIONS  {pred_down}/{n} FEWER with repro ON   "
          f"range {min(rpred):.3f} to {max(rpred):.3f}")
    print(f"PRECISION    {prec_up}/{n} BETTER with repro ON    "
          f"range {min(rprec):.3f} to {max(rprec):.3f}")

    straddles = min(rpred) < 1.0 < max(rpred)
    consistent = prec_up == n
    print(f"\nPRE-REGISTERED FALSIFIER")
    print(f"  prediction ratio straddles 1.0?  {straddles}")
    print(f"  precision improves consistently? {consistent}")
    if straddles or not consistent:
        v = ("FALSIFIER FIRES — repro selection is inert on these axes too. "
             "G24's 'worth approximately nothing' STANDS AS WRITTEN, and "
             "AGENT-2-LANE's C7b reading should be retracted rather than "
             "defended: this run is the designed instrument for that question "
             "and theirs was an accident of contamination with unequal budgets.")
    else:
        floor = 1 / (2 ** n)
        v = (f"FALSIFIER DOES NOT FIRE — predictions fall {pred_down}/{n} and "
             f"precision rises {prec_up}/{n}. Paired sign-test floor "
             f"1/2^{n} = {floor:.3f}, quoted AS THE FLOOR. G24's verdict is "
             f"withdrawn: the mechanism pays, on axes a coverage count cannot "
             f"see.")
    print(f"\nVERDICT: {v}")

    # AGENT-2-LANE's prediction, on the record before these numbers existed:
    # the effect should be LARGER on no_death arms, which have more population
    # to sort. Reported whether or not it holds, because they asked for it.
    by = {}
    for (label, s, a, b), rq in zip(rows, rprec):
        by.setdefault(label, []).append(rq)
    print("\nAGENT-2-LANE's pre-stated ordering (bigger effect where there is "
          "more\npopulation to sort):")
    for label, v_ in by.items():
        print(f"   {label:<10} mean precision ratio {sum(v_) / len(v_):.3f}")
    if len(by) == 2:
        (l1, v1), (l2, v2) = by.items()
        m1, m2 = sum(v1) / len(v1), sum(v2) / len(v2)
        off_bigger = (m1 > m2) == (l1 == "death OFF")
        print(f"   -> {'HOLDS' if off_bigger else 'DOES NOT HOLD'}: their "
              f"explanation for WHY it pays is "
              f"{'supported' if off_bigger else 'not supported'} even where "
              f"the direction is.")

    json.dump({"pairs": [{"pair": l, "seed": s, "on": a, "off": b}
                         for l, s, a, b in rows],
               "coverage_up": cov_up, "pred_down": pred_down,
               "prec_up": prec_up, "n_pairs": n, "verdict": v},
              open(os.path.join(HERE, "axes.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
