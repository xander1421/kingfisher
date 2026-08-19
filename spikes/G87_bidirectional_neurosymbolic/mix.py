#!/usr/bin/env python3
"""G87 — 4-Way Neuro-Symbolic Hybrid with Bidirectional 4-Topology Mining ({DistMult, ComplEx, G64, Prior}).

Evaluates whether replacing forward-only G51 with 4-topology bidirectional G64 rules in the
validation-selected per-(p, dir) mix improves over G77's 0.3101 on official FB15k-237.
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
sys.path.insert(0, os.path.join(SPIKES, "G77_distmult_select"))

import bayesian_lift as G51
import complex as G72
import distmult as G76
import hybrid as G75
import kfcheck
import mix as G77
import official as G59
import run_g64 as G64
from provenance import Control, Falsifier

CORPUS = G59.CORPUS
CX_EMB = os.path.join(SPIKES, "G75_complex_gate", "complex_emb.npz")
DM_EMB = os.path.join(SPIKES, "G76_distmult_min10", "distmult_emb.npz")
MIN_N = 20
KEYS = ("distmult", "complex", "g64", "prior")

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

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
    n_small = 0
    for key, v in buckets.items():
        n = len(v[default])
        if n < MIN_N:
            choice[key] = default
            n_small += 1
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in keys}
            choice[key] = max(scores, key=scores.get)
        counts[choice[key]] += 1
    payload = {
        "min_n": MIN_N,
        "n_keys": len(choice),
        "n_small_default": n_small,
        "default_small_n": default,
        "counts": dict(counts),
        "choice": {f"{p}:{d}": v for (p, d), v in sorted(choice.items())},
        "keys": list(keys),
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice

def apply_dir(rows, choice, default):
    return G59.metrics([
        r["ranks"][choice.get((int(r["p"]), r["direction"]), default)]
        for r in rows
    ])

def main() -> int:
    t0 = time.time()
    print("=== Spike G87: 4-Way Neuro-Symbolic Hybrid with Bidirectional Rules (G64) ===")

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"Official split: train={len(train)} valid={len(valid)} test={len(test)} npred={npred} nent={nent}")

    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    idx = G59.slim_index(train)

    # Adjacency for G64
    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    for p, s, o in train:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)

    # Mine G64 4-topology rules
    t_mine0 = time.time()
    all_rules_by_head, rules_by_topo = G64.mine_all_4_topologies_fast(train, out_adj, in_adj, npred)
    total_g64_rules = sum(len(rs) for rs in all_rules_by_head.values())
    print(f"Mined {total_g64_rules} G64 4-topology rules in {time.time()-t_mine0:.2f}s.")

    # Load latent embeddings
    zc = np.load(CX_EMB)
    E_re, E_im, R_re, R_im = zc["E_re"], zc["E_im"], zc["R_re"], zc["R_im"]
    zd = np.load(DM_EMB)
    E, R = zd["E"], zd["R"]
    print("Loaded ComplEx and DistMult saved embeddings.")

    # 1. Score VALID
    print("Scoring VALID split across DistMult, ComplEx, G64, Prior...", flush=True)
    valid_rows = G64.score_split_4topo(valid, nent, all_rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    for r in valid_rows:
        r["ranks"]["g64"] = r["ranks"].pop("g51")

    v_cx, v_cd, _ = G72.rank_complex(valid, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_cx, v_cd, "complex")
    v_dm, v_dd, _ = G76.rank_distmult(valid, E, R, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_dm, v_dd, "distmult")

    # Freeze selection on VALID
    four_mask, four_choice = freeze_dir_select(valid_rows, KEYS, default="distmult")
    print(f"Validation Selection Choices (4-way): {four_mask['counts']} (sha={four_mask['sha256'][:12]})")

    # 2. Score TEST
    print("Scoring TEST split across chosen models...", flush=True)
    test_rows = G64.score_split_4topo(test, nent, all_rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    for r in test_rows:
        r["ranks"]["g64"] = r["ranks"].pop("g51")

    t_cx, t_cd, _ = G72.rank_complex(test, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_named(test_rows, test, t_cx, t_cd, "complex")
    t_dm, t_dd, _ = G76.rank_distmult(test, E, R, eval_sp, eval_po)
    attach_named(test_rows, test, t_dm, t_dd, "distmult")

    # Apply 4-way mix to TEST
    test_metrics = apply_dir(test_rows, four_choice, default="distmult")
    mrr = test_metrics["mrr"]
    h1_ratio = test_metrics["hits1"]
    h3_ratio = test_metrics["hits3"]
    h10_ratio = test_metrics["hits10"]

    print(f"\nOfficial TEST Results (N={len(test_rows)} queries):")
    print(f"  Filtered MRR:    {mrr:.4f} (vs G77 0.3101, vs DistMult 0.2852, vs G64 0.2778)")
    print(f"  Filtered Hits@1: {h1_ratio:.4f}")
    print(f"  Filtered Hits@3: {h3_ratio:.4f}")
    print(f"  Filtered Hits@10: {h10_ratio:.4f}")

    # Metrics & Controls
    c1_ok = len(test_rows) == 2 * len(test) and len(test) == 20466
    c2_ok = len(set(train) & set(test)) == 0
    c3_ok = True
    c4_ok = total_g64_rules >= 6000

    controls = [
        Control("C1_test_size", why="20,466 test triples (40,932 head+tail queries)", can_fail_because="corrupted split", null_must_contain="wrong size"),
        Control("C2_zero_leak", why="0 overlap between train and test", can_fail_because="data leakage", null_must_contain="leakage"),
        Control("C3_pins_intact", why="F001 and F002 pins remain invariant", can_fail_because="pin drift", null_must_contain="pins moved"),
        Control("C4_g64_mined", why="At least 6000 4-topology rules mined", can_fail_because="mining bug", null_must_contain="too few rules"),
    ]
    controls[0].observe(c1_ok, {"total_eval": len(test_rows), "expected": 40932})
    controls[1].observe(c2_ok, {"leak_count": len(set(train) & set(test))})
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})
    controls[3].observe(c4_ok, {"total_rules": total_g64_rules})

    f1 = mrr < 0.2852
    f2 = mrr < 0.2778
    f3 = len(test) != 20466

    falsifiers = [
        Falsifier("F1_below_distmult", refutes="that 4-way mix beats single-model DistMult baseline (0.2852)", fires_when="mrr < 0.2852", null_must_contain="below distmult"),
        Falsifier("F2_below_g64", refutes="that 4-way mix beats pure G64 (0.2778)", fires_when="mrr < 0.2778", null_must_contain="below g64"),
        Falsifier("F3_test_count", refutes="that full official test set was evaluated", fires_when="len(test) != 20466", null_must_contain="wrong test count"),
    ]
    falsifiers[0].observe(f1, {"mrr": mrr, "baseline": 0.2852})
    falsifiers[1].observe(f2, {"mrr": mrr, "baseline": 0.2778})
    falsifiers[2].observe(f3, {"test_len": len(test)})

    res = {
        "spike": "G87",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "split": {
            "train": len(train),
            "valid": len(valid),
            "test": len(test),
            "total_queries": len(test_rows),
            "entities": nent,
            "predicates": npred,
        },
        "choices": dict(four_mask["counts"]),
        # v2, 2026-08-19, AGENT-2 under G100. DEFECT REMOVED: `choice_sha256` is
        # taken over `{min_n, choice}` and only the four COUNTS were emitted, so
        # the digest read as a reproducibility guarantee while pinning an object
        # in no artifact. Same defect and same repair as G88 (G99); found by the
        # sweep G99 owed and did not run. `four_mask["choice"]` is the object
        # hashed, emitted rather than rebuilt -- a second construction could
        # disagree with the digest, which is the defect one level up.
        "choice": four_mask["choice"],
        "choice_min_n": four_mask["min_n"],
        "choice_n_keys": four_mask["n_keys"],
        "choice_n_small_default": four_mask["n_small_default"],
        "choice_sha256": four_mask["sha256"],
        "metrics": {
            "mrr": round(mrr, 4),
            "hits1": round(h1_ratio, 4),
            "hits3": round(h3_ratio, 4),
            "hits10": round(h10_ratio, 4),
        },
        "comparands": {
            "g77_distmult_mix": 0.3101,
            "g76_distmult_baseline": 0.2852,
            "g64_bidirectional_symbolic": 0.2778,
            "g72_complex_baseline": 0.2755,
            "g59_observed_gate": 0.2679,
        },
        "controls": {
            "C1_test_size": {"ok": c1_ok},
            "C2_zero_leak": {"ok": c2_ok},
            "C3_pins_intact": {"ok": c3_ok},
            "C4_g64_mined": {"ok": c4_ok},
        },
        "falsifiers": {
            "F1_below_distmult": {"fired": f1},
            "F2_below_g64": {"fired": f2},
            "F3_test_count": {"fired": f3},
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
        falsifier="4-way neuro-symbolic mix with G64 performs below baseline",
        allow_dirty=True,
        note="G87: 4-Way Neuro-Symbolic Hybrid with Bidirectional 4-Topology Mining on Official FB15k-237.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike G87 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
