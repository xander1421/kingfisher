#!/usr/bin/env python3
"""G55 — residuals stack; they do not replace.

Question (before any arm): G51's +0.0542 is a residual on the frequency
prior (G49: prior alone 0.1732 beats mined rules; G50: adding conf to
counts is inert). G54's type/analog arms REPLACE G51. If the right
algebra is residual, type should (1) fill queries where no 2-hop fires
and (2) STACK on G51 when both fire. Those two architectures are not
in this repository.

  silent-fill  G51 rank if a 2-hop fires, else type residual. Structural,
               no DEV β (A26).
  stack        G51 log-lift PLUS type log(1 + overlap/z). No extra β.

Not this row: G53 (attention, test-grid β/γ, note claims 0.2284 before
the run). G54 analog (GROK-2 is running that). G52 field-order swap.

Instrument: G51 load / split / mine / rank imported. Per-query prior and
G51 must reproduce 0.1732 / 0.2274 (C1/C2/C6).

  python3 spikes/G55_residual_stack/stack.py
"""
from __future__ import annotations

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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

BIN = G51.BIN
DEP_DIR = G51.DEP_DIR
SEED = G51.SEED
ALPHA = 0.1
BETA = 0.10
SILENT_DELTA_BAR = 0.02


def field_order_ok(tri, npred, nent):
    if not tri:
        return False, {"reason": "empty"}
    max_p = max(p for p, s, o in tri)
    max_s = max(s for p, s, o in tri)
    max_o = max(o for p, s, o in tri)
    ok = max_p < npred and max_s < nent and max_o < nent
    return ok, {
        "declared_order": "p,s,o",
        "npred": npred,
        "nent": nent,
        "max_p": max_p,
        "max_s": max_s,
        "max_o": max_o,
    }


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


def build_type_index(train):
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_tot_obj = defaultdict(int)
    p_tot_sub = defaultdict(int)
    obj_preds = defaultdict(set)
    sub_preds = defaultdict(set)
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_tot_obj[p] += 1
        p_tot_sub[p] += 1
        obj_preds[o].add(p)
        sub_preds[s].add(p)
    range_co = defaultdict(Counter)
    domain_co = defaultdict(Counter)
    for p, s, o in train:
        for q in obj_preds[o]:
            if q != p:
                range_co[p][q] += 1
        for q in sub_preds[s]:
            if q != p:
                domain_co[p][q] += 1
    return {
        "obj_freq": obj_freq,
        "sub_freq": sub_freq,
        "p_tot_obj": p_tot_obj,
        "p_tot_sub": p_tot_sub,
        "obj_preds": obj_preds,
        "sub_preds": sub_preds,
        "range_co": range_co,
        "domain_co": domain_co,
        "range_z": {p: max(1, sum(c.values())) for p, c in range_co.items()},
        "domain_z": {p: max(1, sum(c.values())) for p, c in domain_co.items()},
    }


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


def apply_g51_lift(base_log, freq_map, prior_norm, nent, firings):
    cand_scores = dict(base_log)
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
        cand_scores[cand] += math.log(1.0 + max(0.0, BETA * lift_ratio))
    return cand_scores


def type_on(base, p, want_tail, idx, nent, freq_map, prior_norm):
    scores = dict(base)
    if want_tail:
        co, z, of = idx["range_co"][p], idx["range_z"].get(p, 1), idx["obj_preds"]
    else:
        co, z, of = idx["domain_co"][p], idx["domain_z"].get(p, 1), idx["sub_preds"]
    if not co:
        return scores
    for cand in list(scores):
        overlap = 0
        for q in of.get(cand, ()):
            if q != p:
                overlap += co[q]
        if overlap <= 0:
            continue
        scores[cand] += math.log(1.0 + overlap / z)
    return scores


def log_prior_map(freq_map, tot, nent):
    prior_norm = max(1, tot)
    out = {}
    for cand, count in freq_map.items():
        p_prior = (count + ALPHA) / (prior_norm + ALPHA * nent)
        out[cand] = math.log(max(1e-12, p_prior))
    return out, prior_norm


def score_test(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    rows = []
    for p, s, o in test:
        for want_tail, freq_map, tot, target, filt in (
            (True, idx["obj_freq"][p], idx["p_tot_obj"][p], o, true_sp.get((s, p), set())),
            (False, idx["sub_freq"][p], idx["p_tot_sub"][p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {cand: float(cnt) for cand, cnt in freq_map.items()}
            base_log, prior_norm = log_prior_map(freq_map, tot, nent)
            firings = collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = apply_g51_lift(base_log, freq_map, prior_norm, nent, firings)
            typ = type_on(base_log, p, want_tail, idx, nent, freq_map, prior_norm)
            stacked = type_on(g51, p, want_tail, idx, nent, freq_map, prior_norm)
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            r_type = G51.rank_from_scores(typ, target, filt, nent)
            r_stack = G51.rank_from_scores(stacked, target, filt, nent)
            fired = bool(firings)
            r_fill = r_g51 if fired else r_type
            rows.append({
                "fired": fired,
                "ranks": {
                    "prior": r_prior,
                    "g51": r_g51,
                    "type": r_type,
                    "stack": r_stack,
                    "fill": r_fill,
                },
            })
    return rows


def main():
    t0 = time.time()
    nt, npred, nent, tri = G51.load_raw_triples()
    order_ok, order_obs = field_order_ok(tri, npred, nent)
    train, dev, test, n_groups = G51.pair_disjoint_split(tri, SEED)
    leak = G51.count_same_pair_leak(train, test)
    print(
        f"nt={nt} npred={npred} nent={nent} order_ok={order_ok} "
        f"train={len(train)} test={len(test)} leak={leak}",
        flush=True,
    )
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(tri)
    print("mining 2-hop via G51.mine_2hop_rules ...", flush=True)
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_mine:.1f}s", flush=True)

    idx = build_type_index(train)
    print("scoring TEST (prior / G51 / type / stack / silent-fill) ...", flush=True)
    t_sc = time.time()
    rows = score_test(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    print(f"scored {len(rows)} queries in {time.time() - t_sc:.1f}s", flush=True)

    arms = {
        "A_prior": metrics_from_ranks([r["ranks"]["prior"] for r in rows]),
        "B_g51": metrics_from_ranks([r["ranks"]["g51"] for r in rows]),
        "C_type_replace": metrics_from_ranks([r["ranks"]["type"] for r in rows]),
        "D_silent_fill": metrics_from_ranks([r["ranks"]["fill"] for r in rows]),
        "E_stack": metrics_from_ranks([r["ranks"]["stack"] for r in rows]),
    }
    fired = [r for r in rows if r["fired"]]
    silent = [r for r in rows if not r["fired"]]
    slices = {
        "fired": {
            "n": len(fired),
            "prior": metrics_from_ranks([r["ranks"]["prior"] for r in fired]),
            "g51": metrics_from_ranks([r["ranks"]["g51"] for r in fired]),
            "type": metrics_from_ranks([r["ranks"]["type"] for r in fired]),
            "fill": metrics_from_ranks([r["ranks"]["fill"] for r in fired]),
            "stack": metrics_from_ranks([r["ranks"]["stack"] for r in fired]),
        },
        "silent": {
            "n": len(silent),
            "prior": metrics_from_ranks([r["ranks"]["prior"] for r in silent]),
            "g51": metrics_from_ranks([r["ranks"]["g51"] for r in silent]),
            "type": metrics_from_ranks([r["ranks"]["type"] for r in silent]),
            "fill": metrics_from_ranks([r["ranks"]["fill"] for r in silent]),
            "stack": metrics_from_ranks([r["ranks"]["stack"] for r in silent]),
        },
    }
    silent_g51_delta = round(
        slices["silent"]["g51"]["mrr"] - slices["silent"]["prior"]["mrr"], 4
    )
    fired_g51_delta = round(
        slices["fired"]["g51"]["mrr"] - slices["fired"]["prior"]["mrr"], 4
    )
    fill_vs_g51 = round(arms["D_silent_fill"]["mrr"] - arms["B_g51"]["mrr"], 4)
    stack_vs_g51 = round(arms["E_stack"]["mrr"] - arms["B_g51"]["mrr"], 4)
    type_vs_prior = round(arms["C_type_replace"]["mrr"] - arms["A_prior"]["mrr"], 4)

    # F1: there is no silent hole (G51 already lifts silent queries).
    f1_fired = silent_g51_delta >= SILENT_DELTA_BAR
    # F2: silent-fill does not beat G51. Tie and loss both fire (signed).
    f2_fired = fill_vs_g51 <= 0.0
    # F3: stack does not beat G51. Tie and loss both fire (signed).
    f3_fired = stack_vs_g51 <= 0.0

    c1_ok = abs(arms["A_prior"]["mrr"] - 0.1732) <= 0.0005
    c2_ok = abs(arms["B_g51"]["mrr"] - 0.2274) <= 0.0005
    c3_ok = leak == 0
    c4_ok = order_ok

    res = {
        "spike": "G55",
        "seed": f"0x{SEED:X}",
        "split": "pair_disjoint (0 leak by construction)",
        "field_order": "p,s,o",
        "beta": BETA,
        "alpha": ALPHA,
        "n_train": len(train),
        "n_dev_unused": len(dev),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "n_groups": n_groups,
        "headline_arm": "E_stack",
        "headline_is_test_grid": False,
        "dev_used_for_anything": False,
        "arms": arms,
        "slices": slices,
        "silent_g51_minus_prior": silent_g51_delta,
        "fired_g51_minus_prior": fired_g51_delta,
        "fill_minus_g51": fill_vs_g51,
        "stack_minus_g51": stack_vs_g51,
        "type_minus_prior": type_vs_prior,
        "field_order_obs": order_obs,
        "controls": {
            "C1_prior_reproduction": {
                "expected_mrr": 0.1732,
                "observed_mrr": arms["A_prior"]["mrr"],
                "ok": c1_ok,
            },
            "C2_g51_reproduction": {
                "expected_mrr": 0.2274,
                "observed_mrr": arms["B_g51"]["mrr"],
                "ok": c2_ok,
            },
            "C3_leak_free": {"leak_triples": leak, "ok": c3_ok},
            "C4_field_order": {"ok": c4_ok, **order_obs},
        },
        "falsifiers": {
            "F1_no_silent_hole": {
                "silent_g51_minus_prior": silent_g51_delta,
                "bar": SILENT_DELTA_BAR,
                "fired": f1_fired,
                "description": "Fires if silent-slice G51 already beats prior by >=0.02 (no hole to fill)",
            },
            "F2_silent_fill_does_not_beat_g51": {
                "fill_mrr": arms["D_silent_fill"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": fill_vs_g51,
                "fired": f2_fired,
                "description": "Fires if silent-fill MRR <= G51. Signed.",
            },
            "F3_stack_does_not_beat_g51": {
                "stack_mrr": arms["E_stack"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": stack_vs_g51,
                "fired": f3_fired,
                "description": "Fires if stack MRR <= G51. Signed so a LOSS is visible.",
            },
        },
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out_json = os.path.join(HERE, "stack.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G55 arms ===", flush=True)
    for k, v in arms.items():
        print(
            f"  {k:16s} MRR={v['mrr']:.4f} H@1={v['hits1']:.4f} "
            f"H@10={v['hits10']:.4f} n={v['n_queries']}",
            flush=True,
        )
    print(
        f"silent n={slices['silent']['n']} ΔG51={silent_g51_delta:+.4f}  "
        f"fired n={slices['fired']['n']} ΔG51={fired_g51_delta:+.4f}",
        flush=True,
    )
    print(
        f"F1 fired={f1_fired} F2 fired={f2_fired} (fill {fill_vs_g51:+.4f}) "
        f"F3 fired={f3_fired} (stack {stack_vs_g51:+.4f})",
        flush=True,
    )

    controls = [
        Control(
            "C1_prior_reproduction",
            why="per-query prior must reproduce G51 0.1732",
            can_fail_because="split or rank convention drifted",
            null_must_contain="an unexpected prior MRR",
        ),
        Control(
            "C2_g51_reproduction",
            why="per-query G51 β=0.10 must reproduce 0.2274",
            can_fail_because="lift formula drifted from G51",
            null_must_contain="an unexpected G51 MRR",
        ),
        Control(
            "C3_leak_free",
            why="0 same-pair triples between train and test",
            can_fail_because="partition logic broken",
            null_must_contain="leak_triples > 0",
        ),
        Control(
            "C4_field_order",
            why="triples.bin unpacked as (p,s,o); max(p)<npred",
            can_fail_because="G52-style (s,p,o) swap",
            null_must_contain="max_p >= npred",
        ),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_prior_reproduction"])
    controls[1].observe(c2_ok, res["controls"]["C2_g51_reproduction"])
    controls[2].observe(c3_ok, res["controls"]["C3_leak_free"])
    controls[3].observe(c4_ok, res["controls"]["C4_field_order"])

    falsifiers = [
        Falsifier(
            "F1_no_silent_hole",
            refutes="that silent queries are a hole G51 does not lift",
            fires_when="silent Δ(G51-prior) >= 0.02",
            null_must_contain="a silent-slice delta on either side of 0.02",
        ),
        Falsifier(
            "F2_silent_fill_does_not_beat_g51",
            refutes="that swapping type in on silent queries raises test MRR",
            fires_when="fill_mrr <= g51_mrr",
            null_must_contain="signed fill-g51 delta, including a loss",
        ),
        Falsifier(
            "F3_stack_does_not_beat_g51",
            refutes="that type residual on top of G51 lift raises test MRR",
            fires_when="stack_mrr <= g51_mrr",
            null_must_contain="signed stack-g51 delta, including a loss",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_no_silent_hole"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_silent_fill_does_not_beat_g51"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_stack_does_not_beat_g51"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[DEP_DIR, os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "stack.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("stack_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "silent-slice G51 already lifts by >=0.02 AND silent-fill does not "
            "beat G51 AND stack does not beat G51"
        ),
        allow_dirty=True,
        note="G55: silent-fill and G51+type stack on pair-disjoint split. Residuals stack; they do not replace.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
