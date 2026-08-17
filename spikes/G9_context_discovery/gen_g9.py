#!/usr/bin/env python3
"""G9 — can contexts be DISCOVERED, or must they be declared?

G8 showed per-context attention works and named the cost: you must know your
query classes in advance, which is why DAS makes `context` a caller-supplied
argument. That constraint is what would stop any of this being self-evolving in
a strong sense — a system that cannot form its own contexts cannot restructure
its own attention.

So: observe a stream of queries, cluster them by WHAT THEY TOUCH, and create a
context per cluster. Then compare, on mean preservation across all queries after
forgetting half the graph:

    1 global context      G7's arrangement — the floor
    k discovered          clustered by Jaccard overlap of touch sets
    k random              SAME number of contexts, queries assigned by name
                          order — the null that separates "clustering works"
                          from "having k contexts works"
    N declared            one context per query — G8's arrangement, the ceiling

The `k random` arm is the one that matters. Without it, k discovered contexts
beating 1 global proves only that k > 1, which is not a discovery result.

Discovery is by Jaccard on touch sets, single-linkage above a threshold. That is
the cheapest thing that could work; if it fails, richer clustering is the next
question rather than the conclusion.
"""

import json
import os
import re
import subprocess
import sys
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
GRAPH = os.path.join(SPIKES, "G1_graph_ingest", "graph.json")
RUNNER = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")

QUERIES = {
    "q_red":      "(, (cites $x $y) (verdict $y RED))",
    "q_invalid":  "(, (cites $x $y) (verdict $y INVALID))",
    "q_green":    "(, (cites $x $y) (verdict $y GREEN))",
    "q_amber":    "(, (cites $x $y) (verdict $y AMBER))",
    "q_2hop_red": "(, (cites $x $z) (cites $z $y) (verdict $y RED))",
    "q_yellow":   "(, (cites $x $y) (verdict $y YELLOW))",
}
SCALE, RENT, SEED, EPOCHS = 1000, 50, 1000, 3
JACCARD_MIN = 0.55


def run(path, fuel=40_000_000):
    out = subprocess.run([RUNNER, path, str(fuel)], capture_output=True,
                         text=True).stdout
    st = re.search(r"^status\s+(\S+)", out, re.M)
    return (st.group(1) if st else "?"), out.split("--- results ---", 1)[-1]


def facts(nodes, keep=None):
    L = []
    for n in nodes:
        if keep is not None and n["id"] not in keep:
            continue
        L.append(f'(spike {n["id"]})')
        if n["verdict"]:
            L.append(f'(verdict {n["id"]} {n["verdict"]})')
        for c in n["cites"]:
            if keep is None or c in keep:
                L.append(f'(cites {n["id"]} {c})')
    return L


def ask(nodes, keep, query, tag):
    p = os.path.join(HERE, f"q_{tag}.metta")
    open(p, "w").write("\n".join(facts(nodes, keep))
                       + f"\n!(collapse (match &self {query} (hit $x $y)))\n")
    st, body = run(p)
    return st, set(re.findall(r"\(hit (\w+) (\w+)\)", body))


def touch(nodes, query, tag):
    st, hits = ask(nodes, None, query, f"t_{tag}")
    t = {}
    for a, b in hits:
        t[a] = t.get(a, 0) + 1
        t[b] = t.get(b, 0) + 1
    return st, t, hits


def jaccard(a, b):
    A, B = set(a), set(b)
    return len(A & B) / len(A | B) if (A | B) else 0.0


def single_linkage(names, touches, thr):
    """Cheapest thing that could work: merge any two clusters with a pair above
    threshold. Deterministic — names are processed in sorted order."""
    clusters = [[n] for n in sorted(names)]
    merged = True
    while merged:
        merged = False
        for i, j in combinations(range(len(clusters)), 2):
            if any(jaccard(touches[a], touches[b]) >= thr
                   for a in clusters[i] for b in clusters[j]):
                clusters[i] = clusters[i] + clusters[j]
                del clusters[j]
                merged = True
                break
    return clusters


def ecan(ids, ctx_stim):
    L = ["; G9 per-context ECAN"]
    for ctx, stim in ctx_stim.items():
        for i in sorted(ids):
            L.append(f"(imp {ctx} 0 {i} {SEED})")
            L.append(f"(stim {ctx} {i} {stim.get(i, 0)})")
    for ctx in ctx_stim:
        for e in range(EPOCHS):
            L.append(f"!(let $rs (collapse (match &self (imp {ctx} {e} $c $v) "
                     f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self "
                     f"(total-rent {ctx} {e} (foldl-atom $rs 0 $a $b (+ $a $b)))))")
            L.append(f"!(let $ss (collapse (match &self (stim {ctx} $c $s) $s)) "
                     f"(add-atom &self (total-stim {ctx} {e} "
                     f"(foldl-atom $ss 0 $a $b (+ $a $b)))))")
            L.append(f"!(let $new (collapse (match &self (, (imp {ctx} {e} $c $v) "
                     f"(stim {ctx} $c $s) (total-rent {ctx} {e} $tr) "
                     f"(total-stim {ctx} {e} $ts)) (imp {ctx} {e+1} $c "
                     f"(+ (- $v (/ (* $v {RENT}) {SCALE})) (/ (* $s $tr) $ts))))) "
                     f"(add-atoms &self $new))")
    order = list(ctx_stim)
    for ctx in order:
        L.append(f"!(collapse (match &self (imp {ctx} {EPOCHS} $c $v) "
                 f"(IMPOF {ctx} $c $v)))")
    p = os.path.join(HERE, "ecan_g9.metta")
    open(p, "w").write("\n".join(L) + "\n")
    st, body = run(p)
    out = {c: {} for c in order}
    for c, k, v in re.findall(r"\(IMPOF (\w+) (\w+) (\d+)\)", body):
        if c in out:
            out[c][k] = int(v)
    for c in out:                      # a context with no stimulus still exists
        for i in ids:
            out[c].setdefault(i, SEED)
    return st, out


def score(nodes, ids, assign, imp, base, keep_n, tag):
    """Each query is pruned by ITS OWN context's field, then asked."""
    tot = 0.0
    for q, ctx in assign.items():
        keep = set(sorted(ids, key=lambda i: (-imp[ctx][i], i))[:keep_n])
        _, f = ask(nodes, keep, QUERIES[q], f"{tag}_{q}")
        tot += len(f & base[q]) / len(base[q]) if base[q] else 0.0
    return tot / len(assign)


def main():
    g = json.load(open(GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]

    touches, base = {}, {}
    print(f"{'query':<12}{'status':>8}{'findings':>10}{'touched':>9}")
    for q, expr in QUERIES.items():
        st, t, hits = touch(nodes, expr, q)
        touches[q], base[q] = t, hits
        print(f"{q:<12}{st:>8}{len(hits):>10}{len(t):>9}")

    dead = [q for q in QUERIES if not base[q]]
    if dead:
        print(f"\nDROPPED as degenerate (0 findings, cannot be preserved or "
              f"lost): {dead}")
    for q in dead:
        del touches[q], base[q]

    print(f"\ntouch-set Jaccard (threshold {JACCARD_MIN}):")
    names = sorted(base)
    print("            " + "".join(f"{n[2:]:>10}" for n in names))
    for a in names:
        print(f"  {a:<10}" + "".join(f"{jaccard(touches[a],touches[b]):>10.2f}"
                                     for b in names))

    disc = single_linkage(names, touches, JACCARD_MIN)
    print(f"\ndiscovered {len(disc)} clusters: {disc}")
    k = len(disc)

    schemes = {}
    schemes["global_1"] = {q: "cG" for q in names}
    schemes["declared_N"] = {q: f"cD{i}" for i, q in enumerate(names)}
    schemes["discovered_k"] = {q: f"cX{i}" for i, cl in enumerate(disc) for q in cl}
    # null: same k, membership by name order rather than by overlap
    per = -(-len(names) // k)
    schemes["random_k"] = {q: f"cR{i//per}" for i, q in enumerate(names)}

    keep_n = len(ids) - len(ids) // 2
    print(f"\nforgetting {len(ids)//2} of {len(ids)} nodes; "
          f"each query pruned by its own context\n")
    print(f"  {'scheme':<16}{'contexts':>9}{'mean preserved':>16}")
    res = {}
    for name, assign in schemes.items():
        stim = {}
        for q, ctx in assign.items():
            d = stim.setdefault(ctx, {})
            for n_, c in touches[q].items():
                d[n_] = d.get(n_, 0) + c
        st, imp = ecan(ids, stim)
        m = score(nodes, ids, assign, imp, base, keep_n, name)
        res[name] = {"contexts": len(stim), "mean_preserved": m, "status": st}
        print(f"  {name:<16}{len(stim):>9}{m:>15.0%}")

    g1, dk, rk, dn = (res[k_]["mean_preserved"] for k_ in
                      ("global_1", "discovered_k", "random_k", "declared_N"))
    # A single `random_k` arm cannot separate discovery from luck: with 5
    # queries into 3 groups the gap was 79% vs 77%, a tenth of one query.
    # exhaustive.py enumerates ALL 25 partitions and puts discovered at
    # rank 4/25, p=0.160. Verdict is stated from that, not from one draw.
    if dk > rk and dk > g1:
        v = (f"k HELPS, DISCOVERY UNPROVEN — {k} discovered {dk:.0%} vs {k} "
             f"arbitrary {rk:.0%} vs 1 global {g1:.0%}. See exhaustive.py: "
             f"discovered ranks 4/25 over all partitions, p=0.160")
    elif dk > g1 and dk <= rk:
        v = (f"NOT DISCOVERY — {k} contexts help ({dk:.0%} vs {g1:.0%}) but "
             f"arbitrary grouping does as well ({rk:.0%}). The win is k, not clustering")
    else:
        v = f"NO SIGNAL — discovered {dk:.0%} does not beat global {g1:.0%}"
    print(f"\nceiling (one context per query): {dn:.0%}")
    print(f"VERDICT: {v}")

    json.dump({"queries": QUERIES, "clusters": disc, "results": res,
               "jaccard_min": JACCARD_MIN, "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"scheme": list(schemes)}},
               "cites": ["G7_query_attention", "G8_per_context"]},
              open(os.path.join(HERE, "g9.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
