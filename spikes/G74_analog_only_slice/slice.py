#!/usr/bin/env python3
"""G74 — list and slice G65's 28 analog_only head predicates.

G65 valid-select picked analog_only on 28/223 heads and never named them.
This row reconstructs that choice (same sha256) and asks whether the 28
are a transferable regime or a valid-set fluke.

  PYTHONUNBUFFERED=1 python3 spikes/G74_analog_only_slice/slice.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G63_head_analog"))
sys.path.insert(0, os.path.join(SPIKES, "G65_head_replace"))

import bayesian_lift as G51  # noqa: E402
import head_analog as G63  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
import replace as G65  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
GATED = 0.2679
CHOICE_SHA = "6670401bde8a44a6dca1ba4d610672313219cf6a2cb0e8283a9027d903cb7603"
COUNTS = {"g51": 172, "analog_only": 28, "prior": 14, "analog": 9}


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


def mrr_of(ranks):
    if not ranks:
        return 0.0
    return round(sum(1.0 / x for x in ranks) / len(ranks), 4)


def gated_key(p, use_g51):
    return "g51" if use_g51.get(p, True) else "prior"


def pred_stats(train, npred, rules_by_head):
    n_train = Counter(p for p, _, _ in train)
    sub = defaultdict(Counter)
    obj = defaultdict(Counter)
    for p, s, o in train:
        sub[p][s] += 1
        obj[p][o] += 1
    out = {}
    for p in range(npred):
        out[p] = {
            "n_train": int(n_train[p]),
            "n_rules": len(rules_by_head.get(p, [])),
            "h_sub": round(shannon(sub[p]), 4),
            "h_obj": round(shannon(obj[p]), 4),
            "n_subj": len(sub[p]),
            "n_obj": len(obj[p]),
        }
    return out


def group_summary(pids, stats, use_g51):
    if not pids:
        return {"n": 0}
    trains = [stats[p]["n_train"] for p in pids]
    rules = [stats[p]["n_rules"] for p in pids]
    hsubs = [stats[p]["h_sub"] for p in pids]
    n_off = sum(1 for p in pids if not use_g51.get(p, True))
    n_zero = sum(1 for p in pids if stats[p]["n_rules"] == 0)
    return {
        "n": len(pids),
        "median_n_train": float(median(trains)),
        "mean_n_train": round(sum(trains) / len(trains), 1),
        "median_n_rules": float(median(rules)),
        "mean_n_rules": round(sum(rules) / len(rules), 2),
        "median_h_sub": round(median(hsubs), 4),
        "n_gate_off": n_off,
        "p_gate_off": round(n_off / len(pids), 4),
        "n_zero_rules": n_zero,
        "p_zero_rules": round(n_zero / len(pids), 4),
    }


def head_ranks(rows, pids, key_or_fn):
    xs = []
    for r in rows:
        if r["direction"] != "head" or r["p"] not in pids:
            continue
        if callable(key_or_fn):
            xs.append(r["ranks"][key_or_fn(r["p"])])
        else:
            xs.append(r["ranks"][key_or_fn])
    return xs


def apply_head_override(rows, use_g51, override):
    """Tail stays pred-gate. Head uses override[p] if present else gated."""
    xs, head_xs = [], []
    for r in rows:
        on = use_g51.get(r["p"], True)
        if r["direction"] == "tail":
            k = "g51" if on else "prior"
        else:
            k = override.get(r["p"], "g51" if on else "prior")
        xs.append(r["ranks"][k])
        if r["direction"] == "head":
            head_xs.append(r["ranks"][k])
    return G63.metrics(xs), G63.metrics(head_xs)


def main():
    t0 = time.time()
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    rels = sorted({r for _, r, _ in train_txt + valid_txt + test_txt})
    print(f"official test={len(test)} nent={nent} leak={leak} npred={npred}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    slim = G59.slim_index(train)
    rich = __import__("slice_gated", fromlist=["*"]).build_side_indexes(train, npred)

    dumped = G65.load_or_mine(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in dumped:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))

    print("VALID ...", flush=True)
    t_v = time.time()
    dev_rows = G63.score_all(valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    gate, use_g51 = G63.freeze_pred_gate(dev_rows)
    head_pay, head_choice = G65.freeze_head_choice(dev_rows)
    print(
        f"VALID {len(dev_rows)} in {time.time() - t_v:.1f}s "
        f"choice {head_pay['sha256'][:12]} {head_pay['counts']}",
        flush=True,
    )

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows = G63.score_all(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    stats = pred_stats(train, npred, rules_by_head)
    by_arm = defaultdict(list)
    for p, arm in head_choice.items():
        by_arm[arm].append(p)
    ao = sorted(by_arm["analog_only"])
    g51s = sorted(by_arm["g51"])

    pred_gate, pred_gate_head = G65.apply_pred_gate(test_rows, use_g51)
    selected, selected_head = G65.apply_replace(test_rows, use_g51, head_choice)

    ao_test_ao = mrr_of(head_ranks(test_rows, set(ao), "analog_only"))
    ao_test_g51 = mrr_of(head_ranks(test_rows, set(ao), "g51"))
    ao_test_prior = mrr_of(head_ranks(test_rows, set(ao), "prior"))
    ao_test_gated = mrr_of(head_ranks(test_rows, set(ao), lambda p: gated_key(p, use_g51)))
    ao_test_n = len(head_ranks(test_rows, set(ao), "analog_only"))
    g51_test_ao = mrr_of(head_ranks(test_rows, set(g51s), "analog_only"))
    g51_test_g51 = mrr_of(head_ranks(test_rows, set(g51s), "g51"))

    ao_valid_ao = mrr_of(head_ranks(dev_rows, set(ao), "analog_only"))
    ao_valid_g51 = mrr_of(head_ranks(dev_rows, set(ao), "g51"))
    ao_valid_gated = mrr_of(head_ranks(dev_rows, set(ao), lambda p: gated_key(p, use_g51)))

    # Train-only / valid-gate transfer rules (no test peek).
    zero_rules = {p: "analog_only" for p in head_choice if stats[p]["n_rules"] == 0}
    flatter = {p: "analog_only" for p in head_choice if stats[p]["h_sub"] > stats[p]["h_obj"]}
    gate_off = {p: "analog_only" for p, on in use_g51.items() if not on}
    e_all, e_head = apply_head_override(test_rows, use_g51, zero_rules)
    f_all, f_head = apply_head_override(test_rows, use_g51, flatter)
    g_all, g_head = apply_head_override(test_rows, use_g51, gate_off)

    listed = []
    for p in ao:
        n_test_h = sum(1 for r in test_rows if r["direction"] == "head" and r["p"] == p)
        n_valid_h = sum(1 for r in dev_rows if r["direction"] == "head" and r["p"] == p)
        listed.append({
            "p": p,
            "name": rels[p],
            "n_train": stats[p]["n_train"],
            "n_rules": stats[p]["n_rules"],
            "h_sub": stats[p]["h_sub"],
            "h_obj": stats[p]["h_obj"],
            "gate_on": bool(use_g51.get(p, True)),
            "n_valid_head": n_valid_h,
            "n_test_head": n_test_h,
            "valid_mrr_analog_only": mrr_of(head_ranks(dev_rows, {p}, "analog_only")),
            "valid_mrr_g51": mrr_of(head_ranks(dev_rows, {p}, "g51")),
            "valid_mrr_prior": mrr_of(head_ranks(dev_rows, {p}, "prior")),
            "test_mrr_analog_only": mrr_of(head_ranks(test_rows, {p}, "analog_only")),
            "test_mrr_g51": mrr_of(head_ranks(test_rows, {p}, "g51")),
            "test_mrr_gated": mrr_of(head_ranks(test_rows, {p}, lambda q: gated_key(q, use_g51))),
        })

    ao_sum = group_summary(ao, stats, use_g51)
    g51_sum = group_summary(g51s, stats, use_g51)
    prior_sum = group_summary(by_arm["prior"], stats, use_g51)
    analog_sum = group_summary(by_arm["analog"], stats, use_g51)

    f1_fired = ao_test_ao <= ao_test_gated
    f2_fired = ao_sum["median_n_train"] >= g51_sum["median_n_train"]
    f3_fired = ao_sum["p_gate_off"] <= g51_sum["p_gate_off"]

    train_hash = G59.sha256_file(os.path.join(CORPUS, "train.txt"))
    c1_ok = head_pay["sha256"] == CHOICE_SHA
    c2_ok = dict(head_pay["counts"]) == COUNTS
    c3_ok = len(test) == 20466 and leak == 0
    c4_ok = abs(pred_gate["mrr"] - GATED) <= 0.0005
    c5_ok = train_hash.startswith("6e4c2782169a")

    res = {
        "spike": "G74",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "slice_analog_only_28",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_test": len(test),
        "reconstructed_choice": {
            "sha256": head_pay["sha256"],
            "counts": dict(head_pay["counts"]),
            "expected_sha256": CHOICE_SHA,
        },
        "pred_gate": {"sha256": gate["sha256"], "n_on": gate["n_g51_on"], "n_off": gate["n_g51_off"]},
        "groups": {
            "analog_only": ao_sum,
            "g51": g51_sum,
            "prior": prior_sum,
            "analog": analog_sum,
        },
        "on_28": {
            "n_test_head": ao_test_n,
            "valid": {
                "analog_only": ao_valid_ao,
                "g51": ao_valid_g51,
                "gated": ao_valid_gated,
            },
            "test": {
                "analog_only": ao_test_ao,
                "g51": ao_test_g51,
                "prior": ao_test_prior,
                "gated": ao_test_gated,
            },
            "test_172_g51": {"analog_only": g51_test_ao, "g51": g51_test_g51},
        },
        "transfer_arms": {
            "A_pred_gate": pred_gate,
            "D_g65_select": selected,
            "E_zero_rules": e_all,
            "F_flatter_head": f_all,
            "G_gate_off_analog_only": g_all,
        },
        "transfer_heads": {
            "pred_gate": pred_gate_head,
            "g65_select": selected_head,
            "zero_rules": e_head,
            "flatter_head": f_head,
            "gate_off_analog_only": g_head,
        },
        "n_override": {
            "zero_rules": len(zero_rules),
            "flatter_head": len(flatter),
            "gate_off": len(gate_off),
        },
        "predicates": listed,
        "controls": {
            "C1_choice_sha": {"expected": CHOICE_SHA, "observed": head_pay["sha256"], "ok": c1_ok},
            "C2_counts": {"expected": COUNTS, "observed": dict(head_pay["counts"]), "ok": c2_ok},
            "C3_test_leak": {"n": len(test), "leak": leak, "ok": c3_ok},
            "C4_pred_gate_repro": {"expected": GATED, "observed": pred_gate["mrr"], "ok": c4_ok},
            "C5_train_hash": {"sha256": train_hash, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_no_transfer": {
                "ao_test": ao_test_ao,
                "gated_test": ao_test_gated,
                "delta": round(ao_test_ao - ao_test_gated, 4),
                "fired": f1_fired,
                "description": "Fires if analog_only ≤ gated-head on the 28 at TEST",
            },
            "F2_not_rare": {
                "median_n_train_ao": ao_sum["median_n_train"],
                "median_n_train_g51": g51_sum["median_n_train"],
                "fired": f2_fired,
                "description": "Fires if analog_only preds are not rarer than g51 preds",
            },
            "F3_not_abandoned": {
                "p_off_ao": ao_sum["p_gate_off"],
                "p_off_g51": g51_sum["p_gate_off"],
                "fired": f3_fired,
                "description": "Fires if analog_only is not more often pred-gate OFF than g51",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "slice.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G74 ===", flush=True)
    print(f"choice sha {head_pay['sha256'][:12]} match={c1_ok} {head_pay['counts']}", flush=True)
    print(
        f"28 test head analog_only={ao_test_ao:.4f} gated={ao_test_gated:.4f} "
        f"g51={ao_test_g51:.4f} prior={ao_test_prior:.4f} n={ao_test_n}",
        flush=True,
    )
    print(
        f"median n_train ao={ao_sum['median_n_train']} g51={g51_sum['median_n_train']} "
        f"p_off ao={ao_sum['p_gate_off']} g51={g51_sum['p_gate_off']}",
        flush=True,
    )
    print(
        f"transfer E={e_all['mrr']:.4f} F={f_all['mrr']:.4f} G={g_all['mrr']:.4f} "
        f"G65-D={selected['mrr']:.4f} gate={pred_gate['mrr']:.4f}",
        flush=True,
    )
    print(f"F1={f1_fired} F2={f2_fired} F3={f3_fired} elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_choice_sha", why="reconstruct G65 head-choice bytes",
                can_fail_because="scoring drifted", null_must_contain="sha mismatch"),
        Control("C2_counts", why="172/28/14/9",
                can_fail_because="choice function drifted", null_must_contain="counts differ"),
        Control("C3_test_leak", why="official test 20466 leak 0",
                can_fail_because="wrong split", null_must_contain="n!=20466 or leak"),
        Control("C4_pred_gate_repro", why="G59 pred-gate 0.2679",
                can_fail_because="scorer drifted", null_must_contain="mrr!=0.2679"),
        Control("C5_train_hash", why="same official train as G59",
                can_fail_because="corpus swapped", null_must_contain="hash miss"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_choice_sha"])
    controls[1].observe(c2_ok, res["controls"]["C2_counts"])
    controls[2].observe(c3_ok, res["controls"]["C3_test_leak"])
    controls[3].observe(c4_ok, res["controls"]["C4_pred_gate_repro"])
    controls[4].observe(c5_ok, res["controls"]["C5_train_hash"])

    falsifiers = [
        Falsifier("F1_no_transfer", refutes="that analog_only still wins on the 28 at test",
                  fires_when="TEST analog_only ≤ gated-head on the 28",
                  null_must_contain="transfer fails"),
        Falsifier("F2_not_rare", refutes="that analog_only wins because those preds are rare",
                  fires_when="median n_train(ao) >= median n_train(g51)",
                  null_must_contain="not rarer"),
        Falsifier("F3_not_abandoned", refutes="that analog_only is the pred-gate-OFF set",
                  fires_when="P(OFF|ao) <= P(OFF|g51)",
                  null_must_contain="not more often OFF"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_no_transfer"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_not_rare"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_not_abandoned"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"), CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G65_head_replace")],
        artifacts=[os.path.join(HERE, "slice.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("slice_json", json.dumps(res, sort_keys=True))],
        falsifier="analog_only does not transfer on the 28, or they are not rare, or they are not gate-OFF",
        allow_dirty=True,
        note="G74: slice G65 analog_only 28; do not move official 0.2679.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
