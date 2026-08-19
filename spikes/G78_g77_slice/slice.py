#!/usr/bin/env python3
"""G78 — list G77's DistMult picks; 130/283 lose and were never named.

G77 4-way 0.3101 vs G75 0.3034 (+0.0067). F3 was thin: median +0.0037
and 130/283 DistMult keys lose to ComplEx on test. This row reconstructs
the masks (same sha256) and reads the keys. Not another selector.

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G78_g77_slice/slice.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)


def _numpy_pythons():
    out = [os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")]
    parent = os.path.dirname(ROOT)
    try:
        names = os.listdir(parent)
    except OSError:
        names = []
    for name in names:
        out.append(os.path.join(
            parent, name, "spikes", "S5_hdc_prototype", ".venv", "bin", "python"))
    return out


def _reexec_with_numpy():
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(sys.executable)
    for py in _numpy_pythons():
        if os.path.isfile(py) and os.path.abspath(py) != here:
            os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.stderr.write("numpy required (S5 venv missing)\n")
    sys.exit(2)


_reexec_with_numpy()

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G72_complex_all_entity"))
sys.path.insert(0, os.path.join(SPIKES, "G75_complex_gate"))
sys.path.insert(0, os.path.join(SPIKES, "G76_distmult_min10"))
sys.path.insert(0, os.path.join(SPIKES, "G77_distmult_select"))

import bayesian_lift as G51  # noqa: E402
import complex as G72  # noqa: E402
import distmult as G76  # noqa: E402
import kfcheck  # noqa: E402
import mix as G77  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
FOUR_SHA = "db2e8614dbe9a1308c61cb8229359a60c15f9852918bd9acf6acfc4fa988c4e4"
THREE_SHA = "17509ac9df1ea03725161559a59c22764e4b0cc7a44d19f980dfbdbba1063cae"
CX_EMB_SHA = "f54a5700099b517db4e3057bb1a72e7918032e9a9911089d17193207e9418eef"
DM_EMB_SHA = "61cb61cab600e60f6b2caaba15d13e4f9e2c6255c58265383d9357dacee077cc"
G77_REF = 0.3101
G75_REF = 0.3034
DELTA_REF = 0.0067


def mrr(xs):
    if not xs:
        return 0.0
    return round(sum(1.0 / x for x in xs) / len(xs), 4)


def rr_sum(xs):
    return sum(1.0 / x for x in xs)


def main():
    t0 = time.time()
    if not os.path.isfile(G77.CX_EMB) or not os.path.isfile(G77.DM_EMB):
        raise RuntimeError("need G75/G76 saved embeddings")

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    rels = sorted({r for _, r, _ in train_txt + valid_txt + test_txt})
    print(f"official test={len(test)} nent={nent} leak={leak}", flush=True)

    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    cx_hash = G77.sha256_file(G77.CX_EMB)
    dm_hash = G77.sha256_file(G77.DM_EMB)
    zc = np.load(G77.CX_EMB)
    E_re, E_im, R_re, R_im = zc["E_re"], zc["E_im"], zc["R_re"], zc["R_im"]
    zd = np.load(G77.DM_EMB)
    E, R = zd["E"], zd["R"]

    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    raw_rules = G77.load_or_mine_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in raw_rules:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)

    print("VALID ...", flush=True)
    valid_rows = G59.score_split(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    v_cx, v_cd, _ = G72.rank_complex(valid, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    G77.attach_named(valid_rows, valid, v_cx, v_cd, "complex")
    v_dm, v_dd, _ = G76.rank_distmult(valid, E, R, eval_sp, eval_po)
    G77.attach_named(valid_rows, valid, v_dm, v_dd, "distmult")
    four_mask, four_choice = G77.freeze_dir_select(valid_rows, G77.KEYS, default="distmult")
    three_mask, three_choice = G77.freeze_dir_select(valid_rows, G77.G75_KEYS, default="complex")
    print(f"4-way {four_mask['sha256'][:12]} 3-way {three_mask['sha256'][:12]}", flush=True)

    print("TEST ...", flush=True)
    test_rows = G59.score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    t_cx, t_cd, _ = G72.rank_complex(test, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    G77.attach_named(test_rows, test, t_cx, t_cd, "complex")
    t_dm, t_dd, _ = G76.rank_distmult(test, E, R, eval_sp, eval_po)
    G77.attach_named(test_rows, test, t_dm, t_dd, "distmult")

    n_all = len(test_rows)
    four = G77.apply_dir(test_rows, four_choice, "distmult")
    three = G77.apply_dir(test_rows, three_choice, "complex")
    dm_arm = G59.arm_from_rows(test_rows, "distmult")
    cx_arm = G59.arm_from_rows(test_rows, "complex")
    gated = G59.apply_gate(test_rows, G59.freeze_gate(valid_rows)[1])

    buckets = defaultdict(lambda: {
        "dm": [], "cx": [], "g51": [], "prior": [], "g77": [], "g75": [],
    })
    for r in test_rows:
        key = (int(r["p"]), r["direction"])
        b = buckets[key]
        b["dm"].append(r["ranks"]["distmult"])
        b["cx"].append(r["ranks"]["complex"])
        b["g51"].append(r["ranks"]["g51"])
        b["prior"].append(r["ranks"]["prior"])
        b["g77"].append(r["ranks"][four_choice.get(key, "distmult")])
        b["g75"].append(r["ranks"][three_choice.get(key, "complex")])

    listed = []
    for (p, d), v in buckets.items():
        n = len(v["dm"])
        if n == 0:
            continue
        contrib = (rr_sum(v["g77"]) - rr_sum(v["g75"])) / n_all
        dm_cx = (rr_sum(v["dm"]) - rr_sum(v["cx"])) / n_all
        listed.append({
            "p": p,
            "direction": d,
            "name": rels[p],
            "n_test": n,
            # G77 F3 counts keys IN the valid mask only; apply_dir still
            # defaults test-only keys to distmult/complex.
            "choice_g77": four_choice.get((p, d)),
            "choice_g75": three_choice.get((p, d)),
            "mrr_dm": mrr(v["dm"]),
            "mrr_cx": mrr(v["cx"]),
            "mrr_g51": mrr(v["g51"]),
            "mrr_g77": mrr(v["g77"]),
            "mrr_g75": mrr(v["g75"]),
            "contrib_g_minus_f": round(contrib, 6),
            "contrib_dm_minus_cx": round(dm_cx, 6),
        })
    listed.sort(key=lambda row: -row["contrib_g_minus_f"])

    dm_keys = [row for row in listed if row["choice_g77"] == "distmult"]
    dm_lose = [row for row in dm_keys if row["mrr_dm"] <= row["mrr_cx"]]
    pos = [row for row in listed if row["contrib_g_minus_f"] > 0]
    top10 = listed[:10]
    top10_share = sum(row["contrib_g_minus_f"] for row in top10)
    headline_delta = round(four["mrr"] - three["mrr"], 4)
    f1_share = top10_share / DELTA_REF if DELTA_REF else 0.0
    lose_mass = -sum(row["contrib_dm_minus_cx"] for row in dm_keys if row["contrib_dm_minus_cx"] < 0)

    dm_head = [row for row in dm_keys if row["direction"] == "head"]
    dm_head_n = sum(row["n_test"] for row in dm_head)
    dm_head_dm = mrr([r for row in dm_head for r in buckets[(row["p"], "head")]["dm"]])
    dm_head_cx = mrr([r for row in dm_head for r in buckets[(row["p"], "head")]["cx"]])

    f1_fired = f1_share >= 0.50
    f2_fired = lose_mass >= DELTA_REF
    f3_fired = dm_head_dm <= dm_head_cx

    c1_ok = four_mask["sha256"] == FOUR_SHA
    c2_ok = abs(four["mrr"] - G77_REF) <= 0.0005
    c3_ok = three_mask["sha256"].startswith("17509ac9df1e") and abs(three["mrr"] - G75_REF) <= 0.0005
    c4_ok = len(test) == 20466 and leak == 0
    c5_ok = cx_hash == CX_EMB_SHA and dm_hash == DM_EMB_SHA

    res = {
        "spike": "G78",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "slice_g77_distmult_picks",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "protocol": "filtered_all_entity",
        "n_test": len(test),
        "reconstructed": {
            "four_sha256": four_mask["sha256"],
            "three_sha256": three_mask["sha256"],
            "four_counts": dict(four_mask["counts"]),
            "three_counts": dict(three_mask["counts"]),
        },
        "arms": {
            "four_way": four,
            "three_way": three,
            "distmult": dm_arm,
            "complex": cx_arm,
            "g59_gate": gated,
        },
        "headline_delta": headline_delta,
        "n_all_queries": n_all,
        "distmult_picks": {
            "n_keys": len(dm_keys),
            "n_lose_vs_complex": len(dm_lose),
            "n_test": sum(row["n_test"] for row in dm_keys),
        },
        "concentration": {
            "top10_contrib": round(top10_share, 6),
            "top10_share_of_delta": round(f1_share, 4),
            "n_positive_keys": len(pos),
            "top10": [
                {k: row[k] for k in (
                    "p", "direction", "name", "n_test", "choice_g77",
                    "choice_g75", "mrr_dm", "mrr_cx", "mrr_g77", "mrr_g75",
                    "contrib_g_minus_f",
                )}
                for row in top10
            ],
        },
        "loser_mass": {
            "n_lose": len(dm_lose),
            "neg_dm_cx_mass": round(lose_mass, 6),
            "top_losers": [
                {k: row[k] for k in (
                    "p", "direction", "name", "n_test", "mrr_dm", "mrr_cx",
                    "contrib_dm_minus_cx", "contrib_g_minus_f",
                )}
                for row in sorted(dm_lose, key=lambda r: r["contrib_dm_minus_cx"])[:10]
            ],
        },
        "distmult_heads": {
            "n_keys": len(dm_head),
            "n_test": dm_head_n,
            "mrr_dm": dm_head_dm,
            "mrr_cx": dm_head_cx,
        },
        "keys": listed,
        "controls": {
            "C1_four_sha": {"expected": FOUR_SHA, "observed": four_mask["sha256"], "ok": c1_ok},
            "C2_four_mrr": {"expected": G77_REF, "observed": four["mrr"], "ok": c2_ok},
            "C3_three": {"expected_sha_prefix": "17509ac9df1e", "observed": three_mask["sha256"],
                         "mrr": three["mrr"], "ok": c3_ok},
            "C4_test_leak": {"n": len(test), "leak": leak, "ok": c4_ok},
            "C5_emb_hash": {"complex": cx_hash, "distmult": dm_hash, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_concentrated": {
                "top10_share": round(f1_share, 4),
                "top10_contrib": round(top10_share, 6),
                "delta_ref": DELTA_REF,
                "fired": f1_fired,
                "description": "Fires if top-10 keys carry >= 50% of +0.0067",
            },
            "F2_losers_cover_headline": {
                "neg_dm_cx_mass": round(lose_mass, 6),
                "delta_ref": DELTA_REF,
                "n_lose": len(dm_lose),
                "fired": f2_fired,
                "description": "Fires if DistMult-vs-ComplEx loser mass >= +0.0067",
            },
            "F3_head_distmult_loses": {
                "head_dm": dm_head_dm,
                "head_cx": dm_head_cx,
                "fired": f3_fired,
                "description": "Fires if DistMult-picked heads TEST DM <= CX",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "slice.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G78 ===", flush=True)
    print(f"4-way {four['mrr']:.4f} 3-way {three['mrr']:.4f} Δ={headline_delta:+.4f}", flush=True)
    print(
        f"dm picks {len(dm_keys)} lose {len(dm_lose)} top10 share {f1_share:.3f} "
        f"loser mass {lose_mass:.4f}",
        flush=True,
    )
    print(f"dm heads dm={dm_head_dm:.4f} cx={dm_head_cx:.4f} n={dm_head_n}", flush=True)
    print(f"F1={f1_fired} F2={f2_fired} F3={f3_fired} elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_four_sha", why="reconstruct G77 4-way mask",
                can_fail_because="select drifted", null_must_contain="sha mismatch"),
        Control("C2_four_mrr", why="G77 0.3101",
                can_fail_because="scorer drifted", null_must_contain="mrr!=0.3101"),
        Control("C3_three", why="G75 0.3034 / sha 17509ac9df1e",
                can_fail_because="3-way drifted", null_must_contain="3-way mismatch"),
        Control("C4_test_leak", why="official test 20466 leak 0",
                can_fail_because="wrong split", null_must_contain="n!=20466 or leak"),
        Control("C5_emb_hash", why="same embeddings as G77",
                can_fail_because="npz swapped", null_must_contain="hash miss"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_four_sha"])
    controls[1].observe(c2_ok, res["controls"]["C2_four_mrr"])
    controls[2].observe(c3_ok, res["controls"]["C3_three"])
    controls[3].observe(c4_ok, res["controls"]["C4_test_leak"])
    controls[4].observe(c5_ok, res["controls"]["C5_emb_hash"])

    falsifiers = [
        Falsifier("F1_concentrated", refutes="that +0.0067 is spread across DistMult picks",
                  fires_when="top-10 keys carry >= 50% of +0.0067",
                  null_must_contain="share of delta"),
        Falsifier("F2_losers_cover_headline",
                  refutes="that DistMult wins dominate the 130 losses",
                  fires_when="negative DistMult-vs-ComplEx mass >= +0.0067",
                  null_must_contain="loser mass"),
        Falsifier("F3_head_distmult_loses",
                  refutes="that DistMult-picked heads stay DistMult-better",
                  fires_when="TEST DistMult <= ComplEx on DistMult-picked heads",
                  null_must_contain="head dm vs cx"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_concentrated"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_losers_cover_headline"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_head_distmult_loses"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G77_distmult_select"),
              os.path.join(SPIKES, "G75_complex_gate"),
              os.path.join(SPIKES, "G76_distmult_min10")],
        artifacts=[os.path.join(HERE, "slice.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("slice_json", json.dumps(res, sort_keys=True))],
        falsifier="G77 +0.0067 is concentrated, or loser mass covers it, or DistMult heads lose",
        allow_dirty=True,
        note="G78: slice G77 DistMult picks. Do not move G59 0.2679. No literature MRR.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
