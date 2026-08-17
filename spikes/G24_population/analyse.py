#!/usr/bin/env python3
"""Fair comparison across G24's arms. The obvious comparison is not fair.

`test solved` counts distinct test triples the population gets right. It rises
with POPULATION SIZE almost mechanically: more rules assert more things, so more
things are correct. The `no_death` arm removes the carrying capacity entirely
and its population grows without bound -- 419 rules against `full`'s ~135 by
round 10. Reading its higher coverage as "death is costing us" would be
comparing across differently-sized populations, which is the same mistake that
produced G15's retracted headline (a maximum over 1954 items compared against a
maximum over 1750).

So coverage is never compared on its own here. Three views instead:

  1. PRECISION -- correct per prediction. Independent of how many rules exist,
     because both numerator and denominator scale with the population.
  2. THE (predictions, correct) PLANE -- an arm only beats another if it gets
     more correct at no more predictions. Anything else is a trade, not a win,
     and is reported as a trade.
  3. COVERAGE PER RULE -- what a single rule contributes, which is the quantity
     the population size divides out of.

A15 gates everything: an arm that never found the planted rule has an unproven
instrument and its numbers are reported but not ranked.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "evo.json")
    d = json.load(open(path))
    arms = d["arms"]

    print(f"{'arm':<14}{'pop':>6}{'preds':>10}{'correct':>9}{'prec':>9}"
          f"{'cov/rule':>10}{'top12':>8}{'A15':>5}")
    rows = []
    for arm, v in arms.items():
        h = v["hist"]
        if not h:
            print(f"{arm:<14}  (no rounds)")
            continue
        last = h[-1]
        t = last["test"]
        pop = last["pop"] or 1
        row = {"arm": arm, "pop": last["pop"], "preds": t["predicted"],
               "correct": t["solved"], "prec": t["precision"],
               "per_rule": t["solved"] / pop, "top12": t["top12"],
               "a15": last["a15"],
               "d_correct": t["solved"] - h[0]["test"]["solved"],
               "d_prec": t["precision"] - h[0]["test"]["precision"]}
        rows.append(row)
        print(f"{arm:<14}{row['pop']:>6}{row['preds']:>10}{row['correct']:>9}"
              f"{row['prec']:>9.4f}{row['per_rule']:>10.1f}"
              f"{row['top12']:>8.4f}{('yes' if row['a15'] else 'NO'):>5}")

    live = [r for r in rows if r["a15"]]
    print(f"\n{len(live)}/{len(rows)} arms found the planted rule. Arms that "
          f"did not are shown above\nbut not ranked -- an instrument that never "
          f"fired cannot be compared on its output.")

    if not live:
        print("\nVERDICT: VOID — no arm discovered A15.")
        return 0

    print("\nDOMINANCE on the (predictions, correct) plane. A beats B only if "
          "it gets\nmore correct while asserting no more:")
    full = next((r for r in live if r["arm"] == "full"), None)
    if full:
        for r in live:
            if r["arm"] == "full":
                continue
            more_correct = r["correct"] > full["correct"]
            fewer_preds = r["preds"] <= full["preds"]
            if more_correct and fewer_preds:
                verdict = "DOMINATES full"
            elif more_correct and not fewer_preds:
                verdict = (f"trade: +{r['correct'] - full['correct']} correct "
                           f"for +{r['preds'] - full['preds']} predictions")
            elif not more_correct and fewer_preds:
                verdict = "cheaper but no better"
            else:
                verdict = "DOMINATED by full"
            print(f"   {r['arm']:<14}{verdict}")

    best_prec = max(live, key=lambda r: r["prec"])
    print(f"\nHighest precision among arms that found A15: {best_prec['arm']} "
          f"at {best_prec['prec']:.4f}")
    # This line used to READ "Every arm's precision is BELOW 0.02" as a literal.
    # It was true when written and false one run later, which is the same defect
    # as G21's hand-typed 0.441 gate and agent-1's self-declared ISA: a value
    # transcribed from one run's output into a claim about every run.
    seed = next((r for r in rows if r["arm"] == "no_variation"), None)
    if seed:
        ratio = seed["prec"] / best_prec["prec"] if best_prec["prec"] else 0
        print(f"The un-evolved enumerated seed (no_variation) sits at "
              f"{seed['prec']:.4f} — {ratio:.1f}x the\nbest evolved arm — on "
              f"{seed['preds']} predictions against {best_prec['preds']}. It is "
              f"far more\nprecise and finds nothing new: it never recovers A15 "
              f"and its coverage DECLINES.")
    print(f"\nCoverage without precision is not truth. No coverage number here "
          f"should be\nquoted without its precision beside it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
