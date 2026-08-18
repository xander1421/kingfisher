#!/usr/bin/env python3
"""G47 — noisy-OR against max aggregation, on G46's partition.

G30's own RESULT.md named the lever and never pulled it: *"AnyBURL uses
weighted confidence aggregation (noisy-OR / linear combination), whereas G17
uses simple max confidence."* This runs both, on the same rules, the same
ranker and the same filter index, with the aggregation operator as the only
variable -- and reports every arm on G46's three partitions, because a gain in
the blended 0.2648 may be a better exploitation of the 30% that leaks rather
than a better method.

  python3 spikes/G47_noisyor/run.py

Read-only outside this directory (§10).
"""
import hashlib, json, os, random, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G34 = os.path.join(ROOT, "spikes", "G36_repro_g34")
sys.path.insert(0, HERE)
import agg as A                                                  # noqa: E402

PUBLISHED_MRR, PUBLISHED_HITS10 = 0.2648, 0.3929


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def same_pair_mask(train, test):
    pairs = defaultdict(set)
    for p, s, o in train:
        pairs[(s, o)].add(p)
    return [any(q != p for q in pairs.get((s, o), ())) or (o, s) in pairs
            for p, s, o in test], pairs


def main():
    t0 = time.time()
    nt, npred, nent, tri, train, dev, test = A.load_dataset()
    assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)

    out_adj, in_adj, pair_tr, byp, rev = A.build_graph_index(train)
    true_sp, true_po = A.build_filter_index(tri)
    full = dict(rules_2hop=A.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev))
    sub, inv = A.mine_length1_rules(npred, byp, rev)
    ct, ch = A.mine_constant_rules(npred, byp)
    full.update(rules_subsume=sub, rules_inverse=inv,
                rules_const_tail=ct, rules_const_head=ch)

    mask, _ = same_pair_mask(train, test)
    parts = {"all": test,
             "same_pair": [t for t, m in zip(test, mask) if m],
             "no_same_pair": [t for t, m in zip(test, mask) if not m]}

    res = {"spike": "G47", "seed": f"0x{A.SEED:X}",
           "source_sha256": {
               "g34_original": sha256(os.path.join(G34, "length1_constants.py")),
               "g47_copy": sha256(os.path.join(HERE, "agg.py")),
               "sites_rewritten": 8},
           "partition": {k: len(v) for k, v in parts.items()},
           "arms": {}, "controls": {}, "falsifiers": {}}

    for aggmode in ("max", "noisy_or"):
        A.AGG = aggmode                     # the ONLY variable
        res["arms"][aggmode] = {}
        for pname, subset in parts.items():
            r = A.evaluate_link_prediction_full(subset, out_adj, in_adj,
                                                true_sp, true_po, nent, **full)
            res["arms"][aggmode][pname] = {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in r.items()}
            print(f"  {aggmode:9} {pname:14} n={len(subset):>6} "
                  f"mrr={res['arms'][aggmode][pname].get('mrr')} "
                  f"h10={res['arms'][aggmode][pname].get('hits10')}", flush=True)

    mx, no = res["arms"]["max"], res["arms"]["noisy_or"]

    # C1 -- INSTRUMENT IDENTITY. The copy under the ORIGINAL setting must
    # reproduce the ORIGINAL published figure, or it is a different instrument
    # and no arm from it means anything.
    res["controls"]["C1_copy_reproduces_the_original_under_max"] = {
        "what_would_fail_it": "the max arm of the rewritten file returning "
                              "anything but 0.2648 / 0.3929",
        "mrr": mx["all"].get("mrr"), "hits10": mx["all"].get("hits10"),
        "published_mrr": PUBLISHED_MRR, "published_hits10": PUBLISHED_HITS10,
        "ok": mx["all"].get("mrr") == PUBLISHED_MRR
              and mx["all"].get("hits10") == PUBLISHED_HITS10,
    }
    # C2 -- the two operators must actually differ somewhere, or F3's inertness
    # would be undetectable and this run measures nothing (A15).
    d = defaultdict(float)
    A.AGG = "max"
    A.bump(d, "k", 0.4); A.bump(d, "k", 0.5)
    m_val = d["k"]
    d2 = defaultdict(float)
    A.AGG = "noisy_or"
    A.bump(d2, "k", 0.4); A.bump(d2, "k", 0.5)
    n_val = d2["k"]
    res["controls"]["C2_operators_differ"] = {
        "what_would_fail_it": "both operators returning the same score for the "
                              "same two confidences, which would make the "
                              "rewrite inert by construction",
        "max_of_0.4_0.5": round(m_val, 6),
        "noisy_or_of_0.4_0.5": round(n_val, 6),
        "ok": m_val != n_val,
    }
    res["controls"]["C3_partition_recombines"] = {
        "what_would_fail_it": "the parts not summing to the test set",
        "sum": len(parts["same_pair"]) + len(parts["no_same_pair"]),
        "test": len(parts["all"]),
        "ok": len(parts["same_pair"]) + len(parts["no_same_pair"]) == len(parts["all"]),
    }

    clean_gain = round(no["no_same_pair"]["mrr"] - mx["no_same_pair"]["mrr"], 4)
    all_gain = round(no["all"]["mrr"] - mx["all"]["mrr"], 4)
    # Seed noise for this lane is documented at ~1300 triples of coverage on a
    # different measure; for filtered MRR there is no measured seed band, so the
    # threshold is stated as an ABSOLUTE and small one rather than dressed as a
    # noise estimate. Saying which it is, per A26.
    THRESHOLD = 0.002
    res["falsifiers"]["F1_noisy_or_does_not_help_the_clean_partition"] = {
        "question": "does noisy-OR raise filtered MRR on the no-same-pair part?",
        "max_no_same_pair": mx["no_same_pair"]["mrr"],
        "noisy_or_no_same_pair": no["no_same_pair"]["mrr"],
        "gain": clean_gain, "threshold_absolute": THRESHOLD,
        "threshold_is": "an absolute floor chosen before the run, NOT a measured "
                        "seed band -- no seed band for filtered MRR exists in "
                        "this lane and inventing one would be A26",
        "fired": clean_gain <= THRESHOLD,
        "meaning_if_fired": "the aggregation difference G30 named does not "
                            "explain the gap for this rule set",
    }
    res["falsifiers"]["F2_gain_is_bought_on_the_leaky_third"] = {
        "question": "is any gain confined to the blend and absent from the "
                    "leakage-free partition?",
        "all_gain": all_gain, "clean_gain": clean_gain,
        "fired": all_gain > THRESHOLD and clean_gain <= THRESHOLD,
        "meaning_if_fired": "the gain must NOT be published as a method "
                            "improvement",
    }
    res["falsifiers"]["F3_rewrite_is_inert"] = {
        "question": "did the aggregation change move any ranking at all?",
        "noisy_or_all_mrr": no["all"]["mrr"], "max_all_mrr": mx["all"]["mrr"],
        "fired": no["all"]["mrr"] == mx["all"]["mrr"],
        "meaning_if_fired": "the rewrite is inert and this run measures nothing "
                            "about aggregation -- family A, caught by checking",
    }

    res["elapsed_sec"] = round(time.time() - t0, 3)
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "agg.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls = []
    for name, why, canfail, null in (
        ("C1_copy_reproduces_the_original_under_max",
         "the rewritten file under the ORIGINAL setting must return the "
         "ORIGINAL published figure, or it is a different instrument and no "
         "arm from it means anything",
         "the max arm returning anything but 0.2648 / 0.3929",
         "a differing figure: the literals are transcribed from G34/RESULT.md"),
        ("C2_operators_differ",
         "the two aggregation operators must actually differ, or the rewrite "
         "is inert by construction and F3 could not detect it",
         "both operators returning the same score for the same confidences",
         "an equal pair, which is what an inert rewrite would produce"),
        ("C3_partition_recombines",
         "the parts must sum to the test set, as in G46",
         "parts that do not sum, or an empty part",
         "an unequal sum, which a mis-scoped mask would produce"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, null in (
        ("F1_noisy_or_does_not_help_the_clean_partition",
         "the hypothesis G30 named: that the aggregation operator explains "
         "part of the gap to published rule miners",
         "the no-same-pair gain is at or below the 0.002 floor stated first",
         "no gain, which the same harness reports for the max arm against "
         "itself"),
        ("F2_gain_is_bought_on_the_leaky_third",
         "the right to report any gain as a METHOD improvement",
         "the blended arm gains while the leakage-free partition does not",
         "a clean-partition gain, which is what would license the claim"),
        ("F3_rewrite_is_inert",
         "that this run measures anything about aggregation at all",
         "the noisy-OR arm returning exactly the max arm's blended MRR",
         "a moved number, which C2 shows the operators can produce"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[G34],
        artifacts=[os.path.join(HERE, "run.py"), os.path.join(HERE, "agg.py"),
                   os.path.join(HERE, "agg.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("agg_json", json.dumps(res, sort_keys=True))],
        falsifier="no gain on the leakage-free partition, which would say the "
                  "aggregation difference G30 named does not explain the gap "
                  "for this rule set",
        allow_dirty=True,
        note="G47: noisy-OR against max, one variable, reported on G46's "
             "partition so a gain cannot hide inside the leaky third.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
