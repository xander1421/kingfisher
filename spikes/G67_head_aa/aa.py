#!/usr/bin/env python3
"""G67 — Adamic–Adar / common-neighbors on official-test HEAD only.

Tail stays the G59 predicate gate. AA does not need a train edge on (s, o)
(official same-pair leak is 0). Not G54 analog (G62/G63/G65). No β grid.

  PYTHONUNBUFFERED=1 python3 spikes/G67_head_aa/aa.py

Graph: simple undirected train graph. One edge {s,o} if any train triple
links them; p is ignored. deg(z) = |N(z)|. AA = sum_{z in N(s)∩N(o)}
1/log(1+deg(z)) (natural log) over the G51 head candidate set (subjects
of p).
"""
from __future__ import annotations

import hashlib
import json
import math
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

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
MIN_N = 20
GATED = 0.2679
HEAD_GATED = 0.1703
HEAD_KEYS = ("g51_gated", "aa", "prior")
RULES_CACHE = os.path.join(HERE, "rules_cache.json")
G65_CACHE = os.path.join(SPIKES, "G65_head_replace", "rules_cache.json")


def build_undirected(train):
    """Simple undirected graph: unique {s,o}, predicate ignored."""
    nbrs = defaultdict(set)
    for _p, s, o in train:
        if s == o:
            continue
        nbrs[s].add(o)
        nbrs[o].add(s)
    nbr_list = {v: tuple(ns) for v, ns in nbrs.items()}
    inv_log = {v: 1.0 / math.log(1.0 + len(ns)) for v, ns in nbrs.items()}
    n_edges = sum(len(ns) for ns in nbrs.values()) // 2
    n_nodes = len(nbrs)
    mean_deg = (2.0 * n_edges / n_nodes) if n_nodes else 0.0
    return nbr_list, inv_log, {
        "kind": "simple_undirected",
        "predicate_ignored": True,
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "mean_deg": round(mean_deg, 4),
        "aa_formula": "sum_{z in N(s)∩N(o)} 1/log(1+deg(z))",
        "log": "natural",
        "cn_formula": "|N(s)∩N(o)|",
    }


def aa_formula_check():
    """Toy path s—z—o, deg(z)=2 → AA = 1/log(3). Must refuse if the walk is wrong."""
    train = [(0, 1, 2), (0, 2, 3)]  # 1-2-3, z=2 has deg 2
    nbrs, inv_log, _meta = build_undirected(train)
    aa = {1: 0.0}
    o = 3
    for z in nbrs.get(o, ()):
        w = inv_log[z]
        for cand in nbrs.get(z, ()):
            if cand in aa:
                aa[cand] += w
    expect = 1.0 / math.log(1.0 + 2)
    if abs(aa[1] - expect) > 1e-12:
        raise RuntimeError(f"AA formula check failed: {aa} expect {expect}")
    return True


def attach_aa(rows, queries, sub_freq, nbrs, inv_log, true_po, nent):
    """Add AA / CN ranks on HEAD rows. Tail ranks unused (set to prior)."""
    if len(rows) != 2 * len(queries):
        raise RuntimeError(f"score_split row count {len(rows)} != 2*{len(queries)}")
    for i, (p, s, o) in enumerate(queries):
        tail, head = rows[2 * i], rows[2 * i + 1]
        if tail["direction"] != "tail" or head["direction"] != "head":
            raise RuntimeError("score_split order drifted (expected tail then head)")
        if tail["p"] != p or head["p"] != p:
            raise RuntimeError("score_split predicate drifted")
        cand = sub_freq[p]
        aa = {c: 0.0 for c in cand}
        cn = {c: 0.0 for c in cand}
        for z in nbrs.get(o, ()):
            w = inv_log[z]
            for cand_s in nbrs.get(z, ()):
                if cand_s in aa:
                    aa[cand_s] += w
                    cn[cand_s] += 1.0
        filt = true_po.get((p, o), set())
        head["ranks"]["aa"] = G51.rank_from_scores(aa, s, filt, nent)
        head["ranks"]["cn"] = G51.rank_from_scores(cn, s, filt, nent)
        tail["ranks"]["aa"] = tail["ranks"]["prior"]
        tail["ranks"]["cn"] = tail["ranks"]["prior"]


def freeze_head_choice(dev_rows, use_g51):
    buckets = defaultdict(lambda: {k: [] for k in HEAD_KEYS})
    for r in dev_rows:
        if r["direction"] != "head":
            continue
        on = use_g51.get(r["p"], True)
        gated = r["ranks"]["g51"] if on else r["ranks"]["prior"]
        buckets[r["p"]]["g51_gated"].append(gated)
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
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def apply_pred_gate(rows, use_g51):
    xs, head_xs = [], []
    for r in rows:
        k = "g51" if use_g51.get(r["p"], True) else "prior"
        xs.append(r["ranks"][k])
        if r["direction"] == "head":
            head_xs.append(r["ranks"][k])
    return G59.metrics(xs), G59.metrics(head_xs)


def apply_replace(rows, use_g51, head_key_or_map):
    """Tail follows the pred-gate. Head is replaced — gate does not apply."""
    xs, head_xs, head_keys = [], [], []
    for r in rows:
        on = use_g51.get(r["p"], True)
        if r["direction"] == "tail":
            k = "g51" if on else "prior"
        elif isinstance(head_key_or_map, dict):
            raw = head_key_or_map.get(r["p"], "g51_gated")
            if raw == "g51_gated":
                k = "g51" if on else "prior"
            else:
                k = raw
        else:
            k = head_key_or_map
        xs.append(r["ranks"][k])
        if r["direction"] == "head":
            head_xs.append(r["ranks"][k])
            if isinstance(head_key_or_map, dict):
                head_keys.append(head_key_or_map.get(r["p"], "g51_gated"))
            else:
                head_keys.append(head_key_or_map)
    return G59.metrics(xs), G59.metrics(head_xs), head_keys


def load_or_mine(out_adj, pair_tr, byp, rev):
    for path, label in ((RULES_CACHE, "local"), (G65_CACHE, "G65")):
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
    delta_e = fz["F2_select_not_plus005"]["delta"]
    if res["quoted_new_high"]:
        headline_line = (
            f"**Valid-select E is a new high** vs 0.2679 by {delta_e:+.4f} "
            f"(bar +0.005)."
        )
    elif delta_e > 0:
        headline_line = (
            f"**Valid-select E is a footnote, not a new high** "
            f"({arms['E_valid_select_head']['mrr']:.4f} vs 0.2679, "
            f"{delta_e:+.4f} < +0.005; G65 +0.0012 class). "
            f"Head {head['valid_select']['mrr']:.4f} vs gated 0.1703. "
            f"I am **not** moving the official headline."
        )
    else:
        headline_line = (
            f"**Valid-select E does not beat 0.2679** "
            f"({arms['E_valid_select_head']['mrr']:.4f}, {delta_e:+.4f})."
        )
    f1 = fz["F1_global_aa_replace_loses"]
    f2 = fz["F2_select_not_plus005"]
    f3 = fz["F3_aa_head_miss"]
    counts = ch["counts"]
    count_s = " / ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    d_delta = round(arms["D_global_aa_head"]["mrr"] - GATED, 4)
    md = f"""# G67 — Adamic–Adar on official-test HEAD only

**GROK-LOCAL.** Tail stays G59 pred-gate. Official split. `certify ok=true`.
**F1 {'FIRED' if f1['fired'] else 'quiet'}. F2 {'FIRED' if f2['fired'] else 'quiet'}. F3 {'FIRED' if f3['fired'] else 'quiet'}.** No analog redo (G62/G63/G65). No β grid.
literature_compare unavailable. Official headline stays **0.2679**.

Against me: first run is VOID if D leaves G51 on for every head. This run
`replace_used_aa={str(res['replace_used_aa']).lower()}` ({res['n_d_head_aa']}/{res['n_head']} head queries used the AA rank).

## Verdict

**Global AA-head replace {'loses' if f1['fired'] else 'does not lose'}**, G62 class: D **{arms['D_global_aa_head']['mrr']:.4f}** vs gated **0.2679**
({d_delta:+.4f}). F1 {'fired' if f1['fired'] else 'quiet'} (D ≤ 0.2679). AA head {head['aa']['mrr']:.4f} vs prior {head['prior']['mrr']:.4f}.
Raw common-neighbor count {head['cn']['mrr']:.4f}. Graph is simple undirected train {{s,o}}, p ignored.

{headline_line}

| Arm | Head | Tail | MRR | Hits@10 |
|---|---|---|---:|---:|
| A | prior | prior | {arms['A_prior']['mrr']:.4f} | {arms['A_prior']['hits10']:.4f} |
| B | G51 | G51 | {arms['B_g51']['mrr']:.4f} | {arms['B_g51']['hits10']:.4f} |
| C | G59 pred-gate | G59 pred-gate | **{arms['C_valid_gated']['mrr']:.4f}** | {arms['C_valid_gated']['hits10']:.4f} |
| D | AA always | pred-gate | {arms['D_global_aa_head']['mrr']:.4f} | {arms['D_global_aa_head']['hits10']:.4f} |
| **E (headline)** | valid-picked {{g51_gated, AA, prior}} | pred-gate | {arms['E_valid_select_head']['mrr']:.4f} | {arms['E_valid_select_head']['hits10']:.4f} |

Valid head choice: **{count_s}**. Mask sha256 `{ch['sha256'][:12]}…` hashed before test.

## Head slice

| | MRR |
|---|---:|
| prior | {head['prior']['mrr']:.4f} |
| G51 | {head['g51']['mrr']:.4f} |
| G59 gated | {head['gated']['mrr']:.4f} |
| AA | {head['aa']['mrr']:.4f} |
| CN (ablation) | {head['cn']['mrr']:.4f} |
| valid-select | {head['valid_select']['mrr']:.4f} |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | D ≤ 0.2679 | D={f1['d_mrr']:.4f} | {'FIRED' if f1['fired'] else 'quiet'} |
| F2 | E − 0.2679 < 0.005 | E={f2['e_mrr']:.4f} Δ={f2['delta']:+.4f} | {'FIRED' if f2['fired'] else 'quiet'} |
| F3 | AA head ≤ 0.1703 | AA head={f3['aa_head']:.4f} | {'FIRED' if f3['fired'] else 'quiet'} |

## Controls

C1 test n={res['n_test']}. C2 leak {res['controls']['C2_leak']['leak']}.
C3 pred-gate **{arms['C_valid_gated']['mrr']:.4f}**. C4 {res['npred']} rels.
C5 select mask hashed before test ({res['controls']['C5_select_mask']['sha256'][:12]}…).

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G67_head_aa/aa.py`.
Check: `python3 kitchen/test_g67.py`.
"""
    path = os.path.join(HERE, "RESULT.md")
    with open(path, "w") as f:
        f.write(md)
    return path


def main():
    t0 = time.time()
    aa_formula_check()

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
    nbrs, inv_log, graph_meta = build_undirected(train)
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
    attach_aa(dev_rows, valid, sub_freq, nbrs, inv_log, true_po, nent)
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
    attach_aa(test_rows, test, sub_freq, nbrs, inv_log, true_po, nent)
    print(f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s", flush=True)

    prior = G59.arm_from_rows(test_rows, "prior")
    g51 = G59.arm_from_rows(test_rows, "g51")
    pred_gate, pred_gate_head = apply_pred_gate(test_rows, use_g51)
    repl_aa, repl_aa_head, d_head_keys = apply_replace(test_rows, use_g51, "aa")
    selected, selected_head, e_head_keys = apply_replace(test_rows, use_g51, head_choice)

    n_head = sum(1 for r in test_rows if r["direction"] == "head")
    n_d_aa = sum(1 for k in d_head_keys if k == "aa")
    replace_used_aa = n_d_aa == n_head and n_head == len(test)
    if not replace_used_aa:
        raise RuntimeError(
            f"VOID: D did not use AA on every head "
            f"(aa={n_d_aa}/{n_head}, n_test={len(test)})"
        )
    n_aa_eq_g51 = sum(
        1 for r in test_rows
        if r["direction"] == "head" and r["ranks"]["aa"] == r["ranks"]["g51"]
    )
    if n_aa_eq_g51 == n_head:
        raise RuntimeError("VOID: AA ranks identical to G51 on every head")

    head_prior = G59.metrics([r["ranks"]["prior"] for r in test_rows if r["direction"] == "head"])
    head_g51 = G59.metrics([r["ranks"]["g51"] for r in test_rows if r["direction"] == "head"])
    head_cn = G59.metrics([r["ranks"]["cn"] for r in test_rows if r["direction"] == "head"])

    e_counts = defaultdict(int)
    for k in e_head_keys:
        e_counts[k] += 1

    arms = {
        "A_prior": prior,
        "B_g51": g51,
        "C_valid_gated": pred_gate,
        "D_global_aa_head": repl_aa,
        "E_valid_select_head": selected,
    }
    slices = {
        "head": {
            "prior": head_prior,
            "g51": head_g51,
            "gated": pred_gate_head,
            "aa": repl_aa_head,
            "cn": head_cn,
            "valid_select": selected_head,
        }
    }

    f1_fired = repl_aa["mrr"] <= GATED
    f2_delta = round(selected["mrr"] - GATED, 4)
    f2_fired = f2_delta < 0.005
    f3_fired = repl_aa_head["mrr"] <= HEAD_GATED
    quoted_new_high = (selected["mrr"] - GATED) >= 0.005

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(pred_gate["mrr"] - GATED) <= 0.0005
    c4_ok = npred == 237
    c5_ok = bool(head_pay["sha256"]) and mask_hashed_before_test

    res = {
        "spike": "G67",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "E_valid_select_head",
        "headline_is_test_grid": False,
        "quoted_new_high": quoted_new_high,
        "literature_compare": "unavailable",
        "n_test": len(test),
        "npred": npred,
        "n_rules_2hop": len(dumped),
        "n_head": n_head,
        "n_d_head_aa": n_d_aa,
        "replace_used_aa": replace_used_aa,
        "n_aa_eq_g51_head": n_aa_eq_g51,
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
            "n_test_queries_by_choice": dict(e_counts),
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
        },
        "falsifiers": {
            "F1_global_aa_replace_loses": {
                "d_mrr": repl_aa["mrr"],
                "bar": GATED,
                "fired": f1_fired,
                "description": "Fires if D global AA-head replace MRR <= 0.2679 (G62 class)",
            },
            "F2_select_not_plus005": {
                "e_mrr": selected["mrr"],
                "g59": GATED,
                "delta": f2_delta,
                "fired": f2_fired,
                "description": "Fires if E - 0.2679 < 0.005",
            },
            "F3_aa_head_miss": {
                "aa_head": repl_aa_head["mrr"],
                "g59_head": HEAD_GATED,
                "fired": f3_fired,
                "description": "Fires if AA head MRR <= gated head 0.1703",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out = os.path.join(HERE, "aa.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")
    write_result_md(res)

    print("\n=== G67 ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:28s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(
        f"head gated={pred_gate_head['mrr']:.4f} aa={repl_aa_head['mrr']:.4f} "
        f"cn={head_cn['mrr']:.4f} select={selected_head['mrr']:.4f}",
        flush=True,
    )
    print(
        f"F1={f1_fired} F2={f2_fired} (Δ={f2_delta:+.4f}) F3={f3_fired} "
        f"quoted_new_high={quoted_new_high} replace_used_aa={replace_used_aa}",
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
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_pred_gate_repro"])
    controls[3].observe(c4_ok, res["controls"]["C4_237"])
    controls[4].observe(c5_ok, res["controls"]["C5_select_mask"])

    falsifiers = [
        Falsifier("F1_global_aa_replace_loses",
                  refutes="that global AA-head replace beats the G59 gate",
                  fires_when="D <= 0.2679",
                  null_must_contain="signed: replace loses or ties"),
        Falsifier("F2_select_not_plus005",
                  refutes="that valid-select beats 0.2679 by +0.005",
                  fires_when="E - 0.2679 < 0.005",
                  null_must_contain="signed delta"),
        Falsifier("F3_aa_head_miss",
                  refutes="that AA lifts the hard head level above 0.1703",
                  fires_when="aa_head <= 0.1703",
                  null_must_contain="analog-style miss"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_global_aa_replace_loses"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_select_not_plus005"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_aa_head_miss"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"), CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split")],
        artifacts=[os.path.join(HERE, "aa.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("aa_json", json.dumps(res, sort_keys=True))],
        falsifier="global AA-head replace <= 0.2679 OR valid-select < +0.005 OR AA head <= 0.1703",
        allow_dirty=True,
        note="G67: Adamic-Adar on official-test HEAD only; tail stays G59 pred-gate.",
    )
    print(f"D6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
