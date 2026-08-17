#!/usr/bin/env python3
"""G25 — is `no_death +5059` a real tradeoff or a rent calibration artefact?

G24 reported that removing the finite economy gained MORE test coverage than the
full system (+5059 vs +2842) and dismissed it as a trade: 5.4x worse precision,
dominated on the (predictions, correct) plane. That is correct as far as it goes
and it does not answer the question, because of one thing G24's code says and its
RESULT.md does not:

    THE no_death ARM HAS NO SELECTION IN IT AT ALL.

With `death` off, nothing is ever removed, MAX_POP never applies, and parents are
drawn `rng.choice(pop)` -- uniformly. Wages are still computed and still
accumulate into `imp`, but `imp` is read by exactly one statement, the one death
uses. So no_death is not "the full system minus carrying capacity". It is
propose-and-keep-everything. Its +5059 was earned with zero differential
fitness, which makes "death is what makes fitness differential" a claim measured
against a baseline that is not the full system with one part removed, but a
different algorithm.

That leaves two live explanations for the gap, with opposite consequences:

  (A) CALIBRATION.  Coverage is bought with population size, and population size
      is set by WAGE_POOL/RENT -- a number I picked. The full arm sits at ~110
      rules because 120/1.05 ~ 114, not because 110 is right. If a SELECTED
      population of the same size as no_death's 557 beats no_death, then the
      published operating point was under-populated and the +5059 says nothing
      about death; it says my carrying capacity was arbitrary.
  (B) TRADEOFF.  Selection cannot use the extra room: a selected 557 does no
      better than an unselected 557, so the coverage really is volume and death
      really is paying for precision with coverage.

The discriminator is a MATCHED-POPULATION comparison, which G24 never ran
because MAX_POP=200 made one impossible. Raising WAGE_POOL raises carrying
capacity while leaving the relative wage differences -- the selection -- intact.
So: sweep the capacity, and compare selected-N against unselected-N.

And one cell of G24's own 2x2 was missing. It has (death,abduct)=(on,on)=4144,
(on,off)=1359, (off,on)=6361, and never ran (off,off). Without it there is no
way to attribute the +5059 between "unlimited room" and "problem-directed
proposal", because no_death keeps every abducted rule ever proposed.

CONTROLS, each with the input that would make it fail:
  C1 REPRO      `full_base` must return G24's full arm exactly: pop 110, test
                solved 4144, precision 0.0355. FAILS if the arm-set refactor or
                the monkeypatched globals changed behaviour.
  C2 CAP        `full_cap2000` lifts MAX_POP 200 -> 2000 and changes nothing
                else. FAILS if population differs from `full_base` -- which
                would mean the cap, not the rent, was setting population size,
                and the whole capacity sweep below is aimed at the wrong knob.
  C3 A15        every arm that runs variation must still discover the planted
                rule. FAILS if a capacity setting kills it, and that arm is then
                reported unranked, per G24.
  C4 NULL       `nodeath_noabduct` is the unselected population WITHOUT
                problem-directed proposal. FAILS to support "coverage is just
                volume" if it lands near no_abduct's 1359 rather than near
                no_death's 6361.

Usage:  python3 sweep.py [name ...]     # default: all, skipping finished runs
Each config checkpoints to runs/<name>.json, so this is resumable and the
decisive configs are ordered first.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G24_population"))
import evo  # noqa: E402

RUNS = os.path.join(HERE, "runs")

# name, ablation set, WAGE_POOL, RENT, RENT_PRED, MAX_POP
# Ordered decisive-first: a run that dies halfway still answers the question.
CONFIGS = [
    # C1: must reproduce G24 exactly.
    ("full_base",         "uniform_parents",   120.0, 0.5, 0.05,  200),
    # C4 / the missing 2x2 cell: unselected AND unguided.
    ("nodeath_noabduct",  "no_death+no_abduct+uniform_parents", 120.0, 0.5, 0.05,  200),
    # C2: does the cap bind, or the rent?
    ("full_cap2000",      "uniform_parents",   120.0, 0.5, 0.05, 2000),
    # the capacity sweep: selection intact, carrying capacity raised ~5x so a
    # SELECTED population reaches no_death's size and can be compared to it.
    ("wage600",           "uniform_parents",   600.0, 0.5, 0.05, 2000),
    ("wage300",           "uniform_parents",   300.0, 0.5, 0.05, 2000),
    ("wage1200",          "uniform_parents",  1200.0, 0.5, 0.05, 2000),
    # the dial turned out SUBLINEAR: 10x the pool bought 2.1x the population,
    # because a rule only draws a wage if its confidence exceeds the adversary's
    # and the supply of such rules is finite. These two say whether that is
    # saturation or just a slow climb -- it decides whether a selected
    # population can be grown to no_death's 557 at all.
    ("wage2400",          "uniform_parents",  2400.0, 0.5, 0.05, 4000),
    ("wage4800",          "uniform_parents",  4800.0, 0.5, 0.05, 4000),
    # is the capacity gain (if any) abduction-driven at the larger capacity too?
    ("wage600_noabduct",  "no_abduct+uniform_parents", 600.0, 0.5, 0.05, 2000),
    # no_death re-run under this harness rather than cited from G24's json, so
    # every row on the plane comes from one process and one code state.
    ("nodeath",           "no_death+uniform_parents", 120.0, 0.5, 0.05,  200),
]


# The three points the headline rests on, repeated under two more run seeds.
# One seed per point makes a coverage DIFFERENCE uninterpretable, and this sweep
# is already visibly noisy: wage600 (4455) came out BELOW wage300 (4981) and
# wage2400 (5724) below wage1200 (5934), on a dial that should be monotone. So
# the gap-closing fraction gets an error bar or it does not get quoted.
REPEATS = [(base, s) for base in ("full_base", "wage1200", "nodeath")
           for s in (777, 31337)]


def one(name, arm, wage, rent, rent_pred, max_pop, data, seed=evo.RUN_SEED):
    train, p_dev, p_test, npred, planted = data
    evo.WAGE_POOL, evo.RENT, evo.RENT_PRED, evo.MAX_POP = \
        wage, rent, rent_pred, max_pop
    evo.RUN_SEED = seed
    print(f"CONFIG {name}  arm={arm} wage={wage} rent={rent}/{rent_pred} "
          f"max_pop={max_pop} seed={seed}", flush=True)
    hist, capped, pop = evo.run(arm, train, p_dev, p_test, npred, planted)
    rec = {"name": name, "arm": arm,
           "params": {"wage_pool": wage, "rent": rent, "rent_pred": rent_pred,
                      "max_pop": max_pop, "run_seed": seed, "rounds": evo.ROUNDS,
                      "offspring": evo.OFFSPRING, "pop_seed": evo.POP_SEED,
                      "min_pairs": evo.MIN_PAIRS, "max_pairs": evo.MAX_PAIRS,
                      "adv_tries": evo.ADV_TRIES},
           "hist": hist, "capped_evals": capped, "final_pop": len(pop)}
    json.dump(rec, open(os.path.join(RUNS, name + ".json"), "w"), indent=1)
    return rec


def main():
    os.makedirs(RUNS, exist_ok=True)
    byname = {c[0]: c for c in CONFIGS}
    jobs = [(c[0],) + c[1:] + (evo.RUN_SEED,) for c in CONFIGS]
    for base, s in REPEATS:
        c = byname[base]
        jobs.append((f"{base}_s{s}",) + c[1:] + (s,))
    want = sys.argv[1:] or [j[0] for j in jobs]
    todo = [j for j in jobs if j[0] in want
            and not os.path.exists(os.path.join(RUNS, j[0] + ".json"))]
    if todo:
        data = evo.dataset()
        for j in todo:
            one(*j[:6], data=data, seed=j[6])
            print(flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
