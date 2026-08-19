#!/usr/bin/env python3
"""G82 — 5-Way Neuro-Symbolic Selection with 4-Topology Bidirectional Lift (G64).

Adds G64 4-topology bidirectional 2-hop rules (6,736 rules: Chains, Forks, Colliders, Inverted)
into the all-entity validation selection pool alongside DistMult (G76), ComplEx (G72), G51, and Prior.

Protocol:
- All 14,541 entities evaluated on canonical FB15k-237 (272k train, 17.5k valid, 20.4k test).
- Valid-selection per (p, dir) among {distmult, complex, g64, g51, prior}.
- Decision table hashed before test scoring.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict

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
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G64_bidirectional_topologies"))
sys.path.insert(0, os.path.join(SPIKES, "G72_complex_all_entity"))
sys.path.insert(0, os.path.join(SPIKES, "G75_complex_gate"))
sys.path.insert(0, os.path.join(SPIKES, "G76_distmult_min10"))
sys.path.insert(0, os.path.join(SPIKES, "G77_distmult_select"))

import bayesian_lift as G51  # noqa: E402
import complex as G72  # noqa: E402
import distmult as G76  # noqa: E402
import hybrid as G75  # noqa: E402
import kfcheck  # noqa: E402
import mix as G77  # noqa: E402
import official as G59  # noqa: E402
import run_g64 as G64  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
CX_EMB = os.path.join(SPIKES, "G75_complex_gate", "complex_emb.npz")
DM_EMB = os.path.join(SPIKES, "G76_distmult_min10", "distmult_emb.npz")
G75_RULES = os.path.join(SPIKES, "G75_complex_gate", "rules_cache.json")
MIN_N = 20
NENT_OFFICIAL = 14541
NPRED_OFFICIAL = 237
TEST_N = 20466
G77_REF = 0.3101


def load_g51_rules():
    if not os.path.isfile(G75_RULES):
        raise RuntimeError("G75 rules_cache missing")
    raw = json.loads(open(G75_RULES, encoding="utf-8").read())
    rules_by_head = defaultdict(list)
    for r in raw:
        rules_by_head[r["head"]].append((tuple(r["body"]), float(r["conf"])))
    return rules_by_head, raw


def score_split_all_models(queries, nent, g51_rules, g64_rules, out_adj, in_adj, true_sp, true_po, eval_sp, eval_po, idx, cx_emb, dm_emb):
    """Computes all-entity ranks for prior, g51, g64, complex, and distmult."""
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = idx
    rows = []
    
    # 1. Symbolic & Prior ranks
    print(f"Scoring symbolic and prior ranks for {len(queries)} queries...", flush=True)
    t_sym = time.time()
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G59.G54.log_prior_map(freq_map, tot, nent)
            
            # G51 (forward-only)
            firings_g51 = G59.G54.collect_firings(p, s, o, want_tail, g51_rules, out_adj, in_adj)
            g51_scores = G59.G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings_g51)
            
            # G64 (4-topology bidirectional)
            firings_g64 = G64.collect_4topo_firings(p, s, o, want_tail, g64_rules, out_adj, in_adj)
            g64_scores = G59.G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings_g64)
            
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51_scores, target, filt, nent)
            r_g64 = G51.rank_from_scores(g64_scores, target, filt, nent)
            
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": {
                    "prior": float(r_prior),
                    "g51": float(r_g51),
                    "g64": float(r_g64),
                },
            })
    print(f"Scored symbolic ranks in {time.time()-t_sym:.2f}s", flush=True)

    # 2. ComplEx ranks
    print("Scoring ComplEx all-entity ranks...", flush=True)
    t_cx = time.time()
    E_re, E_im, R_re, R_im = cx_emb
    v_cx, v_cd, _ = G72.rank_complex(queries, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    rows = G77.attach_named(rows, queries, v_cx, v_cd, "complex")
    print(f"Scored ComplEx in {time.time()-t_cx:.2f}s", flush=True)

    # 3. DistMult ranks
    print("Scoring DistMult all-entity ranks...", flush=True)
    t_dm = time.time()
    E, R = dm_emb
    v_dm, v_dd, _ = G76.rank_distmult(queries, E, R, eval_sp, eval_po)
    rows = G77.attach_named(rows, queries, v_dm, v_dd, "distmult")
    print(f"Scored DistMult in {time.time()-t_dm:.2f}s", flush=True)

    return rows


def main():
    t0 = time.time()
    print("=== Spike G82: 5-Way Neuro-Symbolic Selection with 4-Topology Bidirectional Lift ===")

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))

    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"Packed splits: {len(train)} train, {len(valid)} valid, {len(test)} test. {npred} rels, {nent} entities.")

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    idx = G59.slim_index(train)

    # Load G51 forward rules
    g51_rules, g51_raw = load_g51_rules()
    print(f"Loaded {len(g51_raw)} forward rules for G51.")

    # Mine G64 4-topology rules
    g64_rules, rules_by_topo = G64.mine_all_4_topologies_fast(train, out_adj, in_adj, npred)
    print(f"Mined {sum(len(v) for v in g64_rules.values())} 4-topology rules for G64.")

    # Load pre-trained embeddings
    zc = np.load(CX_EMB)
    cx_emb = (zc["E_re"], zc["E_im"], zc["R_re"], zc["R_im"])
    zd = np.load(DM_EMB)
    dm_emb = (zd["E"], zd["R"])
    print("Loaded ComplEx and DistMult pre-trained embeddings.")

    # Score VALID split
    print("\n--- Scoring VALID split (35,070 queries) ---")
    t_val = time.time()
    valid_rows = score_split_all_models(valid, nent, g51_rules, g64_rules, out_adj, in_adj, true_sp, true_po, eval_sp, eval_po, idx, cx_emb, dm_emb)
    print(f"Scored VALID split in {time.time()-t_val:.2f}s")

    # Gate 1: G77 4-Way Baseline Selection (DistMult, ComplEx, G51, Prior)
    g77_gate_payload, g77_choice = G77.freeze_dir_select(valid_rows, G77.KEYS, default="distmult")
    print(f"G77 4-Way Gate Hash: {g77_gate_payload['sha256']}, counts: {g77_gate_payload['counts']}")

    # Gate 2: G82 5-Way Selection (DistMult, ComplEx, G64, G51, Prior)
    KEYS_5WAY = ("distmult", "complex", "g64", "g51", "prior")
    g82_5way_payload, g82_5way_choice = G77.freeze_dir_select(valid_rows, KEYS_5WAY, default="distmult")
    print(f"G82 5-Way Gate Hash: {g82_5way_payload['sha256']}, counts: {g82_5way_payload['counts']}")

    # Gate 3: G82 4-Way Selection replacing G51 with G64 (DistMult, ComplEx, G64, Prior)
    KEYS_4WAY_G64 = ("distmult", "complex", "g64", "prior")
    g82_4way_payload, g82_4way_choice = G77.freeze_dir_select(valid_rows, KEYS_4WAY_G64, default="distmult")
    print(f"G82 4-Way (G64 replace G51) Gate Hash: {g82_4way_payload['sha256']}, counts: {g82_4way_payload['counts']}")

    # Score TEST split
    print("\n--- Scoring TEST split (40,932 queries) ---")
    t_test = time.time()
    test_rows = score_split_all_models(test, nent, g51_rules, g64_rules, out_adj, in_adj, true_sp, true_po, eval_sp, eval_po, idx, cx_emb, dm_emb)
    print(f"Scored TEST split in {time.time()-t_test:.2f}s")

    m_prior = G59.arm_from_rows(test_rows, "prior")
    m_g51 = G59.arm_from_rows(test_rows, "g51")
    m_g64 = G59.arm_from_rows(test_rows, "g64")
    m_cx = G59.arm_from_rows(test_rows, "complex")
    m_dm = G59.arm_from_rows(test_rows, "distmult")

    m_g77_4way = G77.apply_dir(test_rows, g77_choice, default="distmult")
    m_g82_5way = G77.apply_dir(test_rows, g82_5way_choice, default="distmult")
    m_g82_4way = G77.apply_dir(test_rows, g82_4way_choice, default="distmult")

    m_5way_slices = G77.slice_apply(test_rows, g82_5way_choice, default="distmult")

    print("\n=== Official Test Benchmark Results (40,932 queries, 14,541 entities) ===")
    print(f"  Prior Baseline:                  MRR={m_prior['mrr']:.4f}, H@1={m_prior['hits1']:.4f}, H@10={m_prior['hits10']:.4f}")
    print(f"  G51 Forward-Only Bayes:          MRR={m_g51['mrr']:.4f}, H@1={m_g51['hits1']:.4f}, H@10={m_g51['hits10']:.4f}")
    print(f"  G64 4-Topology Bidirectional:    MRR={m_g64['mrr']:.4f}, H@1={m_g64['hits1']:.4f}, H@10={m_g64['hits10']:.4f}")
    print(f"  ComplEx Baseline (G72):          MRR={m_cx['mrr']:.4f}, H@1={m_cx['hits1']:.4f}, H@10={m_cx['hits10']:.4f}")
    print(f"  DistMult Baseline (G76):         MRR={m_dm['mrr']:.4f}, H@1={m_dm['hits1']:.4f}, H@10={m_dm['hits10']:.4f}")
    print(f"  G77 4-Way Baseline (DM+CX+G51):  MRR={m_g77_4way['mrr']:.4f}, H@1={m_g77_4way['hits1']:.4f}, H@10={m_g77_4way['hits10']:.4f}")
    print(f"  G82 4-Way (DM+CX+G64+Prior):     MRR={m_g82_4way['mrr']:.4f}, H@1={m_g82_4way['hits1']:.4f}, H@10={m_g82_4way['hits10']:.4f}")
    print(f"  G82 5-Way (DM+CX+G64+G51+Prior): MRR={m_g82_5way['mrr']:.4f}, H@1={m_g82_5way['hits1']:.4f}, H@10={m_g82_5way['hits10']:.4f}")
    print(f"    - 5-Way Tail:                  MRR={m_5way_slices['tail']['mrr']:.4f}, H@10={m_5way_slices['tail']['hits10']:.4f}")
    print(f"    - 5-Way Head:                  MRR={m_5way_slices['head']['mrr']:.4f}, H@10={m_5way_slices['head']['hits10']:.4f}")

    elapsed = time.time() - t0

    # Controls & Falsifiers
    controls = [
        Control("C1_test_size", why="Test split must have 20,466 triples", can_fail_because="corrupted split", null_must_contain="wrong query count"),
        Control("C2_leak_free", why="0 same-pair triples with train", can_fail_because="train/test leakage", null_must_contain="leak > 0"),
        Control("C3_reproduces_g77", why="G77 4-way must reproduce 0.3101 exact within 0.0005", can_fail_because="instrument drift", null_must_contain="g77 drift"),
    ]
    controls[0].observe(len(test) == 20466, {"n_test": len(test)})
    controls[1].observe(G51.count_same_pair_leak(train, test) == 0, {"leaks": 0})
    controls[2].observe(abs(m_g77_4way["mrr"] - G77_REF) < 0.0005, {"g77_repro": m_g77_4way["mrr"], "ref": G77_REF})

    n_g64_picked = g82_5way_payload["counts"].get("g64", 0)
    delta_vs_g77 = m_g82_5way["mrr"] - m_g77_4way["mrr"]

    falsifiers = [
        Falsifier("F1_beats_g77", refutes="that 5-way selection fails to beat G77 baseline by +0.001", fires_when="5way_mrr - 0.3101 < 0.001", null_must_contain="no lift"),
        Falsifier("F2_5way_improves", refutes="that 5-way selection is worse than G77", fires_when="5way_mrr < 0.3101", null_must_contain="selection degraded"),
        Falsifier("F3_g64_selected", refutes="that G64 4-topology rules are not picked more than G51 alone", fires_when="n_g64_picked <= 77", null_must_contain="g64 not selected"),
    ]
    falsifiers[0].observe(delta_vs_g77 < 0.001, {"delta": delta_vs_g77, "g82_mrr": m_g82_5way["mrr"], "g77_mrr": m_g77_4way["mrr"]})
    falsifiers[1].observe(m_g82_5way["mrr"] < G77_REF, {"g82_mrr": m_g82_5way["mrr"]})
    falsifiers[2].observe(n_g64_picked <= 77, {"n_g64_picked": n_g64_picked, "g51_g77_count": 77})

    res = {
        "spike": "G82",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(elapsed, 2),
        "arms": {
            "prior": m_prior,
            "g51": m_g51,
            "g64": m_g64,
            "complex": m_cx,
            "distmult": m_dm,
            "g77_4way": m_g77_4way,
            "g82_4way": m_g82_4way,
            "g82_5way": m_g82_5way,
            "5way_tail": m_5way_slices["tail"],
            "5way_head": m_5way_slices["head"],
        },
        "gates": {
            "g77_4way": g77_gate_payload,
            "g82_5way": g82_5way_payload,
            "g82_4way": g82_4way_payload,
        },
    }

    out_json = os.path.join(HERE, "g82_results.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS, CX_EMB, DM_EMB],
        artifacts=[os.path.join(HERE, "run.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("g82_results_json", json.dumps(res, sort_keys=True))],
        falsifier="G82 5-way hybrid failing to improve over G77 4-way baseline on official FB15k-237",
        allow_dirty=True,
        note="G82: 5-way neuro-symbolic valid-selection with 4-topology bidirectional rules.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike G82 Completed in {elapsed:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
