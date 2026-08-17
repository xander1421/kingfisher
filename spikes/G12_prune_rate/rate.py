#!/usr/bin/env python3
"""G12 — does ITERATION earn its place, or would one shot do?

G10 pruned 10% per cycle for 10 cycles and preserved 64% of findings at 26 live
nodes. That is better than the no-attention control (16%). It is NOT evidence
that iterating helped: the obvious alternative is to run one ECAN epoch on the
full graph and prune straight to 26 nodes.

If one shot does as well, the loop is ceremony and the architecture should say
so. This sweeps the prune rate and compares **at equal final graph size**, which
is the only comparison that separates the effect of the RATE from the effect of
the AMOUNT pruned.

  rate 0.05  ~16 cycles to reach the target
  rate 0.10   ~8
  rate 0.20   ~4
  rate 0.35   ~2
  rate 1.00   ONE SHOT — a single epoch on the full graph, prune to target

Every arm ends at the same live count, so preservation is directly comparable.
The no-attention control from G10 is carried as the floor.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "G10_closed_loop"))
import loop as L                                        # noqa: E402

TARGET = 26          # G10's endpoint, so the headline number is comparable
RATES = [0.05, 0.10, 0.20, 0.35, 1.00]


def run_arm(nodes, ids, base, rate, attention, tag):
    live = set(ids)
    imp = {q: {i: L.SEED for i in ids} for q in L.QUERIES}
    cycles = 0
    while len(live) > TARGET:
        stims = {}
        for q, expr in L.QUERIES.items():
            hits = L.ask(nodes, live, expr, f"{tag}{cycles}_{q}")
            t = {}
            for a, b in hits:
                t[a] = t.get(a, 0) + 1
                t[b] = t.get(b, 0) + 1
            stims[q] = t
        # rate 1.00 means: one epoch, then cut straight to TARGET
        drop_n = (len(live) - TARGET if rate >= 1.0
                  else min(max(1, int(len(live) * rate)), len(live) - TARGET))
        if attention:
            _, imp = L.epoch(live, stims, imp, f"{tag}{cycles}")
            worth = {i: max(imp[q].get(i, 0) for q in L.QUERIES) for i in live}
            order = sorted(live, key=lambda i: (worth[i], i))
        else:
            order = sorted(live)
        live = live - set(order[:drop_n])
        cycles += 1

    pres = {}
    for q, expr in L.QUERIES.items():
        hits = L.ask(nodes, live, expr, f"{tag}F_{q}")
        pres[q] = len(hits & base[q]) / len(base[q]) if base[q] else 0.0
    return cycles, len(live), sum(pres.values()) / len(pres), pres


def main():
    g = json.load(open(L.GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]
    base = {q: L.ask(nodes, set(ids), e, f"b_{q}") for q, e in L.QUERIES.items()}
    print(f"target {TARGET} of {len(ids)} nodes; every arm ends at the same size\n")
    print(f"  {'rate':>6}{'cycles':>8}{'live':>6}{'mean preserved':>16}")

    res = {}
    for r in RATES:
        c, n, m, pq = run_arm(nodes, ids, base, r, True, f"a{int(r*100)}_")
        res[f"attention_{r:.2f}"] = {"rate": r, "cycles": c, "live": n,
                                     "mean": m, "per_query": pq}
        label = f"{r:.2f}" + (" (one shot)" if r >= 1.0 else "")
        print(f"  {label:>6}{c:>8}{n:>6}{m:>15.0%}")

    c, n, m, pq = run_arm(nodes, ids, base, 0.10, False, "ctl_")
    res["control_0.10"] = {"rate": 0.10, "cycles": c, "live": n, "mean": m,
                           "per_query": pq}
    print(f"  {'ctrl':>6}{c:>8}{n:>6}{m:>15.0%}   (no attention, floor)")

    grad = res["attention_0.05"]["mean"]
    one = res["attention_1.00"]["mean"]
    ten = res["attention_0.10"]["mean"]
    spread = (max(v["mean"] for k, v in res.items() if k.startswith("attention"))
              - min(v["mean"] for k, v in res.items() if k.startswith("attention")))
    if one >= ten - 0.02 and spread < 0.05:
        v = (f"ITERATION IS CEREMONY — one shot {one:.0%} matches gradual "
             f"{ten:.0%}; spread across all rates {spread:.0%}")
    elif ten > one + 0.05:
        v = (f"ITERATION EARNS ITS PLACE — gradual {ten:.0%} beats one shot "
             f"{one:.0%}")
    else:
        v = (f"INCONCLUSIVE — one shot {one:.0%}, 10%/cycle {ten:.0%}, "
             f"5%/cycle {grad:.0%}, spread {spread:.0%}")
    print(f"\nVERDICT: {v}")

    json.dump({"target": TARGET, "rates": RATES, "results": res, "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"prune_rate": RATES}},
               "cites": ["G10_closed_loop"]},
              open(os.path.join(HERE, "rate.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
