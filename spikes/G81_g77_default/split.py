#!/usr/bin/env python3
"""G81 — how much of G77 +0.0067 is the 210-key small-n DistMult default.

G75 defaulted n<20 to ComplEx. G77 defaulted n<20 to DistMult.
G78 listed DistMult picks but did not split valid-picked vs defaulted.

  python3 spikes/G81_g77_default/split.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
MIN_N = 20
DELTA = 0.0067
FOUR_SHA = "db2e8614dbe9a1308c61cb8229359a60c15f9852918bd9acf6acfc4fa988c4e4"
G78 = os.path.join(SPIKES, "G78_g77_slice", "slice.json")
G77 = os.path.join(SPIKES, "G77_distmult_select", "select.json")
LEFTOVER = 1.0 - 0.7842  # G78 top10 share; 0.2158


def main():
    g77 = json.loads(open(G77, encoding="utf-8").read())
    g78 = json.loads(open(G78, encoding="utf-8").read())
    four = g77["valid_select_four"]
    choice = four["choice"]
    n_small_file = four["n_small_default"]

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)

    n_valid = defaultdict(int)
    for p, _s, _o in valid:
        n_valid[(p, "head")] += 1
        n_valid[(p, "tail")] += 1

    n_small = 0
    small_keys = set()
    picked_dm = set()
    for k, arm in choice.items():
        p_s, d = k.split(":")
        key = (int(p_s), d)
        n = n_valid[key]
        if n < MIN_N:
            n_small += 1
            small_keys.add(key)
        if arm == "distmult" and n >= MIN_N:
            picked_dm.add(key)

    by_key = {}
    for row in g78.get("keys") or []:
        by_key[(int(row["p"]), row["direction"])] = row

    def sum_contrib(keys):
        return sum(float(by_key[k]["contrib_g_minus_f"]) for k in keys if k in by_key)

    default_contrib = sum_contrib(small_keys)
    picked_contrib = sum_contrib(picked_dm)
    # other: g51/prior/complex valid-picked changes, and test-only defaults not in four_choice
    all_contrib = sum(float(r["contrib_g_minus_f"]) for r in g78.get("keys") or [])
    other = all_contrib - default_contrib - picked_contrib

    default_share = default_contrib / DELTA if DELTA else 0.0
    picked_share = picked_contrib / DELTA if DELTA else 0.0

    top10 = g78.get("concentration", {}).get("top10") or []
    top10_small = []
    for row in top10:
        key = (int(row["p"]), row["direction"])
        n = n_valid[key]
        if n < MIN_N:
            top10_small.append({"p": row["p"], "direction": row["direction"], "n_valid": n})

    default_n_test = sum(int(by_key[k]["n_test"]) for k in small_keys if k in by_key)
    picked_n_test = sum(int(by_key[k]["n_test"]) for k in picked_dm if k in by_key)

    f1_fired = default_share >= 0.50
    f2_fired = default_share >= LEFTOVER - 1e-9
    f3_fired = len(top10_small) > 0

    four_mrr = (g78.get("arms") or {}).get("four_way", {}).get("mrr")
    three_mrr = (g78.get("arms") or {}).get("three_way", {}).get("mrr")
    c1_ok = n_small == 210 and n_small_file == 210
    c2_ok = four.get("sha256") == FOUR_SHA
    c3_ok = abs(all_contrib - DELTA) <= 0.00015
    c4_ok = abs((four_mrr or 0) - 0.3101) <= 0.0005 and leak == 0 and len(test) == 20466

    rec = {
        "spike": "G81",
        "split": "official FB15k-237 train/valid/test",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_test": len(test),
        "n_small_default": n_small,
        "n_valid_picked_distmult": len(picked_dm),
        "delta_ref": DELTA,
        "contrib": {
            "all_keys": round(all_contrib, 6),
            "default_nlt20": round(default_contrib, 6),
            "valid_picked_distmult": round(picked_contrib, 6),
            "other": round(other, 6),
            "default_share": round(default_share, 4),
            "picked_share": round(picked_share, 4),
            "default_n_test": default_n_test,
            "picked_n_test": picked_n_test,
        },
        "top10_small_n": top10_small,
        "controls": {
            "C1_n_small": {"n": n_small, "file": n_small_file, "ok": c1_ok},
            "C2_four_sha": {"expected": FOUR_SHA, "observed": four.get("sha256"), "ok": c2_ok},
            "C3_delta": {"sum_contrib": round(all_contrib, 6), "ref": DELTA, "ok": c3_ok},
            "C4_g78_arms": {"four": four_mrr, "three": three_mrr, "leak": leak, "ok": c4_ok},
        },
        "falsifiers": {
            "F1_default_is_headline": {
                "default_share": round(default_share, 4),
                "fired": f1_fired,
                "description": "Fires if defaulted share of +0.0067 >= 0.50",
            },
            "F2_leftover_is_default": {
                "default_share": round(default_share, 4),
                "leftover": round(LEFTOVER, 4),
                "fired": f2_fired,
                "description": "Fires if defaulted share >= G78 leftover 0.216",
            },
            "F3_top10_are_defaults": {
                "n_top10_small": len(top10_small),
                "fired": f3_fired,
                "description": "Fires if a G78 top-10 key has n_valid < 20",
            },
        },
    }
    out = os.path.join(HERE, "split.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")

    print("=== G81 ===")
    print(f"n_small={n_small} picked_dm={len(picked_dm)}")
    print(
        f"default {default_contrib:.6f} share={default_share:.4f} "
        f"picked {picked_contrib:.6f} share={picked_share:.4f} other {other:.6f}"
    )
    print(f"F1={f1_fired} F2={f2_fired} F3={f3_fired} top10_small={len(top10_small)}")

    controls = [
        Control("C1_n_small", why="G77 210 small-n keys",
                can_fail_because="valid counts drifted", null_must_contain="n!=210"),
        Control("C2_four_sha", why="G77 mask db2e8614dbe9",
                can_fail_because="choice rewritten", null_must_contain="sha mismatch"),
        Control("C3_delta", why="G78 contribs sum to +0.0067",
                can_fail_because="G78 keys missing", null_must_contain="sum!=0.0067"),
        Control("C4_g78_arms", why="G78 4-way 0.3101 leak 0",
                can_fail_because="wrong G78 file", null_must_contain="mrr/leak"),
    ]
    controls[0].observe(c1_ok, rec["controls"]["C1_n_small"])
    controls[1].observe(c2_ok, rec["controls"]["C2_four_sha"])
    controls[2].observe(c3_ok, rec["controls"]["C3_delta"])
    controls[3].observe(c4_ok, rec["controls"]["C4_g78_arms"])
    falsifiers = [
        Falsifier("F1_default_is_headline",
                  refutes="that +0.0067 is mostly type predicates not the default",
                  fires_when="defaulted share >= 0.50",
                  null_must_contain="default share"),
        Falsifier("F2_leftover_is_default",
                  refutes="that G78 leftover 21.6% is not the 210-key default",
                  fires_when="defaulted share >= 0.216",
                  null_must_contain="leftover vs default"),
        Falsifier("F3_top10_are_defaults",
                  refutes="that G78 top-10 are high-mass valid-picked keys",
                  fires_when="a top-10 key has n_valid < 20",
                  null_must_contain="top10 n_valid"),
    ]
    falsifiers[0].observe(f1_fired, rec["falsifiers"]["F1_default_is_headline"])
    falsifiers[1].observe(f2_fired, rec["falsifiers"]["F2_leftover_is_default"])
    falsifiers[2].observe(f3_fired, rec["falsifiers"]["F3_top10_are_defaults"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G77_distmult_select"),
              os.path.join(SPIKES, "G78_g77_slice"), CORPUS],
        artifacts=[os.path.join(HERE, "split.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("split_json", json.dumps(rec, sort_keys=True))],
        falsifier="the 210-key default is the headline, or the leftover, or the top-10",
        allow_dirty=True,
        note="G81: split G77 +0.0067 into small-n DistMult default vs valid-picked. Do not quote SOTA.",
    )
    print(f"D6 certify ok={ok}")
    for pr in problems:
        print("PROBLEM", pr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
