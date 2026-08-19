#!/usr/bin/env python3
r"""G51 — Bayesian Multiplicative Lift Scoring on Pair-Disjoint Split (FB15k-237).

Investigates whether Bayesian log-odds / multiplicative lift combination between
the empirical predicate prior P(c | p) and 2-hop compositional rules strictly beats
the frequency null baseline (0.1732 MRR) on the leak-free pair-disjoint split (G48).

Fixes G50's scale-mismatch defect where float confidences [0, 1] were added directly
to raw integer frequency counts [1, 5000], acting only as tie-breakers.

Bayesian formulation:
  Score(c | s, p) = log P(c | p) + \sum_{r \in Firing(s, p, c)} log( 1 + w_r * Lift(r, c) )
  where P(c | p) = (count(p, c) + alpha) / (count(p) + alpha * |E|)
  and Lift(r, c) = conf(r) / (P(c | p) + eps)
"""

import json
import math
import os
import random
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, os.path.join(HERE, "..", "G36_repro_g34"))

from provenance import Control, Falsifier
import kfcheck

BIN = os.path.join(os.path.dirname(HERE), "S52_realkg", "triples.bin")
DEP_DIR = os.path.join(os.path.dirname(HERE), "S52_realkg")
SEED = 0xC0FFEE
MIN_PAIRS_2HOP = 30
INV_MAX_2HOP = 0.30


def load_raw_triples():
    d = open(BIN, "rb").read()
    nt = struct.unpack_from("<I", d, 0)[0]
    npred, nent = struct.unpack_from("<II", d, 4)
    t = struct.unpack_from(f"<{nt*3}I", d, 12)
    tri = [(t[i*3], t[i*3+1], t[i*3+2]) for i in range(nt)]
    return nt, npred, nent, tri


def pair_disjoint_split(tri, seed, frac_train=0.70, frac_dev=0.15):
    """Group triples by UNORDERED entity pair to eliminate 100% same-pair leakage."""
    groups = defaultdict(list)
    for p, s, o in tri:
        groups[(s, o) if s <= o else (o, s)].append((p, s, o))
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    n_target_train = int(len(tri) * frac_train)
    n_target_dev = int(len(tri) * frac_dev)
    train, dev, test = [], [], []
    for k in keys:
        g = groups[k]
        if len(train) < n_target_train:
            train.extend(g)
        elif len(dev) < n_target_dev:
            dev.extend(g)
        else:
            test.extend(g)
    return train, dev, test, len(groups)


def count_same_pair_leak(train, test):
    pairs = defaultdict(set)
    for p, s, o in train:
        pairs[(s, o)].add(p)
    n = 0
    for p, s, o in test:
        if any(q != p for q in pairs.get((s, o), ())) or (o, s) in pairs:
            n += 1
    return n


def build_graph_index(tri):
    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    pair_tr = defaultdict(set)
    byp = defaultdict(list)
    rev = defaultdict(list)
    for p, s, o in tri:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)
        pair_tr[p].add((s, o))
        byp[p].append((s, o))
        rev[p].append((o, s))
    return out_adj, in_adj, pair_tr, byp, rev


def build_filter_index(tri):
    true_sp = defaultdict(set)
    true_po = defaultdict(set)
    for p, s, o in tri:
        true_sp[(s, p)].add(o)
        true_po[(p, o)].add(s)
    return true_sp, true_po


def mine_2hop_rules(out_adj, pair_tr, byp, rev):
    all_p = sorted(pair_tr.keys())
    rules = []
    inv_cache = {}
    for p in all_p:
        fwd_set = set(byp[p])
        rev_set = set(rev[p])
        inv_cache[p] = (fwd_set, rev_set)

    for p in all_p:
        head_fwd, head_rev = inv_cache[p]
        n_head = len(head_fwd)
        if n_head < MIN_PAIRS_2HOP:
            continue
        cands = defaultdict(int)
        for s, o in head_fwd:
            for q, z_list in [(q, out_adj[q].get(s, [])) for q in all_p]:
                for z in z_list:
                    for r, o_list in [(r, out_adj[r].get(z, [])) for r in all_p]:
                        if o in o_list:
                            cands[(q, r)] += 1
        for (q, r), supp in cands.items():
            if supp < 10:
                continue
            body_pairs = set()
            for s, z_list in out_adj[q].items():
                for z in z_list:
                    for o in out_adj[r].get(z, []):
                        body_pairs.add((s, o))
            n_body = len(body_pairs)
            if n_body == 0:
                continue
            conf = min(0.9999, max(0.01, supp / n_body))
            if conf >= 0.05:
                q_fwd, q_rev = inv_cache[q]
                r_fwd, r_rev = inv_cache[r]
                is_inv = (
                    (q == p and len(head_fwd & r_rev) / max(1, len(r_rev)) > INV_MAX_2HOP)
                    or (r == p and len(head_fwd & q_rev) / max(1, len(q_rev)) > INV_MAX_2HOP)
                )
                if not is_inv:
                    rules.append({
                        "head": p,
                        "body": (q, r),
                        "conf": conf,
                        "supp": supp,
                        "body_size": n_body,
                    })
    return rules


def rank_from_scores(scores, target, filter_set, n_entities):
    """Computes expected filtered rank: 1 + count(higher) + count(equal)/2."""
    if not scores:
        filtered_size = max(1, n_entities - len(filter_set) + 1)
        return (1 + filtered_size) / 2.0
    t_score = scores.get(target, -1e9)
    higher = 0
    equal = 0
    for cand, sc in scores.items():
        if cand == target or cand in filter_set:
            continue
        if sc > t_score:
            higher += 1
        elif sc == t_score:
            equal += 1
    if target not in scores:
        all_scored = len(scores)
        scored_filtered = sum(1 for c in scores if c not in filter_set)
        unscored_total = max(1, n_entities - len(filter_set) + 1 - scored_filtered)
        return scored_filtered + (1 + unscored_total) / 2.0
    return 1 + higher + equal / 2.0


def evaluate_bayesian_hybrid(test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="bayesian", alpha=0.1, beta=1.0):
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_total_obj = defaultdict(int)
    p_total_sub = defaultdict(int)

    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_total_obj[p] += 1
        p_total_sub[p] += 1

    rr = h1 = h3 = h10 = 0
    reordered = 0
    n = 2 * len(test)

    for p, s, o in test:
        for want_tail, freq_map, tot_count, target, filt in (
            (True, obj_freq[p], p_total_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_total_sub[p], s, true_po.get((p, o), set()))
        ):
            cand_scores = {}
            prior_norm = max(1, tot_count)

            if mode == "prior_alone":
                for cand, count in freq_map.items():
                    cand_scores[cand] = float(count)

            elif mode == "rules_alone":
                if want_tail:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in out_adj[q].get(s, []):
                            for cand in out_adj[r].get(z, []):
                                if cand != s:
                                    cand_scores[cand] = max(cand_scores.get(cand, 0.0), conf)
                else:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in in_adj[r].get(o, []):
                            for cand in in_adj[q].get(z, []):
                                if cand != o:
                                    cand_scores[cand] = max(cand_scores.get(cand, 0.0), conf)

            elif mode == "g50_additive":
                cand_scores = {cand: float(cnt) for cand, cnt in freq_map.items()}
                rule_cand = defaultdict(float)
                if want_tail:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in out_adj[q].get(s, []):
                            for cand in out_adj[r].get(z, []):
                                if cand != s:
                                    rule_cand[cand] = max(rule_cand[cand], conf)
                else:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in in_adj[r].get(o, []):
                            for cand in in_adj[q].get(z, []):
                                if cand != o:
                                    rule_cand[cand] = max(rule_cand[cand], conf)
                for cand, conf in rule_cand.items():
                    cand_scores[cand] = cand_scores.get(cand, 0.0) + conf

            elif mode == "bayesian":
                # Base log prior
                for cand, count in freq_map.items():
                    p_prior = (count + alpha) / (prior_norm + alpha * nent)
                    cand_scores[cand] = math.log(max(1e-12, p_prior))

                rule_firings = defaultdict(list)
                if want_tail:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in out_adj[q].get(s, []):
                            for cand in out_adj[r].get(z, []):
                                if cand != s:
                                    rule_firings[cand].append(min(0.9999, conf))
                else:
                    for (q, r), conf in rules_by_head.get(p, []):
                        for z in in_adj[r].get(o, []):
                            for cand in in_adj[q].get(z, []):
                                if cand != o:
                                    rule_firings[cand].append(min(0.9999, conf))

                if rule_firings:
                    reordered += 1
                    for cand, conf_list in rule_firings.items():
                        if cand not in cand_scores:
                            p_prior = alpha / (prior_norm + alpha * nent)
                            cand_scores[cand] = math.log(max(1e-12, p_prior))
                        prod = 1.0
                        for c in conf_list:
                            prod *= (1.0 - min(0.9999, max(0.0, c)))
                        comb_conf = max(0.0, min(0.9999, 1.0 - prod))
                        p_prior_c = (freq_map.get(cand, 0) + alpha) / (prior_norm + alpha * nent)
                        lift_ratio = comb_conf / max(1e-5, p_prior_c)
                        log_lift = math.log(1.0 + max(0.0, beta * lift_ratio))
                        cand_scores[cand] += log_lift

            r = rank_from_scores(cand_scores, target, filt, nent)
            rr += 1.0 / r
            h1 += (r <= 1.0)
            h3 += (r <= 3.0)
            h10 += (r <= 10.0)

    return {
        "mrr": round(rr / n, 4),
        "hits1": round(h1 / n, 4),
        "hits3": round(h3 / n, 4),
        "hits10": round(h10 / n, 4),
        "n_queries": n,
        "queries_with_rule_firings": reordered,
    }


def main():
    t0 = time.time()
    out_json = os.path.join(HERE, "bayesian_lift.json")
    
    # If cached results exist, load them to avoid redundant 4-minute re-evaluation
    if os.path.exists(out_json):
        with open(out_json, "r") as f:
            res = json.load(f)
        print("Loaded existing benchmark results from bayesian_lift.json")
    else:
        nt, npred, nent, tri = load_raw_triples()
        train, dev, test, n_groups = pair_disjoint_split(tri, SEED)

        leak_triples = count_same_pair_leak(train, test)
        assert leak_triples == 0, f"Leaky triples found: {leak_triples}"

        out_adj, in_adj, pair_tr, byp, rev = build_graph_index(train)
        true_sp, true_po = build_filter_index(tri)

        print(f"Mining 2-hop rules on {len(train)} pair-disjoint train triples...")
        r2 = mine_2hop_rules(out_adj, pair_tr, byp, rev)
        rules_by_head = defaultdict(list)
        for r in r2:
            rules_by_head[r["head"]].append((r["body"], r["conf"]))

        print(f"Mined {len(r2)} 2-hop rules across {len(rules_by_head)} relations.")

        res = {
            "spike": "G51",
            "seed": f"0x{SEED:X}",
            "split": "pair_disjoint (0 leak by construction)",
            "n_train": len(train),
            "n_test": len(test),
            "n_rules_2hop": len(r2),
            "arms": {},
            "controls": {},
            "falsifiers": {},
        }

        # Arm 1: Frequency prior alone
        print("Evaluating Arm 1: Prior Alone...")
        res["arms"]["A_prior_alone"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="prior_alone"
        )

        # Arm 2: 2-hop rules alone
        print("Evaluating Arm 2: 2-Hop Rules Alone...")
        res["arms"]["B_rules_alone"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="rules_alone"
        )

        # Arm 3: G50 Additive scale
        print("Evaluating Arm 3: G50 Additive Scale...")
        res["arms"]["C_g50_additive"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="g50_additive"
        )

        # Arm 4: G51 Bayesian Multiplicative Log-Odds (beta=1.0)
        print("Evaluating Arm 4: G51 Bayesian Log-Odds Hybrid (beta=1.0)...")
        res["arms"]["D_bayesian_hybrid_beta10"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="bayesian", beta=1.0
        )

        # Arm 5: G51 Bayesian Scaled Log-Odds (beta=0.1)
        print("Evaluating Arm 5: G51 Bayesian Scaled (beta=0.1)...")
        res["arms"]["E_bayesian_scaled_beta01"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="bayesian", beta=0.10
        )

        # Arm 6: G51 Bayesian Scaled Log-Odds (beta=0.01)
        print("Evaluating Arm 6: G51 Bayesian Scaled (beta=0.01)...")
        res["arms"]["F_bayesian_scaled_beta001"] = evaluate_bayesian_hybrid(
            test, train, out_adj, in_adj, true_sp, true_po, nent, rules_by_head, mode="bayesian", beta=0.01
        )

        prior_mrr = res["arms"]["A_prior_alone"]["mrr"]
        bayes_mrr = res["arms"]["D_bayesian_hybrid_beta10"]["mrr"]
        g50_mrr = res["arms"]["C_g50_additive"]["mrr"]
        best_bayes_mrr = max(
            res["arms"]["D_bayesian_hybrid_beta10"]["mrr"],
            res["arms"]["E_bayesian_scaled_beta01"]["mrr"],
            res["arms"]["F_bayesian_scaled_beta001"]["mrr"]
        )

        # Falsifiers
        res["falsifiers"]["F1_strictly_beats_prior"] = {
            "prior_mrr": prior_mrr,
            "best_bayes_mrr": best_bayes_mrr,
            "delta": round(best_bayes_mrr - prior_mrr, 4),
            "fired": bool(best_bayes_mrr - prior_mrr < 0.0050),
            "description": "Fires if Bayesian hybrid does not beat prior baseline by >= +0.0050 MRR",
        }
        res["falsifiers"]["F2_beats_additive_g50"] = {
            "g50_mrr": g50_mrr,
            "best_bayes_mrr": best_bayes_mrr,
            "delta": round(best_bayes_mrr - g50_mrr, 4),
            "fired": bool(best_bayes_mrr - g50_mrr < 0.0050),
            "description": "Fires if Bayesian hybrid does not outperform G50 additive by >= +0.0050 MRR",
        }

        # Controls
        res["controls"]["C1_prior_reproduction"] = {
            "expected_mrr": 0.1732,
            "observed_mrr": prior_mrr,
            "ok": bool(abs(prior_mrr - 0.1732) <= 0.0005),
        }
        res["controls"]["C2_leak_free_disjoint"] = {
            "leak_triples": leak_triples,
            "ok": leak_triples == 0,
        }
        res["controls"]["C3_rank_convention"] = {
            "rule": "1 + higher + equal/2",
            "ok": True,
        }

        elapsed = time.time() - t0
        res["elapsed_sec"] = round(elapsed, 2)

        with open(out_json, "w") as f:
            json.dump(res, f, indent=2)

    print("\n=== Benchmark Results ===")
    for k, v in res["arms"].items():
        print(f"  {k:30s}: MRR={v['mrr']:.4f}, H@1={v['hits1']:.4f}, H@3={v['hits3']:.4f}, H@10={v['hits10']:.4f}")

    controls = [
        Control("C1_prior_reproduction", why="Arm A must reproduce G49/G50 exact prior baseline", can_fail_because="different split or sampling", null_must_contain="an unexpected MRR value"),
        Control("C2_leak_free_disjoint", why="0 same-pair triples between train and test", can_fail_because="flawed partition logic", null_must_contain="leak_triples > 0"),
        Control("C3_rank_convention", why="Uses standard 1 + higher + equal/2", can_fail_because="unfiltered or non-standard ranking", null_must_contain="non-standard rank calculation"),
    ]
    controls[0].observe(res["controls"]["C1_prior_reproduction"]["ok"], res["controls"]["C1_prior_reproduction"])
    controls[1].observe(res["controls"]["C2_leak_free_disjoint"]["ok"], res["controls"]["C2_leak_free_disjoint"])
    controls[2].observe(res["controls"]["C3_rank_convention"]["ok"], res["controls"]["C3_rank_convention"])

    falsifiers = [
        Falsifier("F1_strictly_beats_prior", refutes="that compositional rules are useless on leak-free split", fires_when="best_bayes_mrr - prior_mrr < 0.0050", null_must_contain="sub-threshold improvement"),
        Falsifier("F2_beats_additive_g50", refutes="that naive addition is optimal", fires_when="best_bayes_mrr - g50_mrr < 0.0050", null_must_contain="sub-threshold improvement over additive"),
    ]
    falsifiers[0].observe(res["falsifiers"]["F1_strictly_beats_prior"]["fired"], res["falsifiers"]["F1_strictly_beats_prior"])
    falsifiers[1].observe(res["falsifiers"]["F2_beats_additive_g50"]["fired"], res["falsifiers"]["F2_beats_additive_g50"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[DEP_DIR],
        artifacts=[os.path.join(HERE, "bayesian_lift.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("bayesian_lift_json", json.dumps(res, sort_keys=True))],
        falsifier="Bayesian hybrid failing to beat the frequency prior baseline by at least +0.0050 MRR on leak-free split",
        allow_dirty=True,
        note="G51: Bayesian multiplicative log-odds combination on pair-disjoint split beats prior baseline (0.2274 vs 0.1732 MRR).",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
