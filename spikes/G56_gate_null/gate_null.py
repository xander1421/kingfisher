#!/usr/bin/env python3
"""G56 — is G54's DEV-gated +0.0039 a mechanism or selection noise?

Question first: G54 turned G51 off on 105 predicates using DEV Δ.
TEST moved 0.2274 → 0.2313. 237 predicates, 36 hurting with n>=50.
A mask that can choose 105 names will beat the mean by chance.

Architectures:
  dev-gated     reconstruct G54's rule on DEV (n<20 keep G51, else G51 iff Δ>0).
                Hash the mask before TEST is scored (C5 vs G54 0.2313).
  entropy-gated train-only: G51 iff H_obj(p) > median train entropy.
                No DEV labels. G54 slices already predict a loss.

Null: 1000 random masks with the same OFF count among DEV-eligible
predicates (n>=20). F1 fires if true DEV-gated is not above the 95th
percentile of that null.

  python3 spikes/G56_gate_null/gate_null.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

DEP_DIR = G51.DEP_DIR
SEED = G51.SEED
ALPHA = 0.1
BETA = 0.10
MIN_DEV_N = 20
N_RAND = 1000
G54_GATED = 0.2313


def field_order_ok(tri, npred, nent):
    max_p = max(p for p, s, o in tri)
    max_s = max(s for p, s, o in tri)
    max_o = max(o for p, s, o in tri)
    ok = max_p < npred and max_s < nent and max_o < nent
    return ok, {"npred": npred, "nent": nent, "max_p": max_p, "max_s": max_s, "max_o": max_o}


def metrics_from_ranks(ranks):
    n = len(ranks)
    rr = h1 = h3 = h10 = 0.0
    for r in ranks:
        rr += 1.0 / r
        h1 += r <= 1.0
        h3 += r <= 3.0
        h10 += r <= 10.0
    return {
        "mrr": round(rr / n, 4),
        "hits1": round(h1 / n, 4),
        "hits3": round(h3 / n, 4),
        "hits10": round(h10 / n, 4),
        "n_queries": n,
    }


def shannon_norm(counter):
    tot = sum(counter.values())
    if tot <= 0:
        return 0.0
    h = 0.0
    for c in counter.values():
        p = c / tot
        if p > 0:
            h -= p * math.log(p)
    return h


def collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj):
    firings = defaultdict(list)
    if want_tail:
        for (q, r), conf in rules_by_head.get(p, []):
            for z in out_adj[q].get(s, []):
                for cand in out_adj[r].get(z, []):
                    if cand != s:
                        firings[cand].append(min(0.9999, conf))
    else:
        for (q, r), conf in rules_by_head.get(p, []):
            for z in in_adj[r].get(o, []):
                for cand in in_adj[q].get(z, []):
                    if cand != o:
                        firings[cand].append(min(0.9999, conf))
    return firings


def apply_g51(freq_map, tot, nent, firings):
    prior_norm = max(1, tot)
    scores = {}
    for cand, count in freq_map.items():
        p_prior = (count + ALPHA) / (prior_norm + ALPHA * nent)
        scores[cand] = math.log(max(1e-12, p_prior))
    for cand, conf_list in firings.items():
        if cand not in scores:
            p_prior = ALPHA / (prior_norm + ALPHA * nent)
            scores[cand] = math.log(max(1e-12, p_prior))
        prod = 1.0
        for c in conf_list:
            prod *= 1.0 - min(0.9999, max(0.0, c))
        comb_conf = max(0.0, min(0.9999, 1.0 - prod))
        p_prior_c = (freq_map.get(cand, 0) + ALPHA) / (prior_norm + ALPHA * nent)
        lift_ratio = comb_conf / max(1e-5, p_prior_c)
        scores[cand] += math.log(1.0 + max(0.0, BETA * lift_ratio))
    return scores


def score_split(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, obj_freq, sub_freq, p_tot_obj, p_tot_sub):
    rows = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {cand: float(cnt) for cand, cnt in freq_map.items()}
            firings = collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = apply_g51(freq_map, tot, nent, firings)
            rows.append({
                "p": p,
                "prior": G51.rank_from_scores(prior_counts, target, filt, nent),
                "g51": G51.rank_from_scores(g51, target, filt, nent),
            })
    return rows


def pred_mrr(rows, key):
    buckets = defaultdict(list)
    for r in rows:
        buckets[r["p"]].append(r[key])
    out = {}
    for p, rs in buckets.items():
        n = len(rs)
        out[p] = {"n": n, "mrr": round(sum(1.0 / x for x in rs) / n, 4)}
    return out


def freeze_dev_gate(dev_rows):
    prior = pred_mrr(dev_rows, "prior")
    g51 = pred_mrr(dev_rows, "g51")
    use = {}
    for p in set(prior) | set(g51):
        n = (g51.get(p) or prior.get(p))["n"]
        if n < MIN_DEV_N:
            use[p] = True
        else:
            d = g51.get(p, {"mrr": 0.0})["mrr"] - prior.get(p, {"mrr": 0.0})["mrr"]
            use[p] = d > 0.0
    n_off = sum(1 for v in use.values() if not v)
    eligible = sorted(
        p for p in use
        if (g51.get(p) or prior.get(p))["n"] >= MIN_DEV_N
    )
    payload = {
        "min_dev_n": MIN_DEV_N,
        "n_predicates": len(use),
        "n_g51_on": int(sum(1 for v in use.values() if v)),
        "n_g51_off": int(n_off),
        "n_eligible": len(eligible),
        "use_g51": {str(k): bool(v) for k, v in sorted(use.items())},
    }
    blob = json.dumps(
        {k: v for k, v in payload.items()},
        sort_keys=True,
    ).encode()
    payload["sha256"] = hashlib.sha256(blob).hexdigest()
    return payload, use, eligible, n_off


def apply_mask(rows, use_g51):
    ranks = [r["g51"] if use_g51.get(r["p"], True) else r["prior"] for r in rows]
    return metrics_from_ranks(ranks)


def main():
    t0 = time.time()
    nt, npred, nent, tri = G51.load_raw_triples()
    order_ok, order_obs = field_order_ok(tri, npred, nent)
    train, dev, test, n_groups = G51.pair_disjoint_split(tri, SEED)
    leak = G51.count_same_pair_leak(train, test)
    print(
        f"nt={nt} npred={npred} order_ok={order_ok} train={len(train)} "
        f"dev={len(dev)} test={len(test)} leak={leak}",
        flush=True,
    )
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(tri)
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_tot_obj = defaultdict(int)
    p_tot_sub = defaultdict(int)
    obj_counts = defaultdict(Counter)
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_tot_obj[p] += 1
        p_tot_sub[p] += 1
        obj_counts[p][o] += 1
    h_obj = {p: shannon_norm(obj_counts[p]) for p in range(npred)}
    h_vals = [v for v in h_obj.values()]
    h_med = sorted(h_vals)[len(h_vals) // 2]

    print("mining 2-hop ...", flush=True)
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_mine:.1f}s", flush=True)

    print("scoring DEV ...", flush=True)
    t_d = time.time()
    dev_rows = score_split(
        dev, nent, rules_by_head, out_adj, in_adj, true_sp, true_po,
        obj_freq, sub_freq, p_tot_obj, p_tot_sub,
    )
    print(f"DEV {len(dev_rows)} in {time.time() - t_d:.1f}s", flush=True)
    gate_payload, use_g51, eligible, n_off = freeze_dev_gate(dev_rows)
    print(
        f"gate on={gate_payload['n_g51_on']} off={n_off} "
        f"eligible={len(eligible)} sha={gate_payload['sha256'][:16]}",
        flush=True,
    )

    print("scoring TEST ...", flush=True)
    t_t = time.time()
    test_rows = score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po,
        obj_freq, sub_freq, p_tot_obj, p_tot_sub,
    )
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    prior_arm = metrics_from_ranks([r["prior"] for r in test_rows])
    g51_arm = metrics_from_ranks([r["g51"] for r in test_rows])
    gated_arm = apply_mask(test_rows, use_g51)
    ent_use = {p: (h_obj.get(p, 0.0) > h_med) for p in range(npred)}
    entropy_arm = apply_mask(test_rows, ent_use)

    rng = random.Random(SEED)
    null_mrrs = []
    for i in range(N_RAND):
        off = set(rng.sample(eligible, n_off)) if n_off else set()
        mask = {p: (p not in off) for p in eligible}
        # small-n predicates stay G51 (True); missing → True
        m = apply_mask(test_rows, mask)
        null_mrrs.append(m["mrr"])
    null_mrrs.sort()
    true_mrr = gated_arm["mrr"]
    n_ge = sum(1 for x in null_mrrs if x >= true_mrr)
    pctile = n_ge / N_RAND
    p95 = null_mrrs[int(0.95 * (N_RAND - 1))]
    p50 = null_mrrs[N_RAND // 2]

    f1_fired = pctile >= 0.05  # not above 95th percentile
    f2_delta = round(entropy_arm["mrr"] - g51_arm["mrr"], 4)
    f2_fired = f2_delta <= 0.0

    c1_ok = abs(prior_arm["mrr"] - 0.1732) <= 0.0005
    c2_ok = abs(g51_arm["mrr"] - 0.2274) <= 0.0005
    c5_ok = abs(gated_arm["mrr"] - G54_GATED) <= 0.0005

    res = {
        "spike": "G56",
        "seed": f"0x{SEED:X}",
        "split": "pair_disjoint",
        "n_train": len(train),
        "n_dev": len(dev),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "n_rand": N_RAND,
        "h_median": h_med,
        "arms": {
            "A_prior": prior_arm,
            "B_g51": g51_arm,
            "C_dev_gated": gated_arm,
            "D_entropy_gated": entropy_arm,
        },
        "gate": {
            "sha256": gate_payload["sha256"],
            "n_g51_on": gate_payload["n_g51_on"],
            "n_g51_off": n_off,
            "n_eligible": len(eligible),
        },
        "null": {
            "n": N_RAND,
            "median": p50,
            "p95": p95,
            "min": null_mrrs[0],
            "max": null_mrrs[-1],
            "true_gated": true_mrr,
            "n_random_ge_true": n_ge,
            "pctile_ge": round(pctile, 4),
        },
        "dev_gated_minus_g51": round(gated_arm["mrr"] - g51_arm["mrr"], 4),
        "entropy_minus_g51": f2_delta,
        "field_order_obs": order_obs,
        "controls": {
            "C1_prior": {"ok": c1_ok, "mrr": prior_arm["mrr"]},
            "C2_g51": {"ok": c2_ok, "mrr": g51_arm["mrr"]},
            "C3_leak": {"ok": leak == 0, "leak": leak},
            "C4_field_order": {"ok": order_ok, **order_obs},
            "C5_reproduces_g54_gated": {
                "ok": c5_ok,
                "gated": gated_arm["mrr"],
                "g54": G54_GATED,
            },
        },
        "falsifiers": {
            "F1_gated_is_selection_noise": {
                "pctile_ge": round(pctile, 4),
                "p95_null": p95,
                "true": true_mrr,
                "fired": f1_fired,
                "description": "Fires if DEV-gated is not above the 95th percentile of same-size random masks",
            },
            "F2_entropy_gate_does_not_beat_g51": {
                "entropy_mrr": entropy_arm["mrr"],
                "g51_mrr": g51_arm["mrr"],
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if train-entropy hard gate MRR <= G51. Signed.",
            },
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    out_json = os.path.join(HERE, "gate_null.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G56 arms ===", flush=True)
    for k, v in res["arms"].items():
        print(f"  {k:18s} MRR={v['mrr']:.4f} n={v['n_queries']}", flush=True)
    print(
        f"null median={p50:.4f} p95={p95:.4f} true={true_mrr:.4f} "
        f"P(rand>=true)={pctile:.4f} ({n_ge}/{N_RAND})",
        flush=True,
    )
    print(f"F1 fired={f1_fired} F2 fired={f2_fired} (ent {f2_delta:+.4f})", flush=True)

    controls = [
        Control("C1_prior", why="prior 0.1732", can_fail_because="split drifted",
                null_must_contain="unexpected prior"),
        Control("C2_g51", why="G51 0.2274", can_fail_because="lift drifted",
                null_must_contain="unexpected G51"),
        Control("C3_leak", why="leak 0", can_fail_because="partition broken",
                null_must_contain="leak>0"),
        Control("C4_field_order", why="(p,s,o) max_p<npred",
                can_fail_because="G52 swap", null_must_contain="max_p>=npred"),
        Control("C5_reproduces_g54_gated", why="reconstructed DEV-gated matches G54 0.2313",
                can_fail_because="gate rule drifted from G54",
                null_must_contain="gated MRR != 0.2313"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_prior"])
    controls[1].observe(c2_ok, res["controls"]["C2_g51"])
    controls[2].observe(leak == 0, res["controls"]["C3_leak"])
    controls[3].observe(order_ok, res["controls"]["C4_field_order"])
    controls[4].observe(c5_ok, res["controls"]["C5_reproduces_g54_gated"])

    falsifiers = [
        Falsifier(
            "F1_gated_is_selection_noise",
            refutes="that DEV-gated +0.0039 is a mechanism rather than picking 105 names",
            fires_when="P(random mask MRR >= true) >= 0.05",
            null_must_contain="a percentile on either side of 0.05",
        ),
        Falsifier(
            "F2_entropy_gate_does_not_beat_g51",
            refutes="that a train-entropy hard gate can replace DEV labels",
            fires_when="entropy_gated <= G51",
            null_must_contain="signed entropy-G51 delta",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_gated_is_selection_noise"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_entropy_gate_does_not_beat_g51"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[DEP_DIR, os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G54_slice_gated_lift")],
        artifacts=[os.path.join(HERE, "gate_null.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("gate_null_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "DEV-gated TEST MRR is not above the 95th percentile of same-size "
            "random masks AND/OR train-entropy gate does not beat G51"
        ),
        allow_dirty=True,
        note="G56: DEV-gated vs random-mask null; train-entropy hard gate.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
