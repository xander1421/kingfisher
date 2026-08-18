#!/usr/bin/env python3
"""G48 — a split that cannot leak, and the honest number that comes off it.

G46 measured that 30.0% of the current test set has a train edge on the same
entity pair and scores 0.5318 MRR against 0.1503 for the rest. G47 then showed
a real +0.0043 reads as +0.0098 until you partition. Both work AROUND the
defect. This removes it.

THE MECHANISM, AND IT HAS NO KNOB (A26): partition by UNORDERED ENTITY PAIR
instead of by triple. Every triple on a given {s, o} pair goes to one side, so
no test triple can have a train edge on its own pair in either direction -- at
zero, by construction, not below a threshold.

WHAT THIS IS NOT: FB15k-237's official test split, which is not in this
repository (`HUMAN_NEEDED.md` carries the ask). A pair-disjoint re-split of
TRAIN is a better LOCAL benchmark and not a literature comparand.

  python3 spikes/G48_pairdisjoint_split/split.py

Read-only outside this directory (§10).
"""
import json, os, random, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G34 = os.path.join(ROOT, "spikes", "G36_repro_g34")
sys.path.insert(0, G34)
import length1_constants as L                                    # noqa: E402

PUBLISHED_MRR, PUBLISHED_HITS10 = 0.2648, 0.3929
TRAIN_SIZE_TOLERANCE = 0.05          # F3's threshold, stated before the run
TEST_SIZE_TOLERANCE = 0.10           # C2's, likewise


def leak_count(train, test):
    """Test triples with a TRAIN edge on the same entity pair, either way."""
    pairs = defaultdict(set)
    for p, s, o in train:
        pairs[(s, o)].add(p)
    n = 0
    for p, s, o in test:
        if any(q != p for q in pairs.get((s, o), ())) or (o, s) in pairs:
            n += 1
    return n


def pair_disjoint_split(tri, seed, frac_train=0.70, frac_dev=0.15):
    """Group triples by UNORDERED entity pair, then assign whole groups.

    Greedy fill by shuffled group rather than by triple: groups are unequal in
    size, so the realised fractions cannot hit the targets exactly. That
    inexactness is F3's subject and is reported rather than tuned away.
    """
    groups = defaultdict(list)
    for p, s, o in tri:
        groups[(s, o) if s <= o else (o, s)].append((p, s, o))
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    n_target_train = int(len(tri) * frac_train)
    n_target_dev = int(len(tri) * frac_dev)
    train, dev, test = [], [], []
    for k in keys:
        g = groups[k]
        if len(train) < n_target_train:
            train.extend(g)
        elif len(dev) < n_target_dev:
            dev.extend(g)
        else:
            test.extend(g)
    return train, dev, test, len(groups)


def main():
    t0 = time.time()
    nt, npred, nent, tri, o_train, o_dev, o_test = L.load_dataset()
    assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)

    res = {"spike": "G48", "seed": f"0x{L.SEED:X}",
           "arms": {}, "controls": {}, "falsifiers": {}}

    # ---- arm 1: the ORIGINAL 70/15/15 shuffle, unchanged ---------------------
    def run(train, test, label):
        out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
        true_sp, true_po = L.build_filter_index(tri)
        sub, inv = L.mine_length1_rules(npred, byp, rev)
        ct, ch = L.mine_constant_rules(npred, byp)
        r = L.evaluate_link_prediction_full(
            test, out_adj, in_adj, true_sp, true_po, nent,
            rules_2hop=L.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev),
            rules_subsume=sub, rules_inverse=inv,
            rules_const_tail=ct, rules_const_head=ch)
        d = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
        d.update(n_train=len(train), n_test=len(test),
                 same_pair_leak=leak_count(train, test))
        res["arms"][label] = d
        print(f"  {label:16} train={len(train):>6} test={len(test):>6} "
              f"leak={d['same_pair_leak']:>6} mrr={d.get('mrr')} "
              f"h10={d.get('hits10')}", flush=True)
        return d

    a_orig = run(o_train, o_test, "original_shuffle")
    p_train, p_dev, p_test, n_groups = pair_disjoint_split(tri, L.SEED)
    a_pair = run(p_train, p_test, "pair_disjoint")

    res["groups"] = {"unordered_entity_pairs": n_groups,
                     "triples_per_pair_mean": round(nt / n_groups, 3)}

    # ---- controls -----------------------------------------------------------
    res["controls"]["C1_detector_still_fires_on_the_original_split"] = {
        "what_would_fail_it": "the same-pair detector reporting 0 on the "
                              "ORIGINAL split, which would satisfy F1 for the "
                              "wrong reason -- a detector blind everywhere (A15)",
        "original_leak": a_orig["same_pair_leak"],
        "original_leak_pct": round(100 * a_orig["same_pair_leak"] / a_orig["n_test"], 2),
        "ok": a_orig["same_pair_leak"] > 0,
    }
    test_ratio = a_pair["n_test"] / a_orig["n_test"]
    res["controls"]["C2_test_sets_are_comparable_in_size"] = {
        "what_would_fail_it": "a pair-disjoint test set far from 40,818, which "
                              "would make F2 a comparison of two sample sizes",
        "n_test_original": a_orig["n_test"], "n_test_pair": a_pair["n_test"],
        "ratio": round(test_ratio, 4), "tolerance": TEST_SIZE_TOLERANCE,
        "ok": abs(test_ratio - 1.0) <= TEST_SIZE_TOLERANCE,
    }
    res["controls"]["C3_instrument_unchanged_on_the_original_split"] = {
        "what_would_fail_it": "the original arm returning anything but "
                              "0.2648 / 0.3929, which would mean this is not "
                              "the instrument G34, G46 and G47 used",
        "mrr": a_orig.get("mrr"), "hits10": a_orig.get("hits10"),
        "published_mrr": PUBLISHED_MRR, "published_hits10": PUBLISHED_HITS10,
        "ok": a_orig.get("mrr") == PUBLISHED_MRR
              and a_orig.get("hits10") == PUBLISHED_HITS10,
    }

    # ---- falsifiers ---------------------------------------------------------
    res["falsifiers"]["F1_pair_disjoint_split_still_leaks"] = {
        "question": "does the pair-disjoint split leave ANY test triple with a "
                    "same-pair train edge?",
        "leak": a_pair["same_pair_leak"],
        "fired": a_pair["same_pair_leak"] > 0,
        "meaning_if_fired": "the constructor does not do what it claims and the "
                            "instrument is withdrawn -- 'small' is not accepted",
    }
    res["falsifiers"]["F2_leak_free_split_matches_the_headline"] = {
        "question": "does the leak-free split land within 0.002 of 0.2648?",
        "mrr_pair_disjoint": a_pair.get("mrr"),
        "mrr_original": a_orig.get("mrr"),
        "g46_no_same_pair_proxy": 0.1503,
        "fired": abs(a_pair["mrr"] - PUBLISHED_MRR) <= 0.002,
        "meaning_if_fired": "the leakage was not what carried 0.2648; G46's "
                            "mechanism is retracted and only its arithmetic kept",
    }
    train_ratio = a_pair["n_train"] / a_orig["n_train"]
    res["falsifiers"]["F3_train_volume_confound"] = {
        "question": "did pair-grouping move the TRAIN set size enough that the "
                    "drop could be training volume rather than leakage?",
        "n_train_original": a_orig["n_train"], "n_train_pair": a_pair["n_train"],
        "ratio": round(train_ratio, 4), "tolerance": TRAIN_SIZE_TOLERANCE,
        "fired": abs(train_ratio - 1.0) > TRAIN_SIZE_TOLERANCE,
        "meaning_if_fired": "report as 'the split changed and two things moved', "
                            "NOT as a leakage measurement",
    }

    res["not_the_official_split"] = {
        "what_this_is": "a pair-disjoint re-split of FB15k-237's official TRAIN "
                        "split, leak-free by construction",
        "what_it_is_not": "FB15k-237's official 20,466-triple test split, which "
                          "is not in this repository (HUMAN_NEEDED.md)",
        "literature_comparison": "UNAVAILABLE and recorded as unavailable",
        "threshold_note": "`.github/autoloop/PROGRAM.md:40` sets filtered_mrr "
                          ">= 0.2500 on the same line as (Current: 0.2648), so "
                          "the bar was derived from the number it gates. The "
                          "gate is UNINFORMATIVE: both arms here are measured "
                          "against it and neither is evidence about it. Not "
                          "re-baselined by this lane -- A22 in either direction.",
    }

    res["elapsed_sec"] = round(time.time() - t0, 3)
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "split.json"), "w") as f:
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
        ("C1_detector_still_fires_on_the_original_split",
         "the same-pair detector must still report the original split's "
         "leakage, or F1's zero is a blind detector rather than a clean split",
         "the detector reporting 0 on a split G46 measured at 30%",
         "a non-zero count, which is what the original split produces"),
        ("C2_test_sets_are_comparable_in_size",
         "the two test sets must be comparable, or F2 compares sample sizes",
         "a pair-disjoint test set far from 40,818 triples",
         "an out-of-tolerance ratio, which unequal pair sizes could produce"),
        ("C3_instrument_unchanged_on_the_original_split",
         "the original arm must return the published figure, or this is not "
         "the instrument G34, G46 and G47 used",
         "the original arm returning anything but 0.2648 / 0.3929",
         "a differing figure: the literals come from G34/RESULT.md"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, null in (
        ("F1_pair_disjoint_split_still_leaks",
         "the instrument itself: a gate that does not gate is withdrawn",
         "one or more test triples have a same-pair train edge",
         "a non-zero leak, which C1 shows the same detector reports"),
        ("F2_leak_free_split_matches_the_headline",
         "G46's mechanism: that same-pair leakage is what carried 0.2648",
         "the leak-free split lands within 0.002 of 0.2648",
         "a matching figure, which the original arm produces on this same run"),
        ("F3_train_volume_confound",
         "the right to read the drop as leakage rather than training volume",
         "the pair-disjoint train set differs from the original by over 5%",
         "an out-of-tolerance ratio, which greedy group fill could produce"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[G34],
        artifacts=[os.path.join(HERE, "split.py"),
                   os.path.join(HERE, "split.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("split_json", json.dumps(res, sort_keys=True))],
        falsifier="any same-pair train edge surviving in the pair-disjoint "
                  "test set, which would mean the constructor does not do what "
                  "it claims and the instrument is fiction",
        allow_dirty=True,
        note="G48: a split that cannot leak by construction, and the honest "
             "filtered MRR that comes off it. No knob, no threshold, nothing "
             "fitted to the answer.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
