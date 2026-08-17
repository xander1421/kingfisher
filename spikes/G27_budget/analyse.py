#!/usr/bin/env python3
"""Both matchings, reported side by side, including where they disagree.

G25 wanted a population-matched comparison and could not build one. The reason it
could not is structural, not a shortfall of effort: no_death's population IS its
proposal budget, because nothing is ever removed. So at equal budget a selected
population is necessarily smaller, and to make it equal in size you must hand it
a larger budget. There is no setting where both are matched.

  BUDGET-MATCHED      the fair comparison of two ALGORITHMS given equal resources
  POPULATION-MATCHED  the fair comparison of two POPULATIONS of equal size, and
                      the selected one attempted more variation to get there

Reporting one and calling it the answer is what let "removing the finite economy
gains coverage" stand through two spikes. Both are computed. If they disagree,
that disagreement is the finding and the verdict says so.
"""

import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G25_carrying_capacity"))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import analyse as G25A   # noqa: E402  row()/dominates(), so the plane test and
                         # the row schema are literally the same code as G25's
import provenance as P    # noqa: E402

RUNS = os.path.join(HERE, "runs")
G25RUNS = os.path.join(HERE, "..", "G25_carrying_capacity", "runs")
MATCH_TOL = 0.25


def load(d):
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            rec = json.load(open(os.path.join(d, f)))
            if rec["hist"]:
                out[rec["name"]] = rec
    return out


def main():
    recs = load(RUNS)
    if not recs:
        print("no runs yet")
        return 1
    rows = {}
    for n, rec in recs.items():
        r = G25A.row(rec)
        r["rounds"] = rec["params"]["rounds"]
        r["offspring"] = rec["params"]["offspring"]
        r["budget"] = r["rounds"] * r["offspring"]
        r["sel"] = "no_death" not in r["arm"]
        rows[n] = r

    print(f"{'config':<16}{'rounds':>7}{'offs':>6}{'budget':>8}{'pop':>6}"
          f"{'preds':>10}{'correct':>9}{'prec':>9}{'cov/rule':>10}{'A15':>5}")
    for n, r in sorted(rows.items(), key=lambda kv: (not kv[1]["sel"],
                                                     kv[1]["budget"])):
        print(f"{n:<16}{r['rounds']:>7}{r['offspring']:>6}{r['budget']:>8}"
              f"{r['pop']:>6}{r['preds']:>10}{r['correct']:>9}{r['prec']:>9.4f}"
              f"{r['cov_per_rule']:>10.1f}{('yes' if r['a15'] else 'NO'):>5}")

    print("\nCONTROLS")
    # C1' the 15x40 cells must reproduce G25's runs under the same seed.
    g25 = load(G25RUNS)
    for mine, theirs in (("sel_r15_o40", "wage1200"), ("nd_r15_o40", "nodeath")):
        if mine in rows and theirs in g25:
            a, b = rows[mine], G25A.row(g25[theirs])
            ok = a["pop"] == b["pop"] and a["correct"] == b["correct"] \
                and a["preds"] == b["preds"]
            print(f"  C1' REPRO  {'PASS' if ok else 'FAIL'} — {mine} "
                  f"{a['pop']}/{a['preds']}/{a['correct']} vs G25 {theirs} "
                  f"{b['pop']}/{b['preds']}/{b['correct']}")
    # C5 does the selected population track the PROPOSAL BUDGET, as G25's stated
    # reason for saturation requires, or is it pinned near 239 regardless?
    sel = sorted((r for r in rows.values() if r["sel"]),
                 key=lambda r: r["budget"])
    if len(sel) >= 2:
        lo, hi = sel[0], sel[-1]
        fb = hi["budget"] / lo["budget"]
        fp = hi["pop"] / lo["pop"]
        moved = fp >= 1.5
        print(f"  C5 SUPPLY  {'PASS' if moved else 'FAIL'} — {fb:.1f}x the "
              f"proposal budget ({lo['budget']} -> {hi['budget']}) moved the "
              f"selected population {lo['pop']} -> {hi['pop']} ({fp:.2f}x). "
              + ("Supply of adversary-beating rules is the ceiling, as G25 said."
                 if moved else
                 "The population is NOT budget-limited, so G25's stated reason "
                 "for saturation is WRONG and the ceiling is something else."))
    bad = [n for n, r in rows.items() if not r["a15"]]
    print(f"  C6 A15     {'PASS' if not bad else 'FAIL'} — "
          + ("every arm found the plant" if not bad else f"missing in {bad}"))

    # ---- matching 1: equal budget
    print("\nBUDGET-MATCHED (same rounds x offspring; populations differ)")
    pairs = []
    for r in rows.values():
        if not r["sel"]:
            continue
        nd = next((x for x in rows.values() if not x["sel"]
                   and x["budget"] == r["budget"]
                   and x["rounds"] == r["rounds"]), None)
        if nd:
            pairs.append((r, nd))
    for r, nd in sorted(pairs, key=lambda p: p[0]["budget"]):
        tag = ("SELECTED DOMINATES" if G25A.dominates(r, nd)
               else "no_death dominates" if G25A.dominates(nd, r) else "trade")
        print(f"  budget {r['budget']:>5}: selected {r['correct']:>5}/"
              f"{r['preds']:>8} pop {r['pop']:>4} prec {r['prec']:.4f}   "
              f"no_death {nd['correct']:>5}/{nd['preds']:>8} pop {nd['pop']:>4} "
              f"prec {nd['prec']:.4f}   {tag}")

    # ---- matching 2: equal population
    print("\nPOPULATION-MATCHED (selected arm grown to a no_death population)")
    matches = []
    for nd in (x for x in rows.values() if not x["sel"]):
        for r in (x for x in rows.values() if x["sel"]):
            if abs(r["pop"] - nd["pop"]) / nd["pop"] <= MATCH_TOL:
                matches.append((r, nd))
    if not matches:
        big = max((r for r in rows.values() if r["sel"]), key=lambda r: r["pop"])
        small = min((r for r in rows.values() if not r["sel"]),
                    key=lambda r: r["pop"])
        print(f"  STILL UNREACHABLE — largest selected population {big['pop']} "
              f"({big['name']}, budget {big['budget']}) against the smallest "
              f"no_death {small['pop']} ({small['name']}). G25's hole is not "
              f"closed by the budget either.")
    for r, nd in sorted(matches, key=lambda p: p[0]["pop"]):
        tag = ("SELECTED DOMINATES" if G25A.dominates(r, nd)
               else "no_death dominates" if G25A.dominates(nd, r) else "trade")
        print(f"  pop {r['pop']} vs {nd['pop']}: selected {r['name']} "
              f"{r['correct']}/{r['preds']} prec {r['prec']:.4f} at budget "
              f"{r['budget']}   vs {nd['name']} {nd['correct']}/{nd['preds']} "
              f"prec {nd['prec']:.4f} at budget {nd['budget']}   {tag} "
              f"(selected attempted {r['budget'] / nd['budget']:.1f}x the "
              f"proposals — the stated confound)")

    # ---- verdict: both matchings, and their disagreement if any
    bm = [(r, nd, G25A.dominates(r, nd), G25A.dominates(nd, r))
          for r, nd in pairs]
    pm = [(r, nd, G25A.dominates(r, nd), G25A.dominates(nd, r))
          for r, nd in matches]
    sel_wins_b = [t for t in bm if t[2]]
    nd_wins_b = [t for t in bm if t[3]]
    sel_wins_p = [t for t in pm if t[2]]
    nd_wins_p = [t for t in pm if t[3]]
    parts = []
    if bm:
        parts.append(f"BUDGET-MATCHED: selected dominates in "
                     f"{len(sel_wins_b)}/{len(bm)} budgets, no_death in "
                     f"{len(nd_wins_b)}/{len(bm)}, rest trades")
    if pm:
        parts.append(f"POPULATION-MATCHED: selected dominates in "
                     f"{len(sel_wins_p)}/{len(pm)}, no_death in "
                     f"{len(nd_wins_p)}/{len(pm)}")
    else:
        parts.append("POPULATION-MATCHED: not attainable — no_death's population "
                     "is its budget, so the two matchings cannot both hold and "
                     "G25's intended comparison does not exist in this design")
    # The matchings disagree whenever one of them produces a winner and the other
    # does not, or they name opposite winners. G25 wanted the population-matched
    # answer and G24 reported the budget-matched one, so a disagreement here is
    # the reason both spikes could be honest and still conflict.
    b_winner = ("selected" if sel_wins_b else "no_death" if nd_wins_b else None)
    p_winner = ("selected" if sel_wins_p else "no_death" if nd_wins_p else None)
    if b_winner != p_winner:
        parts.append(f"THE MATCHINGS DISAGREE — budget-matched winner "
                     f"{b_winner or 'none, all trades'}, population-matched "
                     f"winner {p_winner or 'none, all trades'}. Which arm 'wins' "
                     f"is a choice of what to hold fixed, not a property of the "
                     f"algorithms, and G24 reported the budget-matched view while "
                     f"G25 was asking the population-matched question")
    v = ". ".join(parts) + "."
    print(f"\nVERDICT: {v}")

    ctl = []
    if len(sel) >= 2:
        c = P.Control("C5_supply_is_the_ceiling",
                      "G25 attributed saturation to the supply of "
                      "adversary-beating rules; if the selected population does "
                      "not track the proposal budget that reason is wrong",
                      null_must_contain="a selected population pinned near 239 "
                      "while the budget rises several-fold",
                      can_fail_because="the budget rises 12x here; a population "
                      "that stayed under 1.5x would fire it negative and would "
                      "mean G25's stated reason for saturation is wrong")
        c.observe(sel[-1]["pop"] / sel[0]["pop"] >= 1.5,
                  {r["name"]: [r["budget"], r["pop"], r["correct"], r["preds"]]
                   for r in sel})
        ctl.append(c)
    c = P.Control("C6_a15_plant", "an arm that never finds the planted rule has "
                  "an unproven instrument; every arm here runs abduction",
                  null_must_contain="a budget large enough to swamp the plant",
                  can_fail_because="G24's no_abduct arms miss the plant, so the "
                  "observation is attainable: any arm here failing to find it "
                  "would void that arm's row")
    c.observe(not bad, {n: r["a15"] for n, r in rows.items()}, f"missing {bad}")
    ctl.append(c)
    ok, _ = P.record(HERE, artifacts=[os.path.join(HERE, "sweep.py"),
                                      os.path.join(HERE, "analyse.py")]
                     + [os.path.join(RUNS, f) for f in sorted(os.listdir(RUNS))],
                     controls=ctl, allow_dirty=True,
                     no_deps_reason="pure Python inside the workspace; the "
                     "dependencies are G24's evo.py and G25's sweep.py/"
                     "analyse.py, reused unmodified and digested by G25's own "
                     "provenance.json",
                     note="G27: can a selected population reach no_death's "
                          "size, and which matching is attainable")
    json.dump({"rows": rows, "verdict": v,
               "conditions": {"data": "real:FB15k-237+planted",
                              "split": "70/15/15", "split_seed": "0xC0FFEE",
                              "run_seed": 1234,
                              "platforms": [["macos", "aarch64"]],
                              "swept": {"rounds": sorted({r["rounds"] for r in rows.values()}),
                                        "offspring": sorted({r["offspring"] for r in rows.values()}),
                                        "arm": sorted({r["arm"] for r in rows.values()})}},
               "cites": ["G24_population", "G25_carrying_capacity"]},
              open(os.path.join(HERE, "budget.json"), "w"), indent=1)
    print(f"provenance.json ok={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
