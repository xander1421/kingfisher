#!/usr/bin/env python3
"""G63 — head is hard because the prior is flat. Head-only analogical residual.

G60: (p, direction) gate is a wash. Official head 0.1703 vs tail 0.3655
is a PRIOR gap (0.1363 vs 0.3305), not a coarse mask.

Question: median H(subjects | p) > median H(objects | p)? Then replace
only the HEAD prior with G54's analogical residual. Tail stays G59
valid-gated. Global analog already failed F3 on pair-disjoint.

  PYTHONUNBUFFERED=1 python3 spikes/G61_head_analog/head_analog.py
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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
MIN_DEV_N = 20
HEAD_PRIOR_BAR = 0.1363
GATED_BAR = 0.2679
ANALOG_LIFT_BAR = 0.005


def shannon(counter):
    tot = sum(counter.values())
    if tot <= 0:
        return 0.0
    h = 0.0
    for c in counter.values():
        p = c / tot
        if p > 0:
            h -= p * math.log(p)
    return h


def train_entropies(train, npred):
    obj = defaultdict(Counter)
    sub = defaultdict(Counter)
    for p, s, o in train:
        obj[p][o] += 1
        sub[p][s] += 1
    h_obj = [shannon(obj[p]) for p in range(npred) if obj[p]]
    h_sub = [shannon(sub[p]) for p in range(npred) if sub[p]]
    h_obj.sort()
    h_sub.sort()

    def med(xs):
        if not xs:
            return 0.0
        return xs[len(xs) // 2]

    return {
        "n": len(h_obj),
        "median_h_obj": round(med(h_obj), 4),
        "median_h_sub": round(med(h_sub), 4),
        "mean_h_obj": round(sum(h_obj) / len(h_obj), 4) if h_obj else 0.0,
        "mean_h_sub": round(sum(h_sub) / len(h_sub), 4) if h_sub else 0.0,
    }


def metrics(ranks):
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


def freeze_pred_gate(dev_rows):
    buckets = defaultdict(lambda: {"a": [], "b": []})
    for r in dev_rows:
        buckets[r["p"]]["a"].append(r["ranks"]["prior"])
        buckets[r["p"]]["b"].append(r["ranks"]["g51"])
    use = {}
    for p, v in buckets.items():
        n = len(v["a"])
        ma = sum(1.0 / x for x in v["a"]) / n
        mb = sum(1.0 / x for x in v["b"]) / n
        use[p] = True if n < MIN_DEV_N else (mb - ma > 0.0)
    payload = {
        "min_dev_n": MIN_DEV_N,
        "n_g51_on": int(sum(1 for v in use.values() if v)),
        "n_g51_off": int(sum(1 for v in use.values() if not v)),
        "use_g51": {str(k): bool(v) for k, v in sorted(use.items())},
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return payload, use


def score_all(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich):
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = slim
    rows = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            firings = G54.collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings)
            analog = G54.analog_residual(base_log, p, s, o, want_tail, rich, nent, prior_norm)
            analog_only = G54.analog_residual({}, p, s, o, want_tail, rich, nent, prior_norm)
            g51_on_analog = G54.apply_g51_lift(dict(analog), freq_map, prior_norm, nent, firings)
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": {
                    "prior": G51.rank_from_scores(prior_counts, target, filt, nent),
                    "g51": G51.rank_from_scores(g51, target, filt, nent),
                    "analog": G51.rank_from_scores(analog, target, filt, nent),
                    "analog_only": G51.rank_from_scores(analog_only, target, filt, nent),
                    "g51_on_analog": G51.rank_from_scores(g51_on_analog, target, filt, nent),
                },
            })
    return rows


def pick(rows, key, direction=None):
    xs = []
    for r in rows:
        if direction and r["direction"] != direction:
            continue
        xs.append(r["ranks"][key])
    return metrics(xs)


def gated_mix(rows, use_g51, head_key, tail_key, off="prior"):
    """OFF predicates use `off` in BOTH directions (G59 predicate gate)."""
    xs = []
    for r in rows:
        on = use_g51.get(r["p"], True)
        if r["direction"] == "tail":
            k = tail_key if on else off
        else:
            k = head_key if on else off
        xs.append(r["ranks"][k])
    return metrics(xs)


def main():
    t0 = time.time()
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    print(f"official train={len(train)} valid={len(valid)} test={len(test)} nent={nent} leak={leak}", flush=True)

    ent = train_entropies(train, npred)
    print(f"entropy median H_obj={ent['median_h_obj']} H_sub={ent['median_h_sub']}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    slim = G59.slim_index(train)
    rich = G54.build_side_indexes(train, npred)

    print("mining official train ...", flush=True)
    t_m = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_m:.1f}s", flush=True)

    print("VALID ...", flush=True)
    t_v = time.time()
    dev_rows = score_all(valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    gate, use_g51 = freeze_pred_gate(dev_rows)
    print(f"VALID {len(dev_rows)} in {time.time() - t_v:.1f}s gate {gate['sha256'][:12]} on={gate['n_g51_on']}", flush=True)

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows = score_all(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    pred_gate = gated_mix(test_rows, use_g51, head_key="g51", tail_key="g51")
    # head analog residual + G51, tail G59-style gate
    head_analog_gated = gated_mix(test_rows, use_g51, head_key="g51_on_analog", tail_key="g51")
    # for OFF predicates, head analog residual without G51, tail prior
    def mix_off_prior(rows, use, head_on, head_off, tail_on):
        xs = []
        for r in rows:
            on = use.get(r["p"], True)
            if r["direction"] == "tail":
                xs.append(r["ranks"][tail_on if on else "prior"])
            else:
                xs.append(r["ranks"][head_on if on else head_off])
        return metrics(xs)

    headline = mix_off_prior(test_rows, use_g51, "g51_on_analog", "analog", "g51")

    arms = {
        "A_prior": pick(test_rows, "prior"),
        "B_g51": pick(test_rows, "g51"),
        "C_pred_gate": pred_gate,
        "D_head_analog_gated": headline,
        "E_head_analog_only": pick(test_rows, "analog_only"),
    }
    slices = {
        "head": {
            "prior": pick(test_rows, "prior", "head"),
            "g51": pick(test_rows, "g51", "head"),
            "analog": pick(test_rows, "analog", "head"),
            "analog_only": pick(test_rows, "analog_only", "head"),
            "g51_on_analog": pick(test_rows, "g51_on_analog", "head"),
        },
        "tail": {
            "prior": pick(test_rows, "prior", "tail"),
            "g51": pick(test_rows, "g51", "tail"),
            "pred_gate": pick(
                [r for r in test_rows if r["direction"] == "tail"],
                "g51",
            ),
        },
    }
    # tail pred_gate should use the mix
    slices["tail"]["pred_gate"] = metrics([
        r["ranks"]["g51"] if use_g51.get(r["p"], True) else r["ranks"]["prior"]
        for r in test_rows if r["direction"] == "tail"
    ])

    head_analog_mrr = slices["head"]["analog_only"]["mrr"]
    head_prior_mrr = slices["head"]["prior"]["mrr"]
    f1_fired = ent["median_h_sub"] <= ent["median_h_obj"]
    f2_delta = round(head_analog_mrr - head_prior_mrr, 4)
    f2_fired = f2_delta < ANALOG_LIFT_BAR
    f3_delta = round(headline["mrr"] - GATED_BAR, 4)
    f3_fired = headline["mrr"] <= GATED_BAR

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(pred_gate["mrr"] - GATED_BAR) <= 0.0005
    c4_ok = npred == 237
    train_hash = G59.sha256_file(os.path.join(CORPUS, "train.txt"))
    c5_ok = train_hash.startswith("6e4c2782169a")

    res = {
        "spike": "G63",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "D_head_analog_gated",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "entropy": ent,
        "gate": {"sha256": gate["sha256"], "n_g51_on": gate["n_g51_on"], "n_g51_off": gate["n_g51_off"]},
        "arms": arms,
        "slices": slices,
        "controls": {
            "C1_test_n": {"n": len(test), "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_pred_gate_repro": {"expected": GATED_BAR, "observed": pred_gate["mrr"], "ok": c3_ok},
            "C4_237": {"npred": npred, "ok": c4_ok},
            "C5_train_hash": {"sha256": train_hash, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_head_is_not_flatter": {
                "median_h_sub": ent["median_h_sub"],
                "median_h_obj": ent["median_h_obj"],
                "fired": f1_fired,
                "description": "Fires if median H(subject|p) <= median H(object|p)",
            },
            "F2_head_analog_not_better_prior": {
                "head_analog_only": head_analog_mrr,
                "head_prior": head_prior_mrr,
                "delta": f2_delta,
                "bar": ANALOG_LIFT_BAR,
                "fired": f2_fired,
                "description": "Fires if head-analog-only does not beat head prior by +0.005",
            },
            "F3_headline_does_not_beat_g59": {
                "headline_mrr": headline["mrr"],
                "g59_gated": GATED_BAR,
                "delta": f3_delta,
                "fired": f3_fired,
                "description": "Fires if gated+head-analog <= G59 0.2679. Signed.",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "head_analog.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G63 ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:24s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(f"head prior={head_prior_mrr:.4f} analog_only={head_analog_mrr:.4f} analog+g51={slices['head']['g51_on_analog']['mrr']:.4f}", flush=True)
    print(f"F1={f1_fired} F2={f2_fired} (Δ={f2_delta:+.4f}) F3={f3_fired} (Δ={f3_delta:+.4f})", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong split", null_must_contain="n!=20466"),
        Control("C2_leak", why="official leak 0", can_fail_because="id packing broke pairs", null_must_contain="leak>0"),
        Control("C3_pred_gate_repro", why="G59 pred-gate 0.2679", can_fail_because="gate or scorer drifted", null_must_contain="mrr!=0.2679"),
        Control("C4_237", why="237 relations", can_fail_because="vocab broken", null_must_contain="npred!=237"),
        Control("C5_train_hash", why="same official train file as G59", can_fail_because="corpus swapped", null_must_contain="hash prefix miss"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_pred_gate_repro"])
    controls[3].observe(c4_ok, res["controls"]["C4_237"])
    controls[4].observe(c5_ok, res["controls"]["C5_train_hash"])

    falsifiers = [
        Falsifier("F1_head_is_not_flatter", refutes="that head is the higher-entropy side",
                  fires_when="median H_sub <= median H_obj", null_must_contain="subjects not flatter"),
        Falsifier("F2_head_analog_not_better_prior", refutes="that analogical is a better head prior",
                  fires_when="head analog-only − head prior < +0.005", null_must_contain="signed delta"),
        Falsifier("F3_headline_does_not_beat_g59", refutes="that head-analog raises official gated MRR",
                  fires_when="headline <= 0.2679", null_must_contain="signed delta"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_head_is_not_flatter"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_head_analog_not_better_prior"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_headline_does_not_beat_g59"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"), CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "head_analog.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("head_analog_json", json.dumps(res, sort_keys=True))],
        falsifier="head is not flatter OR analog is not a better head prior OR headline does not beat 0.2679",
        allow_dirty=True,
        note="G63: official-split head entropy + head-only analogical residual.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
