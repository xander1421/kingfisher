#!/usr/bin/env python3
"""G60 — valid-fitted gate per (predicate, direction) on official test.

G59 gates whole predicates. Official head MRR 0.1703 vs tail 0.3655.
Question: do some predicates help one direction and hurt the other?

  PYTHONUNBUFFERED=1 python3 spikes/G60_direction_gate/dir_gate.py
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
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

MIN_N = 20
PRED_GATE_REF = 0.2679
HEAD_GATE_REF = 0.1703


def freeze_pred_gate(valid_rows):
    return G59.freeze_gate(valid_rows)


def freeze_dir_gate(valid_rows):
    buckets = defaultdict(lambda: {"a": [], "b": []})
    for r in valid_rows:
        buckets[(r["p"], r["direction"])]["a"].append(r["ranks"]["prior"])
        buckets[(r["p"], r["direction"])]["b"].append(r["ranks"]["g51"])
    use = {}
    for key, v in buckets.items():
        n = len(v["a"])
        ma = sum(1.0 / x for x in v["a"]) / n
        mb = sum(1.0 / x for x in v["b"]) / n
        use[key] = True if n < MIN_N else (mb - ma > 0.0)
    payload = {
        "min_n": MIN_N,
        "n_keys": len(use),
        "n_on": int(sum(1 for v in use.values() if v)),
        "n_off": int(sum(1 for v in use.values() if not v)),
        "use": {f"{p}:{d}": bool(v) for (p, d), v in sorted(use.items())},
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    payload["sha256"] = hashlib.sha256(blob).hexdigest()
    return payload, use


def apply_pred(rows, use):
    return G59.apply_gate(rows, use)


def apply_dir(rows, use):
    return G59.metrics([
        r["ranks"]["g51"] if use.get((r["p"], r["direction"]), True) else r["ranks"]["prior"]
        for r in rows
    ])


def disagree_count(pred_use, dir_use):
    n = 0
    for (p, d), on in dir_use.items():
        if pred_use.get(p, True) != on:
            n += 1
    return n


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
    print("mining 2-hop on official train ...", flush=True)
    t_m = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_m:.1f}s", flush=True)
    idx = G59.slim_index(train)

    print("scoring VALID ...", flush=True)
    t_v = time.time()
    valid_rows = G59.score_split(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx
    )
    print(f"VALID {len(valid_rows)} in {time.time() - t_v:.1f}s", flush=True)
    pred_payload, pred_use = freeze_pred_gate(valid_rows)
    dir_payload, dir_use = freeze_dir_gate(valid_rows)
    print(
        f"pred-gate on={pred_payload['n_g51_on']} off={pred_payload['n_g51_off']} "
        f"dir-gate on={dir_payload['n_on']} off={dir_payload['n_off']} "
        f"disagree={disagree_count(pred_use, dir_use)}",
        flush=True,
    )

    print("scoring TEST ...", flush=True)
    t_t = time.time()
    test_rows = G59.score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx
    )
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    arms = {
        "A_prior": G59.arm_from_rows(test_rows, "prior"),
        "B_g51": G59.arm_from_rows(test_rows, "g51"),
        "C_pred_gate": apply_pred(test_rows, pred_use),
        "D_dir_gate": apply_dir(test_rows, dir_use),
    }
    slices = {
        "prior": G59.slice_direction(test_rows, "prior"),
        "g51": G59.slice_direction(test_rows, "g51"),
        "pred_gate": {
            d: G59.metrics([
                r["ranks"]["g51"] if pred_use.get(r["p"], True) else r["ranks"]["prior"]
                for r in test_rows if r["direction"] == d
            ])
            for d in ("tail", "head")
        },
        "dir_gate": {
            d: G59.metrics([
                r["ranks"]["g51"] if dir_use.get((r["p"], d), True) else r["ranks"]["prior"]
                for r in test_rows if r["direction"] == d
            ])
            for d in ("tail", "head")
        },
    }
    d_all = round(arms["D_dir_gate"]["mrr"] - arms["C_pred_gate"]["mrr"], 4)
    d_head = round(slices["dir_gate"]["head"]["mrr"] - slices["pred_gate"]["head"]["mrr"], 4)
    f1_fired = d_all <= 0.0
    f2_fired = d_head <= 0.0

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(arms["C_pred_gate"]["mrr"] - PRED_GATE_REF) <= 0.0005
    c4_ok = npred == 237
    c5_ok = bool(dir_payload.get("sha256"))

    res = {
        "spike": "G60",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "D_dir_gate",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "n_disagree_pd": disagree_count(pred_use, dir_use),
        "pred_gate": {
            "sha256": pred_payload["sha256"],
            "n_on": pred_payload["n_g51_on"],
            "n_off": pred_payload["n_g51_off"],
        },
        "dir_gate": {
            "sha256": dir_payload["sha256"],
            "n_on": dir_payload["n_on"],
            "n_off": dir_payload["n_off"],
        },
        "arms": arms,
        "slices": slices,
        "dir_minus_pred": d_all,
        "dir_head_minus_pred_head": d_head,
        "controls": {
            "C1_test_n": {"ok": c1_ok, "n": len(test)},
            "C2_leak": {"ok": c2_ok, "leak": leak},
            "C3_pred_gate_repro": {
                "ok": c3_ok,
                "mrr": arms["C_pred_gate"]["mrr"],
                "ref": PRED_GATE_REF,
            },
            "C4_npred": {"ok": c4_ok, "npred": npred},
            "C5_hashed": {"ok": c5_ok, "sha256": dir_payload["sha256"]},
        },
        "falsifiers": {
            "F1_dir_gate_does_not_beat_pred_gate": {
                "dir_mrr": arms["D_dir_gate"]["mrr"],
                "pred_mrr": arms["C_pred_gate"]["mrr"],
                "delta": d_all,
                "fired": f1_fired,
                "description": "Fires if (p,direction) gate MRR <= predicate gate. Signed.",
            },
            "F2_dir_gate_does_not_lift_head": {
                "dir_head": slices["dir_gate"]["head"]["mrr"],
                "pred_head": slices["pred_gate"]["head"]["mrr"],
                "delta": d_head,
                "fired": f2_fired,
                "description": "Fires if dir-gate head <= pred-gate head 0.1703. Signed.",
            },
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    out = os.path.join(HERE, "dir_gate.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G60 arms ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:14s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(
        f"head pred={slices['pred_gate']['head']['mrr']:.4f} "
        f"dir={slices['dir_gate']['head']['mrr']:.4f} Δ={d_head:+.4f}",
        flush=True,
    )
    print(f"F1 fired={f1_fired} (Δ={d_all:+.4f}) F2 fired={f2_fired}", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong file",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="same-pair leak 0", can_fail_because="loader mixed splits",
                null_must_contain="leak>0"),
        Control("C3_pred_gate_repro", why="predicate gate reproduces G59 0.2679",
                can_fail_because="G51/G54 scorer drifted",
                null_must_contain="gated MRR != 0.2679"),
        Control("C4_npred", why="237 relations", can_fail_because="dict unpack wrong",
                null_must_contain="npred!=237"),
        Control("C5_hashed", why="dir mask hashed before test apply",
                can_fail_because="missing sha",
                null_must_contain="empty sha256"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_pred_gate_repro"])
    controls[3].observe(c4_ok, res["controls"]["C4_npred"])
    controls[4].observe(c5_ok, res["controls"]["C5_hashed"])

    falsifiers = [
        Falsifier(
            "F1_dir_gate_does_not_beat_pred_gate",
            refutes="that gating per direction raises official-test MRR",
            fires_when="dir_gate <= pred_gate",
            null_must_contain="signed dir-pred delta",
        ),
        Falsifier(
            "F2_dir_gate_does_not_lift_head",
            refutes="that a per-direction gate closes the official-test head gap",
            fires_when="dir_head <= pred_head",
            null_must_contain="signed head delta",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_dir_gate_does_not_beat_pred_gate"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_dir_gate_does_not_lift_head"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "S52_realkg")],
        artifacts=[os.path.join(HERE, "dir_gate.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("dir_gate_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "per-(p,direction) valid-gate does not beat G59 predicate gate "
            "AND does not raise official-test head MRR"
        ),
        allow_dirty=True,
        note="G60: direction-split valid gate on official FB15k-237. Literature unavailable.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
