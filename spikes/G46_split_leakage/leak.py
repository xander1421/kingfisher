#!/usr/bin/env python3
"""G46 — how much of G34's 0.2648 is the RE-SPLIT rather than the method?

`spikes/S52_realkg/triples.bin` is FB15k-237's OFFICIAL TRAIN SPLIT (272,115
triples, 237 relations, 14,505 entities -- `realkg.c`'s own header says so).
`length1_constants.py::load_dataset()` re-splits it 70/15/15 under seed
0xC0FFEE, so what G34 calls "the FB15k-237 test split" is a random 15% slice of
TRAIN and the official test set is never touched.

FB15k-237 exists because FB15k leaked through inverse relations, and the 237
version removed that leakage RELATIVE TO ITS OWN train/test boundary. A fresh
random split re-opens it at a new boundary. Measured: 30.0% of the re-split's
test triples have a train edge on the same entity pair (`fraction.out`).

This partitions the SAME test set on that property and runs the SAME published
full-system arm on each part. Nothing about the miner, the ranker or the filter
is modified: the rules, the graph index and the filter index are built exactly
as `main()` builds them, and the only variable is which test triples are scored.

  python3 spikes/G46_split_leakage/leak.py
"""
import json, os, random, struct, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G34 = os.path.join(ROOT, "spikes", "G36_repro_g34")
sys.path.insert(0, G34)
import length1_constants as L                                   # noqa: E402

PUBLISHED_MRR, PUBLISHED_HITS10 = 0.2648, 0.3929


def same_pair_mask(train, test):
    """True where a TRAIN edge joins the same entity pair in either direction.

    Forward matches require a DIFFERENT predicate -- an identical (p, s, o) in
    train would be the test triple itself, and the split is disjoint, but the
    guard is stated rather than assumed.
    """
    pairs = defaultdict(set)
    for p, s, o in train:
        pairs[(s, o)].add(p)
    out = []
    for p, s, o in test:
        fwd = any(q != p for q in pairs.get((s, o), ()))
        inv = (o, s) in pairs
        out.append(fwd or inv)
    return out, pairs


def main():
    t0 = time.time()
    nt, npred, nent, tri, train, dev, test = L.load_dataset()
    assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)

    out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
    true_sp, true_po = L.build_filter_index(tri)
    rules_2hop = L.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_subsume, rules_inverse = L.mine_length1_rules(npred, byp, rev)
    rules_const_tail, rules_const_head = L.mine_constant_rules(npred, byp)
    full = dict(rules_2hop=rules_2hop, rules_subsume=rules_subsume,
                rules_inverse=rules_inverse, rules_const_tail=rules_const_tail,
                rules_const_head=rules_const_head)

    mask, pairs = same_pair_mask(train, test)
    leaky = [t for t, m in zip(test, mask) if m]
    clean = [t for t, m in zip(test, mask) if not m]

    res = {"spike": "G46", "seed": f"0x{L.SEED:X}",
           "corpus": {"nt": nt, "npred": npred, "nent": nent,
                      "equals_fb15k237_official_train": nt == 272115},
           "partition": {"test": len(test), "same_pair": len(leaky),
                         "no_same_pair": len(clean),
                         "same_pair_pct": round(100 * len(leaky) / len(test), 2)},
           "arms": {}, "controls": {}, "falsifiers": {}}

    for name, subset in (("all", test), ("same_pair", leaky),
                         ("no_same_pair", clean)):
        r = L.evaluate_link_prediction_full(subset, out_adj, in_adj, true_sp,
                                            true_po, nent, **full)
        res["arms"][name] = {k: (round(v, 4) if isinstance(v, float) else v)
                             for k, v in r.items()}
        print(f"  {name:14} n={len(subset):>6}  {res['arms'][name]}", flush=True)

    a_all, a_leak, a_clean = (res["arms"][k] for k in
                              ("all", "same_pair", "no_same_pair"))

    # C1 -- the unmodified protocol must reproduce the PUBLISHED figure before
    # any new number here is believed. The literals are transcribed from
    # G34/RESULT.md, not read from this run.
    res["controls"]["C1_reproduces_published_headline"] = {
        "what_would_fail_it": "an `all` arm that does not return the published "
                              "0.2648 / 0.3929, which would mean this harness "
                              "is not the instrument that produced them",
        "mrr": a_all.get("mrr"), "hits10": a_all.get("hits10"),
        "published_mrr": PUBLISHED_MRR, "published_hits10": PUBLISHED_HITS10,
        "ok": a_all.get("mrr") == PUBLISHED_MRR
              and a_all.get("hits10") == PUBLISHED_HITS10,
    }
    # C2 -- the same-pair detector must be matching PAIRS and not just density.
    rng = random.Random(999)
    ctl = sum(1 for _ in range(len(test))
              if ((rng.randrange(nent), rng.randrange(nent)) in pairs))
    res["controls"]["C2_detector_matches_pairs_not_density"] = {
        "what_would_fail_it": "a randomised-pair control returning a rate "
                              "comparable to the measured 30%, which would mean "
                              "the detector matches any pair at all",
        "randomised_pair_hits": ctl,
        "randomised_pair_pct": round(100 * ctl / len(test), 3),
        "ok": ctl / len(test) < 0.01,
    }
    # C3 -- the two parts must recombine into the whole, or the partition lost
    # or double-counted queries.
    res["controls"]["C3_partition_is_exhaustive_and_disjoint"] = {
        "what_would_fail_it": "the parts not summing to the whole",
        "sum": len(leaky) + len(clean), "test": len(test),
        "ok": len(leaky) + len(clean) == len(test) and len(leaky) > 0
              and len(clean) > 0,
    }

    res["falsifiers"]["F2_clean_subset_matches_the_headline"] = {
        "question": "is filtered MRR on test triples with NO same-pair train "
                    "edge within seed noise of the published 0.2648?",
        "mrr_all": a_all.get("mrr"), "mrr_same_pair": a_leak.get("mrr"),
        "mrr_no_same_pair": a_clean.get("mrr"),
        "drop_vs_published": (round(PUBLISHED_MRR - a_clean["mrr"], 4)
                              if a_clean.get("mrr") is not None else None),
        "fired": (a_clean.get("mrr") is not None
                  and abs(a_clean["mrr"] - PUBLISHED_MRR) < 0.01),
        "meaning_if_fired": "the re-split contributed nothing measurable and "
                            "the finding shrinks to labelling only",
    }
    res["falsifiers"]["F3_same_pair_share_too_small_to_matter"] = {
        "question": "can a 30% share carry a 0.063 -> 0.265 jump at all?",
        "same_pair_pct": res["partition"]["same_pair_pct"],
        "fired": res["partition"]["same_pair_pct"] < 10.0,
        "meaning_if_fired": "the causal story is wrong even if the number moves",
    }

    # CEILING, in the artifact and not only in the prose: `no_same_pair` is NOT
    # the official FB15k-237 test split. It is the re-split with ONE leakage
    # structure removed -- a same-entity-pair train edge. The official split
    # differs in more ways than that, so this number is a PROXY for what an
    # official-split evaluation would report and is not a substitute for one.
    # The official test triples are not on disk; recording that rather than
    # quoting a literature figure against them.
    res["ceiling_proxy_not_official_split"] = {
        "what_this_is": "the re-split with same-entity-pair test triples removed",
        "what_it_is_not": "an evaluation on FB15k-237's official 20,466-triple "
                          "test split, which is not present in this repository",
        "literature_comparison": "UNAVAILABLE, recorded as unavailable rather "
                                 "than quoted (G35: 7 of 7 external attributions "
                                 "in this tree resolve to nothing under corpus/)",
    }

    res["elapsed_sec"] = round(time.time() - t0, 3)
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "leak.json"), "w") as f:
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
        ("C1_reproduces_published_headline",
         "the unmodified protocol must return the published figure before any "
         "number from this harness is believed",
         "an `all` arm that does not return 0.2648 / 0.3929",
         "a differing figure: the literals are transcribed from G34/RESULT.md, "
         "not read from this run"),
        ("C2_detector_matches_pairs_not_density",
         "the same-pair detector must be matching entity PAIRS, not the "
         "density of a graph where any pair is likely",
         "a randomised-pair control returning a rate near the measured 30%",
         "a high rate, which is what a density artefact would produce"),
        ("C3_partition_is_exhaustive_and_disjoint",
         "the two parts must recombine into the whole, or queries were lost "
         "or double counted",
         "parts that do not sum to the test set, or an empty part",
         "an unequal sum, which a mis-scoped mask would produce"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, null in (
        ("F2_clean_subset_matches_the_headline",
         "the whole row: if the leakage-free part scores like the headline, "
         "the re-split contributed nothing and this is a labelling defect",
         "filtered MRR on the no-same-pair part is within 0.01 of 0.2648",
         "both outcomes: the same arm on the same rules scores the `all` "
         "partition at exactly the published figure"),
        ("F3_same_pair_share_too_small_to_matter",
         "the causal story: a share too small could not carry the jump "
         "whatever the restricted MRR says",
         "fewer than 10% of test triples have a same-pair train edge",
         "a small share, which the randomised control shows this detector "
         "does report when the pairs are not there"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[G34],
        artifacts=[os.path.join(HERE, "leak.py"),
                   os.path.join(HERE, "leak.json"),
                   os.path.join(HERE, "fraction.out")],
        controls=controls, falsifiers=falsifiers,
        captures=[("leak_json", json.dumps(res, sort_keys=True))],
        falsifier="filtered MRR on the leakage-free part landing within 0.01 "
                  "of the published 0.2648, which would mean the re-split "
                  "contributed nothing measurable and the finding is labelling "
                  "only",
        allow_dirty=True,
        note="G46: how much of G34's 0.2648 is the re-split rather than the "
             "method? Same rules, same ranker, same filter; the only variable "
             "is which test triples are scored.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
