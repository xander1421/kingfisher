#!/usr/bin/env python3
"""G54 — slice G51's lift, then two architectures that do not exist.

Question (stated before any arm): G51's +0.0542 filtered MRR is an aggregate.
If the lift is concentrated, inverted, or direction-specific, a gated model
that turns it OFF where DEV says it hurts should beat 0.2274 with no test
β. That is G46's lesson applied to G51 itself.

Architectures that are not in this repository:
  gated   DEV-selected residual: per predicate, use G51 iff DEV Δ>0, else prior.
          Mask is hashed before test is scored. No test-fitted β (A26).
  type    Second-order type residual: log P(c|p) + log(1 + co-predicate overlap
          of c with the empirical range of p). No ontology, no rules.
  analog  Neighborhood analogical prior: score c by Jaccard of predicate
          signatures between the query entity and train partners of p.

Not this row: G53 (attention, unrun, knobs). G52 (triples.bin unpacked as
(s,p,o); the file is (p,s,o) — C4 exists because that happened).

Instrument identity: G51's load / split / mine / rank / evaluate are imported,
not rewritten. C1/C2 call G51.evaluate_bayesian_hybrid on the same objects.

  python3 spikes/G54_slice_gated_lift/slice_gated.py

Read-only outside this directory except harness + G51 imports.
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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

BIN = G51.BIN
DEP_DIR = G51.DEP_DIR
SEED = G51.SEED
ALPHA = 0.1
BETA = 0.10  # G51 published arm E, not re-selected
MIN_DEV_N = 20  # pre-registered: fewer DEV queries → keep G51 (status quo)
HURT_MIN_N = 50  # pre-registered: a "hurting predicate" needs this many test queries
SLICE_DELTA_BAR = 0.02  # F1: |slice_Δ - agg_Δ| must exceed this to count as non-uniform


def field_order_ok(tri, npred, nent):
    """triples.bin is (p, s, o). G52 treated it as (s, p, o)."""
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
        "swap_would_fail": bool(max_p < npred and max(max_s, max_o) >= npred),
    }


def quartile_edges(values):
    xs = sorted(values)
    if not xs:
        return (0.0, 0.0, 0.0)
    n = len(xs)

    def at(q):
        i = min(n - 1, max(0, int(q * (n - 1))))
        return float(xs[i])

    return (at(0.25), at(0.50), at(0.75))


def qbin(x, edges):
    e1, e2, e3 = edges
    if x <= e1:
        return 0
    if x <= e2:
        return 1
    if x <= e3:
        return 2
    return 3


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


def jaccard(a, b):
    if not a and not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def build_side_indexes(train, npred):
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_tot_obj = defaultdict(int)
    p_tot_sub = defaultdict(int)
    pred_set = defaultdict(set)
    obj_preds = defaultdict(set)
    sub_preds = defaultdict(set)
    tail_pairs = defaultdict(list)  # p -> [(s, o), ...]
    subj_objs = defaultdict(lambda: defaultdict(list))  # p -> s -> [o, ...]
    obj_subs = defaultdict(lambda: defaultdict(list))  # p -> o -> [s, ...]
    obj_counts = defaultdict(Counter)
    sub_counts = defaultdict(Counter)

    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_tot_obj[p] += 1
        p_tot_sub[p] += 1
        pred_set[s].add(p)
        pred_set[o].add(p)
        obj_preds[o].add(p)
        sub_preds[s].add(p)
        tail_pairs[p].append((s, o))
        obj_counts[p][o] += 1
        sub_counts[p][s] += 1
        subj_objs[p][s].append(o)
        obj_subs[p][o].append(s)

    range_co = defaultdict(Counter)
    domain_co = defaultdict(Counter)
    for p, s, o in train:
        for q in obj_preds[o]:
            if q != p:
                range_co[p][q] += 1
        for q in sub_preds[s]:
            if q != p:
                domain_co[p][q] += 1

    range_z = {p: max(1, sum(c.values())) for p, c in range_co.items()}
    domain_z = {p: max(1, sum(c.values())) for p, c in domain_co.items()}

    h_obj = {p: shannon_norm(obj_counts[p]) for p in range(npred)}
    h_sub = {p: shannon_norm(sub_counts[p]) for p in range(npred)}
    deg = {p: p_tot_obj[p] + p_tot_sub[p] for p in range(npred)}
    h_edges = quartile_edges(list(h_obj.values()))
    d_edges = quartile_edges([v for v in deg.values() if v > 0] or [0.0])

    pred_frozen = {e: frozenset(ps) for e, ps in pred_set.items()}

    return {
        "obj_freq": obj_freq,
        "sub_freq": sub_freq,
        "p_tot_obj": p_tot_obj,
        "p_tot_sub": p_tot_sub,
        "pred_frozen": pred_frozen,
        "obj_preds": obj_preds,
        "sub_preds": sub_preds,
        "tail_pairs": tail_pairs,
        "subj_objs": subj_objs,
        "obj_subs": obj_subs,
        "range_co": range_co,
        "domain_co": domain_co,
        "range_z": range_z,
        "domain_z": domain_z,
        "h_obj": h_obj,
        "h_sub": h_sub,
        "deg": deg,
        "h_edges": h_edges,
        "d_edges": d_edges,
    }


def log_prior_map(freq_map, tot, nent):
    prior_norm = max(1, tot)
    out = {}
    for cand, count in freq_map.items():
        p_prior = (count + ALPHA) / (prior_norm + ALPHA * nent)
        out[cand] = math.log(max(1e-12, p_prior))
    return out, prior_norm


def apply_g51_lift(cand_scores, freq_map, prior_norm, nent, firings):
    """G51 arm E: noisy-OR confidences, then log(1 + β * conf / P(c|p))."""
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


def type_residual(base_log, p, want_tail, idx, nent, freq_map, prior_norm):
    scores = dict(base_log)
    if want_tail:
        co, z, of = idx["range_co"][p], idx["range_z"].get(p, 1), idx["obj_preds"]
    else:
        co, z, of = idx["domain_co"][p], idx["domain_z"].get(p, 1), idx["sub_preds"]
    if not co:
        return scores
    # Rerank the prior's support only. Scoring every entity is G52-slow and
    # is a different candidate set than G51 (A18).
    for cand in list(scores):
        overlap = 0
        for q in of.get(cand, ()):
            if q != p:
                overlap += co[q]
        if overlap <= 0:
            continue
        if cand not in scores:
            p_prior = ALPHA / (prior_norm + ALPHA * nent)
            scores[cand] = math.log(max(1e-12, p_prior))
        scores[cand] += math.log(1.0 + overlap / z)
    return scores


def analog_residual(base_log, p, s, o, want_tail, idx, nent, prior_norm):
    """Same sum as scanning every train pair of p; grouped by the analog entity.

    Scores: for each train (s2, o2) of p, add Jaccard(sig(query), sig(partner)).
    Grouping does one Jaccard per unique partner, then adds that sim to each
    of that partner's objects/subjects. Identical to the pair scan.
    """
    scores = dict(base_log)
    frozen = idx["pred_frozen"]
    if want_tail:
        partners = idx["subj_objs"].get(p, {})
        if not partners:
            return scores
        qsig = frozen.get(s, frozenset())
        analog = defaultdict(float)
        for s2, objs in partners.items():
            sim = jaccard(qsig, frozen.get(s2, frozenset()))
            if sim > 0.0:
                for o2 in objs:
                    analog[o2] += sim
    else:
        partners = idx["obj_subs"].get(p, {})
        if not partners:
            return scores
        qsig = frozen.get(o, frozenset())
        analog = defaultdict(float)
        for o2, subs in partners.items():
            sim = jaccard(qsig, frozen.get(o2, frozenset()))
            if sim > 0.0:
                for s2 in subs:
                    analog[s2] += sim
    if not analog:
        return scores
    z = max(analog.values())
    if z <= 0:
        return scores
    for cand, raw in analog.items():
        if cand not in scores:
            p_prior = ALPHA / (prior_norm + ALPHA * nent)
            scores[cand] = math.log(max(1e-12, p_prior))
        scores[cand] += math.log(1.0 + raw / z)
    return scores


def score_split(queries, train, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    """One pass: prior counts, G51 lift, type residual, analog residual."""
    rows = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt, hval in (
            (True, idx["obj_freq"][p], idx["p_tot_obj"][p], o, true_sp.get((s, p), set()), idx["h_obj"].get(p, 0.0)),
            (False, idx["sub_freq"][p], idx["p_tot_sub"][p], s, true_po.get((p, o), set()), idx["h_sub"].get(p, 0.0)),
        ):
            prior_counts = {cand: float(cnt) for cand, cnt in freq_map.items()}
            base_log, prior_norm = log_prior_map(freq_map, tot, nent)
            firings = collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings)
            typ = type_residual(base_log, p, want_tail, idx, nent, freq_map, prior_norm)
            analog = analog_residual(base_log, p, s, o, want_tail, idx, nent, prior_norm)

            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            r_type = G51.rank_from_scores(typ, target, filt, nent)
            r_analog = G51.rank_from_scores(analog, target, filt, nent)

            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "entropy_q": qbin(hval, idx["h_edges"]),
                "degree_q": qbin(idx["deg"].get(p, 0), idx["d_edges"]),
                "rule_fired": bool(firings),
                "ranks": {
                    "prior": r_prior,
                    "g51": r_g51,
                    "type": r_type,
                    "analog": r_analog,
                },
            })
    return rows


def arm_from_rows(rows, key):
    return metrics_from_ranks([r["ranks"][key] for r in rows])


def slice_table(rows, arm_a, arm_b):
    """Δ = MRR(arm_b) - MRR(arm_a) inside each slice."""
    out = {}
    for axis, getter in (
        ("direction", lambda r: r["direction"]),
        ("entropy_q", lambda r: f"Q{r['entropy_q']}"),
        ("degree_q", lambda r: f"Q{r['degree_q']}"),
        ("rule_fired", lambda r: "fired" if r["rule_fired"] else "silent"),
    ):
        buckets = defaultdict(lambda: {"a": [], "b": []})
        for r in rows:
            k = getter(r)
            buckets[k]["a"].append(r["ranks"][arm_a])
            buckets[k]["b"].append(r["ranks"][arm_b])
        axis_out = {}
        for k, v in buckets.items():
            ma = metrics_from_ranks(v["a"])
            mb = metrics_from_ranks(v["b"])
            axis_out[str(k)] = {
                "n": ma["n_queries"],
                "mrr_a": ma["mrr"],
                "mrr_b": mb["mrr"],
                "delta": round(mb["mrr"] - ma["mrr"], 4),
            }
        out[axis] = axis_out
    return out


def predicate_deltas(rows, arm_a, arm_b):
    buckets = defaultdict(lambda: {"a": [], "b": []})
    for r in rows:
        buckets[r["p"]]["a"].append(r["ranks"][arm_a])
        buckets[r["p"]]["b"].append(r["ranks"][arm_b])
    out = {}
    for p, v in buckets.items():
        ma = metrics_from_ranks(v["a"])
        mb = metrics_from_ranks(v["b"])
        out[int(p)] = {
            "n": ma["n_queries"],
            "mrr_a": ma["mrr"],
            "mrr_b": mb["mrr"],
            "delta": round(mb["mrr"] - ma["mrr"], 4),
        }
    return out


def freeze_gate(dev_rows):
    """Per-predicate winner on DEV. n < MIN_DEV_N keeps G51 (status quo)."""
    d_g51 = predicate_deltas(dev_rows, "prior", "g51")
    d_type = predicate_deltas(dev_rows, "prior", "type")
    d_analog = predicate_deltas(dev_rows, "prior", "analog")
    use_g51 = {}
    best = {}
    for p in set(d_g51) | set(d_type) | set(d_analog):
        n = (d_g51.get(p) or d_type.get(p) or d_analog.get(p))["n"]
        g = d_g51.get(p, {"delta": 0.0})["delta"]
        use_g51[p] = True if n < MIN_DEV_N else (g > 0.0)
        scores = {
            "prior": 0.0,
            "g51": d_g51.get(p, {"delta": 0.0})["delta"],
            "type": d_type.get(p, {"delta": 0.0})["delta"],
            "analog": d_analog.get(p, {"delta": 0.0})["delta"],
        }
        if n < MIN_DEV_N:
            best[p] = "g51"
        else:
            best[p] = max(scores, key=scores.get)
    payload = {
        "min_dev_n": MIN_DEV_N,
        "n_dev_queries": sum(d_g51[p]["n"] for p in d_g51),
        "n_predicates": len(use_g51),
        "n_g51_on": int(sum(1 for v in use_g51.values() if v)),
        "n_g51_off": int(sum(1 for v in use_g51.values() if not v)),
        "best_counts": dict(Counter(best.values())),
        "use_g51": {str(k): bool(v) for k, v in sorted(use_g51.items())},
        "best": {str(k): v for k, v in sorted(best.items())},
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    payload["sha256"] = hashlib.sha256(blob).hexdigest()
    return payload, use_g51, best


def apply_gate(rows, use_g51, best):
    gated = []
    mix = []
    for r in rows:
        p = r["p"]
        gated.append(r["ranks"]["g51"] if use_g51.get(p, True) else r["ranks"]["prior"])
        mix.append(r["ranks"][best.get(p, "g51")])
    return metrics_from_ranks(gated), metrics_from_ranks(mix)


def max_abs_slice_shift(slices, agg_delta):
    biggest = 0.0
    where = None
    for axis, buckets in slices.items():
        for k, v in buckets.items():
            shift = abs(v["delta"] - agg_delta)
            if shift > biggest:
                biggest = shift
                where = f"{axis}:{k}"
    return round(biggest, 4), where


def main():
    t0 = time.time()
    nt, npred, nent, tri = G51.load_raw_triples()
    order_ok, order_obs = field_order_ok(tri, npred, nent)
    train, dev, test, n_groups = G51.pair_disjoint_split(tri, SEED)
    leak = G51.count_same_pair_leak(train, test)
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(tri)

    print(f"triples.bin nt={nt} npred={npred} nent={nent} field_order_ok={order_ok}")
    print(f"split train={len(train)} dev={len(dev)} test={len(test)} groups={n_groups} leak={leak}")
    print("mining 2-hop rules via G51.mine_2hop_rules ...")
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} rules in {time.time() - t_mine:.1f}s")

    print("G51 instrument identity (C1/C2) ...")
    t_id = time.time()
    c1 = G51.evaluate_bayesian_hybrid(
        test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="prior_alone"
    )
    c2 = G51.evaluate_bayesian_hybrid(
        test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head,
        mode="bayesian", alpha=ALPHA, beta=BETA,
    )
    print(f"C1 prior MRR={c1['mrr']:.4f} C2 G51 MRR={c2['mrr']:.4f} ({time.time() - t_id:.1f}s)")

    idx = build_side_indexes(train, npred)
    print("scoring DEV ...")
    t_dev = time.time()
    dev_rows = score_split(dev, train, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    print(f"DEV {len(dev_rows)} queries in {time.time() - t_dev:.1f}s")

    gate_payload, use_g51, best = freeze_gate(dev_rows)
    gate_hash = gate_payload["sha256"]
    print(f"gate frozen sha256={gate_hash} g51_on={gate_payload['n_g51_on']} off={gate_payload['n_g51_off']} best={gate_payload['best_counts']}")

    print("scoring TEST ...")
    t_test = time.time()
    test_rows = score_split(test, train, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    print(f"TEST {len(test_rows)} queries in {time.time() - t_test:.1f}s")

    arms = {
        "A_prior": arm_from_rows(test_rows, "prior"),
        "B_g51": arm_from_rows(test_rows, "g51"),
        "C_dev_gated": None,
        "D_type": arm_from_rows(test_rows, "type"),
        "E_analog": arm_from_rows(test_rows, "analog"),
        "F_dev_mix": None,
    }
    arms["C_dev_gated"], arms["F_dev_mix"] = apply_gate(test_rows, use_g51, best)

    slices = slice_table(test_rows, "prior", "g51")
    pred_d = predicate_deltas(test_rows, "prior", "g51")
    hurting = [
        {"p": p, **v} for p, v in pred_d.items()
        if v["n"] >= HURT_MIN_N and v["delta"] < 0.0
    ]
    hurting.sort(key=lambda x: x["delta"])
    helping = [
        {"p": p, **v} for p, v in pred_d.items()
        if v["n"] >= HURT_MIN_N and v["delta"] > 0.0
    ]
    helping.sort(key=lambda x: -x["delta"])

    agg_delta = round(arms["B_g51"]["mrr"] - arms["A_prior"]["mrr"], 4)
    slice_shift, slice_where = max_abs_slice_shift(slices, agg_delta)

    # F1: lift is uniform (nothing to slice). Fires if both: small slice
    # shifts AND no hurting predicates. Signed so a LOSS is visible.
    f1_fired = (slice_shift < SLICE_DELTA_BAR) and (len(hurting) == 0)
    # F2: gated does not beat G51. A loss is a fire, a tie is a fire.
    f2_delta = round(arms["C_dev_gated"]["mrr"] - arms["B_g51"]["mrr"], 4)
    f2_fired = f2_delta <= 0.0
    # F3: neither new residual beats the prior by +0.005. Signed.
    type_vs_prior = round(arms["D_type"]["mrr"] - arms["A_prior"]["mrr"], 4)
    analog_vs_prior = round(arms["E_analog"]["mrr"] - arms["A_prior"]["mrr"], 4)
    f3_fired = (type_vs_prior < 0.005) and (analog_vs_prior < 0.005)

    c1_ok = abs(c1["mrr"] - 0.1732) <= 0.0005
    c2_ok = abs(c2["mrr"] - 0.2274) <= 0.0005
    # Per-query prior/g51 aggregates must match the imported evaluator.
    c6_ok = (
        abs(arms["A_prior"]["mrr"] - c1["mrr"]) <= 0.0005
        and abs(arms["B_g51"]["mrr"] - c2["mrr"]) <= 0.0005
    )
    recomputed_gate = hashlib.sha256(
        json.dumps({k: v for k, v in gate_payload.items() if k != "sha256"}, sort_keys=True).encode()
    ).hexdigest()
    c5_ok = (recomputed_gate == gate_hash) and (gate_payload["n_dev_queries"] == len(dev_rows))

    res = {
        "spike": "G54",
        "seed": f"0x{SEED:X}",
        "split": "pair_disjoint (0 leak by construction)",
        "field_order": "p,s,o",
        "headline_arm": "C_dev_gated",
        "headline_is_test_grid": False,
        "beta": BETA,
        "alpha": ALPHA,
        "n_train": len(train),
        "n_dev": len(dev),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "n_groups": n_groups,
        "instrument": "G51.evaluate_bayesian_hybrid imported, not copied",
        "arms": arms,
        "slices": slices,
        "slice_shift_max": slice_shift,
        "slice_shift_where": slice_where,
        "agg_delta_g51_minus_prior": agg_delta,
        "hurting_predicates": hurting[:20],
        "n_hurting_predicates": len(hurting),
        "helping_predicates_top": helping[:10],
        "n_helping_predicates": len(helping),
        "gate": {
            "sha256": gate_hash,
            "min_dev_n": MIN_DEV_N,
            "n_g51_on": gate_payload["n_g51_on"],
            "n_g51_off": gate_payload["n_g51_off"],
            "best_counts": gate_payload["best_counts"],
        },
        "field_order_obs": order_obs,
        "controls": {
            "C1_prior_reproduction": {
                "expected_mrr": 0.1732,
                "observed_mrr": c1["mrr"],
                "ok": c1_ok,
            },
            "C2_g51_reproduction": {
                "expected_mrr": 0.2274,
                "observed_mrr": c2["mrr"],
                "ok": c2_ok,
            },
            "C3_leak_free": {"leak_triples": leak, "ok": leak == 0},
            "C4_field_order": {"ok": order_ok, **order_obs},
            "C5_gate_frozen_before_test": {
                "sha256": gate_hash,
                "recomputed": recomputed_gate,
                "n_dev_queries": gate_payload["n_dev_queries"],
                "len_dev_rows": len(dev_rows),
                "ok": c5_ok,
            },
            "C6_per_query_matches_g51_eval": {
                "prior_mrr": arms["A_prior"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "ok": c6_ok,
            },
        },
        "falsifiers": {
            "F1_lift_is_uniform": {
                "slice_shift_max": slice_shift,
                "slice_shift_where": slice_where,
                "n_hurting": len(hurting),
                "agg_delta": agg_delta,
                "bar": SLICE_DELTA_BAR,
                "fired": f1_fired,
                "description": "Fires if lift is uniform: max|slice_Δ-agg_Δ|<0.02 AND zero hurting predicates n>=50",
            },
            "F2_gated_does_not_beat_g51": {
                "gated_mrr": arms["C_dev_gated"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if DEV-gated MRR <= G51 MRR (turning lift off does not help). Signed.",
            },
            "F3_new_architectures_have_no_signal": {
                "type_minus_prior": type_vs_prior,
                "analog_minus_prior": analog_vs_prior,
                "fired": f3_fired,
                "description": "Fires if type and analogical both fail to beat prior by +0.005. Signed so a LOSS is visible.",
            },
        },
    }
    elapsed = time.time() - t0
    res["elapsed_sec"] = round(elapsed, 2)

    out_json = os.path.join(HERE, "slice_gated.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G54 arms ===")
    for k, v in arms.items():
        print(f"  {k:16s} MRR={v['mrr']:.4f} H@1={v['hits1']:.4f} H@3={v['hits3']:.4f} H@10={v['hits10']:.4f} n={v['n_queries']}")
    print(f"slice_shift_max={slice_shift} at {slice_where} agg_Δ={agg_delta} hurting={len(hurting)}")
    print(f"F1 fired={f1_fired} F2 fired={f2_fired} (Δ={f2_delta:+.4f}) F3 fired={f3_fired} type={type_vs_prior:+.4f} analog={analog_vs_prior:+.4f}")
    print(f"elapsed {elapsed:.1f}s")

    controls = [
        Control("C1_prior_reproduction", why="imported G51 prior must reproduce 0.1732",
                can_fail_because="split or rank convention drifted",
                null_must_contain="an unexpected prior MRR"),
        Control("C2_g51_reproduction", why="imported G51 bayesian β=0.10 must reproduce 0.2274",
                can_fail_because="rule miner or lift formula drifted",
                null_must_contain="an unexpected G51 MRR"),
        Control("C3_leak_free", why="0 same-pair triples between train and test",
                can_fail_because="partition logic broken",
                null_must_contain="leak_triples > 0"),
        Control("C4_field_order", why="triples.bin unpacked as (p,s,o); max(p)<npred",
                can_fail_because="G52-style (s,p,o) swap, max first-field >= 237",
                null_must_contain="max_p >= npred"),
        Control("C5_gate_frozen_before_test", why="DEV mask hashed before TEST scoring",
                can_fail_because="gate computed from test rows",
                null_must_contain="missing sha256"),
        Control("C6_per_query_matches_g51_eval", why="per-query prior/g51 MRR match imported evaluator",
                can_fail_because="slice scorer is a different instrument",
                null_must_contain="aggregate mismatch"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_prior_reproduction"])
    controls[1].observe(c2_ok, res["controls"]["C2_g51_reproduction"])
    controls[2].observe(leak == 0, res["controls"]["C3_leak_free"])
    controls[3].observe(order_ok, res["controls"]["C4_field_order"])
    controls[4].observe(c5_ok, res["controls"]["C5_gate_frozen_before_test"])
    controls[5].observe(c6_ok, res["controls"]["C6_per_query_matches_g51_eval"])

    falsifiers = [
        Falsifier("F1_lift_is_uniform",
                  refutes="that G51's +0.0542 is a blend hiding inverted slices",
                  fires_when="max|slice_Δ-agg_Δ|<0.02 AND n_hurting==0",
                  null_must_contain="uniform lift"),
        Falsifier("F2_gated_does_not_beat_g51",
                  refutes="that turning lift off on DEV-hurt predicates raises test MRR",
                  fires_when="gated_mrr <= g51_mrr",
                  null_must_contain="gated loss or tie, signed"),
        Falsifier("F3_new_architectures_have_no_signal",
                  refutes="that type-signature or analogical residuals beat the frequency prior",
                  fires_when="type_Δ<0.005 AND analog_Δ<0.005",
                  null_must_contain="signed deltas, including losses"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_lift_is_uniform"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_gated_does_not_beat_g51"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_new_architectures_have_no_signal"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[DEP_DIR, os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "slice_gated.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("slice_gated_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "G51 lift uniform across slices AND DEV-gated fails to beat G51 "
            "AND type/analog both fail to beat the prior by +0.005"
        ),
        allow_dirty=True,
        note="G54: slice G51 lift; DEV-gated residual; type-signature and analogical priors on pair-disjoint split.",
    )
    print(f"\nD6 certify ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
