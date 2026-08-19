#!/usr/bin/env python3
"""G68 — body-side spray filters on official FB15k-237 2-hop rules.

G57: spray is rare false cands with huge lift (write 5.40 vs true 2.72).
G61 capped lift at p95 of TRUE lifts (43627) and was inert (+0.0003):
true answers already live in the spray regime. Unread fix: filter the
PATH, not the lift size.

Pre-registered, train-only, not a test grid:
  1. Skip 2-hop through hub z (undirected unique-neighbour degree > p95
     of train nodes that appear as intermediates: in_deg>0 and out_deg>0).
  2. Last hop must occur at least twice in train (mincount=2).

Tail: s -q-> z -r-> c. Hub is z. Last hop is (z, r, c) = (subj z, rel r, obj c).
Head: cand -q-> z -r-> o, walked as G54.collect_firings via in_adj:
      o -r-> z -q-> cand. Hub is z. Last hop of the walk that produces
      the candidate is (cand, q, z).

  PYTHONUNBUFFERED=1 python3 spikes/G68_body_filter/body.py
"""
from __future__ import annotations

import hashlib
import json
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

G51_REF = 0.2585
GATED_REF = 0.2679
PRIOR_REF = 0.2334
MINCOUNT = 2  # pre-registered
G65_CACHE = os.path.join(SPIKES, "G65_head_replace", "rules_cache.json")
G59_GATE_SHA_PREFIX = "9559856568a9"


def p95(xs):
    if not xs:
        return 0.0
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(0.95 * (len(ys) - 1))))
    return float(ys[i])


def train_degree_tables(train):
    """Undirected unique-neighbour degree. Intermediates: in>0 and out>0."""
    nbr = defaultdict(set)
    n_out = defaultdict(int)
    n_in = defaultdict(int)
    hop_count = Counter()
    for p, s, o in train:
        nbr[s].add(o)
        nbr[o].add(s)
        n_out[s] += 1
        n_in[o] += 1
        hop_count[(s, p, o)] += 1
    deg = {e: len(xs) for e, xs in nbr.items()}
    intermediates = [e for e in deg if n_out[e] > 0 and n_in[e] > 0]
    inter_degs = [deg[e] for e in intermediates]
    all_degs = list(deg.values())
    cut_inter = p95(inter_degs)
    cut_all = p95(all_degs)
    # Stated choice: p95 of intermediate-node degrees (train-only).
    hub_cut = cut_inter
    hubs = {e for e in intermediates if deg[e] > hub_cut}
    return {
        "deg": deg,
        "hop_count": hop_count,
        "n_nodes": len(deg),
        "n_intermediates": len(intermediates),
        "hub_cut": hub_cut,
        "hub_cut_all_nodes": cut_all,
        "hub_population": "train nodes with in_deg>0 and out_deg>0 (appear as 2-hop intermediates)",
        "degree_def": "undirected unique-neighbour count (train only)",
        "n_hubs": len(hubs),
        "max_deg": max(all_degs) if all_degs else 0,
        "max_triple_multiplicity": max(hop_count.values()) if hop_count else 0,
        "n_triples_count_ge2": int(sum(1 for c in hop_count.values() if c >= MINCOUNT)),
        "hubs": hubs,
    }


def iter_paths(p, s, o, want_tail, rules_by_head, out_adj, in_adj):
    """Yield (cand, conf, z, last_hop_triple).

    Tail last hop: (z, r, cand). Head last hop: (cand, q, z).
    """
    if want_tail:
        for (q, r), conf in rules_by_head.get(p, []):
            for z in out_adj[q].get(s, []):
                for cand in out_adj[r].get(z, []):
                    if cand != s:
                        yield cand, conf, z, (z, r, cand)
    else:
        for (q, r), conf in rules_by_head.get(p, []):
            for z in in_adj[r].get(o, []):
                for cand in in_adj[q].get(z, []):
                    if cand != o:
                        yield cand, conf, z, (cand, q, z)


def firings_from_paths(paths, hubs, hop_count, use_hub, use_mincount, mincount):
    firings = defaultdict(list)
    n = 0
    for cand, conf, z, last in paths:
        if use_hub and z in hubs:
            continue
        if use_mincount and hop_count.get(last, 0) < mincount:
            continue
        firings[cand].append(min(0.9999, conf))
        n += 1
    return firings, n


def collect_firings_filtered(
    p, s, o, want_tail, rules_by_head, out_adj, in_adj,
    hub_cut=None, mincount=None, hubs=None, hop_count=None,
):
    """G54.collect_firings with body-side adjacency wraps.

    Drop z with deg > hub_cut (hubs set). Drop last hop if train count < mincount.
    """
    paths = iter_paths(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
    use_hub = hubs is not None and hub_cut is not None
    use_mc = mincount is not None and mincount > 1
    firings, _n = firings_from_paths(
        paths, hubs or set(), hop_count or {}, use_hub, use_mc, mincount or 1
    )
    return firings


def load_or_mine(out_adj, pair_tr, byp, rev):
    if os.path.isfile(G65_CACHE):
        raw = json.loads(open(G65_CACHE).read())
        if len(raw) == 2201:
            h = hashlib.sha256(open(G65_CACHE, "rb").read()).hexdigest()
            print(f"loaded {len(raw)} official-train rules from G65 cache sha={h[:16]}", flush=True)
            return raw, "G65_head_replace/rules_cache.json", h
    print("mining 2-hop on official train ...", flush=True)
    t0 = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    dumped = [{"head": r["head"], "body": list(r["body"]), "conf": r["conf"]} for r in rules]
    print(f"mined {len(rules)} in {time.time() - t0:.1f}s", flush=True)
    return dumped, "G51.mine_2hop_rules", None


def score_split(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx,
                hubs, hop_count, mincount, identity_n=200):
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = idx
    rows = []
    dropped = {
        "n_paths_unfiltered": 0,
        "n_paths_hub": 0,
        "n_paths_mincount": 0,
        "n_paths_both": 0,
        "n_queries": 0,
        "n_queries_unfiltered_fired": 0,
        "n_queries_hub_fired": 0,
        "n_queries_mincount_fired": 0,
        "n_queries_both_fired": 0,
        "identity_checked": 0,
        "identity_matched": 0,
    }
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            paths = list(iter_paths(p, s, o, want_tail, rules_by_head, out_adj, in_adj))
            f_unf, n_unf = firings_from_paths(paths, hubs, hop_count, False, False, mincount)
            f_hub, n_hub = firings_from_paths(paths, hubs, hop_count, True, False, mincount)
            f_mc, n_mc = firings_from_paths(paths, hubs, hop_count, False, True, mincount)
            f_both, n_both = firings_from_paths(paths, hubs, hop_count, True, True, mincount)
            if dropped["identity_checked"] < identity_n:
                ref = G54.collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
                same = (set(ref) == set(f_unf)
                        and all(ref[c] == f_unf[c] for c in ref))
                dropped["identity_checked"] += 1
                dropped["identity_matched"] += int(same)
            g51 = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, f_unf)
            g_hub = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, f_hub)
            g_mc = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, f_mc)
            g_both = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, f_both)
            ranks = {
                "prior": G51.rank_from_scores(prior_counts, target, filt, nent),
                "g51": G51.rank_from_scores(g51, target, filt, nent),
                "hub": G51.rank_from_scores(g_hub, target, filt, nent),
                "mincount": G51.rank_from_scores(g_mc, target, filt, nent),
                "both": G51.rank_from_scores(g_both, target, filt, nent),
            }
            dropped["n_paths_unfiltered"] += n_unf
            dropped["n_paths_hub"] += n_hub
            dropped["n_paths_mincount"] += n_mc
            dropped["n_paths_both"] += n_both
            dropped["n_queries"] += 1
            dropped["n_queries_unfiltered_fired"] += int(bool(f_unf))
            dropped["n_queries_hub_fired"] += int(bool(f_hub))
            dropped["n_queries_mincount_fired"] += int(bool(f_mc))
            dropped["n_queries_both_fired"] += int(bool(f_both))
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": ranks,
            })
    dropped["n_paths_dropped_hub"] = dropped["n_paths_unfiltered"] - dropped["n_paths_hub"]
    dropped["n_paths_dropped_mincount"] = dropped["n_paths_unfiltered"] - dropped["n_paths_mincount"]
    dropped["n_paths_dropped_both"] = dropped["n_paths_unfiltered"] - dropped["n_paths_both"]
    return rows, dropped


def apply_g59_gate(rows, use_g51, key):
    return G59.metrics([
        r["ranks"][key] if use_g51.get(r["p"], True) else r["ranks"]["prior"]
        for r in rows
    ])


def slice_dir(rows, key):
    out = {}
    for d in ("tail", "head"):
        out[d] = G59.metrics([r["ranks"][key] for r in rows if r["direction"] == d])
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

    deg_tab = train_degree_tables(train)
    hubs = deg_tab["hubs"]
    hop_count = deg_tab["hop_count"]
    print(
        f"hub_cut={deg_tab['hub_cut']:.0f} (p95 of {deg_tab['n_intermediates']} intermediates; "
        f"all-nodes p95={deg_tab['hub_cut_all_nodes']:.0f}) n_hubs={deg_tab['n_hubs']} "
        f"max_mult={deg_tab['max_triple_multiplicity']} n_ge2={deg_tab['n_triples_count_ge2']}",
        flush=True,
    )

    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(train + valid + test)
    dumped, rules_src, rules_sha = load_or_mine(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in dumped:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)

    print("VALID ...", flush=True)
    t_v = time.time()
    valid_rows, valid_drop = score_split(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx,
        hubs, hop_count, MINCOUNT,
    )
    gate, use_g51 = G59.freeze_gate(valid_rows)
    print(
        f"VALID {len(valid_rows)} in {time.time() - t_v:.1f}s "
        f"gate {gate['sha256'][:12]} on={gate['n_g51_on']} off={gate['n_g51_off']} "
        f"id {valid_drop['identity_matched']}/{valid_drop['identity_checked']}",
        flush=True,
    )

    print("TEST ...", flush=True)
    t_t = time.time()
    test_rows, test_drop = score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx,
        hubs, hop_count, MINCOUNT,
    )
    print(
        f"TEST {len(test_rows)} in {time.time() - t_t:.1f}s "
        f"paths unf={test_drop['n_paths_unfiltered']} "
        f"hub_drop={test_drop['n_paths_dropped_hub']} "
        f"mc_drop={test_drop['n_paths_dropped_mincount']} "
        f"both_drop={test_drop['n_paths_dropped_both']}",
        flush=True,
    )

    # Pick better of D/E/F on VALID G51-filter MRR (not test). Apply G59 mask.
    valid_filter_mrr = {
        "D_g51_hub": G59.arm_from_rows(valid_rows, "hub")["mrr"],
        "E_g51_mincount": G59.arm_from_rows(valid_rows, "mincount")["mrr"],
        "F_g51_both": G59.arm_from_rows(valid_rows, "both")["mrr"],
    }
    best_arm = max(valid_filter_mrr, key=valid_filter_mrr.get)
    best_key = {"D_g51_hub": "hub", "E_g51_mincount": "mincount", "F_g51_both": "both"}[best_arm]

    arms = {
        "A_prior": G59.arm_from_rows(test_rows, "prior"),
        "B_g51": G59.arm_from_rows(test_rows, "g51"),
        "C_valid_gated": apply_g59_gate(test_rows, use_g51, "g51"),
        "D_g51_hub": G59.arm_from_rows(test_rows, "hub"),
        "E_g51_mincount": G59.arm_from_rows(test_rows, "mincount"),
        "F_g51_both": G59.arm_from_rows(test_rows, "both"),
        "G_gated_best_filter": apply_g59_gate(test_rows, use_g51, best_key),
    }

    d_hub = round(arms["D_g51_hub"]["mrr"] - arms["B_g51"]["mrr"], 4)
    d_mc = round(arms["E_g51_mincount"]["mrr"] - arms["B_g51"]["mrr"], 4)
    d_g = round(arms["G_gated_best_filter"]["mrr"] - arms["C_valid_gated"]["mrr"], 4)
    f1_fired = arms["D_g51_hub"]["mrr"] <= G51_REF
    f2_fired = arms["E_g51_mincount"]["mrr"] <= G51_REF
    f3_fired = arms["G_gated_best_filter"]["mrr"] <= GATED_REF

    c1_ok = len(test) == 20466
    c2_ok = leak == 0
    c3_ok = abs(arms["B_g51"]["mrr"] - G51_REF) <= 0.0005
    c4_ok = abs(arms["C_valid_gated"]["mrr"] - GATED_REF) <= 0.0005
    c5_ok = npred == 237
    id_ok = (
        test_drop["identity_checked"] > 0
        and test_drop["identity_matched"] == test_drop["identity_checked"]
        and valid_drop["identity_matched"] == valid_drop["identity_checked"]
    )

    last_hop_map = {
        "tail": "s -q-> z -r-> c ; last hop (z, r, c) as (subject z, rel r, object c)",
        "head": (
            "cand -q-> z -r-> o walked via in_adj as G54.collect_firings "
            "(o -r-> z -q-> cand); last hop of the walk that produces cand is "
            "(cand, q, z) as (subject cand, rel q, object z). Hub remains z."
        ),
        "mincount_counts": "train multiplicity of that last-hop triple",
    }

    res = {
        "spike": "G68",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "G_gated_best_filter",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "npred": npred,
        "nent": nent,
        "n_rules_2hop": len(dumped),
        "rules_source": rules_src,
        "rules_cache_sha256": rules_sha,
        "hub": {
            "cut": deg_tab["hub_cut"],
            "cut_all_nodes_p95": deg_tab["hub_cut_all_nodes"],
            "population": deg_tab["hub_population"],
            "degree_def": deg_tab["degree_def"],
            "n_nodes": deg_tab["n_nodes"],
            "n_intermediates": deg_tab["n_intermediates"],
            "n_hubs": deg_tab["n_hubs"],
            "max_deg": deg_tab["max_deg"],
        },
        "mincount": {
            "value": MINCOUNT,
            "max_triple_multiplicity": deg_tab["max_triple_multiplicity"],
            "n_train_triples_count_ge2": deg_tab["n_triples_count_ge2"],
            "note": (
                "FB15k-237 train triples are unique, so last-hop count is 0 or 1. "
                "mincount=2 is a complete last-hop veto on this graph."
            ),
        },
        "last_hop_mapping": last_hop_map,
        "gate": {
            "sha256": gate["sha256"],
            "n_g51_on": gate["n_g51_on"],
            "n_g51_off": gate["n_g51_off"],
            "applied_to_G": (
                "G59 freeze_gate on unfiltered valid prior vs g51; "
                f"mask applied to valid-best of D/E/F = {best_arm} (key={best_key}). "
                "Not a newly fitted filter-specific gate."
            ),
        },
        "valid_filter_mrr": valid_filter_mrr,
        "best_filter_on_valid": best_arm,
        "firings_test": test_drop,
        "firings_valid": valid_drop,
        "arms": arms,
        "slices": {
            "prior": slice_dir(test_rows, "prior"),
            "g51": slice_dir(test_rows, "g51"),
            "hub": slice_dir(test_rows, "hub"),
            "mincount": slice_dir(test_rows, "mincount"),
            "both": slice_dir(test_rows, "both"),
        },
        "deltas": {
            "hub_minus_g51": d_hub,
            "mincount_minus_g51": d_mc,
            "gated_best_minus_gated": d_g,
        },
        "controls": {
            "C1_test_n": {"ok": c1_ok, "n": len(test)},
            "C2_leak": {"ok": c2_ok, "leak": leak},
            "C3_g51": {"ok": c3_ok, "mrr": arms["B_g51"]["mrr"], "expected": G51_REF},
            "C4_gated": {"ok": c4_ok, "mrr": arms["C_valid_gated"]["mrr"], "expected": GATED_REF},
            "C5_npred": {"ok": c5_ok, "npred": npred},
            "C6_firings_identity": {
                "ok": id_ok,
                "valid": f"{valid_drop['identity_matched']}/{valid_drop['identity_checked']}",
                "test": f"{test_drop['identity_matched']}/{test_drop['identity_checked']}",
            },
        },
        "falsifiers": {
            "F1_hub_filter_does_not_beat_g51": {
                "hub_mrr": arms["D_g51_hub"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": d_hub,
                "fired": f1_fired,
                "description": "Fires if hub-filter G51 <= unfiltered G51 0.2585. Signed.",
            },
            "F2_mincount_does_not_beat_g51": {
                "mincount_mrr": arms["E_g51_mincount"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": d_mc,
                "fired": f2_fired,
                "description": "Fires if mincount-2 G51 <= 0.2585. Signed.",
            },
            "F3_gated_filter_does_not_beat_gated": {
                "gated_filter_mrr": arms["G_gated_best_filter"]["mrr"],
                "gated_mrr": arms["C_valid_gated"]["mrr"],
                "best_filter": best_arm,
                "delta": d_g,
                "fired": f3_fired,
                "description": "Fires if gated+filter <= 0.2679. Signed.",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out = os.path.join(HERE, "body.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G68 arms ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:22s} MRR={v['mrr']:.4f} H@10={v['hits10']:.4f}", flush=True)
    print(
        f"F1 fired={f1_fired} Δ={d_hub:+.4f} "
        f"F2 fired={f2_fired} Δ={d_mc:+.4f} "
        f"F3 fired={f3_fired} Δ={d_g:+.4f} best={best_arm}",
        flush=True,
    )
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test 20466", can_fail_because="wrong file",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="leak 0", can_fail_because="loader mix",
                null_must_contain="leak>0"),
        Control("C3_g51", why="official G51 0.2585", can_fail_because="scorer drifted",
                null_must_contain="G51 != 0.2585"),
        Control("C4_gated", why="valid-gated 0.2679", can_fail_because="gate drifted",
                null_must_contain="gated != 0.2679"),
        Control("C5_npred", why="237 relations", can_fail_because="vocab broken",
                null_must_contain="npred!=237"),
        Control("C6_firings_identity", why="unfiltered collect_firings matches G54",
                can_fail_because="wrapper is a different instrument",
                null_must_contain="identity mismatch"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_g51"])
    controls[3].observe(c4_ok, res["controls"]["C4_gated"])
    controls[4].observe(c5_ok, res["controls"]["C5_npred"])
    controls[5].observe(id_ok, res["controls"]["C6_firings_identity"])

    falsifiers = [
        Falsifier(
            "F1_hub_filter_does_not_beat_g51",
            refutes="that skipping hub intermediates raises official G51",
            fires_when="hub-filter G51 <= 0.2585",
            null_must_contain="signed hub-G51 delta",
        ),
        Falsifier(
            "F2_mincount_does_not_beat_g51",
            refutes="that last-hop mincount=2 raises official G51",
            fires_when="mincount-2 G51 <= 0.2585",
            null_must_contain="signed mincount-G51 delta",
        ),
        Falsifier(
            "F3_gated_filter_does_not_beat_gated",
            refutes="that a body filter under the G59 gate raises 0.2679",
            fires_when="gated+filter <= 0.2679",
            null_must_contain="signed gated_filter-gated delta",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_hub_filter_does_not_beat_g51"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_mincount_does_not_beat_g51"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_gated_filter_does_not_beat_gated"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G54_slice_gated_lift"),
              G59.CORPUS],
        artifacts=[os.path.join(HERE, "body.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("body_json", json.dumps(res, sort_keys=True))],
        falsifier="hub-filter G51 <= 0.2585 OR mincount-2 G51 <= 0.2585 OR gated+filter <= 0.2679",
        allow_dirty=True,
        note="G68: body-side spray filters (hub p95, last-hop mincount=2) on official FB15k-237. Literature unavailable.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
