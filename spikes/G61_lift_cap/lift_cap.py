#!/usr/bin/env python3
"""G61 — valid-fitted lift cap on official test (spray without signed write).

G57: rare false candidates get huge lift = conf/P(c|p); true lift is always >1
when fired; signed log(lift) lost. Cap at the p95 of TRUE-target lifts on
valid, hashed before test.

  PYTHONUNBUFFERED=1 python3 spikes/G61_lift_cap/lift_cap.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

ALPHA = 0.1
BETA = 0.10
G51_REF = 0.2585
GATED_REF = 0.2679


def apply_g51_capped(base_log, freq_map, prior_norm, nent, firings, cap=None):
    cand_scores = dict(base_log)
    true_lift = None
    for cand, conf_list in firings.items():
        if cand not in cand_scores:
            p_prior = ALPHA / (prior_norm + ALPHA * nent)
            cand_scores[cand] = math.log(max(1e-12, p_prior))
        prod = 1.0
        for c in conf_list:
            prod *= 1.0 - min(0.9999, max(0.0, c))
        comb_conf = max(0.0, min(0.9999, 1.0 - prod))
        p_prior_c = (freq_map.get(cand, 0) + ALPHA) / (prior_norm + ALPHA * nent)
        lift_ratio = comb_conf / max(1e-5, p_prior_c)
        if cap is not None:
            lift_ratio = min(lift_ratio, cap)
        cand_scores[cand] += math.log(1.0 + max(0.0, BETA * lift_ratio))
    return cand_scores


def score_with_lifts(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx, cap=None):
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = idx
    rows = []
    true_lifts = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            firings = G54.collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = apply_g51_capped(base_log, freq_map, prior_norm, nent, firings, cap=None)
            capped = apply_g51_capped(base_log, freq_map, prior_norm, nent, firings, cap=cap)
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            r_cap = G51.rank_from_scores(capped, target, filt, nent)
            tl = None
            if target in firings:
                conf_list = firings[target]
                prod = 1.0
                for c in conf_list:
                    prod *= 1.0 - min(0.9999, max(0.0, c))
                comb = max(0.0, min(0.9999, 1.0 - prod))
                p_prior_c = (freq_map.get(target, 0) + ALPHA) / (prior_norm + ALPHA * nent)
                tl = comb / max(1e-5, p_prior_c)
                true_lifts.append(tl)
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "true_lift": tl,
                "ranks": {"prior": r_prior, "g51": r_g51, "cap": r_cap},
            })
    return rows, true_lifts


def p95(xs):
    if not xs:
        return 0.0
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(0.95 * (len(ys) - 1))))
    return float(ys[i])


def main():
    t0 = time.time()
    train_txt = G59.load_split_txt(os.path.join(G59.CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(G59.CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(G59.CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    print(
        f"official train={len(train)} valid={len(valid)} test={len(test)} "
        f"npred={npred} nent={nent} leak={leak}",
        flush=True,
    )
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(train + valid + test)
    print("mining 2-hop ...", flush=True)
    t_m = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_m:.1f}s", flush=True)
    idx = G59.slim_index(train)

    print("VALID uncapped (collect true lifts) ...", flush=True)
    t_v = time.time()
    valid_rows, valid_lifts = score_with_lifts(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx, cap=None
    )
    cap = p95(valid_lifts)
    cap_payload = {
        "stat": "p95_true_target_lift_on_valid",
        "n_true_fired": len(valid_lifts),
        "p50": (sorted(valid_lifts)[len(valid_lifts) // 2] if valid_lifts else 0.0),
        "p95": cap,
        "max": max(valid_lifts) if valid_lifts else 0.0,
        "min": min(valid_lifts) if valid_lifts else 0.0,
    }
    blob = json.dumps(cap_payload, sort_keys=True).encode()
    cap_payload["sha256"] = hashlib.sha256(blob).hexdigest()
    print(
        f"VALID {len(valid_rows)} in {time.time() - t_v:.1f}s "
        f"true_fired={len(valid_lifts)} cap_p95={cap:.4f} sha={cap_payload['sha256'][:16]}",
        flush=True,
    )
    pred_payload, pred_use = G59.freeze_gate(valid_rows)

    print("TEST with cap ...", flush=True)
    t_t = time.time()
    test_rows, test_lifts = score_with_lifts(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx, cap=cap
    )
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    def gated(key):
        return G59.metrics([
            r["ranks"][key] if pred_use.get(r["p"], True) else r["ranks"]["prior"]
            for r in test_rows
        ])

    arms = {
        "A_prior": G59.arm_from_rows(test_rows, "prior"),
        "B_g51": G59.arm_from_rows(test_rows, "g51"),
        "C_valid_gated": gated("g51"),
        "D_cap_all": G59.arm_from_rows(test_rows, "cap"),
        "E_gated_cap": gated("cap"),
    }
    d_cap_g51 = round(arms["D_cap_all"]["mrr"] - arms["B_g51"]["mrr"], 4)
    d_gc_g = round(arms["E_gated_cap"]["mrr"] - arms["C_valid_gated"]["mrr"], 4)
    f1_fired = d_cap_g51 <= 0.0
    f2_fired = d_gc_g <= 0.0

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(arms["B_g51"]["mrr"] - G51_REF) <= 0.0005
    c4_ok = abs(arms["C_valid_gated"]["mrr"] - GATED_REF) <= 0.0005
    c5_ok = bool(cap_payload.get("sha256"))

    res = {
        "spike": "G61",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "E_gated_cap",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "cap": cap_payload,
        "pred_gate": {
            "sha256": pred_payload["sha256"],
            "n_on": pred_payload["n_g51_on"],
            "n_off": pred_payload["n_g51_off"],
        },
        "arms": arms,
        "cap_minus_g51": d_cap_g51,
        "gated_cap_minus_gated": d_gc_g,
        "controls": {
            "C1_test_n": {"ok": c1_ok, "n": len(test)},
            "C2_leak": {"ok": c2_ok, "leak": leak},
            "C3_g51": {"ok": c3_ok, "mrr": arms["B_g51"]["mrr"]},
            "C4_gated": {"ok": c4_ok, "mrr": arms["C_valid_gated"]["mrr"]},
            "C5_cap_hashed": {"ok": c5_ok, "sha256": cap_payload["sha256"]},
        },
        "falsifiers": {
            "F1_cap_all_does_not_beat_g51": {
                "cap_mrr": arms["D_cap_all"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": d_cap_g51,
                "fired": f1_fired,
                "description": "Fires if lift-cap-all <= official G51. Signed.",
            },
            "F2_gated_cap_does_not_beat_gated": {
                "gated_cap_mrr": arms["E_gated_cap"]["mrr"],
                "gated_mrr": arms["C_valid_gated"]["mrr"],
                "delta": d_gc_g,
                "fired": f2_fired,
                "description": "Fires if gated+cap <= G59 gated 0.2679. Signed.",
            },
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    out = os.path.join(HERE, "lift_cap.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G61 arms ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:16s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(f"F1 fired={f1_fired} Δ={d_cap_g51:+.4f} F2 fired={f2_fired} Δ={d_gc_g:+.4f}", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong file",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="leak 0", can_fail_because="loader mix",
                null_must_contain="leak>0"),
        Control("C3_g51", why="official G51 0.2585", can_fail_because="scorer drifted",
                null_must_contain="G51 != 0.2585"),
        Control("C4_gated", why="valid-gated 0.2679", can_fail_because="gate drifted",
                null_must_contain="gated != 0.2679"),
        Control("C5_cap_hashed", why="p95 cap hashed before test",
                can_fail_because="missing sha", null_must_contain="empty sha"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_g51"])
    controls[3].observe(c4_ok, res["controls"]["C4_gated"])
    controls[4].observe(c5_ok, res["controls"]["C5_cap_hashed"])

    falsifiers = [
        Falsifier(
            "F1_cap_all_does_not_beat_g51",
            refutes="that clipping rare-entity lift raises official G51",
            fires_when="cap_all <= G51",
            null_must_contain="signed cap-G51 delta",
        ),
        Falsifier(
            "F2_gated_cap_does_not_beat_gated",
            refutes="that a lift cap on top of the G59 gate raises official MRR",
            fires_when="gated_cap <= gated",
            null_must_contain="signed gated_cap-gated delta",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_cap_all_does_not_beat_g51"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_gated_cap_does_not_beat_gated"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "lift_cap.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("lift_cap_json", json.dumps(res, sort_keys=True))],
        falsifier="valid p95 true-lift cap does not beat G51 and does not beat G59 gated",
        allow_dirty=True,
        note="G61: valid-fitted lift cap on official FB15k-237. Literature unavailable.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
