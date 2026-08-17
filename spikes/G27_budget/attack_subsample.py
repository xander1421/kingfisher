#!/usr/bin/env python3
"""ATTACK on G27's own headline: is the population-matched dominance just budget?

G27 reports that a SELECTED population of 568 dominates an UNSELECTED one of 557
on the (predictions, correct) plane, 3/3 seeds. The stated confound is that the
selected arm attempted 4x the proposals to reach that size -- 2400 against 600 --
because selection discards and no_death does not. A skeptic's reading of the whole
result is therefore: of course it won, it did four times the work.

That confound is REMOVABLE, and G27 shipped without removing it.

  nd_r15_o160  is no_death at budget 2400: 2031 rules, all kept.
  sel_r15_o160 is selection at budget 2400:  568 rules, chosen.

Both saw the SAME 2400 proposals. So draw 568 of no_death's 2031 rules at random
and score that. Now budget matches AND population matches, and the only remaining
difference is WHICH 568 -- selection versus a coin. That is the comparison the
claim "selection uses the extra room" actually needs, and it is the one no cell of
G24, G25 or G27 contains.

  If selected's point beats the whole random distribution -> the 4x-proposals
  confound is answered and the dominance is about selection.
  If selected's point sits inside it -> G27's headline is a budget artefact and
  the population-matched column has to be withdrawn.

The null here can contain the effect (A20): a random 568 of no_death's rules is
drawn from a population that ALREADY contains every rule selection kept plus
1463 more, so if the kept ones are not special the draw reproduces them by
chance. 20 draws, seeds recorded.

Usage: python3 attack_subsample.py [n_draws]
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G24_population"))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import evo  # noqa: E402
import provenance as P  # noqa: E402

TARGET = 568          # sel_r15_o160's standing population at seed 1234
SEL_POINT = (809066, 6875)   # its (predictions, correct) on test
DRAWS = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def main():
    train, p_dev, p_test, npred, planted = evo.dataset()
    evo.ROUNDS, evo.OFFSPRING = 15, 160
    evo.WAGE_POOL, evo.RENT, evo.RENT_PRED, evo.MAX_POP = 120.0, 0.5, 0.05, 200
    evo.RUN_SEED = 1234
    print(f"re-running nd_r15_o160 to recover its final population "
          f"(budget {evo.ROUNDS * evo.OFFSPRING})", flush=True)
    hist, _capped, pop = evo.run("no_death+uniform_parents", train, p_dev,
                                 p_test, npred, planted, log=False)
    print(f"population {len(pop)}, published metrics "
          f"{hist[-1]['test']['predicted']}/{hist[-1]['test']['solved']}",
          flush=True)

    # Re-score the final population once. `ev` is not returned by run(), and the
    # subsample metrics need each rule's candidate pair set, so this recomputes
    # exactly what the last round computed -- against TRAIN structure, excluding
    # train facts, scored on TEST. Test is read only here, after all selection
    # in the run has already happened.
    idx = evo.Idx(train)
    ev = {}
    for r in pop:
        ev[r["id"]] = evo.score(idx, r["body"], r["head"], idx.pair, p_test)
    whole = evo.population_metrics(pop, ev, p_test)
    print(f"recomputed whole-population point "
          f"{whole['predicted']}/{whole['solved']}", flush=True)

    draws = []
    for k in range(DRAWS):
        rng = random.Random(9000 + k)
        sub = rng.sample(pop, TARGET)
        m = evo.population_metrics(sub, ev, p_test)
        draws.append({"seed": 9000 + k, "preds": m["predicted"],
                      "correct": m["solved"], "prec": m["precision"]})
        print(f"  draw {k:>2} seed {9000 + k}: {m['solved']:>5} correct / "
              f"{m['predicted']:>8} preds  prec {m['precision']:.4f}", flush=True)

    sp, sc = SEL_POINT
    dominated = [d for d in draws if sc > d["correct"] and sp <= d["preds"]]
    beats_correct = [d for d in draws if sc > d["correct"]]
    fewer_preds = [d for d in draws if sp <= d["preds"]]
    print(f"\nselected 568: {sc} correct / {sp} preds")
    print(f"random 568 of no_death's {len(pop)}, {DRAWS} draws: correct "
          f"{min(d['correct'] for d in draws)}-{max(d['correct'] for d in draws)}, "
          f"preds {min(d['preds'] for d in draws)}-{max(d['preds'] for d in draws)}")
    print(f"selected DOMINATES {len(dominated)}/{DRAWS} draws "
          f"(more correct in {len(beats_correct)}, no more predictions in "
          f"{len(fewer_preds)})")

    if len(dominated) == DRAWS:
        v = (f"CONFOUND ANSWERED — at matched budget AND matched population, "
             f"selection's 568 dominates {DRAWS}/{DRAWS} random draws of 568 "
             f"from no_death's own {len(pop)} rules. The population-matched "
             f"dominance in G27 is about which rules are kept, not about the "
             f"4x proposals.")
    elif not dominated:
        v = (f"G27'S HEADLINE IS A BUDGET ARTEFACT — selection's 568 dominates "
             f"0/{DRAWS} random draws of the same size from the same budget. "
             f"The population-matched column must be withdrawn.")
    else:
        v = (f"PARTIAL — selection dominates {len(dominated)}/{DRAWS} random "
             f"draws. The dominance is real but not robust to which 568 the "
             f"coin picks, so it is weaker than G27 states.")
    print(f"\nVERDICT: {v}")

    c = P.Control("C8_random_subsample_null",
                  "removes the 4x-proposals confound: same budget, same "
                  "population size, only the choice of which rules differs",
                  null_must_contain="a random 568 that matches or beats "
                  "selection's 568 -- it is drawn from a superset containing "
                  "every rule selection kept plus 1463 more",
                  can_fail_because="if the kept rules are not special the draws "
                  "reproduce them by chance and selection's point lands inside "
                  "the distribution, which withdraws G27's population-matched "
                  "column")
    c.observe(len(dominated) == DRAWS,
              {"selected": {"preds": sp, "correct": sc},
               "whole_nodeath": {"preds": whole["predicted"],
                                 "correct": whole["solved"],
                                 "pop": len(pop)},
               "draws": draws})
    json.dump({"verdict": v, "selected": {"preds": sp, "correct": sc},
               "nodeath_pop": len(pop), "draws": draws,
               "conditions": {"data": "real:FB15k-237+planted",
                              "split": "70/15/15", "split_seed": "0xC0FFEE",
                              "run_seed": 1234, "budget": 2400,
                              "draw_seeds": [d["seed"] for d in draws],
                              "platforms": [["macos", "aarch64"]]},
               "cites": ["G27_budget", "G25_carrying_capacity"]},
              open(os.path.join(HERE, "attack_subsample.json"), "w"), indent=1)
    ok, _ = P.record(HERE, deps=[os.path.join(HERE, "..", "G24_population"),
                                os.path.join(HERE, "..", "G17_composition_redo")],
                     artifacts=[os.path.join(HERE, "attack_subsample.py"),
                                os.path.join(HERE, "attack_subsample.json")],
                     controls=[c], allow_dirty=True,
                     note="G27 ATTACK: random-subsample null against the "
                          "population-matched dominance")
    print(f"provenance ok={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
