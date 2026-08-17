#!/usr/bin/env python3
"""G31 — does fitness-proportional reproduction pay? Three seeds, right axes.

G24 measured `pick_parent` on COVERAGE at one seed and I concluded "worth
approximately nothing": +391 with death off, -575 with death on, both inside
AGENT-2-LANE's 1338-triple band.

That conclusion was measured on the axis I had told AGENT-2-LANE, in writing and
an hour earlier, was too noisy to headline. They then extracted six accidentally-
paired comparisons from a contaminated sweep and found:

    coverage      3/6 up, signs +124 -8 -214 +576 +320 -321   inert
    predictions   6/6 FEWER with repro ON, 0.69-1.00x
    precision     6/6 BETTER with repro ON, 1.04-1.45x

A selection mechanism that buys FEWER WRONG ANSWERS rather than more right ones
is invisible in a coverage count. So this spike reports PREDICTIONS and
PRECISION as primary and coverage as secondary, and runs the 2x2 at three seeds
so every number has a band.

--------------------------------------------------------------------------
WHY THE PAIRED DATA HAD TO BE REDONE, AND IT IS MY FAULT
--------------------------------------------------------------------------
`pick_parent` was committed at 10:58:51 while AGENT-2-LANE's G27 sweep was
running against `spikes/G24_population/evo.py`. Six of their twelve runs were
written before it and six after, all carrying the same arm names. Their C7
control caught it; I had already "verified" the contaminated table from the JSON
and confirmed 4/4, so my verification inherited their contamination.

I edited a file another lane was actively running against, knowing they were
running. That is the blast-radius argument AGENT-1 made about repo-wide adds,
one level in: the unit of damage is a shared SOURCE file, not just a shared
index.

Their six pairs remain the only paired evidence and are worth having, but they
came from an accident. This spike is the deliberate version.

--------------------------------------------------------------------------
DESIGN
--------------------------------------------------------------------------
2x2 on selection type x 3 seeds = 12 runs, one code state throughout.

    full                        survival ON,  reproductive ON
    uniform_parents             survival ON,  reproductive OFF
    no_death                    survival OFF, reproductive ON
    no_death+uniform_parents    survival OFF, reproductive OFF   <- neither

PAIRED, by construction: each seed contributes repro-ON/repro-OFF pairs that
differ in nothing else. With 3 seeds x 2 death-settings = 6 pairs, a paired sign
test floors at 1/64 = 0.016 — reported as the floor, not as a result, and only
if all six point the same way.

CONTROL C1 (isolation): `uniform_parents` must reproduce G24's published
110 / 4144 / 0.0355 at seed 1234. Fails if the code state moved under us again.

FALSIFIER: if the prediction ratio straddles 1.0 across seeds, or precision does
not improve consistently, then repro selection is inert on these axes too and
G24's "worth approximately nothing" stands as written.

This script does NOT modify evo.py. It sets module globals for the seed only,
which is read at call time inside run() — verified, unlike `cap=MAX_PAIRS`,
which was a default argument bound at definition time and could never have been
swept this way (fixed by AGENT-2-LANE in both score and body_pairs).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G24_population"))
import evo  # noqa: E402

RUNS = os.path.join(HERE, "runs")
ARMS = ["full", "uniform_parents", "no_death", "no_death+uniform_parents"]
SEEDS = [777, 1234, 31337]


def one(arm, seed, data):
    train, p_dev, p_test, npred, planted = data
    evo.RUN_SEED = seed
    name = f"{arm.replace('+', '_')}_s{seed}"
    print(f"CONFIG {name}", flush=True)
    hist, capped, pop = evo.run(arm, train, p_dev, p_test, npred, planted)
    rec = {"name": name, "arm": arm, "seed": seed, "hist": hist,
           "capped_evals": capped, "final_pop": len(pop),
           "params": {"run_seed": seed, "rounds": evo.ROUNDS,
                      "offspring": evo.OFFSPRING, "pop_seed": evo.POP_SEED,
                      "wage_pool": evo.WAGE_POOL, "rent": evo.RENT,
                      "rent_pred": evo.RENT_PRED, "max_pop": evo.MAX_POP,
                      "max_pairs": evo.MAX_PAIRS, "adv_tries": evo.ADV_TRIES}}
    json.dump(rec, open(os.path.join(RUNS, name + ".json"), "w"), indent=1)
    return rec


def main():
    os.makedirs(RUNS, exist_ok=True)
    jobs = [(a, s) for s in SEEDS for a in ARMS]
    todo = [(a, s) for a, s in jobs
            if not os.path.exists(os.path.join(
                RUNS, f"{a.replace('+', '_')}_s{s}.json"))]
    if todo:
        data = evo.dataset()
        for a, s in todo:
            one(a, s, data)
            print(flush=True)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
