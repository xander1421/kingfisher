#!/usr/bin/env python3
"""G27 — can a SELECTED population reach no_death's size, and which matching is
even attainable?

G25 left exactly one hole. It wanted to compare a selected population of 557
rules against no_death's unselected 557 and could not build one: 40x the wage
pool bought 2.17x the population and saturated at ~239. The reason matters —
a rule draws a wage only if its confidence exceeds the co-evolving adversary's,
so the ceiling is the SUPPLY of adversary-beating rules, and money cannot
manufacture more of them.

Supply is not a constant. It depends on how many proposals are attempted, which
is ROUNDS x OFFSPRING and was fixed at 15 x 40 = 600 for the whole G-series. So
this spike turns the budget rather than the price.

--------------------------------------------------------------------------
THE THING TO SEE BEFORE READING ANY NUMBER HERE
--------------------------------------------------------------------------
no_death's population IS its proposal budget. Nothing is ever removed, so its
standing population equals every non-degenerate proposal it has ever made. A
selected population therefore CANNOT match it at equal budget by construction —
selection's whole function is to keep fewer than it was handed.

That makes the two matchings mutually exclusive, and G25 quietly wanted both:

  BUDGET-MATCHED      same ROUNDS x OFFSPRING both arms. Populations differ
                      (110 vs 557 at the published point). This is what G24 and
                      G25 actually ran, and the fair comparison of the two
                      ALGORITHMS.
  POPULATION-MATCHED  same standing population. Requires giving the selected arm
                      a LARGER budget, because it discards. This is the fair
                      comparison of the two POPULATIONS, and the confound is
                      stated rather than removed: the selected arm attempted more
                      variation to get there.

Neither is the "correct" one. Reporting only one of them is how "removing the
finite economy gains coverage" survived two spikes. Both get computed here, and
where they disagree that disagreement is the result.

  budget grid: ROUNDS x OFFSPRING at WAGE_POOL=1200 (G25's best selected point)
  no_death is run on the same grid where affordable, so the budget-matched
  comparison exists at more than one budget instead of only at 15x40.

CONTROLS, with the input that would make each fail:
  C5 SATURATION  the selected population must be measured against its own
                 proposal budget, not just reported. FAILS to support "supply is
                 the ceiling" if the population stays at ~239 while the budget
                 rises 6x -- that would mean the ceiling is something else and
                 G25's stated reason for saturation is wrong.
  C6 A15         every ranked (abduction-on) arm must still find the plant.
  C1' REPRO      the 15x40 wage1200 cell must reproduce G25's runs/wage1200.json
                 exactly, since it is the same config under the same seed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G25_carrying_capacity"))
sys.path.insert(0, os.path.join(HERE, "..", "G24_population"))
import evo      # noqa: E402
import sweep as G25   # noqa: E402  reused, NOT edited: G25's sweep.py digest is
                      # recorded in its provenance.json, so a shipped artifact
                      # stays byte-identical and this spike still gets one runner.

RUNS = os.path.join(HERE, "runs")

# name, arm, wage, rent, rent_pred, max_pop, rounds, offspring
# Ordered so the decisive cells land first: the budget that might reach 557
# selected, and the no_death point it would be compared against.
CONFIGS = [
    # C1' the repro cell: identical to G25's wage1200 under the same seed.
    ("sel_r15_o40",    "full",     1200.0, 0.5, 0.05, 4000, 15,  40),
    # more proposals per round -- 4x the supply at the same number of rounds
    ("sel_r15_o160",   "full",     1200.0, 0.5, 0.05, 4000, 15, 160),
    # more rounds -- same supply per round, more chances to accumulate survivors
    ("sel_r45_o40",    "full",     1200.0, 0.5, 0.05, 4000, 45,  40),
    ("sel_r30_o40",    "full",     1200.0, 0.5, 0.05, 4000, 30,  40),
    # both, if either alone falls short of 557
    ("sel_r45_o160",   "full",     1200.0, 0.5, 0.05, 4000, 45, 160),
    # no_death on the same budgets, for the budget-matched comparison. Its
    # population is its budget, so these are also the population reference
    # points. r45_o160 is deliberately absent: pop would be ~7000 and the body
    # walks are superlinear in population, which buys nothing the cheaper cells
    # do not already show.
    ("nd_r15_o40",     "no_death",  120.0, 0.5, 0.05,  200, 15,  40),
    ("nd_r30_o40",     "no_death",  120.0, 0.5, 0.05,  200, 30,  40),
    ("nd_r15_o160",    "no_death",  120.0, 0.5, 0.05,  200, 15, 160),
]


def main():
    os.makedirs(RUNS, exist_ok=True)
    want = sys.argv[1:] or [c[0] for c in CONFIGS]
    todo = [c for c in CONFIGS if c[0] in want
            and not os.path.exists(os.path.join(RUNS, c[0] + ".json"))]
    if not todo:
        return 0
    data = evo.dataset()
    G25.RUNS = RUNS          # checkpoint into THIS spike's runs/
    for name, arm, wage, rent, rp, mp, rounds, offspring in todo:
        evo.ROUNDS, evo.OFFSPRING = rounds, offspring
        print(f"BUDGET rounds={rounds} offspring={offspring} "
              f"= {rounds * offspring} proposals", flush=True)
        G25.one(name, arm, wage, rent, rp, mp, data=data, seed=evo.RUN_SEED)
        print(flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
