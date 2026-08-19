#!/usr/bin/env python3
"""H160 — Adversarial Audit & RotatE Boundary Ablation on G88 5-Way Hybrid.

Attacks the G88 headline (0.3143 MRR) and evaluates whether RotatE selections:
1. Generalize to test queries with positive MRR delta over DistMult on those 26 keys.
2. Outperform ComplEx on those 26 keys (verifying rotational distance over bilinear dot product).
3. Exhibit specific relation properties (e.g. 1-to-N / N-to-1 cardinality or symmetry).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict

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

import numpy as np
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G64_bidirectional_topologies"))
sys.path.insert(0, os.path.join(SPIKES, "G72_complex_all_entity"))
sys.path.insert(0, os.path.join(SPIKES, "G75_complex_gate"))
sys.path.insert(0, os.path.join(SPIKES, "G76_distmult_min10"))
sys.path.insert(0, os.path.join(SPIKES, "G79_rotate_all_entity"))

import bayesian_lift as G51
import complex as G72
import distmult as G76
import hybrid as G75
import kfcheck
import official as G59
import rotate as G79
import run_g64 as G64
from provenance import Control, Falsifier

CORPUS = G59.CORPUS
CX_EMB = os.path.join(SPIKES, "G75_complex_gate", "complex_emb.npz")
DM_EMB = os.path.join(SPIKES, "G76_distmult_min10", "distmult_emb.npz")
ROT_EMB = os.path.join(SPIKES, "G79_rotate_all_entity", "rotate_emb.npz")
G88_RES = os.path.join(SPIKES, "G88_5way_hybrid", "result.json")
KEYS = ("distmult", "complex", "rotate", "g64", "prior")
MIN_N = 20

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

def attach_named(rows, queries, ranks, dirs, name):
    if len(rows) != 2 * len(queries) or len(ranks) != len(rows):
        raise RuntimeError(f"{name} length drift {len(rows)} vs {len(ranks)}")
    if not (dirs[0] == "tail" and dirs[1] == "head"):
        ranks, dirs = G75.unbatch_complex_ranks(ranks, dirs, len(queries))
    for i, r in enumerate(rows):
        if r["direction"] != dirs[i]:
            raise RuntimeError(f"{name} dir drift at {i}: {r['direction']} vs {dirs[i]}")
        r["ranks"][name] = float(ranks[i])
    return rows

def freeze_dir_select(valid_rows, keys, default):
    buckets = defaultdict(lambda: {k: [] for k in keys})
    for r in valid_rows:
        key = (int(r["p"]), r["direction"])
        for k in keys:
            buckets[key][k].append(r["ranks"][k])
    choice = {}
    counts = defaultdict(int)
    for key, v in buckets.items():
        n = len(v[default])
        if n < MIN_N:
            choice[key] = default
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in keys}
            choice[key] = max(scores, key=scores.get)
        counts[choice[key]] += 1
    return choice, counts

def main() -> int:
    t0 = time.time()
    print("=== Spike H160: Adversarial Audit of G88 5-Way Hybrid (RotatE Ablation) ===")

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"Official split: train={len(train)} valid={len(valid)} test={len(test)} npred={npred} nent={nent}")

    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    idx = G59.slim_index(train)

    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    for p, s, o in train:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)

    all_rules_by_head, _ = G64.mine_all_4_topologies_fast(train, out_adj, in_adj, npred)

    zc = np.load(CX_EMB)
    E_re_c, E_im_c, R_re_c, R_im_c = zc["E_re"], zc["E_im"], zc["R_re"], zc["R_im"]

    zd = np.load(DM_EMB)
    E_d, R_d = zd["E"], zd["R"]

    zr = np.load(ROT_EMB)
    E_re_r, E_im_r, theta_r = zr["E_re"], zr["E_im"], zr["theta"]

    # 1. Validation selection
    print("Re-evaluating VALID split to isolate 26 RotatE-selected keys...", flush=True)
    valid_rows = G64.score_split_4topo(valid, nent, all_rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    for r in valid_rows:
        r["ranks"]["g64"] = r["ranks"].pop("g51")

    v_cx, v_cd, _ = G72.rank_complex(valid, E_re_c, E_im_c, R_re_c, R_im_c, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_cx, v_cd, "complex")

    v_dm, v_dd, _ = G76.rank_distmult(valid, E_d, R_d, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_dm, v_dd, "distmult")

    v_rot, v_rd, _ = G79.rank_rotate(valid, E_re_r, E_im_r, theta_r, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_rot, v_rd, "rotate")

    five_choice, counts = freeze_dir_select(valid_rows, KEYS, default="distmult")
    rotate_keys = {k for k, v in five_choice.items() if v == "rotate"}
    print(f"Isolated {len(rotate_keys)} RotatE-selected keys on valid (counts: {dict(counts)})")

    # 2. Score TEST split for all 3 models on RotatE-selected keys
    print("Scoring TEST split across RotatE, DistMult, and ComplEx on RotatE-selected keys...", flush=True)
    test_rows = G64.score_split_4topo(test, nent, all_rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    for r in test_rows:
        r["ranks"]["g64"] = r["ranks"].pop("g51")

    t_cx, t_cd, _ = G72.rank_complex(test, E_re_c, E_im_c, R_re_c, R_im_c, eval_sp, eval_po)
    attach_named(test_rows, test, t_cx, t_cd, "complex")

    t_dm, t_dd, _ = G76.rank_distmult(test, E_d, R_d, eval_sp, eval_po)
    attach_named(test_rows, test, t_dm, t_dd, "distmult")

    t_rot, t_rd, _ = G79.rank_rotate(test, E_re_r, E_im_r, theta_r, eval_sp, eval_po)
    attach_named(test_rows, test, t_rot, t_rd, "rotate")

    # Filter test rows for RotatE keys
    rot_test_rows = [r for r in test_rows if (int(r["p"]), r["direction"]) in rotate_keys]
    n_rot_test = len(rot_test_rows)
    print(f"\nEvaluating {n_rot_test} test queries ({n_rot_test / len(test_rows) * 100:.2f}% of test) under RotatE keys:")

    ranks_rot = [r["ranks"]["rotate"] for r in rot_test_rows]
    ranks_dm = [r["ranks"]["distmult"] for r in rot_test_rows]
    ranks_cx = [r["ranks"]["complex"] for r in rot_test_rows]

    mrr_rot = sum(1.0 / x for x in ranks_rot) / n_rot_test if n_rot_test else 0.0
    mrr_dm = sum(1.0 / x for x in ranks_dm) / n_rot_test if n_rot_test else 0.0
    mrr_cx = sum(1.0 / x for x in ranks_cx) / n_rot_test if n_rot_test else 0.0

    delta_vs_dm = mrr_rot - mrr_dm
    delta_vs_cx = mrr_rot - mrr_cx

    print(f"  RotatE Test MRR:   {mrr_rot:.4f}")
    print(f"  DistMult Test MRR: {mrr_dm:.4f} (RotatE Δ = {delta_vs_dm:+.4f})")
    print(f"  ComplEx Test MRR:  {mrr_cx:.4f} (RotatE Δ = {delta_vs_cx:+.4f})")

    # Predicate-level gain analysis
    per_pred_gain = defaultdict(lambda: {"n": 0, "rot_mrr_mass": 0.0, "dm_mrr_mass": 0.0, "cx_mrr_mass": 0.0})
    for r in rot_test_rows:
        p = int(r["p"])
        per_pred_gain[p]["n"] += 1
        per_pred_gain[p]["rot_mrr_mass"] += 1.0 / r["ranks"]["rotate"]
        per_pred_gain[p]["dm_mrr_mass"] += 1.0 / r["ranks"]["distmult"]
        per_pred_gain[p]["cx_mrr_mass"] += 1.0 / r["ranks"]["complex"]

    distinct_preds = len(per_pred_gain)
    total_net_gain_mass_dm = sum(v["rot_mrr_mass"] - v["dm_mrr_mass"] for v in per_pred_gain.values())
    print(f"\nNet MRR Mass Gain over DistMult: {total_net_gain_mass_dm:+.2f} across {distinct_preds} distinct predicates.")

    # Controls & Falsifiers
    c1_ok = len(test) == 20466
    c2_ok = len(rotate_keys) == 26
    c3_ok = len(set(train) & set(test)) == 0

    controls = [
        Control("C1_test_size", why="20,466 test triples", can_fail_because="corrupted split", null_must_contain="wrong size"),
        Control("C2_rotate_keys_count", why="Exactly 26 RotatE-selected keys from validation", can_fail_because="selection drift", null_must_contain="key count mismatch"),
        Control("C3_zero_leak", why="Zero leak between train and test", can_fail_because="data leakage", null_must_contain="leakage"),
    ]
    controls[0].observe(c1_ok, {"test_len": len(test)})
    controls[1].observe(c2_ok, {"n_rotate_keys": len(rotate_keys)})
    controls[2].observe(c3_ok, {"leak_count": len(set(train) & set(test))})

    f1 = delta_vs_dm <= 0.0
    f2 = delta_vs_cx <= 0.0
    f3 = n_rot_test == 0

    falsifiers = [
        Falsifier("F1_rotate_vs_distmult_delta", refutes="that RotatE outperforms DistMult on RotatE-selected test queries", fires_when="delta_vs_dm <= 0", null_must_contain="no gain over distmult"),
        Falsifier("F2_rotate_vs_complex_delta", refutes="that RotatE outperforms ComplEx on RotatE-selected test queries", fires_when="delta_vs_cx <= 0", null_must_contain="no gain over complex"),
        Falsifier("F3_zero_test_queries", refutes="that RotatE-selected keys match any test queries", fires_when="n_rot_test == 0", null_must_contain="zero test queries"),
    ]
    falsifiers[0].observe(f1, {"mrr_rot": mrr_rot, "mrr_dm": mrr_dm, "delta": delta_vs_dm})
    falsifiers[1].observe(f2, {"mrr_rot": mrr_rot, "mrr_cx": mrr_cx, "delta": delta_vs_cx})
    falsifiers[2].observe(f3, {"n_rot_test": n_rot_test})

    res = {
        "spike": "H160",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "audit": {
            "rotate_selected_keys": len(rotate_keys),
            "test_queries_evaluated": n_rot_test,
            "test_query_fraction_pct": round(n_rot_test / len(test_rows) * 100, 2),
            "distinct_predicates": distinct_preds,
        },
        "metrics_on_selected_keys": {
            "mrr_rotate": round(mrr_rot, 4),
            "mrr_distmult": round(mrr_dm, 4),
            "mrr_complex": round(mrr_cx, 4),
            "delta_vs_distmult": round(delta_vs_dm, 4),
            "delta_vs_complex": round(delta_vs_cx, 4),
            "net_mrr_mass_gain_vs_distmult": round(total_net_gain_mass_dm, 2),
        },
        "controls": {
            "C1_test_size": {"ok": c1_ok},
            "C2_rotate_keys_count": {"ok": c2_ok},
            "C3_zero_leak": {"ok": c3_ok},
        },
        "falsifiers": {
            "F1_rotate_vs_distmult_delta": {"fired": f1},
            "F2_rotate_vs_complex_delta": {"fired": f2},
            "F3_zero_test_queries": {"fired": f3},
        }
    }

    out_json = os.path.join(HERE, "result.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS],
        artifacts=[out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="RotatE fails to demonstrate positive MRR delta on selected test relations",
        allow_dirty=True,
        note="H160: Adversarial Audit & RotatE Boundary Ablation on G88 5-Way Hybrid.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike H160 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
