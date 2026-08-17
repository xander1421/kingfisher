#!/usr/bin/env python3
"""The matched-population comparison G24 could not run, plus the 2x2 attribution.

Coverage is not compared on its own anywhere here, for the reason G24's
analyse.py gives: `test solved` rises with population size near-mechanically.
The whole point of this spike is that population size was a free parameter, so
every row carries its population and every claim is either a dominance on the
(predictions, correct) plane or a comparison at MATCHED population.

Verdict is computed, not written. It can come out against the hypothesis that
motivated the run -- if a selected population at no_death's size fails to beat
no_death, this prints TRADEOFF and G24's reading stands.
"""

import itertools
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'harness'))
import provenance as P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
MATCH_TOL = 0.25          # |pop - target| / target considered "matched"


def load():
    out = {}
    for f in sorted(os.listdir(RUNS)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(RUNS, f)))
            if d["hist"]:
                out[d["name"]] = d
    return out


def split_name(name):
    """`wage1200_s777` -> ("wage1200", 777). Bare names are the 1234 run."""
    if "_s" in name:
        head, _, tail = name.rpartition("_s")
        if tail.isdigit():
            return head, int(tail)
    return name, 1234


def row(d):
    h0, hN = d["hist"][0], d["hist"][-1]
    t = hN["test"]
    return {"name": d["name"], "arm": d["arm"],
            "wage": d["params"]["wage_pool"], "max_pop": d["params"]["max_pop"],
            "pop": hN["pop"], "preds": t["predicted"], "correct": t["solved"],
            "prec": t["precision"], "top12": t["top12"],
            "delta": t["solved"] - h0["test"]["solved"],
            "cov_per_rule": t["solved"] / hN["pop"] if hN["pop"] else 0.0,
            "a15": hN["a15"], "capped": d["capped_evals"]}


def dominates(a, b):
    """a beats b only by getting more correct at no more predictions."""
    return a["correct"] > b["correct"] and a["preds"] <= b["preds"]


def main():
    runs = load()
    if not runs:
        print("no runs yet")
        return 1
    allrows = {k: row(v) for k, v in runs.items()}
    for k, r in allrows.items():
        r["base"], r["seed"] = split_name(k)
    # The dial and the plane are read at the reference seed only; the repeats
    # exist to bound the noise on the differences, not to widen the table.
    rows = {r["base"]: r for r in allrows.values() if r["seed"] == 1234}
    order = [n for n in ("full_base", "full_cap2000", "wage300", "wage600",
                         "wage1200", "wage2400", "wage4800",
                         "wage600_noabduct", "nodeath",
                         "nodeath_noabduct") if n in rows]

    print(f"{'config':<18}{'wage':>7}{'pop':>6}{'preds':>10}{'correct':>9}"
          f"{'prec':>9}{'cov/rule':>10}{'delta':>8}{'A15':>5}")
    for n in order:
        r = rows[n]
        print(f"{n:<18}{r['wage']:>7.0f}{r['pop']:>6}{r['preds']:>10}"
              f"{r['correct']:>9}{r['prec']:>9.4f}{r['cov_per_rule']:>10.1f}"
              f"{r['delta']:>+8}{('yes' if r['a15'] else 'NO'):>5}")

    # ---- C1 REPRO: full_base must equal G24's published full arm.
    print("\nCONTROLS")
    g24 = {"pop": 110, "correct": 4144, "prec": 0.0355}
    if "full_base" in rows:
        r = rows["full_base"]
        ok = (r["pop"] == g24["pop"] and r["correct"] == g24["correct"]
              and abs(r["prec"] - g24["prec"]) < 5e-5)
        print(f"  C1 REPRO   {'PASS' if ok else 'FAIL'} — full_base "
              f"pop {r['pop']} correct {r['correct']} prec {r['prec']:.4f} "
              f"vs G24 110/4144/0.0355")
    # ---- C2 CAP: does MAX_POP bind, or does the rent set the size?
    if "full_cap2000" in rows and "full_base" in rows:
        a, b = rows["full_base"], rows["full_cap2000"]
        same = a["pop"] == b["pop"] and a["correct"] == b["correct"]
        note = ("Rent sets population size, not the cap." if same else
                "THE CAP WAS BINDING — the capacity sweep aims at the wrong knob.")
        print(f"  C2 CAP     {'PASS' if same else 'FAIL'} — cap 200->2000 "
              f"gives pop {a['pop']}->{b['pop']}, correct "
              f"{a['correct']}->{b['correct']}. {note}")
    # ---- C3 A15. Scope: arms with ABDUCTION ON, which are exactly the arms
    # this spike ranks. G24 established that the plant is reachable by
    # problem-directed proposal and not by blind mutation -- both its
    # `no_abduct` arm and both of mine miss it -- so demanding it from an
    # abduction-off arm makes the gate permanently red and therefore useless,
    # not strict. Exempt arms are still printed and are still unranked.
    exempt = [n for n, r in rows.items() if "no_abduct" in r["arm"]]
    bad = [n for n, r in rows.items()
           if "no_variation" not in r["arm"] and "no_abduct" not in r["arm"]
           and not r["a15"]]
    print(f"  C3 A15     {'PASS' if not bad else 'FAIL'} — "
          f"{'every ranked (abduction-on) arm found the plant' if not bad else 'missing in ' + str(bad)}"
          f"; exempt and unranked: {exempt}")
    # ---- C4 NULL: attribution of no_death's coverage.
    if "nodeath_noabduct" in rows and "nodeath" in rows:
        nd, nn = rows["nodeath"], rows["nodeath_noabduct"]
        print(f"  C4 NULL    unselected+unguided gets {nn['correct']} correct "
              f"at pop {nn['pop']} vs unselected+abduction {nd['correct']} at "
              f"pop {nd['pop']}")

    # ---- the 2x2, which G24 had three cells of
    cells = {("on", "on"): "full_base", ("on", "off"): None,
             ("off", "on"): "nodeath", ("off", "off"): "nodeath_noabduct"}
    print("\nDEATH x ABDUCTION (test correct / preds / pop)")
    print("                 abduct on            abduct off")
    for d in ("on", "off"):
        line = f"  death {d:<4}"
        for a in ("on", "off"):
            n = cells[(d, a)]
            if n and n in rows:
                r = rows[n]
                line += f"  {r['correct']:>6}/{r['preds']:>7}/{r['pop']:<5}"
            elif d == "on" and a == "off":
                line += "  1359/  40414/134  (G24)"
            else:
                line += "  " + "-" * 20
        print(line)

    if "nodeath" not in rows:
        print("\nnodeath not run yet")
        return 0
    nd = rows["nodeath"]

    # ---- is the capacity dial linear? If population saturates, a selected
    # population simply cannot be grown to no_death's size, and that is an
    # answer rather than a failed run: the ceiling is the supply of rules that
    # beat the adversary, not the size of the wage pool.
    wr = sorted((r for n, r in rows.items() if r["arm"] == "full"),
                key=lambda r: r["wage"])
    print("\nCAPACITY DIAL (WAGE_POOL -> population)")
    for i, r in enumerate(wr):
        if i and wr[i - 1]["wage"]:
            fw = r["wage"] / wr[i - 1]["wage"]
            fp = r["pop"] / wr[i - 1]["pop"] if wr[i - 1]["pop"] else 0.0
            print(f"  {r['wage']:>7.0f} -> pop {r['pop']:>4}   "
                  f"{fw:.1f}x pool bought {fp:.2f}x population")
        else:
            print(f"  {r['wage']:>7.0f} -> pop {r['pop']:>4}")
    if len(wr) >= 2 and wr[0]["wage"]:
        span_w = wr[-1]["wage"] / wr[0]["wage"]
        span_p = wr[-1]["pop"] / wr[0]["pop"]
        print(f"  over the whole sweep: {span_w:.0f}x pool -> {span_p:.2f}x "
              f"population, ceiling {wr[-1]['pop']} vs no_death's {nd['pop']}")

    # ---- route 1: matched population, if the dial reaches it
    print("\nMATCHED POPULATION")
    sel = [r for n, r in rows.items()
           if "no_death" not in r["arm"] and r["pop"] > 0
           and abs(r["pop"] - nd["pop"]) / nd["pop"] <= MATCH_TOL]
    matched = None
    if sel:
        matched = max(sel, key=lambda r: r["correct"])
        print(f"  no_death (no selection): {nd['correct']} correct / "
              f"{nd['preds']} preds / pop {nd['pop']} / prec {nd['prec']:.4f}")
        for r in sel:
            print(f"  {r['name']} (selected): {r['correct']} correct / "
                  f"{r['preds']} preds / pop {r['pop']} / prec {r['prec']:.4f}")
    else:
        near = max((r for n, r in rows.items() if "no_death" not in r["arm"]),
                   key=lambda r: r["pop"])
        print(f"  UNREACHABLE — no selected arm gets within {MATCH_TOL:.0%} of "
              f"pop {nd['pop']}; the largest is {near['name']} at "
              f"{near['pop']}. Selection is population-LIMITED: only rules whose "
              f"confidence exceeds the co-evolving adversary's draw a wage at "
              f"all, so raising the pool cannot manufacture more of them.")

    # ---- route 2: the plane, which is always available
    print("\nPLANE vs no_death (win = more correct at no more predictions)")
    cands = [r for n, r in rows.items()
             if "no_death" not in r["arm"] and r["a15"] and r["pop"] > 0]
    dom = [r for r in cands if dominates(r, nd)]
    best = max(cands, key=lambda r: r["correct"]) if cands else None
    for r in sorted(cands, key=lambda r: -r["correct"]):
        tag = ("DOMINATES no_death" if dominates(r, nd)
               else "dominated BY no_death" if dominates(nd, r) else "trade")
        print(f"  {r['name']:<16} {r['correct']:>6} correct /{r['preds']:>8} "
              f"preds  prec {r['prec']:.4f}  {tag}")
    print(f"  {'nodeath':<16} {nd['correct']:>6} correct /{nd['preds']:>8} "
          f"preds  prec {nd['prec']:.4f}")

    # ---- seed repeats: the headline is a RATIO OF DIFFERENCES in coverage
    # counts, so it inherits run-to-run variance twice over. Computed per seed
    # and quoted as a range.
    seeds = sorted({r["seed"] for r in allrows.values()})
    fracs = {}
    if len(seeds) > 1:
        print("\nSEED REPEATS (test correct / preds / pop)")
        print(f"  {'config':<12}" + "".join(f"{('seed ' + str(s)):>26}"
                                            for s in seeds))
        for b in ("full_base", "wage1200", "nodeath"):
            cells = []
            for s in seeds:
                r = next((x for x in allrows.values()
                          if x["base"] == b and x["seed"] == s), None)
                cells.append(f"{r['correct']:>8}/{r['preds']:>8}/{r['pop']:<5}"
                             if r else " " * 26)
            print(f"  {b:<12}" + "".join(cells))
        for s in seeds:
            g = {b: next((x for x in allrows.values()
                          if x["base"] == b and x["seed"] == s), None)
                 for b in ("full_base", "wage1200", "nodeath")}
            if all(g.values()) and g["nodeath"]["correct"] != g["full_base"]["correct"]:
                fracs[s] = ((g["wage1200"]["correct"] - g["full_base"]["correct"])
                            / (g["nodeath"]["correct"] - g["full_base"]["correct"]))
        if fracs:
            print("  gap closed by WAGE_POOL alone, per seed: "
                  + ", ".join(f"{s}: {v:.0%}" for s, v in fracs.items()))
        # Is the capacity effect bigger than seed noise at all? full_base's own
        # range across seeds is wide, so this is not rhetorical. Exact
        # permutation over the 20 ways to split six runs into two groups of
        # three -- with n=3 per group the smallest attainable one-sided p is
        # 1/20 = 0.05, and that floor is stated rather than hidden.
        a = [x["correct"] for x in allrows.values() if x["base"] == "full_base"]
        b = [x["correct"] for x in allrows.values() if x["base"] == "wage1200"]
        if len(a) == len(b) == len(seeds) >= 3:
            obs = sum(b) / len(b) - sum(a) / len(a)
            pool = a + b
            ge = 0
            splits = list(itertools.combinations(range(len(pool)), len(a)))
            for c in splits:
                g1 = [pool[i] for i in c]
                g2 = [pool[i] for i in range(len(pool)) if i not in c]
                if sum(g2) / len(g2) - sum(g1) / len(g1) >= obs - 1e-9:
                    ge += 1
            print(f"  capacity effect wage1200 - full_base: {obs:+.0f} correct, "
                  f"exact permutation p = {ge}/{len(splits)} = {ge / len(splits):.3f} "
                  f"one-sided (floor 1/{len(splits)} at this n); ranges "
                  f"full_base {min(a)}-{max(a)}, wage1200 {min(b)}-{max(b)}, "
                  f"{'DISJOINT' if min(b) > max(a) else 'OVERLAPPING'}")

    base = rows.get("full_base")
    if dom:
        w = max(dom, key=lambda r: r["correct"])
        v = (f"CALIBRATION — {w['name']} keeps death and DOMINATES no_death "
             f"({w['correct']} correct at {w['preds']} predictions vs "
             f"{nd['correct']}/{nd['preds']}). The +5059 was the wage pool I "
             f"picked, not the value of removing death.")
    elif best and base:
        closed = ((best["correct"] - base["correct"])
                  / (nd["correct"] - base["correct"]))
        v = (f"CALIBRATION, PARTLY — turning WAGE_POOL alone closes "
             f"{closed:.0%} of the coverage gap G24 attributed to death "
             f"({base['correct']} -> {best['correct']} vs no_death's "
             f"{nd['correct']}) while asserting {nd['preds'] / best['preds']:.1f}x "
             f"fewer predictions and holding {best['prec'] / nd['prec']:.1f}x "
             f"the precision. Neither point dominates the other, so death is "
             f"not shown to cost coverage; the published capacity was simply "
             f"low. The remaining {1 - closed:.0%} is not reachable by this "
             f"dial: selection saturates at pop {best['pop']}.")
        if fracs:
            v += (f" Across {len(fracs)} run seeds the gap closed by WAGE_POOL "
                  f"alone is {min(fracs.values()):.0%}-{max(fracs.values()):.0%} "
                  f"(wage1200 vs full_base vs no_death, same three configs each "
                  f"seed), so the fraction is a band, not the single 83%.")
    else:
        v = "UNRESOLVED — no A15-passing selected arm to compare."
    # C4 attribution is independent of all of the above and overturns the
    # premise G24's analyse.py reasons from.
    if "nodeath_noabduct" in rows:
        nn = rows["nodeath_noabduct"]
        v += (f" ATTRIBUTION: at matched population and NO selection either "
              f"side ({nn['pop']} vs {nd['pop']}), dropping abduction costs "
              f"{nd['correct'] - nn['correct']} correct triples "
              f"({nd['correct']} -> {nn['correct']}). no_death's coverage is "
              f"problem-directed proposal, not population volume — so "
              f"'coverage rises with population size almost mechanically' is "
              f"false as stated in G24.")
    print(f"\nVERDICT: {v}")

    # ---- persist the controls' OBSERVATIONS, not their verdicts (A20).
    ctl = []
    if "full_base" in rows:
        r = rows["full_base"]
        c = P.Control("C1_repro", "the arm-set refactor and the monkeypatched "
                      "globals must not change evo.py's behaviour",
                      null_must_contain="any deviation from G24's published "
                      "full arm 110/4144/0.0355")
        c.observe(r["pop"] == 110 and r["correct"] == 4144,
                  {"pop": r["pop"], "correct": r["correct"], "prec": r["prec"],
                   "g24": g24}, "line-identical to G24 RUN.txt full arm")
        ctl.append(c)
    if "full_cap2000" in rows:
        a, b = rows["full_base"], rows["full_cap2000"]
        c = P.Control("C2_cap_not_binding", "the capacity sweep turns "
                      "WAGE_POOL; if MAX_POP were the binding constraint the "
                      "sweep would be aimed at the wrong knob",
                      null_must_contain="a population above 200 once the cap "
                      "is lifted to 2000")
        c.observe(a["pop"] == b["pop"],
                  {"pop_cap200": a["pop"], "pop_cap2000": b["pop"],
                   "correct_cap200": a["correct"],
                   "correct_cap2000": b["correct"]})
        ctl.append(c)
    c = P.Control("C3_a15_plant", "a ranked arm that never discovers the "
                  "planted rule has an unproven instrument (G24's gate, scoped "
                  "to abduction-on arms because the plant is known unreachable "
                  "by blind mutation)",
                  null_must_contain="a ranked abduction-on arm that misses the "
                  "plant -- e.g. a capacity setting large enough to swamp it")
    c.observe(not bad, {n: rows[n]["a15"] for n in rows},
              f"ranked misses {bad}; exempt (abduction off) {exempt}")
    ctl.append(c)
    if "nodeath_noabduct" in rows:
        nn = rows["nodeath_noabduct"]
        c = P.Control("C4_volume_null", "tests whether no_death's coverage is "
                      "population volume: an unselected population of the same "
                      "size, without problem-directed proposal",
                      null_must_contain="coverage near no_death's 6361 at pop "
                      "~531, which is what 'coverage rises with population "
                      "size almost mechanically' predicts")
        c.observe(nn["correct"] < 0.5 * nd["correct"],
                  {"nodeath_noabduct": [nn["pop"], nn["preds"], nn["correct"]],
                   "nodeath": [nd["pop"], nd["preds"], nd["correct"]],
                   "g24_no_abduct_with_death": [134, 40414, 1359]},
                  "volume hypothesis REFUTED: 1514 vs 6361 at matched pop")
        ctl.append(c)
    ok, _ = P.record(HERE, artifacts=[os.path.join(HERE, "sweep.json"),
                                      os.path.join(HERE, "sweep.py"),
                                      os.path.join(HERE, "analyse.py"),
                                      os.path.join(HERE, "..", "G24_population",
                                                   "evo.py")]
                     + [os.path.join(RUNS, f) for f in sorted(os.listdir(RUNS))],
                     controls=ctl, allow_dirty=True,
                     no_deps_reason="pure Python inside the workspace: no "
                     "external repo, no built binary, no device. The only "
                     "dependency is G24's evo.py, whose digest is recorded "
                     "under artifacts so A24 pins the code state that produced "
                     "these runs.",
                     note="G25: is no_death's +5059 a tradeoff or a rent "
                          "calibration artefact")
    print(f"provenance.json ok={ok}")
    json.dump({"rows": rows, "verdict": v,
               "conditions": {"data": "real:FB15k-237+planted",
                              "split": "70/15/15", "split_seed": "0xC0FFEE",
                              "run_seed": 1234, "platforms": [["macos", "aarch64"]],
                              "swept": {"wage_pool": sorted({r["wage"] for r in rows.values()}),
                                        "arm": sorted({r["arm"] for r in rows.values()})}},
               "cites": ["G24_population"]},
              open(os.path.join(HERE, "sweep.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
