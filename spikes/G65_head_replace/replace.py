#!/usr/bin/env python3
"""G65 — replace G51 on head; do not stack.

G63: analog beats the head prior (+0.009) and stacked under the gate is
+0.0001. This row uses analog (or a valid-picked head arm) INSTEAD of
G51 on head. Tail stays the G59 predicate gate.

  PYTHONUNBUFFERED=1 python3 spikes/G65_head_replace/replace.py
"""
from __future__ import annotations

import hashlib
import json
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
sys.path.insert(0, os.path.join(SPIKES, "G63_head_analog"))

import bayesian_lift as G51  # noqa: E402
import head_analog as G63  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
MIN_N = 20
GATED = 0.2679
HEAD_GATED = 0.1703
HEAD_KEYS = ("prior", "analog", "analog_only", "g51")
RULES_CACHE = os.path.join(HERE, "rules_cache.json")


def metrics(ranks):
    return G63.metrics(ranks)


def freeze_head_choice(dev_rows):
    buckets = defaultdict(lambda: {k: [] for k in HEAD_KEYS})
    for r in dev_rows:
        if r["direction"] != "head":
            continue
        for k in HEAD_KEYS:
            buckets[r["p"]][k].append(r["ranks"][k])
    choice = {}
    counts = defaultdict(int)
    for p, v in buckets.items():
        n = len(v["g51"])
        if n < MIN_N:
            choice[p] = "g51"
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in HEAD_KEYS}
            choice[p] = max(scores, key=scores.get)
        counts[choice[p]] += 1
    payload = {
        "min_n": MIN_N,
        "n_predicates": len(choice),
        "counts": dict(counts),
        "choice": {str(k): v for k, v in sorted(choice.items())},
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def apply_pred_gate(rows, use_g51):
    """G59: OFF predicates use prior in BOTH directions."""
    xs, head_xs = [], []
    for r in rows:
        on = use_g51.get(r["p"], True)
        k = "g51" if on else "prior"
        xs.append(r["ranks"][k])
        if r["direction"] == "head":
            head_xs.append(r["ranks"][k])
    return metrics(xs), metrics(head_xs)


def apply_replace(rows, use_g51, head_key_or_map):
    """Tail follows the pred-gate. Head is replaced (gate does not apply)."""
    xs, head_xs = [], []
    for r in rows:
        on = use_g51.get(r["p"], True)
        if r["direction"] == "tail":
            k = "g51" if on else "prior"
        elif isinstance(head_key_or_map, dict):
            k = head_key_or_map.get(r["p"], "g51")
        else:
            k = head_key_or_map
        xs.append(r["ranks"][k])
        if r["direction"] == "head":
            head_xs.append(r["ranks"][k])
    return metrics(xs), metrics(head_xs)


def load_or_mine(out_adj, pair_tr, byp, rev):
    if os.path.isfile(RULES_CACHE):
        raw = json.loads(open(RULES_CACHE).read())
        print(f"loaded {len(raw)} cached rules", flush=True)
        return raw
    print("mining official train ...", flush=True)
    t0 = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    dumped = [{"head": r["head"], "body": list(r["body"]), "conf": r["conf"]} for r in rules]
    with open(RULES_CACHE, "w") as f:
        json.dump(dumped, f)
    print(f"mined {len(rules)} in {time.time() - t0:.1f}s", flush=True)
    return dumped


def main():
    t0 = time.time()
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    print(f"official test={len(test)} nent={nent} leak={leak}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    slim = G59.slim_index(train)
    rich = __import__("slice_gated", fromlist=["*"]).build_side_indexes(train, npred)

    dumped = load_or_mine(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in dumped:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))

    print("VALID ...", flush=True)
    t_v = time.time()
    dev_rows = G63.score_all(valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    gate, use_g51 = G63.freeze_pred_gate(dev_rows)
    head_pay, head_choice = freeze_head_choice(dev_rows)
    print(
        f"VALID {len(dev_rows)} in {time.time() - t_v:.1f}s "
        f"pred-gate {gate['sha256'][:12]} head-choice {head_pay['sha256'][:12]} {head_pay['counts']}",
        flush=True,
    )

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows = G63.score_all(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, rich)
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    pred_gate, pred_gate_head = apply_pred_gate(test_rows, use_g51)
    repl_analog, repl_analog_head = apply_replace(test_rows, use_g51, "analog")
    repl_only, repl_only_head = apply_replace(test_rows, use_g51, "analog_only")
    selected, selected_head = apply_replace(test_rows, use_g51, head_choice)

    arms = {
        "A_pred_gate": pred_gate,
        "B_replace_analog": repl_analog,
        "C_replace_analog_only": repl_only,
        "D_valid_select_head": selected,
    }
    slices = {
        "head": {
            "pred_gate": pred_gate_head,
            "replace_analog": repl_analog_head,
            "replace_analog_only": repl_only_head,
            "valid_select": selected_head,
        }
    }

    f1_fired = max(repl_analog["mrr"], repl_only["mrr"]) >= GATED
    f2_delta = round(selected_head["mrr"] - HEAD_GATED, 4)
    f2_fired = f2_delta < 0.005
    f3_delta = round(selected["mrr"] - GATED, 4)
    f3_fired = selected["mrr"] <= GATED

    train_hash = G59.sha256_file(os.path.join(CORPUS, "train.txt"))
    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(pred_gate["mrr"] - GATED) <= 0.0005
    c4_ok = npred == 237
    c5_ok = train_hash.startswith("6e4c2782169a")

    res = {
        "spike": "G65",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "D_valid_select_head",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_test": len(test),
        "n_rules_2hop": len(dumped),
        "pred_gate": {"sha256": gate["sha256"], "n_on": gate["n_g51_on"], "n_off": gate["n_g51_off"]},
        "head_choice": {
            "sha256": head_pay["sha256"],
            "counts": head_pay["counts"],
            "n_predicates": head_pay["n_predicates"],
        },
        "arms": arms,
        "slices": slices,
        "controls": {
            "C1_test_n": {"n": len(test), "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_pred_gate_repro": {"expected": GATED, "observed": pred_gate["mrr"], "ok": c3_ok},
            "C4_237": {"npred": npred, "ok": c4_ok},
            "C5_train_hash": {"sha256": train_hash, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_global_replace_helps": {
                "replace_analog": repl_analog["mrr"],
                "replace_analog_only": repl_only["mrr"],
                "bar": GATED,
                "fired": f1_fired,
                "description": "Fires if B or C >= 0.2679 (global replace helps)",
            },
            "F2_select_head_not_better": {
                "select_head": selected_head["mrr"],
                "g59_head": HEAD_GATED,
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if selected head does not beat 0.1703 by +0.005",
            },
            "F3_select_does_not_beat_g59": {
                "select_mrr": selected["mrr"],
                "g59": GATED,
                "delta": f3_delta,
                "fired": f3_fired,
                "description": "Fires if D <= 0.2679. Signed.",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "replace.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G65 ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:28s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(f"head pred-gate={pred_gate_head['mrr']:.4f} analog={repl_analog_head['mrr']:.4f} "
          f"analog_only={repl_only_head['mrr']:.4f} select={selected_head['mrr']:.4f}", flush=True)
    print(f"F1={f1_fired} F2={f2_fired} (Δ={f2_delta:+.4f}) F3={f3_fired} (Δ={f3_delta:+.4f})", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong split", null_must_contain="n!=20466"),
        Control("C2_leak", why="official leak 0", can_fail_because="id packing broke", null_must_contain="leak>0"),
        Control("C3_pred_gate_repro", why="G59 pred-gate 0.2679", can_fail_because="scorer drifted", null_must_contain="mrr!=0.2679"),
        Control("C4_237", why="237 relations", can_fail_because="vocab broken", null_must_contain="npred!=237"),
        Control("C5_train_hash", why="same official train as G59", can_fail_because="corpus swapped", null_must_contain="hash miss"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_pred_gate_repro"])
    controls[3].observe(c4_ok, res["controls"]["C4_237"])
    controls[4].observe(c5_ok, res["controls"]["C5_train_hash"])

    falsifiers = [
        Falsifier("F1_global_replace_helps", refutes="that G63 slices predict a loss for global replace",
                  fires_when="B or C >= 0.2679", null_must_contain="replace wins without selection"),
        Falsifier("F2_select_head_not_better", refutes="that valid-selected head beats gated head by +0.005",
                  fires_when="select_head − 0.1703 < 0.005", null_must_contain="signed delta"),
        Falsifier("F3_select_does_not_beat_g59", refutes="that head replacement raises official gated MRR",
                  fires_when="D <= 0.2679", null_must_contain="signed delta"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_global_replace_helps"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_select_head_not_better"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_select_does_not_beat_g59"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"), CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "replace.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("replace_json", json.dumps(res, sort_keys=True))],
        falsifier="global replace helps OR valid-select does not beat 0.2679 / head 0.1703",
        allow_dirty=True,
        note="G65: replace G51 on head (global analog or valid-selected arm); tail stays G59 gate.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
