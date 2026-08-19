#!/usr/bin/env python3
"""G62 — analog residual on official-test HEAD only; tail stays G59 gate.

Official same-pair leak is 0, so length-1 same-pair features cannot fire.
Head prior is 0.1363 vs tail 0.3305. G54 global analog failed +0.005 vs prior.

  PYTHONUNBUFFERED=1 python3 spikes/G62_head_analog/head_analog.py
"""
from __future__ import annotations

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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

GATED_REF = 0.2679
HEAD_GATED_REF = 0.1703


def score(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, side):
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
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            if want_tail:
                r_an = r_prior
            else:
                analog = G54.analog_residual(
                    base_log, p, s, o, False, side, nent, prior_norm
                )
                r_an = G51.rank_from_scores(analog, target, filt, nent)
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": {"prior": r_prior, "g51": r_g51, "analog": r_an},
            })
    return rows


def hybrid_ranks(rows, pred_use, head_key):
    out = []
    for r in rows:
        if r["direction"] == "tail":
            out.append(r["ranks"]["g51"] if pred_use.get(r["p"], True) else r["ranks"]["prior"])
        else:
            out.append(r["ranks"][head_key])
    return out


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
    slim = G59.slim_index(train)
    side = G54.build_side_indexes(train, npred)

    print("VALID (predicate gate only) ...", flush=True)
    valid_rows = score(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, side
    )
    pred_payload, pred_use = G59.freeze_gate(valid_rows)
    print(
        f"VALID {len(valid_rows)} gate on={pred_payload['n_g51_on']} "
        f"off={pred_payload['n_g51_off']}",
        flush=True,
    )

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows = score(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim, side
    )
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    gated = G59.apply_gate(test_rows, pred_use)
    hybrid = G59.metrics(hybrid_ranks(test_rows, pred_use, "analog"))
    head_rows = [r for r in test_rows if r["direction"] == "head"]
    tail_rows = [r for r in test_rows if r["direction"] == "tail"]
    slices = {
        "head": {
            "prior": G59.arm_from_rows(head_rows, "prior"),
            "g51": G59.arm_from_rows(head_rows, "g51"),
            "gated": G59.metrics([
                r["ranks"]["g51"] if pred_use.get(r["p"], True) else r["ranks"]["prior"]
                for r in head_rows
            ]),
            "analog": G59.arm_from_rows(head_rows, "analog"),
        },
        "tail": {
            "prior": G59.arm_from_rows(tail_rows, "prior"),
            "gated": G59.metrics([
                r["ranks"]["g51"] if pred_use.get(r["p"], True) else r["ranks"]["prior"]
                for r in tail_rows
            ]),
        },
    }
    d_hyb = round(hybrid["mrr"] - gated["mrr"], 4)
    d_head = round(slices["head"]["analog"]["mrr"] - slices["head"]["gated"]["mrr"], 4)
    f1_fired = d_hyb <= 0.0
    f2_fired = d_head <= 0.0

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(gated["mrr"] - GATED_REF) <= 0.0005
    c4_ok = npred == 237

    res = {
        "spike": "G62",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "D_hybrid_gated_tail_analog_head",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "n_rules_2hop": len(rules),
        "pred_gate": {
            "sha256": pred_payload["sha256"],
            "n_on": pred_payload["n_g51_on"],
            "n_off": pred_payload["n_g51_off"],
        },
        "arms": {
            "A_prior": G59.arm_from_rows(test_rows, "prior"),
            "B_g51": G59.arm_from_rows(test_rows, "g51"),
            "C_valid_gated": gated,
            "D_hybrid_gated_tail_analog_head": hybrid,
        },
        "slices": slices,
        "hybrid_minus_gated": d_hyb,
        "analog_head_minus_gated_head": d_head,
        "controls": {
            "C1_test_n": {"ok": c1_ok, "n": len(test)},
            "C2_leak": {"ok": c2_ok, "leak": leak},
            "C3_gated": {"ok": c3_ok, "mrr": gated["mrr"], "ref": GATED_REF},
            "C4_npred": {"ok": c4_ok, "npred": npred},
        },
        "falsifiers": {
            "F1_hybrid_does_not_beat_gated": {
                "hybrid_mrr": hybrid["mrr"],
                "gated_mrr": gated["mrr"],
                "delta": d_hyb,
                "fired": f1_fired,
                "description": "Fires if gated-tail+analog-head <= G59 0.2679. Signed.",
            },
            "F2_analog_does_not_lift_head": {
                "analog_head": slices["head"]["analog"]["mrr"],
                "gated_head": slices["head"]["gated"]["mrr"],
                "delta": d_head,
                "fired": f2_fired,
                "description": "Fires if analog head <= gated head 0.1703. Signed.",
            },
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    out = os.path.join(HERE, "head_analog.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G62 arms ===", flush=True)
    for k, v in res["arms"].items():
        print(f"  {k:36s} MRR={v['mrr']:.4f}", flush=True)
    print(
        f"head analog={slices['head']['analog']['mrr']:.4f} "
        f"gated={slices['head']['gated']['mrr']:.4f} Δ={d_head:+.4f}",
        flush=True,
    )
    print(f"F1 fired={f1_fired} Δ={d_hyb:+.4f} F2 fired={f2_fired}", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong file",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="leak 0", can_fail_because="loader mix",
                null_must_contain="leak>0"),
        Control("C3_gated", why="pred-gate 0.2679", can_fail_because="G59 scorer drifted",
                null_must_contain="gated != 0.2679"),
        Control("C4_npred", why="237 relations", can_fail_because="dict unpack",
                null_must_contain="npred!=237"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_gated"])
    controls[3].observe(c4_ok, res["controls"]["C4_npred"])

    falsifiers = [
        Falsifier(
            "F1_hybrid_does_not_beat_gated",
            refutes="that analog on head plus gated tail raises official MRR",
            fires_when="hybrid <= gated",
            null_must_contain="signed hybrid-gated delta",
        ),
        Falsifier(
            "F2_analog_does_not_lift_head",
            refutes="that object-signature analog moves the official-test head level",
            fires_when="analog_head <= gated_head",
            null_must_contain="signed analog-head delta",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_hybrid_does_not_beat_gated"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_analog_does_not_lift_head"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G54_slice_gated_lift")],
        artifacts=[os.path.join(HERE, "head_analog.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("head_analog_json", json.dumps(res, sort_keys=True))],
        falsifier="head-only analog does not beat G59 gated overall and does not lift head",
        allow_dirty=True,
        note="G62: official-test head analog; tail stays G59 gate. Literature unavailable.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
