r"""G37 — filtered-MRR evaluation for rule bodies of ANY length.

THE BLOCKER THIS REMOVES
------------------------
This lane evolved rule populations across G22/G24/G25/G27 and scored them with
`top12` mean held-out confidence — a heuristic G30 then retired (and whose
retirement G33 corrected the evidence for). The obvious repair is to score the
evolved populations on G30's filtered-MRR yardstick instead. **It cannot be
done with the instrument as built.**

  evo.py    GENOTYPE is "(body predicate tuple, head predicate)", and `OPS`
            includes `extend` and `contract` -- bodies are VARIABLE LENGTH.
  yardstick.py:143   rules_by_head[r["head"]].append((r["body"], r["conf"]))
  yardstick.py:156   for (p1, p2), conf in rules_by_head.get(p, ()):

A body is destructured as exactly two predicates and walked by two hard-coded
nested loops. Every number G30 published is therefore about 2-hop rules **by
construction** — which is also the honest reading of G30's "gap to AnyBURL",
since AnyBURL mines length 1, 2 and 3.

Neither spike is wrong. They cannot be connected, and this is the connector.

SCOPE, deliberately narrow (§2: PARTIAL is not a verdict, so split the row).
This spike delivers THE EVALUATOR and its controls. It does NOT evaluate an
evolved population: G24/G27 persist summary stats (`arms`, `verdict`, `rows`),
not populations, so that needs the evolution re-run and is a separate row.

FALSIFIER, STATED IN CHANNEL.md BEFORE THE RUN
----------------------------------------------
F1  If the generalised walk does not reproduce G30's `G17_all` numbers EXACTLY
    on the same 2-hop rules, it is a DIFFERENT INSTRUMENT, no result may be
    compared across it, and it is withdrawn rather than published.
    (MRR 0.0631, Hits@1 0.0311, Hits@3 0.0662, Hits@10 0.1229.)
F2  If the general walk finds nothing that the 2-hop walk misses, the
    generalisation is decorative and is reported as such.

The guards are preserved from the original, not reinvented: every node on a
path must be distinct. `yardstick.py` spells this `b_node != s`,
`c_node != s and c_node != b_node`; `evo.py:160` states the same rule as "no
step returns". A generalisation that quietly drops a guard would inflate every
number it produces, which is why F1 is exact-match and not approximate.
"""
import json
import os
import random
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G30_external_yardstick"))

import provenance as P  # noqa: E402
import kfcheck  # noqa: E402
import yardstick as Y  # noqa: E402   the instrument under generalisation

G30 = os.path.join(SPIKES, "G30_external_yardstick")

# G30's published G17_all row. F1 compares against these to the last digit.
G30_PUBLISHED = {"mrr": 0.0631, "hits1": 0.0311, "hits3": 0.0662, "hits10": 0.1229}


def walk_forward(start, body, out_adj):
    """Endpoints reachable from `start` by following `body` in order.

    All nodes on the path must be DISTINCT -- the guard `yardstick.py` writes
    out per-hop and `evo.py:160` calls "no step returns". Returned as a set,
    matching the original's behaviour of scoring each endpoint once.
    """
    frontier = {(start, (start,))}
    for pred in body:
        nxt = set()
        for node, seen in frontier:
            for pp, dst in out_adj.get(node, ()):
                if pp == pred and dst not in seen:
                    nxt.add((dst, seen + (dst,)))
        frontier = nxt
        if not frontier:
            return set()
    return {node for node, _ in frontier}


def walk_backward(end, body, in_adj):
    """Sources that reach `end` by following `body` in order. Mirror of above."""
    frontier = {(end, (end,))}
    for pred in reversed(body):
        nxt = set()
        for node, seen in frontier:
            for pp, src in in_adj.get(node, ()):
                if pp == pred and src not in seen:
                    nxt.add((src, seen + (src,)))
        frontier = nxt
        if not frontier:
            return set()
    return {node for node, _ in frontier}


def evaluate_varlen(rules, test_triples, out_adj, in_adj, true_sp, true_po,
                    nent, sample_limit=None):
    """Filtered link prediction over bodies of ANY length.

    Ranking, filtering and tie-breaking are transcribed from
    `yardstick.evaluate_link_prediction` unchanged -- only the walk is
    generalised. F1 is what proves that claim rather than asserting it.
    """
    rules_by_head = defaultdict(list)
    for r in rules:
        body = tuple(r["body"]) if isinstance(r["body"], (list, tuple)) else (r["body"],)
        rules_by_head[r["head"]].append((body, r["conf"]))

    eval_set = test_triples if sample_limit is None else test_triples[:sample_limit]
    rr_t, rr_h = [], []
    h1t = h3t = h10t = h1h = h3h = h10h = 0
    lengths = defaultdict(int)
    for body_list in rules_by_head.values():
        for body, _ in body_list:
            lengths[len(body)] += 1

    t0 = time.time()
    for p, s, o in eval_set:
        # ---- tail: (s, p, ?o)
        cand_t = defaultdict(float)
        for body, conf in rules_by_head.get(p, ()):
            for c_node in walk_forward(s, body, out_adj):
                if conf > cand_t[c_node]:
                    cand_t[c_node] = conf
        filt_sp = true_sp.get((s, p), set())
        valid_t = {c: sc for c, sc in cand_t.items() if c == o or c not in filt_sp}
        tgt_t = valid_t.get(o, 0.0)
        n_filt_t = nent - (len(filt_sp) - (1 if o in filt_sp else 0))
        if tgt_t > 0.0:
            higher = sum(1 for c, sc in valid_t.items() if sc > tgt_t)
            equal = sum(1 for c, sc in valid_t.items() if sc == tgt_t and c != o)
            rank_t = 1.0 + higher + equal / 2.0
        else:
            higher = sum(1 for c, sc in valid_t.items() if sc > 0.0)
            rank_t = 1.0 + higher + ((n_filt_t - higher) - 1) / 2.0
        rr_t.append(1.0 / rank_t)
        h1t += rank_t <= 1.0
        h3t += rank_t <= 3.0
        h10t += rank_t <= 10.0

        # ---- head: (?s, p, o)
        cand_h = defaultdict(float)
        for body, conf in rules_by_head.get(p, ()):
            for a_node in walk_backward(o, body, in_adj):
                if conf > cand_h[a_node]:
                    cand_h[a_node] = conf
        filt_po = true_po.get((p, o), set())
        valid_h = {c: sc for c, sc in cand_h.items() if c == s or c not in filt_po}
        tgt_h = valid_h.get(s, 0.0)
        n_filt_h = nent - (len(filt_po) - (1 if s in filt_po else 0))
        if tgt_h > 0.0:
            higher = sum(1 for c, sc in valid_h.items() if sc > tgt_h)
            equal = sum(1 for c, sc in valid_h.items() if sc == tgt_h and c != s)
            rank_h = 1.0 + higher + equal / 2.0
        else:
            higher = sum(1 for c, sc in valid_h.items() if sc > 0.0)
            rank_h = 1.0 + higher + ((n_filt_h - higher) - 1) / 2.0
        rr_h.append(1.0 / rank_h)
        h1h += rank_h <= 1.0
        h3h += rank_h <= 3.0
        h10h += rank_h <= 10.0

    n = len(eval_set)
    tot = 2 * n
    return {
        "mrr": (sum(rr_t) + sum(rr_h)) / tot,
        "hits1": (h1t + h1h) / tot,
        "hits3": (h3t + h3h) / tot,
        "hits10": (h10t + h10h) / tot,
        "n_queries": tot,
        "body_lengths": dict(sorted(lengths.items())),
        "elapsed_sec": time.time() - t0,
    }


def plant_len_n_rule(n_hops, npred, nent, train, test, rng, n_planted=30):
    """A synthetic relation entailed by a chain of exactly `n_hops` predicates.

    Used by C2/C3: the general walk must find it, and the 2-hop walk must NOT
    (for n_hops != 2). Both directions matter -- a control that only shows the
    general walk succeeding cannot tell generalisation from a scoring change.
    """
    chain = tuple(npred + 1 + i for i in range(n_hops))
    target = npred + 1 + n_hops
    extra_tr, extra_te = [], []
    base = nent + 1000
    for k in range(n_planted):
        nodes = [base + k * (n_hops + 1) + i for i in range(n_hops + 1)]
        for i, pred in enumerate(chain):
            extra_tr.append((pred, nodes[i], nodes[i + 1]))
        extra_te.append((target, nodes[0], nodes[-1]))
    return chain, target, extra_tr, extra_te


def main():
    print("=" * 78)
    print("G37 — filtered-MRR evaluation for rule bodies of any length")
    print("=" * 78)

    nt, npred, nent, tri, train, dev, test = Y.load_dataset()
    out_adj, in_adj, _, _, _ = Y.build_graph_index(train, nent)
    true_sp, true_po = Y.build_filter_index(tri)
    rules_2hop = Y.mine_g17_rules(train)
    print(f"\nloaded: {len(train):,} train / {len(test):,} test, "
          f"{len(rules_2hop):,} 2-hop rules mined")

    # ---- F1: the generalised walk must reproduce G30 exactly on 2-hop input
    print("\n1. F1 — generalised walk on the SAME 2-hop rules "
          "(must equal G30 exactly)")
    gen = evaluate_varlen(rules_2hop, test, out_adj, in_adj, true_sp, true_po, nent)
    orig = Y.evaluate_link_prediction(rules_2hop, test, out_adj, in_adj,
                                      true_sp, true_po, nent)
    print(f"{'metric':<10}{'G30 published':>15}{'yardstick.py':>15}{'G37 general':>15}  match")
    f1_ok = True
    for k in ("mrr", "hits1", "hits3", "hits10"):
        same = abs(gen[k] - orig[k]) < 1e-12
        pub_same = abs(round(gen[k], 4) - G30_PUBLISHED[k]) < 1e-9
        f1_ok = f1_ok and same and pub_same
        print(f"{k:<10}{G30_PUBLISHED[k]:>15.4f}{orig[k]:>15.6f}{gen[k]:>15.6f}"
              f"  {'OK' if same and pub_same else 'DIFFERS'}")

    # ---- C2/C3: planted length-3 and length-1 rules
    print("\n2. C2/C3 — planted rules the 2-hop walk structurally cannot see")
    planted = {}
    for n_hops in (1, 3):
        rng = random.Random(31337 + n_hops)
        chain, target, ex_tr, ex_te = plant_len_n_rule(n_hops, npred, nent,
                                                       train, test, rng)
        del rng
        p_out, p_in, _, _, _ = Y.build_graph_index(train + ex_tr, nent + 5000)
        p_sp, p_po = Y.build_filter_index(tri + ex_tr + ex_te)
        rule = [{"body": chain, "head": target, "conf": 1.0}]
        g = evaluate_varlen(rule, ex_te, p_out, p_in, p_sp, p_po, nent + 5000)
        # the 2-hop instrument, handed the same rule
        try:
            o = Y.evaluate_link_prediction(rule, ex_te, p_out, p_in, p_sp,
                                           p_po, nent + 5000)
            o_mrr, o_err = o["mrr"], None
        except Exception as e:                     # a length!=2 body cannot unpack
            o_mrr, o_err = None, f"{type(e).__name__}: {e}"
        planted[n_hops] = {"general_mrr": g["mrr"], "twohop_mrr": o_mrr,
                           "twohop_error": o_err}
        print(f"  length-{n_hops} planted rule: general MRR={g['mrr']:.4f}   "
              f"2-hop walk -> {o_err or f'MRR={o_mrr:.4f}'}")

    f2_fires = all(
        planted[n]["twohop_mrr"] is None or planted[n]["twohop_mrr"] < 0.5
        for n in (1, 3)) and all(planted[n]["general_mrr"] > 0.9 for n in (1, 3))

    out = {"f1_reproduces_g30": f1_ok,
           "g30_published": G30_PUBLISHED,
           "yardstick_rerun": {k: orig[k] for k in ("mrr", "hits1", "hits3", "hits10")},
           "g37_general": {k: gen[k] for k in ("mrr", "hits1", "hits3", "hits10")},
           "body_lengths_seen": gen["body_lengths"],
           "planted": planted,
           "f2_generalisation_is_load_bearing": f2_fires}
    out_json = os.path.join(HERE, "varlen.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    controls, falsifiers = [], []
    c1 = P.Control(
        "C1_general_walk_reproduces_the_specialised_one",
        "a generalisation that changes the numbers is a different instrument",
        null_must_contain="any metric differing from yardstick.py on identical "
                          "2-hop rules",
        can_fail_because="dropping the distinct-node guard, or scoring an "
                         "endpoint reached by two paths twice, would both raise "
                         "MRR while looking like a successful generalisation")
    c1.observe(f1_ok, {"g30_published": G30_PUBLISHED,
                       "g37": {k: gen[k] for k in G30_PUBLISHED}})
    controls.append(c1)

    c2 = P.Control(
        "C2_planted_len3_found_by_general_missed_by_twohop",
        "the generalisation must buy something structural, not just parse",
        null_must_contain="the 2-hop walk scoring a length-3 rule as well as "
                          "the general walk",
        can_fail_because="if the 2-hop walk also solved it, the extra length "
                         "would be decorative")
    c2.observe(planted[3]["general_mrr"] > 0.9 and
               (planted[3]["twohop_mrr"] is None or planted[3]["twohop_mrr"] < 0.5),
               planted[3])
    controls.append(c2)

    c3 = P.Control(
        "C3_planted_len1_found_by_general_missed_by_twohop",
        "length-1 is the class G34 measured as carrying most of the lift",
        null_must_contain="the 2-hop walk scoring a length-1 rule",
        can_fail_because="a body of length 1 would unpack under the 2-hop "
                         "destructure only if the guard were absent")
    c3.observe(planted[1]["general_mrr"] > 0.9 and
               (planted[1]["twohop_mrr"] is None or planted[1]["twohop_mrr"] < 0.5),
               planted[1])
    controls.append(c3)

    f1 = P.Falsifier(
        "F1_instrument_drift",
        "WITHDRAW the evaluator if it does not reproduce G30 exactly",
        "any of MRR/Hits@1/Hits@3/Hits@10 differs from yardstick.py on the "
        "same 2-hop rules, or from G30's published row at 4 dp",
        null_must_contain="an exact match on all four metrics")
    f1.observe(not f1_ok, {"match": f1_ok})
    falsifiers.append(f1)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G30, os.path.join(SPIKES, "S52_realkg")],
        artifacts=[os.path.join(HERE, "varlen.py"), out_json],
        controls=controls, falsifiers=falsifiers,
        falsifier="The generalised walk differs from yardstick.py on identical "
                  "2-hop rules, or finds nothing the 2-hop walk misses",
        allow_dirty=True,
        note="G37: filtered-MRR evaluation for variable-length rule bodies")

    print(f"\nF1 (instrument drift): {'FIRED — WITHDRAWN' if not f1_ok else 'did not fire'}")
    print(f"F2 (generalisation load-bearing): {f2_fires}")
    print(f"D6 Provenance Certified: ok={ok}")
    for p_ in problems:
        print(f"  PROBLEM: {p_}")
    return 0 if (ok and f1_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
