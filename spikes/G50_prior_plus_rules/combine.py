#!/usr/bin/env python3
"""G50 — can anything in this lane beat 0.1732?

G49 measured that on the leak-free split a predicate-conditional frequency
prior scores 0.1732 while the full mined system scores 0.1358, the constant
rules are that prior restated and worse, and the length-1 families are actively
harmful. This tries to make the rules earn their place ON TOP of the prior
rather than instead of it -- which is what published rule miners actually do.

NO TUNED MIXING WEIGHT (A26). The combination is lexicographic: the prior
orders the candidates and rule confidence breaks its ties. There is no `a` or
`b` to fit, because a fitted mixing constant is the knob this repo has already
killed twice. Concretely, score = prior_count + conf, where conf < 1 <= any
non-zero integer count -- so a candidate the prior ranks higher can never be
overtaken by rule confidence alone, and among equal counts the rules decide.

  python3 spikes/G50_prior_plus_rules/combine.py

Read-only outside this directory (§10).
"""
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G34 = os.path.join(ROOT, "spikes", "G36_repro_g34")
G48 = os.path.join(ROOT, "spikes", "G48_pairdisjoint_split")
G49 = os.path.join(ROOT, "spikes", "G49_frequency_null")
for p in (G34, G48, G49):
    sys.path.insert(0, p)
import length1_constants as L                                    # noqa: E402
from split import pair_disjoint_split                            # noqa: E402
from null import rank_from_scores                                # noqa: E402

PRIOR_MRR, PRIOR_HITS10 = 0.1732, 0.2855        # G49, transcribed
TWO_HOP_MRR = 0.0572                            # G49, transcribed
EPS = 0.002


def rule_scores(p, s, o, out_adj, in_adj, rules, want_tail):
    """Max-confidence rule score per candidate, for one query direction.

    Only the families this row is allowed to use are consulted; the caller
    decides which by what it puts in `rules`.
    """
    cand = defaultdict(float)

    def bump(k, c):
        if c > cand[k]:
            cand[k] = c

    if want_tail:
        for (p1, p2), conf in rules.get("g17_by_head", {}).get(p, ()):
            for pp1, b in out_adj.get(s, ()):
                if pp1 == p1 and b != s:
                    for pp2, c_node in out_adj.get(b, ()):
                        if pp2 == p2 and c_node != s and c_node != b:
                            bump(c_node, conf)
        for r in rules.get("subsume", {}).get(p, ()):
            for pq, c_node in out_adj.get(s, ()):
                if pq == r["body"] and c_node != s:
                    bump(c_node, r["conf"])
        for r in rules.get("inverse", {}).get(p, ()):
            for pq, c_node in in_adj.get(s, ()):
                if pq == r["body"] and c_node != s:
                    bump(c_node, r["conf"])
    else:
        for (p1, p2), conf in rules.get("g17_by_head", {}).get(p, ()):
            for pp2, b in in_adj.get(o, ()):
                if pp2 == p2 and b != o:
                    for pp1, a in in_adj.get(b, ()):
                        if pp1 == p1 and a != o and a != b:
                            bump(a, conf)
        for r in rules.get("subsume", {}).get(p, ()):
            for pq, a in in_adj.get(o, ()):
                if pq == r["body"] and a != o:
                    bump(a, r["conf"])
        for r in rules.get("inverse", {}).get(p, ()):
            for pq, a in out_adj.get(o, ()):
                if pq == r["body"] and a != o:
                    bump(a, r["conf"])
    return cand


def evaluate(test, train, out_adj, in_adj, true_sp, true_po, nent, rules):
    """Prior orders; rule confidence breaks ties. `rules` empty => prior alone."""
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1

    rr = h1 = h3 = h10 = 0
    reordered = 0
    for p, s, o in test:
        for want_tail, freq, target, filt in (
                (True, obj_freq[p], o, true_sp.get((s, p), set())),
                (False, sub_freq[p], s, true_po.get((p, o), set()))):
            base = dict(freq)
            if rules:
                rs = rule_scores(p, s, o, out_adj, in_adj, rules, want_tail)
                if rs:
                    combined = dict(base)
                    for k, c in rs.items():
                        combined[k] = combined.get(k, 0) + c
                    if combined != base:
                        reordered += 1
                    base = combined
            r = rank_from_scores(base, target, filt, nent)
            rr += 1.0 / r
            h1 += r <= 1.0
            h3 += r <= 3.0
            h10 += r <= 10.0
    n = 2 * len(test)
    return {"mrr": round(rr / n, 4), "hits1": round(h1 / n, 4),
            "hits3": round(h3 / n, 4), "hits10": round(h10 / n, 4),
            "n_queries": n, "queries_reordered_by_rules": reordered}


def main():
    t0 = time.time()
    nt, npred, nent, tri, _, _, _ = L.load_dataset()
    assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)
    train, dev, test, _ = pair_disjoint_split(tri, L.SEED)

    out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
    true_sp, true_po = L.build_filter_index(tri)
    r2 = L.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev)
    sub, inv = L.mine_length1_rules(npred, byp, rev)
    g17_by_head = defaultdict(list)
    for r in r2:
        g17_by_head[r["head"]].append((r["body"], r["conf"]))

    res = {"spike": "G50", "seed": f"0x{L.SEED:X}",
           "split": "pair_disjoint (G48)", "n_test": len(test),
           "arms": {}, "controls": {}, "falsifiers": {}}

    def arm(label, rules):
        res["arms"][label] = evaluate(test, train, out_adj, in_adj,
                                      true_sp, true_po, nent, rules)
        a = res["arms"][label]
        print(f"  {label:26} mrr={a['mrr']} h10={a['hits10']} "
              f"reordered={a['queries_reordered_by_rules']}", flush=True)

    arm("C_prior_alone", {})
    arm("A_prior_plus_all_rules", {"g17_by_head": g17_by_head,
                                   "subsume": sub, "inverse": inv})
    arm("B_prior_plus_2hop_only", {"g17_by_head": g17_by_head})
    # And the rule side on its own, as G49 measured it, so C1 can pin it.
    two_hop = L.evaluate_link_prediction_full(test, out_adj, in_adj, true_sp,
                                              true_po, nent, rules_2hop=r2)
    res["arms"]["two_hop_only_no_prior"] = {
        k: (round(v, 4) if isinstance(v, float) else v) for k, v in two_hop.items()}
    print(f"  {'two_hop_only_no_prior':26} "
          f"mrr={res['arms']['two_hop_only_no_prior'].get('mrr')}", flush=True)

    C = res["arms"]["C_prior_alone"]
    A = res["arms"]["A_prior_plus_all_rules"]
    B = res["arms"]["B_prior_plus_2hop_only"]

    res["controls"]["C1_rule_side_matches_G49"] = {
        "what_would_fail_it": "the 2-hop-only arm returning anything but "
                              "G49's 0.0572, which would mean a different "
                              "rule side and no comparison here would hold",
        "mrr": res["arms"]["two_hop_only_no_prior"].get("mrr"),
        "g49_two_hop_mrr": TWO_HOP_MRR,
        "ok": res["arms"]["two_hop_only_no_prior"].get("mrr") == TWO_HOP_MRR,
    }
    res["controls"]["C2_combination_actually_reorders"] = {
        "what_would_fail_it": "the rules changing no candidate score, which "
                              "would make every combined arm the prior with "
                              "extra steps and F1 a measurement of nothing",
        "A_reordered": A["queries_reordered_by_rules"],
        "B_reordered": B["queries_reordered_by_rules"],
        "n_queries": A["n_queries"],
        "ok": A["queries_reordered_by_rules"] > 0 and B["queries_reordered_by_rules"] > 0,
    }
    res["controls"]["C3_same_rank_convention"] = {
        "what_would_fail_it": "a different rank rule or filter from G48/G49",
        "how": "rank_from_scores imported from G49, which lifted G34's "
               "1 + higher + equal/2 verbatim; same true_sp / true_po index",
        "ok": True,
    }

    best = max(A["mrr"], B["mrr"])
    res["falsifiers"]["F1_nothing_beats_the_prior"] = {
        "question": "does ANY arm exceed the prior by more than 0.002?",
        "prior_mrr": C["mrr"], "A_mrr": A["mrr"], "B_mrr": B["mrr"],
        "best_combined": best, "delta_vs_prior": round(best - C["mrr"], 4),
        "threshold": EPS,
        # WRITTEN TWO-SIDED ON PURPOSE. G49's F1 asked only whether the null
        # MATCHED and could not express that the null WON, so its `fired: false`
        # read as survival after a nineteen-fold loss. This states all three
        # outcomes and which claim each refutes.
        "verdict": ("rules ADD -- survives" if best - C["mrr"] > EPS else
                    "rules INERT -- refuted as useless" if abs(best - C["mrr"]) <= EPS
                    else "rules HARM -- refuted as worse than nothing"),
        "fired": best - C["mrr"] <= EPS,
        "meaning_if_fired": "nothing this lane has mined adds anything to "
                            "counting on an honest split, and that is the "
                            "lane's headline rather than an ablation footnote",
    }
    res["falsifiers"]["F2_prior_is_not_the_same_prior"] = {
        "question": "does arm C reproduce G49's prior exactly?",
        "mrr": C["mrr"], "hits10": C["hits10"],
        "g49_mrr": PRIOR_MRR, "g49_hits10": PRIOR_HITS10,
        "fired": not (C["mrr"] == PRIOR_MRR and C["hits10"] == PRIOR_HITS10),
        "meaning_if_fired": "no comparison in this row means anything",
    }
    res["falsifiers"]["F3_length1_families_are_not_harmful"] = {
        "question": "does dropping the length-1 families (B) beat keeping "
                    "them (A), as G49's 'actively harmful' reading predicts?",
        "A_with_length1": A["mrr"], "B_without": B["mrr"],
        "delta": round(B["mrr"] - A["mrr"], 4),
        "fired": B["mrr"] <= A["mrr"],
        "meaning_if_fired": "G49's 'actively harmful' reading is wrong and I "
                            "retract it",
    }

    res["elapsed_sec"] = round(time.time() - t0, 3)
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "combine.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls = []
    for name, why, canfail, nmc in (
        ("C1_rule_side_matches_G49",
         "the rule side must be G49's rule side, or no comparison holds",
         "the 2-hop arm returning anything but 0.0572",
         "a differing figure: the literal is transcribed from G49/RESULT.md"),
        ("C2_combination_actually_reorders",
         "the rules must change some candidate score, or every combined arm "
         "is the prior with extra steps and F1 measures nothing",
         "zero reordered queries in either combined arm",
         "a zero, which an inert combination would produce"),
        ("C3_same_rank_convention",
         "one rank rule and one filter index across G48, G49 and this row",
         "a different convention, making this a protocol comparison",
         "both: the function is imported, not reimplemented"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=nmc)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, nmc in (
        ("F1_nothing_beats_the_prior",
         "that anything mined in this lane adds to counting on an honest split",
         "no combined arm exceeds the prior by more than 0.002 -- and the "
         "verdict field states separately whether the rules were INERT or "
         "HARMFUL, because a two-arm falsifier must say which arm winning "
         "refutes what (G49's F1 could not)",
         "an arm above the prior, which the same harness would report"),
        ("F2_prior_is_not_the_same_prior",
         "the comparability of every number in this row",
         "arm C fails to reproduce G49's 0.1732 / 0.2855",
         "a differing figure: the literals come from G49/RESULT.md"),
        ("F3_length1_families_are_not_harmful",
         "G49's reading that the length-1 families are actively harmful",
         "dropping them does not beat keeping them",
         "both orderings: the ablation is free to come out either way"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=nmc)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[G34, G48, G49],
        artifacts=[os.path.join(HERE, "combine.py"),
                   os.path.join(HERE, "combine.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("combine_json", json.dumps(res, sort_keys=True))],
        falsifier="no combined arm exceeding the frequency prior by more than "
                  "0.002, which would mean nothing mined in this lane adds to "
                  "counting on a split that cannot leak",
        allow_dirty=True,
        note="G50: does anything here beat 0.1732? Prior orders, rule "
             "confidence breaks ties, no mixing weight to fit.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
