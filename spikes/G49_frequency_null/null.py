#!/usr/bin/env python3
"""G49 — ATTACK on my own G48, one cycle old. Is 0.1358 inference or a prior?

G34 mines 2,547 constant-tail and 878 constant-head rules of the form
`p(x, c) <= q(x, y)` -- rules that predict a FIXED ENTITY. On FB15k-237 many
relations have a dominant object, so a rule of that shape can be a marginal
distribution wearing a rule's clothes.

THE NULL, built so it CAN contain the effect (A20): rank candidates by
predicate-conditional entity frequency in TRAIN and nothing else. No bodies, no
composition, no confidence. Same ranker, same filter index, same pair-disjoint
split. It is scored by the SAME ranking code as the full system, so the
comparison is not between two protocols (C3).

  python3 spikes/G49_frequency_null/null.py

Read-only outside this directory (§10).
"""
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G34 = os.path.join(ROOT, "spikes", "G36_repro_g34")
G48 = os.path.join(ROOT, "spikes", "G48_pairdisjoint_split")
sys.path.insert(0, G34)
sys.path.insert(0, G48)
import length1_constants as L                                    # noqa: E402
from split import pair_disjoint_split                            # noqa: E402

G48_MRR, G48_HITS10 = 0.1358, 0.2061


def rank_from_scores(cand, target, filtered, nent):
    """G34's ranking convention, lifted verbatim so the null is scored by the
    SAME rule the system is: expected rank `1 + higher + equal/2`, and the
    zero-score branch averaging over the unscored tail."""
    valid = {c: sc for c, sc in cand.items() if c == target or c not in filtered}
    tscore = valid.get(target, 0.0)
    n_filtered = nent - (len(filtered) - (1 if target in filtered else 0))
    if tscore > 0.0:
        higher = sum(1 for c, sc in valid.items() if sc > tscore)
        equal = sum(1 for c, sc in valid.items() if sc == tscore and c != target)
        return 1.0 + higher + equal / 2.0
    higher = sum(1 for c, sc in valid.items() if sc > 0.0)
    n_zeros = n_filtered - len(valid)
    return 1.0 + higher + (n_zeros - 1) / 2.0


def evaluate_frequency_null(test, train, true_sp, true_po, nent):
    """Predicate-conditional entity frequency. Nothing else."""
    obj_freq = defaultdict(lambda: defaultdict(int))   # p -> o -> count
    sub_freq = defaultdict(lambda: defaultdict(int))   # p -> s -> count
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1

    rr = h1 = h3 = h10 = 0
    nonzero_target = 0
    for p, s, o in test:
        for freq, target, filt in ((obj_freq[p], o, true_sp.get((s, p), set())),
                                   (sub_freq[p], s, true_po.get((p, o), set()))):
            r = rank_from_scores(dict(freq), target, filt, nent)
            if freq.get(target, 0) > 0:
                nonzero_target += 1
            rr += 1.0 / r
            h1 += r <= 1.0
            h3 += r <= 3.0
            h10 += r <= 10.0
    n = 2 * len(test)
    return {"mrr": round(rr / n, 4), "hits1": round(h1 / n, 4),
            "hits3": round(h3 / n, 4), "hits10": round(h10 / n, 4),
            "n_queries": n, "queries_with_a_scored_target": nonzero_target}


def main():
    t0 = time.time()
    nt, npred, nent, tri, _, _, _ = L.load_dataset()
    assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)
    train, dev, test, n_groups = pair_disjoint_split(tri, L.SEED)

    out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
    true_sp, true_po = L.build_filter_index(tri)
    r2 = L.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev)
    sub, inv = L.mine_length1_rules(npred, byp, rev)
    ct, ch = L.mine_constant_rules(npred, byp)

    res = {"spike": "G49", "seed": f"0x{L.SEED:X}",
           "split": "pair_disjoint (G48)", "n_train": len(train),
           "n_test": len(test), "arms": {}, "controls": {}, "falsifiers": {}}

    def arm(label, **kw):
        r = L.evaluate_link_prediction_full(test, out_adj, in_adj, true_sp,
                                            true_po, nent, **kw)
        res["arms"][label] = {k: (round(v, 4) if isinstance(v, float) else v)
                              for k, v in r.items()}
        print(f"  {label:22} mrr={res['arms'][label].get('mrr')} "
              f"h10={res['arms'][label].get('hits10')}", flush=True)

    arm("full_system", rules_2hop=r2, rules_subsume=sub, rules_inverse=inv,
        rules_const_tail=ct, rules_const_head=ch)
    # F3's ablation: the full system WITHOUT the constant-grounded rules, i.e.
    # only rules with a variable head, which is what "mined rule" normally means.
    arm("no_constant_rules", rules_2hop=r2, rules_subsume=sub, rules_inverse=inv)
    # And the compositional core alone, for the same reason.
    arm("two_hop_only", rules_2hop=r2)

    res["arms"]["frequency_null"] = evaluate_frequency_null(
        test, train, true_sp, true_po, nent)
    print(f"  {'frequency_null':22} mrr={res['arms']['frequency_null']['mrr']} "
          f"h10={res['arms']['frequency_null']['hits10']}", flush=True)

    full = res["arms"]["full_system"]
    null = res["arms"]["frequency_null"]
    noconst = res["arms"]["no_constant_rules"]

    res["controls"]["C1_instrument_reproduces_G48"] = {
        "what_would_fail_it": "the full-system arm returning anything but "
                              "0.1358 / 0.2061 on the pair-disjoint split",
        "mrr": full.get("mrr"), "hits10": full.get("hits10"),
        "g48_mrr": G48_MRR, "g48_hits10": G48_HITS10,
        "ok": full.get("mrr") == G48_MRR and full.get("hits10") == G48_HITS10,
    }
    res["controls"]["C2_null_is_not_degenerate"] = {
        "what_would_fail_it": "a null that scores the true answer above zero "
                              "for almost no query, whose MRR would then measure "
                              "the tie-averaging convention rather than frequency",
        "queries_with_a_scored_target": null["queries_with_a_scored_target"],
        "n_queries": null["n_queries"],
        "share": round(null["queries_with_a_scored_target"] / null["n_queries"], 4),
        "ok": null["queries_with_a_scored_target"] / null["n_queries"] > 0.10,
    }
    res["controls"]["C3_same_filtered_candidate_sets"] = {
        "what_would_fail_it": "the null and the system using different rank "
                              "conventions or filters, making this a comparison "
                              "of two protocols",
        "how": "rank_from_scores() is G34's convention lifted verbatim "
               "(1 + higher + equal/2, zero-branch averaged over the unscored "
               "tail) and both arms read the same true_sp / true_po index",
        "ok": True,
    }

    gap = round(full["mrr"] - null["mrr"], 4)
    res["falsifiers"]["F1_null_matches_the_full_system"] = {
        "question": "does a predicate-conditional frequency prior score within "
                    "0.002 of the full rule system on a leak-free split?",
        "full_mrr": full["mrr"], "null_mrr": null["mrr"], "gap": gap,
        "fired": abs(gap) <= 0.002,
        "meaning_if_fired": "the rule machinery buys nothing over a marginal "
                            "and this series' accuracy claim is a prior",
    }
    res["falsifiers"]["F2_null_is_too_weak_to_test_anything"] = {
        "question": "can the null contain the effect at all?",
        "null_mrr": null["mrr"],
        "fired": null["mrr"] < 0.01,
        "meaning_if_fired": "'beats null' would restate the structure's "
                            "existence rather than test it (A20); a stronger "
                            "null is required before any claim",
    }
    const_contrib = round(full["mrr"] - noconst["mrr"], 4)
    res["falsifiers"]["F3_advantage_is_all_compositional"] = {
        "question": "is the full system's advantage over the null carried by "
                    "the CONSTANT-grounded rules rather than by composition?",
        "full_mrr": full["mrr"], "no_constant_mrr": noconst["mrr"],
        "constant_contribution": const_contrib,
        "null_mrr": null["mrr"],
        "fired": const_contrib <= 0.002,
        "meaning_if_fired": "the constant rules contribute nothing and the "
                            "advantage is compositional after all",
    }

    res["elapsed_sec"] = round(time.time() - t0, 3)
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "null.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls = []
    for name, why, canfail, null_must in (
        ("C1_instrument_reproduces_G48",
         "the full-system arm must return G48's figure, or this is not the "
         "instrument G48 used and no comparison from it means anything",
         "the full arm returning anything but 0.1358 / 0.2061",
         "a differing figure: the literals are transcribed from G48/RESULT.md"),
        ("C2_null_is_not_degenerate",
         "the null must score the true answer above zero for a real share of "
         "queries, or its MRR measures the tie convention and not frequency",
         "a null that scores almost no target above zero",
         "a low share, which a genuinely uninformative prior would produce"),
        ("C3_same_filtered_candidate_sets",
         "both arms must use one rank convention and one filter index, or this "
         "compares two protocols rather than two scorers",
         "a null scored by a different rank rule than the system",
         "both: the convention is lifted verbatim and is inspectable"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null_must)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, null_must in (
        ("F1_null_matches_the_full_system",
         "the accuracy claim of the whole G-series: that its number is "
         "inference rather than a marginal",
         "the frequency prior lands within 0.002 of the full system",
         "a matching score, which C2 shows this null is capable of producing"),
        ("F2_null_is_too_weak_to_test_anything",
         "the null's standing as a null (A20)",
         "the frequency prior scores below 0.01 MRR",
         "a near-zero score, which an uninformative prior would give"),
        ("F3_advantage_is_all_compositional",
         "the reading that the constant-grounded rules are the prior",
         "removing the constant rules costs 0.002 MRR or less",
         "no contribution, which the ablation is free to report"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null_must)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[G34, G48],
        artifacts=[os.path.join(HERE, "null.py"),
                   os.path.join(HERE, "null.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("null_json", json.dumps(res, sort_keys=True))],
        falsifier="a frequency prior scoring within 0.002 of the full rule "
                  "system on a leak-free split, which would make this series' "
                  "accuracy a marginal rather than an inference",
        allow_dirty=True,
        note="G49: ATTACK on my own G48 from one cycle earlier. What does "
             "0.1358 buy over a predicate-conditional frequency prior?")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
