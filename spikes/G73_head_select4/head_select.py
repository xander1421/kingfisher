#!/usr/bin/env python3
"""G73 — valid-select HEAD among {gated-G51, analog_only, AA, prior}.

Tail stays the G59 predicate gate. analog_only is G63: rank analog scores
only, NOT residual-on-prior (head 0.1453 vs prior 0.1363). AA is G67:
undirected train graph, AA = sum_{z in N(s)∩N(o)} 1/log(1+deg(z)),
natural log. Do not quote G67 0.2706 as already including analog_only.

  PYTHONUNBUFFERED=1 python3 spikes/G73_head_select4/head_select.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G67_head_aa"))

import aa as G67  # noqa: E402
import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
MIN_N = 20
GATED = 0.2679
HEAD_GATED = 0.1703
HEAD_ANALOG_ONLY = 0.1453
HEAD_AA = 0.1344
HEAD_KEYS = ("g51_gated", "analog_only", "aa", "prior")
RULES_CACHE = os.path.join(HERE, "rules_cache.json")
G67_CACHE = os.path.join(SPIKES, "G67_head_aa", "rules_cache.json")
G65_CACHE = os.path.join(SPIKES, "G65_head_replace", "rules_cache.json")


def attach_analog_only(rows, queries, sub_freq, p_tot_sub, rich, true_po, nent):
    """HEAD analog_only = G54.analog_residual on empty base (not residual-on-prior).

    Scores depend on (p, o) only; cache that map. Tail ranks unused (prior).
    """
    if len(rows) != 2 * len(queries):
        raise RuntimeError(f"score_split row count {len(rows)} != 2*{len(queries)}")
    cache = {}
    for i, (p, s, o) in enumerate(queries):
        tail, head = rows[2 * i], rows[2 * i + 1]
        if tail["direction"] != "tail" or head["direction"] != "head":
            raise RuntimeError("score_split order drifted (expected tail then head)")
        if tail["p"] != p or head["p"] != p:
            raise RuntimeError("score_split predicate drifted")
        key = (p, o)
        if key not in cache:
            freq_map = sub_freq[p]
            tot = p_tot_sub[p]
            _base, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            cache[key] = G54.analog_residual({}, p, s, o, False, rich, nent, prior_norm)
        filt = true_po.get((p, o), set())
        head["ranks"]["analog_only"] = G51.rank_from_scores(cache[key], s, filt, nent)
        tail["ranks"]["analog_only"] = tail["ranks"]["prior"]
        if (i + 1) % 5000 == 0:
            print(f"  analog_only {i + 1}/{len(queries)} cache={len(cache)}", flush=True)


def freeze_head_choice(dev_rows, use_g51):
    buckets = defaultdict(lambda: {k: [] for k in HEAD_KEYS})
    for r in dev_rows:
        if r["direction"] != "head":
            continue
        on = use_g51.get(r["p"], True)
        gated = r["ranks"]["g51"] if on else r["ranks"]["prior"]
        buckets[r["p"]]["g51_gated"].append(gated)
        buckets[r["p"]]["analog_only"].append(r["ranks"]["analog_only"])
        buckets[r["p"]]["aa"].append(r["ranks"]["aa"])
        buckets[r["p"]]["prior"].append(r["ranks"]["prior"])
    choice = {}
    counts = defaultdict(int)
    for p, v in buckets.items():
        n = len(v["g51_gated"])
        if n < MIN_N:
            choice[p] = "g51_gated"
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in HEAD_KEYS}
            choice[p] = max(scores, key=scores.get)
        counts[choice[p]] += 1
    payload = {
        "min_n": MIN_N,
        "n_predicates": len(choice),
        "counts": dict(counts),
        "choice": {str(k): v for k, v in sorted(choice.items())},
        "head_keys": list(HEAD_KEYS),
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def load_or_mine(out_adj, pair_tr, byp, rev):
    for path, label in ((RULES_CACHE, "local"), (G67_CACHE, "G67"), (G65_CACHE, "G65")):
        if os.path.isfile(path):
            raw = json.loads(open(path).read())
            if path != RULES_CACHE:
                os.makedirs(HERE, exist_ok=True)
                shutil.copy2(path, RULES_CACHE)
            print(f"loaded {len(raw)} cached rules ({label})", flush=True)
            return raw
    print("mining official train ...", flush=True)
    t0 = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    dumped = [{"head": r["head"], "body": list(r["body"]), "conf": r["conf"]} for r in rules]
    with open(RULES_CACHE, "w") as f:
        json.dump(dumped, f)
    print(f"mined {len(rules)} in {time.time() - t0:.1f}s", flush=True)
    return dumped


def write_result_md(res):
    arms = res["arms"]
    head = res["slices"]["head"]
    fz = res["falsifiers"]
    ch = res["head_choice"]
    delta_f = fz["F2_select_not_plus005"]["delta"]
    if res["quoted_new_high"]:
        headline_line = (
            f"**Valid-select F is a new high** vs 0.2679 by {delta_f:+.4f} "
            f"(bar +0.005)."
        )
    elif delta_f > 0:
        headline_line = (
            f"**Valid-select F is a footnote, not a new high** "
            f"({arms['F_valid_select_head']['mrr']:.4f} vs 0.2679, "
            f"{delta_f:+.4f} < +0.005). "
            f"Head {head['valid_select']['mrr']:.4f} vs gated 0.1703. "
            f"G67 0.2706 was {{g51_gated, AA, prior}} without analog_only; "
            f"this row is a new measurement. I am **not** moving the official headline."
        )
    else:
        headline_line = (
            f"**Valid-select F does not beat 0.2679** "
            f"({arms['F_valid_select_head']['mrr']:.4f}, {delta_f:+.4f}). "
            f"G67 0.2706 was without analog_only."
        )
    f1 = fz["F1_global_analog_only_replace_loses"]
    f2 = fz["F2_select_not_plus005"]
    f3 = fz["F3_analog_only_head_miss"]
    counts = ch["counts"]
    count_s = " / ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    d_delta = round(arms["D_global_analog_only_head"]["mrr"] - GATED, 4)
    e_delta = round(arms["E_global_aa_head"]["mrr"] - GATED, 4)
    md = f"""# G73 — valid-select HEAD among {{gated-G51, analog_only, AA, prior}}

**GROK-LOCAL.** Tail stays G59 pred-gate. Official split. `certify ok=true`.
**F1 {'FIRED' if f1['fired'] else 'quiet'}. F2 {'FIRED' if f2['fired'] else 'quiet'}. F3 {'FIRED' if f3['fired'] else 'quiet'}.**
analog_only is G63 (rank analog scores, not residual-on-prior). AA is G67.
G67 0.2706 did **not** include analog_only. literature_compare unavailable.
Official headline stays **0.2679**.

Against me: first run is VOID if D leaves G51 on for every head, or if
analog_only is residual-on-prior (head 0.1398). This run
`replace_used_analog_only={str(res['replace_used_analog_only']).lower()}`
({res['n_d_head_analog_only']}/{res['n_head']} head queries used analog_only)
`replace_used_aa={str(res['replace_used_aa']).lower()}`
({res['n_e_head_aa']}/{res['n_head']} head queries used AA).

## Verdict

**Global analog_only-head replace {'loses' if f1['fired'] else 'does not lose'}**: D **{arms['D_global_analog_only_head']['mrr']:.4f}** vs gated **0.2679**
({d_delta:+.4f}). F1 {'fired' if f1['fired'] else 'quiet'} (D ≤ 0.2679). analog_only head {head['analog_only']['mrr']:.4f} vs prior {head['prior']['mrr']:.4f} vs gated 0.1703.
Global AA-head E **{arms['E_global_aa_head']['mrr']:.4f}** ({e_delta:+.4f}); AA head {head['aa']['mrr']:.4f}.

{headline_line}

| Arm | Head | Tail | MRR | Hits@10 |
|---|---|---|---:|---:|
| A | prior | prior | {arms['A_prior']['mrr']:.4f} | {arms['A_prior']['hits10']:.4f} |
| B | G51 | G51 | {arms['B_g51']['mrr']:.4f} | {arms['B_g51']['hits10']:.4f} |
| C | G59 pred-gate | G59 pred-gate | **{arms['C_valid_gated']['mrr']:.4f}** | {arms['C_valid_gated']['hits10']:.4f} |
| D | analog_only always | pred-gate | {arms['D_global_analog_only_head']['mrr']:.4f} | {arms['D_global_analog_only_head']['hits10']:.4f} |
| E | AA always | pred-gate | {arms['E_global_aa_head']['mrr']:.4f} | {arms['E_global_aa_head']['hits10']:.4f} |
| **F (headline)** | valid-picked {{g51_gated, analog_only, AA, prior}} | pred-gate | {arms['F_valid_select_head']['mrr']:.4f} | {arms['F_valid_select_head']['hits10']:.4f} |

Valid head choice: **{count_s}**. Mask sha256 `{ch['sha256'][:12]}…` hashed before test.

## Head slice

| | MRR |
|---|---:|
| prior | {head['prior']['mrr']:.4f} |
| G51 | {head['g51']['mrr']:.4f} |
| G59 gated | {head['gated']['mrr']:.4f} |
| analog_only | {head['analog_only']['mrr']:.4f} |
| AA | {head['aa']['mrr']:.4f} |
| valid-select | {head['valid_select']['mrr']:.4f} |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | D ≤ 0.2679 | D={f1['d_mrr']:.4f} | {'FIRED' if f1['fired'] else 'quiet'} |
| F2 | F − 0.2679 < 0.005 | F={f2['f_mrr']:.4f} Δ={f2['delta']:+.4f} | {'FIRED' if f2['fired'] else 'quiet'} |
| F3 | analog_only head ≤ 0.1703 | analog_only head={f3['analog_only_head']:.4f} | {'FIRED' if f3['fired'] else 'quiet'} |

## Controls

C1 test n={res['n_test']}. C2 leak {res['controls']['C2_leak']['leak']}.
C3 pred-gate **{arms['C_valid_gated']['mrr']:.4f}**. C4 {res['npred']} rels.
C5 select mask hashed before test ({res['controls']['C5_select_mask']['sha256'][:12]}…).
C6 analog_only head **{head['analog_only']['mrr']:.4f}** (G63 0.1453, not residual 0.1398).
C7 AA head **{head['aa']['mrr']:.4f}** (G67 0.1344).

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G73_head_select4/head_select.py`.
Check: `python3 kitchen/test_g73.py`.
"""
    path = os.path.join(HERE, "RESULT.md")
    with open(path, "w") as f:
        f.write(md)
    return path


def main():
    t0 = time.time()
    G67.aa_formula_check()

    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    leak = G51.count_same_pair_leak(train, test)
    print(f"official test={len(test)} nent={nent} npred={npred} leak={leak}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    slim = G59.slim_index(train)
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = slim
    rich = G54.build_side_indexes(train, npred)
    nbrs, inv_log, graph_meta = G67.build_undirected(train)
    print(
        f"undirected simple |V|={graph_meta['n_nodes']} |E|={graph_meta['n_edges']} "
        f"mean_deg={graph_meta['mean_deg']}",
        flush=True,
    )

    dumped = load_or_mine(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in dumped:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))

    print("VALID ...", flush=True)
    t_v = time.time()
    dev_rows = G59.score_split(valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim)
    G67.attach_aa(dev_rows, valid, sub_freq, nbrs, inv_log, true_po, nent)
    attach_analog_only(dev_rows, valid, sub_freq, p_tot_sub, rich, true_po, nent)
    gate, use_g51 = G59.freeze_gate(dev_rows)
    head_pay, head_choice = freeze_head_choice(dev_rows, use_g51)
    mask_hashed_before_test = True
    print(
        f"VALID {len(dev_rows)} in {time.time() - t_v:.1f}s "
        f"pred-gate {gate['sha256'][:12]} on={gate['n_g51_on']} off={gate['n_g51_off']} "
        f"head-choice {head_pay['sha256'][:12]} {head_pay['counts']}",
        flush=True,
    )

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows = G59.score_split(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, slim)
    G67.attach_aa(test_rows, test, sub_freq, nbrs, inv_log, true_po, nent)
    attach_analog_only(test_rows, test, sub_freq, p_tot_sub, rich, true_po, nent)
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    prior = G59.arm_from_rows(test_rows, "prior")
    g51 = G59.arm_from_rows(test_rows, "g51")
    pred_gate, pred_gate_head = G67.apply_pred_gate(test_rows, use_g51)
    repl_ao, repl_ao_head, d_head_keys = G67.apply_replace(test_rows, use_g51, "analog_only")
    repl_aa, repl_aa_head, e_head_keys = G67.apply_replace(test_rows, use_g51, "aa")
    selected, selected_head, f_head_keys = G67.apply_replace(test_rows, use_g51, head_choice)

    n_head = sum(1 for r in test_rows if r["direction"] == "head")
    n_d_ao = sum(1 for k in d_head_keys if k == "analog_only")
    n_e_aa = sum(1 for k in e_head_keys if k == "aa")
    replace_used_analog_only = n_d_ao == n_head and n_head == len(test)
    replace_used_aa = n_e_aa == n_head and n_head == len(test)
    if not replace_used_analog_only:
        raise RuntimeError(
            f"VOID: D did not use analog_only on every head "
            f"(analog_only={n_d_ao}/{n_head}, n_test={len(test)})"
        )
    if not replace_used_aa:
        raise RuntimeError(
            f"VOID: E did not use AA on every head "
            f"(aa={n_e_aa}/{n_head}, n_test={len(test)})"
        )
    n_ao_eq_g51 = sum(
        1 for r in test_rows
        if r["direction"] == "head" and r["ranks"]["analog_only"] == r["ranks"]["g51"]
    )
    if n_ao_eq_g51 == n_head:
        raise RuntimeError("VOID: analog_only ranks identical to G51 on every head")
    n_ao_eq_prior = sum(
        1 for r in test_rows
        if r["direction"] == "head" and r["ranks"]["analog_only"] == r["ranks"]["prior"]
    )
    if n_ao_eq_prior == n_head:
        raise RuntimeError("VOID: analog_only ranks identical to prior on every head")

    head_prior = G59.metrics([r["ranks"]["prior"] for r in test_rows if r["direction"] == "head"])
    head_g51 = G59.metrics([r["ranks"]["g51"] for r in test_rows if r["direction"] == "head"])

    if abs(repl_ao_head["mrr"] - HEAD_ANALOG_ONLY) > 0.0005:
        raise RuntimeError(
            f"VOID: analog_only head {repl_ao_head['mrr']} != {HEAD_ANALOG_ONLY} "
            f"(residual-on-prior is 0.1398; G63 analog_only is 0.1453)"
        )
    if abs(repl_aa_head["mrr"] - HEAD_AA) > 0.0005:
        raise RuntimeError(
            f"VOID: AA head {repl_aa_head['mrr']} != {HEAD_AA} (G67 formula drift)"
        )

    f_counts = defaultdict(int)
    for k in f_head_keys:
        f_counts[k] += 1

    arms = {
        "A_prior": prior,
        "B_g51": g51,
        "C_valid_gated": pred_gate,
        "D_global_analog_only_head": repl_ao,
        "E_global_aa_head": repl_aa,
        "F_valid_select_head": selected,
    }
    slices = {
        "head": {
            "prior": head_prior,
            "g51": head_g51,
            "gated": pred_gate_head,
            "analog_only": repl_ao_head,
            "aa": repl_aa_head,
            "valid_select": selected_head,
        }
    }

    f1_fired = repl_ao["mrr"] <= GATED
    f2_delta = round(selected["mrr"] - GATED, 4)
    f2_fired = f2_delta < 0.005
    f3_fired = repl_ao_head["mrr"] <= HEAD_GATED
    quoted_new_high = (selected["mrr"] - GATED) >= 0.005

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(pred_gate["mrr"] - GATED) <= 0.0005
    c4_ok = npred == 237
    c5_ok = bool(head_pay["sha256"]) and mask_hashed_before_test
    c6_ok = abs(repl_ao_head["mrr"] - HEAD_ANALOG_ONLY) <= 0.0005
    c7_ok = abs(repl_aa_head["mrr"] - HEAD_AA) <= 0.0005

    res = {
        "spike": "G73",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "F_valid_select_head",
        "headline_is_test_grid": False,
        "quoted_new_high": quoted_new_high,
        "literature_compare": "unavailable",
        "g67_0.2706_is_not_this_row": True,
        "note": "G67 0.2706 was {g51_gated, AA, prior} without analog_only",
        "n_test": len(test),
        "npred": npred,
        "n_rules_2hop": len(dumped),
        "n_head": n_head,
        "n_d_head_analog_only": n_d_ao,
        "n_e_head_aa": n_e_aa,
        "replace_used_analog_only": replace_used_analog_only,
        "replace_used_aa": replace_used_aa,
        "n_analog_only_eq_g51_head": n_ao_eq_g51,
        "n_analog_only_eq_prior_head": n_ao_eq_prior,
        "head_keys": list(HEAD_KEYS),
        "graph": graph_meta,
        "pred_gate": {
            "sha256": gate["sha256"],
            "n_on": gate["n_g51_on"],
            "n_off": gate["n_g51_off"],
        },
        "head_choice": {
            "sha256": head_pay["sha256"],
            "counts": head_pay["counts"],
            "n_predicates": head_pay["n_predicates"],
            "n_test_queries_by_choice": dict(f_counts),
        },
        "arms": arms,
        "slices": slices,
        "controls": {
            "C1_test_n": {"n": len(test), "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_pred_gate_repro": {"expected": GATED, "observed": pred_gate["mrr"], "ok": c3_ok},
            "C4_237": {"npred": npred, "ok": c4_ok},
            "C5_select_mask": {
                "sha256": head_pay["sha256"],
                "hashed_before_test": mask_hashed_before_test,
                "ok": c5_ok,
            },
            "C6_analog_only_head": {
                "expected": HEAD_ANALOG_ONLY,
                "observed": repl_ao_head["mrr"],
                "residual_on_prior_is": 0.1398,
                "ok": c6_ok,
            },
            "C7_aa_head": {"expected": HEAD_AA, "observed": repl_aa_head["mrr"], "ok": c7_ok},
        },
        "falsifiers": {
            "F1_global_analog_only_replace_loses": {
                "d_mrr": repl_ao["mrr"],
                "bar": GATED,
                "fired": f1_fired,
                "description": "Fires if D global analog_only-head replace MRR <= 0.2679",
            },
            "F2_select_not_plus005": {
                "f_mrr": selected["mrr"],
                "g59": GATED,
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if F - 0.2679 < 0.005",
            },
            "F3_analog_only_head_miss": {
                "analog_only_head": repl_ao_head["mrr"],
                "g59_head": HEAD_GATED,
                "fired": f3_fired,
                "description": "Fires if analog_only head MRR <= gated head 0.1703",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "select.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")
    write_result_md(res)

    print("\n=== G73 ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:32s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(
        f"head gated={pred_gate_head['mrr']:.4f} analog_only={repl_ao_head['mrr']:.4f} "
        f"aa={repl_aa_head['mrr']:.4f} select={selected_head['mrr']:.4f}",
        flush=True,
    )
    print(f"choice counts {dict(head_pay['counts'])} queries {dict(f_counts)}", flush=True)
    print(
        f"F1={f1_fired} F2={f2_fired} (Δ={f2_delta:+.4f}) F3={f3_fired} "
        f"quoted_new_high={quoted_new_high}",
        flush=True,
    )
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong split",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="official leak 0", can_fail_because="id packing broke",
                null_must_contain="leak>0"),
        Control("C3_pred_gate_repro", why="G59 pred-gate 0.2679", can_fail_because="scorer drifted",
                null_must_contain="mrr!=0.2679"),
        Control("C4_237", why="237 relations", can_fail_because="vocab broken",
                null_must_contain="npred!=237"),
        Control("C5_select_mask", why="head-select mask hashed before test",
                can_fail_because="hashed after peeking at test",
                null_must_contain="hash missing or after test"),
        Control("C6_analog_only_head", why="G63 analog_only head 0.1453 not residual 0.1398",
                can_fail_because="residual-on-prior or analog scorer drift",
                null_must_contain="head!=0.1453"),
        Control("C7_aa_head", why="G67 AA head 0.1344", can_fail_because="AA formula drift",
                null_must_contain="head!=0.1344"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_pred_gate_repro"])
    controls[3].observe(c4_ok, res["controls"]["C4_237"])
    controls[4].observe(c5_ok, res["controls"]["C5_select_mask"])
    controls[5].observe(c6_ok, res["controls"]["C6_analog_only_head"])
    controls[6].observe(c7_ok, res["controls"]["C7_aa_head"])

    falsifiers = [
        Falsifier("F1_global_analog_only_replace_loses",
                  refutes="that global analog_only-head replace beats the G59 gate",
                  fires_when="D <= 0.2679",
                  null_must_contain="signed: replace loses or ties"),
        Falsifier("F2_select_not_plus005",
                  refutes="that valid-select beats 0.2679 by +0.005",
                  fires_when="F - 0.2679 < 0.005",
                  null_must_contain="signed delta"),
        Falsifier("F3_analog_only_head_miss",
                  refutes="that analog_only lifts the hard head level above 0.1703",
                  fires_when="analog_only_head <= 0.1703",
                  null_must_contain="analog-style miss"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_global_analog_only_replace_loses"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_select_not_plus005"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_analog_only_head_miss"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"), CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G54_slice_gated_lift"),
              os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G67_head_aa")],
        artifacts=[os.path.join(HERE, "head_select.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("select_json", json.dumps(res, sort_keys=True))],
        falsifier="global analog_only-head replace <= 0.2679 OR valid-select < +0.005 OR analog_only head <= 0.1703",
        allow_dirty=True,
        note="G73: valid-select HEAD among {gated-G51, analog_only, AA, prior}; tail stays G59 pred-gate.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
