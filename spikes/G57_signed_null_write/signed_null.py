#!/usr/bin/env python3
"""G57 — G51's write is always positive. Diagnose p=13; try NULL/signed writes.

G51's published formula is
    score = log P(c|p) + log(1 + β · conf / P(c|p))
The second term is >0 whenever a rule fires. A transformer residual can
write nothing (softmax mass on NULL) or write a negative (log-odds).
G51 cannot.

Question: on G54's canary p=13 (n=3856, Δ=−0.049), is the hurt
"rules fire and miss the true target"? Then two knob-free writes:
  lift>1   G51 write only when comb_conf > P(c|p)
  signed   log P + log(comb_conf / P)   (negative when lift<1)
  null     α = lift/(lift+1); write = α · log(lift)   (damped signed)

Not G53 attention. Not G56's random-mask null. Hurting names frozen
from G54 json. Headline = lift>1 (same units as G51; tests the
always-positive-write hypothesis). Signed and null are reported, not
promoted after the run.

  PYTHONUNBUFFERED=1 python3 spikes/G57_signed_null_write/signed_null.py
"""
from __future__ import annotations

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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

BIN = G51.BIN
DEP_DIR = G51.DEP_DIR
SEED = G51.SEED
ALPHA = 0.1
BETA = 0.10
CANARY_P = 13
G54_JSON = os.path.join(SPIKES, "G54_slice_gated_lift", "slice_gated.json")


def load_hurting():
    with open(G54_JSON) as f:
        d = json.load(f)
    names = [int(row["p"]) for row in d.get("hurting_predicates") or []]
    n13 = None
    for row in d.get("hurting_predicates") or []:
        if int(row["p"]) == CANARY_P:
            n13 = int(row["n"])
            break
    return set(names), n13, d["arms"]["C_dev_gated"]["mrr"]


def slim_index(train):
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_tot_obj = defaultdict(int)
    p_tot_sub = defaultdict(int)
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_tot_obj[p] += 1
        p_tot_sub[p] += 1
    return obj_freq, sub_freq, p_tot_obj, p_tot_sub


def noisy_or(conf_list):
    prod = 1.0
    for c in conf_list:
        prod *= 1.0 - min(0.9999, max(0.0, c))
    return max(0.0, min(0.9999, 1.0 - prod))


def writes_for_firings(firings, freq_map, prior_norm, nent):
    """Per-candidate (g51_write, signed_write, lift, comb_conf, p_prior)."""
    out = {}
    for cand, conf_list in firings.items():
        comb = noisy_or(conf_list)
        p_prior = (freq_map.get(cand, 0) + ALPHA) / (prior_norm + ALPHA * nent)
        lift = comb / max(1e-5, p_prior)
        g51_w = math.log(1.0 + max(0.0, BETA * lift))
        signed_w = math.log(max(1e-12, lift))
        alpha = lift / (lift + 1.0)
        null_w = alpha * signed_w
        out[cand] = {
            "g51": g51_w,
            "signed": signed_w,
            "null": null_w,
            "lift": lift,
            "comb": comb,
            "p_prior": p_prior,
        }
    return out


def apply_writes(base_log, freq_map, prior_norm, nent, writes, mode):
    scores = dict(base_log)
    for cand, w in writes.items():
        if cand not in scores:
            p_prior = ALPHA / (prior_norm + ALPHA * nent)
            scores[cand] = math.log(max(1e-12, p_prior))
        if mode == "g51":
            scores[cand] += w["g51"]
        elif mode == "lift_gt1":
            if w["lift"] > 1.0:
                scores[cand] += w["g51"]
        elif mode == "signed":
            scores[cand] += w["signed"]
        elif mode == "null":
            scores[cand] += w["null"]
        else:
            raise ValueError(mode)
    return scores


def metrics_from_ranks(ranks):
    n = len(ranks)
    if n == 0:
        return {"mrr": 0.0, "hits1": 0.0, "hits3": 0.0, "hits10": 0.0, "n_queries": 0}
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


def main():
    t0 = time.time()
    hurting, g54_n13, g54_gated = load_hurting()
    nt, npred, nent, tri = G51.load_raw_triples()
    order_ok, order_obs = G54.field_order_ok(tri, npred, nent)
    train, dev, test, n_groups = G51.pair_disjoint_split(tri, SEED)
    leak = G51.count_same_pair_leak(train, test)
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(tri)
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = slim_index(train)

    print(f"nt={nt} npred={npred} nent={nent} field_ok={order_ok} leak={leak}", flush=True)
    print(f"split train={len(train)} dev={len(dev)} test={len(test)} hurting={len(hurting)}", flush=True)

    print("mining via G51.mine_2hop_rules ...", flush=True)
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_mine:.1f}s", flush=True)

    print("C1/C2 imported G51 eval ...", flush=True)
    t_id = time.time()
    c1 = G51.evaluate_bayesian_hybrid(
        test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="prior_alone"
    )
    c2 = G51.evaluate_bayesian_hybrid(
        test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head,
        mode="bayesian", alpha=ALPHA, beta=BETA,
    )
    print(f"C1 {c1['mrr']:.4f} C2 {c2['mrr']:.4f} ({time.time() - t_id:.1f}s)", flush=True)

    ranks = {k: [] for k in ("prior", "g51", "lift_gt1", "signed", "null")}
    meta = []  # direction, p, hurt_pred
    canary = {
        "n": 0,
        "n_any_fire": 0,
        "n_true_fired": 0,
        "n_g51_worse": 0,
        "n_worse_and_true_fired": 0,
        "n_worse_and_true_miss": 0,
        "sum_write_true": 0.0,
        "sum_write_false": 0.0,
        "n_write_false": 0,
        "n_lift_lt1_true": 0,
        "n_lift_gt1_true": 0,
    }

    print("scoring TEST ...", flush=True)
    t_sc = time.time()
    for p, s, o in test:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            firings = G54.collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            writes = writes_for_firings(firings, freq_map, prior_norm, nent)

            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            scored = {
                "prior": r_prior,
                "g51": G51.rank_from_scores(
                    apply_writes(base_log, freq_map, prior_norm, nent, writes, "g51"),
                    target, filt, nent,
                ),
                "lift_gt1": G51.rank_from_scores(
                    apply_writes(base_log, freq_map, prior_norm, nent, writes, "lift_gt1"),
                    target, filt, nent,
                ),
                "signed": G51.rank_from_scores(
                    apply_writes(base_log, freq_map, prior_norm, nent, writes, "signed"),
                    target, filt, nent,
                ),
                "null": G51.rank_from_scores(
                    apply_writes(base_log, freq_map, prior_norm, nent, writes, "null"),
                    target, filt, nent,
                ),
            }
            for k, rv in scored.items():
                ranks[k].append(rv)
            meta.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "hurting_pred": p in hurting,
            })

            if p == CANARY_P:
                canary["n"] += 1
                any_fire = bool(writes)
                true_fired = target in writes
                if any_fire:
                    canary["n_any_fire"] += 1
                if true_fired:
                    canary["n_true_fired"] += 1
                    if writes[target]["lift"] < 1.0:
                        canary["n_lift_lt1_true"] += 1
                    else:
                        canary["n_lift_gt1_true"] += 1
                    canary["sum_write_true"] += writes[target]["g51"]
                worse = scored["g51"] > scored["prior"] + 1e-12
                if worse:
                    canary["n_g51_worse"] += 1
                    if true_fired:
                        canary["n_worse_and_true_fired"] += 1
                    else:
                        canary["n_worse_and_true_miss"] += 1
                for cand, w in writes.items():
                    if cand == target:
                        continue
                    canary["sum_write_false"] += w["g51"]
                    canary["n_write_false"] += 1

    print(f"TEST {len(ranks['prior'])} queries in {time.time() - t_sc:.1f}s", flush=True)

    arms = {k: metrics_from_ranks(ranks[k]) for k in ranks}

    def slice_axis(keyfn):
        buckets = defaultdict(lambda: {k: [] for k in ranks})
        for i, m in enumerate(meta):
            b = keyfn(m)
            for k in ranks:
                buckets[b][k].append(ranks[k][i])
        out = {}
        for b, v in buckets.items():
            out[str(b)] = {k: metrics_from_ranks(v[k]) for k in ranks}
            out[str(b)]["delta_g51_minus_prior"] = round(
                out[str(b)]["g51"]["mrr"] - out[str(b)]["prior"]["mrr"], 4
            )
            out[str(b)]["delta_gt1_minus_g51"] = round(
                out[str(b)]["lift_gt1"]["mrr"] - out[str(b)]["g51"]["mrr"], 4
            )
        return out

    slices = {
        "direction": slice_axis(lambda m: m["direction"]),
        "hurting_pred": slice_axis(lambda m: "hurt" if m["hurting_pred"] else "help_or_small"),
    }

    n13 = canary["n"]
    worse = canary["n_g51_worse"]
    frac_worse_true_fired = (
        canary["n_worse_and_true_fired"] / worse if worse else None
    )
    # F1: among hurt p=13 queries, true is in firings ≥50% → miss is NOT the mechanism
    f1_fired = (frac_worse_true_fired is not None) and (frac_worse_true_fired >= 0.50)
    f2_delta = round(arms["lift_gt1"]["mrr"] - arms["g51"]["mrr"], 4)
    f2_fired = f2_delta <= 0.0
    f3_delta = round(arms["signed"]["mrr"] - arms["g51"]["mrr"], 4)
    f3_fired = f3_delta <= 0.0
    null_delta = round(arms["null"]["mrr"] - arms["g51"]["mrr"], 4)

    c1_ok = abs(c1["mrr"] - 0.1732) <= 0.0005
    c2_ok = abs(c2["mrr"] - 0.2274) <= 0.0005
    c6_ok = (
        abs(arms["prior"]["mrr"] - c1["mrr"]) <= 0.0005
        and abs(arms["g51"]["mrr"] - c2["mrr"]) <= 0.0005
    )
    c5_ok = (g54_n13 is not None) and (n13 == g54_n13)

    canary_out = {
        **canary,
        "mean_write_true": (canary["sum_write_true"] / canary["n_true_fired"]) if canary["n_true_fired"] else None,
        "mean_write_false": (canary["sum_write_false"] / canary["n_write_false"]) if canary["n_write_false"] else None,
        "frac_any_fire": round(canary["n_any_fire"] / n13, 4) if n13 else None,
        "frac_true_fired": round(canary["n_true_fired"] / n13, 4) if n13 else None,
        "frac_g51_worse": round(canary["n_g51_worse"] / n13, 4) if n13 else None,
        "frac_worse_true_fired": None if frac_worse_true_fired is None else round(frac_worse_true_fired, 4),
        "frac_worse_true_miss": None if not worse else round(canary["n_worse_and_true_miss"] / worse, 4),
    }

    res = {
        "spike": "G57",
        "seed": f"0x{SEED:X}",
        "split": "pair_disjoint (0 leak by construction)",
        "field_order": "p,s,o",
        "headline_arm": "C_lift_gt1",
        "headline_is_test_grid": False,
        "beta": BETA,
        "n_train": len(train),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "n_hurting_frozen_from_g54": len(hurting),
        "g54_gated_mrr": g54_gated,
        "arms": {
            "A_prior": arms["prior"],
            "B_g51": arms["g51"],
            "C_lift_gt1": arms["lift_gt1"],
            "D_signed": arms["signed"],
            "E_softmax_null": arms["null"],
        },
        "slices": slices,
        "canary_p13": canary_out,
        "field_order_obs": order_obs,
        "controls": {
            "C1_prior_reproduction": {"expected_mrr": 0.1732, "observed_mrr": c1["mrr"], "ok": c1_ok},
            "C2_g51_reproduction": {"expected_mrr": 0.2274, "observed_mrr": c2["mrr"], "ok": c2_ok},
            "C3_leak_free": {"leak_triples": leak, "ok": leak == 0},
            "C4_field_order": {"ok": order_ok, **order_obs},
            "C5_canary_n": {"expected": g54_n13, "observed": n13, "ok": c5_ok},
            "C6_per_query_matches_g51_eval": {
                "prior_mrr": arms["prior"]["mrr"],
                "g51_mrr": arms["g51"]["mrr"],
                "ok": c6_ok,
            },
        },
        "falsifiers": {
            "F1_canary_is_not_a_miss": {
                "frac_worse_true_fired": canary_out["frac_worse_true_fired"],
                "n_g51_worse": worse,
                "fired": f1_fired,
                "description": "Fires if among p=13 queries G51-worse-than-prior, true is in firings ≥50% (miss is NOT the mechanism)",
            },
            "F2_lift_gt1_does_not_beat_g51": {
                "lift_gt1_mrr": arms["lift_gt1"]["mrr"],
                "g51_mrr": arms["g51"]["mrr"],
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if lift>1 gate MRR ≤ G51. Signed.",
            },
            "F3_signed_does_not_beat_g51": {
                "signed_mrr": arms["signed"]["mrr"],
                "g51_mrr": arms["g51"]["mrr"],
                "delta": f3_delta,
                "null_delta": null_delta,
                "fired": f3_fired,
                "description": "Fires if signed residual MRR ≤ G51. Signed. null_delta recorded so a LOSS is visible.",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "signed_null.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G57 arms ===", flush=True)
    for k, v in res["arms"].items():
        print(f"  {k:18s} MRR={v['mrr']:.4f} H@1={v['hits1']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(f"p13 n={n13} any_fire={canary_out['frac_any_fire']} true_fired={canary_out['frac_true_fired']} "
          f"g51_worse={canary_out['frac_g51_worse']} worse_miss={canary_out['frac_worse_true_miss']}", flush=True)
    print(f"F1 fired={f1_fired} F2 fired={f2_fired} (Δ={f2_delta:+.4f}) F3 fired={f3_fired} (Δ={f3_delta:+.4f}) null Δ={null_delta:+.4f}", flush=True)
    print(f"slices direction={slices['direction']} hurting={slices['hurting_pred']}", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_prior_reproduction", why="imported G51 prior = 0.1732",
                can_fail_because="split drifted", null_must_contain="unexpected prior"),
        Control("C2_g51_reproduction", why="imported G51 β=0.10 = 0.2274",
                can_fail_because="lift formula drifted", null_must_contain="unexpected G51"),
        Control("C3_leak_free", why="0 same-pair leak",
                can_fail_because="partition broken", null_must_contain="leak>0"),
        Control("C4_field_order", why="(p,s,o) max(p)<npred",
                can_fail_because="G52 swap", null_must_contain="max_p>=npred"),
        Control("C5_canary_n", why="p=13 query count matches G54",
                can_fail_because="split or query loop drifted", null_must_contain="n≠3856"),
        Control("C6_per_query_matches_g51_eval", why="per-query prior/g51 match imported eval",
                can_fail_because="different instrument", null_must_contain="aggregate mismatch"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_prior_reproduction"])
    controls[1].observe(c2_ok, res["controls"]["C2_g51_reproduction"])
    controls[2].observe(leak == 0, res["controls"]["C3_leak_free"])
    controls[3].observe(order_ok, res["controls"]["C4_field_order"])
    controls[4].observe(c5_ok, res["controls"]["C5_canary_n"])
    controls[5].observe(c6_ok, res["controls"]["C6_per_query_matches_g51_eval"])

    falsifiers = [
        Falsifier("F1_canary_is_not_a_miss",
                  refutes="that p=13 hurt is rules missing the true target",
                  fires_when="among G51-worse p=13 queries, true in firings ≥50%",
                  null_must_contain="true mostly present on hurt queries"),
        Falsifier("F2_lift_gt1_does_not_beat_g51",
                  refutes="that refusing lift<1 writes raises MRR",
                  fires_when="lift_gt1_mrr ≤ g51_mrr",
                  null_must_contain="signed delta, including a loss"),
        Falsifier("F3_signed_does_not_beat_g51",
                  refutes="that a signed log-odds residual beats always-positive G51",
                  fires_when="signed_mrr ≤ g51_mrr",
                  null_must_contain="signed delta, including a loss"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_canary_is_not_a_miss"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_lift_gt1_does_not_beat_g51"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_signed_does_not_beat_g51"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[DEP_DIR, os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G54_slice_gated_lift")],
        artifacts=[os.path.join(HERE, "signed_null.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("signed_null_json", json.dumps(res, sort_keys=True))],
        falsifier="p=13 hurt is not a miss AND lift>1 and signed both fail to beat G51",
        allow_dirty=True,
        note="G57: diagnose p=13; lift>1 gate and signed/null residual writes on pair-disjoint split.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
