#!/usr/bin/env python3
"""G9's real control: enumerate ALL partitions rather than sample one.

`gen_g9.py`'s `random_k` arm gave 79% discovered against 77% arbitrary, and the
verdict logic called that DISCOVERY WORKS. Two points across five queries is a
tenth of one query — the same lenient-threshold failure as G2's 5-shuffle
"REAL SIGNAL".

With 5 queries into 3 groups there are only S(5,3) = 25 partitions, so the
honest test is exhaustive rather than sampled. No p-value estimation, no
sampling error: every alternative is evaluated.

Measured: discovered ranks 4/25, exact p = 0.160.
"""

import json
import sys

sys.path.insert(0, ".")
import gen_g9 as G


def partitions(c, k):
    """Every way to split list `c` into exactly `k` non-empty groups."""
    if k == 1:
        yield [list(c)]
        return
    if len(c) == k:
        yield [[x] for x in c]
        return
    first, rest = c[0], c[1:]
    for p in partitions(rest, k - 1):
        yield [[first]] + p
    for p in partitions(rest, k):
        for i in range(len(p)):
            yield p[:i] + [[first] + p[i]] + p[i + 1:]


def main():
    g = json.load(open(G.GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]

    touches, base = {}, {}
    for q, expr in G.QUERIES.items():
        _, t, h = G.touch(nodes, expr, q)
        touches[q], base[q] = t, h
    for q in [q for q in G.QUERIES if not base[q]]:
        del touches[q], base[q]          # degenerate: 0 findings
    names = sorted(base)
    keep_n = len(ids) - len(ids) // 2

    def mean_pres(parts, tag):
        assign = {q: f"c{i}" for i, cl in enumerate(parts) for q in cl}
        stim = {}
        for q, ctx in assign.items():
            d = stim.setdefault(ctx, {})
            for n_, c in touches[q].items():
                d[n_] = d.get(n_, 0) + c
        _, imp = G.ecan(ids, stim)
        return G.score(nodes, ids, assign, imp, base, keep_n, tag)

    disc = G.single_linkage(names, touches, G.JACCARD_MIN)
    d = mean_pres(disc, "disc")
    allp = list(partitions(names, 3))
    print(f"discovered partition {disc} -> {d:.1%}")
    print(f"enumerating ALL {len(allp)} partitions of {len(names)} into 3\n")

    scored = sorted(((mean_pres(p, f"p{i}"), p) for i, p in enumerate(allp)),
                    reverse=True)
    ge = sum(1 for s, _ in scored if s >= d)
    p_exact = ge / len(scored)
    print(f"  best   {scored[0][0]:.1%}  {scored[0][1]}")
    print(f"  median {scored[len(scored)//2][0]:.1%}")
    print(f"  worst  {scored[-1][0]:.1%}  {scored[-1][1]}")
    print(f"\n  discovered ranks {ge}/{len(scored)}   exact p = {p_exact:.3f}")
    print("  VERDICT: " + ("DISCOVERY BEATS CHANCE" if p_exact < 0.05 else
          "NOT DISCOVERY — clustering is no better than an arbitrary 3-way split"))

    json.dump({"discovered": disc, "discovered_score": d,
               "n_partitions": len(scored), "rank": ge, "p_exact": p_exact,
               "best": scored[0][1], "best_score": scored[0][0],
               "median_score": scored[len(scored) // 2][0],
               "worst_score": scored[-1][0],
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"partition": len(scored)}},
               "cites": ["G9_context_discovery"]},
              open("exhaustive.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
