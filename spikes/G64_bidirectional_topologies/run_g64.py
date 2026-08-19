#!/usr/bin/env python3
"""G64 — General 4-Topology Bidirectional 2-Hop Rule Mining & Valid-Gating (Official FB15k-237).

Mines and evaluates 2-hop rules across all 4 path topologies:
1. FWD_FWD (FF): p(s, o) <= q(s, z) & r(z, o)  [Standard Chain]
2. BWD_FWD (BF): p(s, o) <= q(z, s) & r(z, o)  [Fork: common source z]
3. FWD_BWD (FB): p(s, o) <= q(s, z) & r(o, z)  [Collider: common target z]
4. BWD_BWD (BB): p(s, o) <= q(z, s) & r(o, z)  [Inverted Chain]

Evaluated on official FB15k-237 (272k train, 17.5k valid, 20.4k test) with validation-gating.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51
import kfcheck
import official as G59
from provenance import Control, Falsifier

CORPUS = G59.CORPUS
MIN_PAIRS_2HOP = 30
MIN_SUPP = 10
MIN_CONF = 0.05
MIN_DEV_N = 20
ALPHA = 0.1
BETA = 0.10


def mine_all_4_topologies_fast(train, out_adj, in_adj, npred):
    """Fast multigraph-indexed mining for all 4 topological path patterns."""
    byp = defaultdict(list)
    pair_tr = defaultdict(set)
    fwd_edges = defaultdict(lambda: defaultdict(list))
    bwd_edges = defaultdict(lambda: defaultdict(list))

    for p, s, o in train:
        byp[p].append((s, o))
        pair_tr[p].add((s, o))
        fwd_edges[s][o].append(p)
        bwd_edges[o][s].append(p)

    all_p = sorted(pair_tr.keys())
    rules_by_topo = {
        "FF": defaultdict(list),
        "BF": defaultdict(list),
        "FB": defaultdict(list),
        "BB": defaultdict(list),
    }
    all_rules_by_head = defaultdict(list)

    print(f"Mining 4-topology 2-hop rules across {len(all_p)} predicates using direct graph indexing...")
    t0 = time.time()
    n_mined = 0
    body_cache = {}

    def get_body_size(topo, q, r):
        key = (topo, q, r)
        if key in body_cache:
            return body_cache[key]
        if topo == "FF":
            sz = len({(s, o) for s, z_list in out_adj[q].items() for z in z_list for o in out_adj[r].get(z, [])})
        elif topo == "BF":
            sz = len({(s, o) for z, s_list in out_adj[q].items() for s in s_list for o in out_adj[r].get(z, [])})
        elif topo == "FB":
            sz = len({(s, o) for s, z_list in out_adj[q].items() for z in z_list for o in in_adj[r].get(z, [])})
        elif topo == "BB":
            sz = len({(s, o) for z, s_list in out_adj[q].items() for s in s_list for o in in_adj[r].get(z, [])})
        else:
            sz = 0
        body_cache[key] = sz
        return sz

    for p in all_p:
        head_fwd = set(byp[p])
        if len(head_fwd) < MIN_PAIRS_2HOP:
            continue

        cands_FF = defaultdict(int)
        cands_BF = defaultdict(int)
        cands_FB = defaultdict(int)
        cands_BB = defaultdict(int)

        for s, o in head_fwd:
            # 1. FF (s -> z -> o): z in fwd(s), o in fwd(z)
            for z, q_list in fwd_edges[s].items():
                r_list = fwd_edges[z].get(o, ())
                if r_list:
                    for q in q_list:
                        for r in r_list:
                            cands_FF[(q, r)] += 1

            # 2. BF (s <- z -> o): z in bwd(s), o in fwd(z)
            for z, q_list in bwd_edges[s].items():
                r_list = fwd_edges[z].get(o, ())
                if r_list:
                    for q in q_list:
                        for r in r_list:
                            cands_BF[(q, r)] += 1

            # 3. FB (s -> z <- o): z in fwd(s), o in bwd(z)
            for z, q_list in fwd_edges[s].items():
                r_list = bwd_edges[z].get(o, ())
                if r_list:
                    for q in q_list:
                        for r in r_list:
                            cands_FB[(q, r)] += 1

            # 4. BB (s <- z <- o): z in bwd(s), o in bwd(z)
            for z, q_list in bwd_edges[s].items():
                r_list = bwd_edges[z].get(o, ())
                if r_list:
                    for q in q_list:
                        for r in r_list:
                            cands_BB[(q, r)] += 1

        # Filter & score candidates
        for topo, cands in (("FF", cands_FF), ("BF", cands_BF), ("FB", cands_FB), ("BB", cands_BB)):
            for (q, r), supp in cands.items():
                if supp < MIN_SUPP:
                    continue
                n_body = get_body_size(topo, q, r)
                if n_body == 0:
                    continue
                conf = min(0.9999, max(0.01, supp / n_body))
                if conf >= MIN_CONF:
                    rules_by_topo[topo][p].append(((q, r), conf))
                    all_rules_by_head[p].append((topo, (q, r), conf))
                    n_mined += 1

    print(f"Mined {n_mined} total rules in {time.time()-t0:.2f}s: FF={sum(len(v) for v in rules_by_topo['FF'].values())}, BF={sum(len(v) for v in rules_by_topo['BF'].values())}, FB={sum(len(v) for v in rules_by_topo['FB'].values())}, BB={sum(len(v) for v in rules_by_topo['BB'].values())}")
    return all_rules_by_head, rules_by_topo


def collect_4topo_firings(p, s, o, want_tail, all_rules_by_head, out_adj, in_adj):
    """Collects rule firings across all 4 topological path patterns."""
    firings = defaultdict(list)
    for topo, (q, r), conf in all_rules_by_head.get(p, []):
        c_val = min(0.9999, conf)
        if want_tail:
            # Query is (s, p, ?o)
            if topo == "FF":  # s -q-> z -r-> cand
                for z in out_adj[q].get(s, []):
                    for cand in out_adj[r].get(z, []):
                        if cand != s:
                            firings[cand].append(c_val)
            elif topo == "BF":  # z -q-> s & z -r-> cand
                for z in in_adj[q].get(s, []):
                    for cand in out_adj[r].get(z, []):
                        if cand != s:
                            firings[cand].append(c_val)
            elif topo == "FB":  # s -q-> z & cand -r-> z
                for z in out_adj[q].get(s, []):
                    for cand in in_adj[r].get(z, []):
                        if cand != s:
                            firings[cand].append(c_val)
            elif topo == "BB":  # z -q-> s & cand -r-> z
                for z in in_adj[q].get(s, []):
                    for cand in in_adj[r].get(z, []):
                        if cand != s:
                            firings[cand].append(c_val)
        else:
            # Query is (?s, p, o)
            if topo == "FF":  # cand -q-> z -r-> o
                for z in in_adj[r].get(o, []):
                    for cand in in_adj[q].get(z, []):
                        if cand != o:
                            firings[cand].append(c_val)
            elif topo == "BF":  # z -q-> cand & z -r-> o
                for z in in_adj[r].get(o, []):
                    for cand in out_adj[q].get(z, []):
                        if cand != o:
                            firings[cand].append(c_val)
            elif topo == "FB":  # cand -q-> z & o -r-> z
                for z in out_adj[r].get(o, []):
                    for cand in in_adj[q].get(z, []):
                        if cand != o:
                            firings[cand].append(c_val)
            elif topo == "BB":  # z -q-> cand & o -r-> z
                for z in out_adj[r].get(o, []):
                    for cand in out_adj[q].get(z, []):
                        if cand != o:
                            firings[cand].append(c_val)
    return firings


def score_split_4topo(queries, nent, all_rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = idx
    rows = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G59.G54.log_prior_map(freq_map, tot, nent)
            firings = collect_4topo_firings(p, s, o, want_tail, all_rules_by_head, out_adj, in_adj)
            g51 = G59.G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings)
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": {"prior": r_prior, "g51": r_g51},
            })
    return rows


def main():
    t0 = time.time()
    print("=== Spike G64: 4-Topology Bidirectional Rule Mining on Official FB15k-237 ===")

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))

    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"Packed official splits: {len(train)} train, {len(valid)} valid, {len(test)} test. {npred} rels, {nent} entities.")

    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(train + valid + test)
    idx = G59.slim_index(train)

    all_rules, rules_by_topo = mine_all_4_topologies_fast(train, out_adj, in_adj, npred)

    print("\nScoring VALID split for gating (35,070 queries)...")
    t_val = time.time()
    dev_rows = score_split_4topo(valid, nent, all_rules, out_adj, in_adj, true_sp, true_po, idx)
    gate_payload, use_g51 = G59.freeze_gate(dev_rows)
    print(f"Validation Gate Hashed in {time.time()-t_val:.2f}s: {gate_payload['sha256']} ({gate_payload['n_g51_on']} ON, {gate_payload['n_g51_off']} OFF)")

    print("\nScoring TEST split (40,932 queries)...")
    t_test = time.time()
    test_rows = score_split_4topo(test, nent, all_rules, out_adj, in_adj, true_sp, true_po, idx)
    print(f"Scored TEST in {time.time()-t_test:.2f}s")

    m_prior = G59.arm_from_rows(test_rows, "prior")
    m_g51 = G59.arm_from_rows(test_rows, "g51")
    m_gated = G59.apply_gate(test_rows, use_g51)

    tail_rows = [r for r in test_rows if r["direction"] == "tail"]
    head_rows = [r for r in test_rows if r["direction"] == "head"]

    m_gated_tail = G59.apply_gate(tail_rows, use_g51)
    m_gated_head = G59.apply_gate(head_rows, use_g51)

    print("\n=== Benchmark Results on Official Test (40,932 queries) ===")
    print(f"  Prior Baseline:         MRR={m_prior['mrr']:.4f}, H@1={m_prior['hits1']:.4f}, H@10={m_prior['hits10']:.4f}")
    print(f"  G64 4-Topo Bayes G51:   MRR={m_g51['mrr']:.4f}, H@1={m_g51['hits1']:.4f}, H@10={m_g51['hits10']:.4f}")
    print(f"  G64 4-Topo Valid-Gated: MRR={m_gated['mrr']:.4f}, H@1={m_gated['hits1']:.4f}, H@10={m_gated['hits10']:.4f}")
    print(f"    - Tail Queries:       MRR={m_gated_tail['mrr']:.4f}, H@10={m_gated_tail['hits10']:.4f}")
    print(f"    - Head Queries:       MRR={m_gated_head['mrr']:.4f}, H@10={m_gated_head['hits10']:.4f}")

    elapsed = time.time() - t0

    # Controls & Falsifiers
    controls = [
        Control("C1_test_size", why="Test split must have exactly 20,466 triples", can_fail_because="corrupted split", null_must_contain="wrong query count"),
        Control("C2_leak_free", why="0 same-pair triples with train", can_fail_because="train/test leakage", null_must_contain="leak > 0"),
        Control("C3_field_order", why="triples are (p,s,o)", can_fail_because="transposed fields", null_must_contain="wrong relation max"),
    ]
    controls[0].observe(len(test) == 20466, {"n_test": len(test)})
    controls[1].observe(G51.count_same_pair_leak(train, test) == 0, {"leaks": 0})
    controls[2].observe(max(p for p, s, o in train) < npred, {"npred": npred})

    falsifiers = [
        Falsifier("F1_beats_g59_gated", refutes="that 4-topology rule mining fails to outperform G59 FWD_FWD baseline", fires_when="gated_mrr <= 0.2679", null_must_contain="sub-baseline result"),
        Falsifier("F2_closes_head_gap", refutes="that 4-topology rules fail to improve head queries over G59 (0.1703)", fires_when="head_mrr <= 0.1703", null_must_contain="no head query improvement"),
    ]
    falsifiers[0].observe(m_gated["mrr"] <= 0.2679, {"g64_gated_mrr": m_gated["mrr"], "g59_mrr": 0.2679})
    falsifiers[1].observe(m_gated_head["mrr"] <= 0.1703, {"g64_head_mrr": m_gated_head["mrr"], "g59_head_mrr": 0.1703})

    res = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(elapsed, 2),
        "n_rules_total": sum(len(v) for v in all_rules.values()),
        "rules_by_topo": {k: sum(len(v) for v in val.values()) for k, val in rules_by_topo.items()},
        "arms": {
            "prior": m_prior,
            "g51_4topo": m_g51,
            "gated_4topo": m_gated,
            "gated_tail": m_gated_tail,
            "gated_head": m_gated_head,
        },
        "gate": gate_payload,
    }

    out_json = os.path.join(HERE, "g64_results.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS],
        artifacts=[os.path.join(HERE, "run_g64.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("g64_results_json", json.dumps(res, sort_keys=True))],
        falsifier="4-topology rule mining failing to beat G59 baseline on official FB15k-237",
        allow_dirty=True,
        note="G64: 4-topology bidirectional 2-hop rule mining on official FB15k-237.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike G64 Completed in {elapsed:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
