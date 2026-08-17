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
    allrows = {}
    for n, rec in recs.items():
        r = G25A.row(rec)
        r["rounds"] = rec["params"]["rounds"]
        r["offspring"] = rec["params"]["offspring"]
        r["budget"] = r["rounds"] * r["offspring"]
        r["sel"] = "no_death" not in r["arm"]
        r["base"], r["seed"] = G25A.split_name(n)
        allrows[n] = r
    # Repeats exist to test the headline, not to widen the grid: the matchings
    # below are read at the reference seed and then gated on the seed test.
    rows = {r["base"]: r for r in allrows.values() if r["seed"] == 1234}

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

    # ---- the headline pair under repeated seeds. 6875 vs 6361 is 514 correct
    # apart and G25 measured a 1338-triple seed band, so at one seed this
    # dominance is not distinguishable from variance. Per-seed dominance is the
    # test that matters: a dominance holding at every seed is a different claim
    # from one holding on average.
    HEAD = ("sel_r15_o160", "nd_r15_o40")
    seeds = sorted({r["seed"] for r in allrows.values()
                    if r["base"] in HEAD})
    per_seed, dom_seeds = {}, []
    print("\nHEADLINE PAIR UNDER REPEATED SEEDS "
          f"({HEAD[0]} vs {HEAD[1]}, correct/preds/pop)")
    for s in seeds:
        a = next((r for r in allrows.values()
                  if r["base"] == HEAD[0] and r["seed"] == s), None)
        b = next((r for r in allrows.values()
                  if r["base"] == HEAD[1] and r["seed"] == s), None)
        if not (a and b):
            continue
        d = G25A.dominates(a, b)
        nd_d = G25A.dominates(b, a)
        per_seed[s] = (a, b, d)
        if d:
            dom_seeds.append(s)
        tag = ("SELECTED DOMINATES" if d else
               "no_death dominates" if nd_d else "trade")
        print(f"  seed {s:<6} selected {a['correct']:>5}/{a['preds']:>8}/"
              f"{a['pop']:<4} prec {a['prec']:.4f}   no_death {b['correct']:>5}/"
              f"{b['preds']:>8}/{b['pop']:<4} prec {b['prec']:.4f}   {tag}")
    seed_gate = None
    if len(per_seed) >= 3:
        ca = [v[0]["correct"] for v in per_seed.values()]
        cb = [v[1]["correct"] for v in per_seed.values()]
        obs = sum(ca) / len(ca) - sum(cb) / len(cb)
        pool = ca + cb
        splits = list(itertools.combinations(range(len(pool)), len(ca)))
        ge = 0
        for c in splits:
            g1 = [pool[i] for i in c]
            g2 = [pool[i] for i in range(len(pool)) if i not in c]
            if sum(g1) / len(g1) - sum(g2) / len(g2) >= obs - 1e-9:
                ge += 1
        seed_gate = len(dom_seeds) == len(per_seed)
        print(f"  dominance holds at {len(dom_seeds)}/{len(per_seed)} seeds")
        # TWO AXES, and the weak one is the one I first reported. AGENT-2's
        # review: the coverage ranges are disjoint by TWENTY triples, which is
        # 1.5% of the 1338-triple band I measured on full_base and then used to
        # retire two of their G24 claims. Paired, the coverage differences are
        # +514 / +20 / +1031 -- one of three is indistinguishable from zero. The
        # prediction axis has no such problem, so it leads.
        pairs_c = [(v[0]["correct"] - v[1]["correct"]) for v in per_seed.values()]
        ratios = [v[0]["preds"] / v[1]["preds"] for v in per_seed.values()]
        print(f"  COVERAGE axis (weak): paired differences "
              f"{', '.join(f'{d:+d}' for d in pairs_c)}; ranges selected "
              f"{min(ca)}-{max(ca)} vs no_death {min(cb)}-{max(cb)}, "
              f"{'disjoint by ' + str(min(ca) - max(cb)) + ' triples' if min(ca) > max(cb) else 'OVERLAPPING'}"
              f" -- compare G25's 1338-triple seed band before leaning on this")
        print(f"  PREDICTION axis (robust): selected asserts "
              f"{', '.join(f'{r:.2f}x' for r in ratios)} of no_death's "
              f"predictions, {min(ratios):.2f}-{max(ratios):.2f}x, monotone in "
              f"direction across all {len(ratios)} seeds")
        # Two tests, both reported, because they differ in what they assume and
        # the one with the smaller floor is the one that throws away the pairing.
        same_dir = sum(1 for d in pairs_c if d > 0)
        sign_p = 2 ** -len(pairs_c)
        print(f"  paired sign test (respects the seed pairing): "
              f"{same_dir}/{len(pairs_c)} same direction, floor "
              f"p = 1/{2 ** len(pairs_c)} = {sign_p:.3f}")
        print(f"  unpaired permutation on coverage means: {obs:+.0f}, "
              f"p = {ge}/{len(splits)} = {ge / len(splits):.3f} -- smaller floor, "
              f"but it DISCARDS the pairing the design built in, so the sign "
              f"test is the honest one and 0.125 is the number to quote")

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
        gate = ("" if seed_gate is None else
                f", and it survives seed repetition ({len(dom_seeds)}/"
                f"{len(per_seed)} seeds) — carried by the PREDICTION axis "
                f"({min(ratios):.2f}-{max(ratios):.2f}x of no_death's assertions, "
                f"same direction every seed), not by the coverage axis, whose "
                f"ranges separate by only {min(ca) - max(cb)} triples against a "
                f"1338-triple seed band; paired sign test floor p={sign_p:.3f}"
                if seed_gate else
                f", but it does NOT survive seed repetition — dominance holds at "
                f"only {len(dom_seeds)}/{len(per_seed)} seeds, so it is inside "
                f"the noise band and is not a result")
        parts.append(f"POPULATION-MATCHED: selected dominates in "
                     f"{len(sel_wins_p)}/{len(pm)}, no_death in "
                     f"{len(nd_wins_p)}/{len(pm)}{gate}")
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
    # C7 REGENERATION EQUIVALENCE, same control G25 gained from AGENT-2's review.
    # This spike's first 8 runs were also produced before sweep.py grew REPEATS,
    # and all of them predate pick_parent, so the whole set was regenerated with
    # the arms renamed to the explicit uniform_parents token. Identical numbers
    # prove the renaming and the edit were behaviour-neutral; any config that
    # moved fails this and takes the matching RESULT.md row with it.
    # `pick_parent` (importance-weighted reproduction) was committed at
    # 4964ad7, 2026-08-17 10:58:51 +0100, MID-SWEEP. Runs written after it used
    # reproductive selection; runs before it did not. Classification is by that
    # external timestamp, NOT by which runs happen to differ -- and it agrees
    # with the observed reproduce/diverge split 12 of 12, which is what makes it
    # a check rather than a story fitted to the data.
    PICK_PARENT_TS = 1786960731
    mixed_dir = os.path.join(HERE, "runs_mixed_state")
    if os.path.isdir(mixed_dir):
        old_recs = load(mixed_dir)
        pre, post = [], []
        for n, oldrec in old_recs.items():
            if n not in recs:
                continue
            a, b = G25A.row(oldrec), G25A.row(recs[n])
            same = (a["pop"], a["preds"], a["correct"]) == \
                   (b["pop"], b["preds"], b["correct"])
            mt = os.path.getmtime(os.path.join(mixed_dir, n + ".json"))
            (post if mt > PICK_PARENT_TS else pre).append((n, a, b, same))
        # C7a: runs from BEFORE the mechanism landed must reproduce exactly.
        moved_pre = [n for n, a, b, same in pre if not same]
        c = P.Control("C7a_regeneration_equivalence",
                      "runs produced before pick_parent landed must reproduce "
                      "under the renamed uniform_parents arms; if they do not, "
                      "the numbers belong to code that did not produce them",
                      null_must_contain="a pre-mechanism config whose "
                      "(pop, preds, correct) moved",
                      can_fail_because="the arm renaming is a real intervention; "
                      "a wrong mapping moves these numbers, and 6 of the 12 runs "
                      "in this set DID move")
        c.observe(not moved_pre, {"compared": len(pre), "moved": moved_pre})
        ctl.append(c)
        print(f"\n  C7a REGEN  {'PASS' if not moved_pre else 'FAIL'} — "
              f"{len(pre)} pre-mechanism runs compared, {len(moved_pre)} moved")
        # C7b: runs from AFTER it landed are a paired repro-ON vs repro-OFF
        # measurement, at the same seed and budget. This is the band AGENT-2
        # wanted on pick_parent, and it fell out of my own contamination.
        if post:
            print(f"  C7b PICK_PARENT MEASURED — {len(post)} pairs, same seed and "
                  f"budget, differing only in reproductive selection:")
            dcorr, dpred, dprec = [], [], []
            for n, on, off, same in sorted(post):
                dcorr.append(on["correct"] - off["correct"])
                dpred.append(on["preds"] / off["preds"])
                dprec.append(on["prec"] / off["prec"])
                print(f"    {n:<22} ON {on['correct']:>5}/{on['preds']:>8} "
                      f"prec {on['prec']:.4f}   OFF {off['correct']:>5}/"
                      f"{off['preds']:>8} prec {off['prec']:.4f}   "
                      f"dcorrect {on['correct'] - off['correct']:+5d}  "
                      f"preds {on['preds'] / off['preds']:.2f}x  "
                      f"prec {on['prec'] / off['prec']:.2f}x")
            up = sum(1 for x in dcorr if x > 0)
            fewer = sum(1 for x in dpred if x < 1.0)
            better = sum(1 for x in dprec if x > 1.0)
            print(f"    coverage: {up}/{len(dcorr)} up, signs "
                  f"{', '.join(f'{x:+d}' for x in dcorr)} — no consistent "
                  f"direction, which matches AGENT-2's 'worth ~nothing' on this "
                  f"axis")
            print(f"    predictions: {fewer}/{len(dpred)} FEWER with it on "
                  f"({min(dpred):.2f}-{max(dpred):.2f}x); precision "
                  f"{better}/{len(dprec)} BETTER ({min(dprec):.2f}-"
                  f"{max(dprec):.2f}x) — sign test floor "
                  f"p = 1/{2 ** len(dpred)} = {2 ** -len(dpred):.4f}")
            c = P.Control("C7b_pick_parent_effect",
                          "the contaminated runs are a controlled repro-ON vs "
                          "repro-OFF comparison; reporting the contamination "
                          "without measuring it wastes the only paired data "
                          "either lane has on the mechanism",
                          null_must_contain="pairs with no consistent direction "
                          "on any axis, which is what 'worth nothing' predicts",
                          can_fail_because="if the prediction ratios straddled "
                          "1.0 the mechanism would be measured as inert; they do "
                          "not, and the coverage axis DOES straddle zero")
            c.observe(fewer == len(dpred),
                      {"d_correct": dcorr, "preds_ratio": dpred,
                       "prec_ratio": dprec,
                       "pairs": [n for n, _a, _b, _s in sorted(post)]})
            ctl.append(c)

    # RECORD LAST, after budget.json is written: G25's record was digesting its
    # own summary artifact one invocation stale, and the repaired A24 check
    # caught it. deps are the external source trees; this spike's own dir cannot
    # be a dep of itself because its newest file is its own run log.
    ok, _ = P.record(HERE, deps=[os.path.join(HERE, "..", "G24_population"),
                                 os.path.join(HERE, "..", "G25_carrying_capacity"),
                                 os.path.join(HERE, "..", "G17_composition_redo")],
                     artifacts=[os.path.join(HERE, "sweep.py"),
                                      os.path.join(HERE, "analyse.py")]
                     + [os.path.join(RUNS, f) for f in sorted(os.listdir(RUNS))],
                     controls=ctl, allow_dirty=True,
                     note="G27: can a selected population reach no_death's "
                          "size, and which matching is attainable")
    print(f"provenance.json ok={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
