#!/usr/bin/env python3
"""G7 — query-driven attention, tested for GENERALISATION rather than memory.

G6 inverted: in-degree importance ranked foundational GREEN spikes highest and
recently-refuted INVALID ones near the bottom, so pruning by it dropped exactly
what an audit query needed. The named fix was to stimulate what a QUERY touched,
which is what DAS's `stimulate(HandleCount)` actually does.

But the naive version of that is circular: stimulate the atoms the test query
needs, prune by that, then show the test query still answers. Of course it does.
That is memorisation dressed as attention, and it is the S65 defect — a
commitment that binds nothing.

So attention is trained on ONE query and evaluated on a DIFFERENT one:

  TRAIN   (, (cites $x $y) (verdict $y RED))       — spikes resting on a RED
  TEST    (, (cites $x $y) (verdict $y INVALID))   — G1's independently
                                                     verified finding

The atoms touched by successful TRAIN matches receive stimulus. ECAN runs.
The graph is pruned by the resulting importance. Then TEST is asked.

If the regions of the graph that matter for one audit query overlap with those
for another, attention generalises. If it only preserves what it was stimulated
on, it memorises, and the honest report is that it memorises.

FOUR ARMS, so the instrument can distinguish those cases:
  query_attention  prune lowest query-driven importance     the treatment
  indegree         G6's arm, kept as the thing being beaten
  keep_low         prune HIGHEST importance                 must be worse
  arbitrary        name order, no importance                the null

A one-sided control cannot separate "attention works" from "this graph is
robust to any pruning" — that is the N1c lesson, and it is why keep_low is here.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
GRAPH = os.path.join(SPIKES, "G1_graph_ingest", "graph.json")
RUNNER = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")

TRAIN = "(, (cites $x $y) (verdict $y RED))"
TEST = "(, (cites $x $y) (verdict $y INVALID))"

SCALE, RENT, SEED, EPOCHS = 1000, 50, 1000, 3


def run(path, fuel=20_000_000):
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


def query_stimulus(nodes):
    """Which nodes does the TRAIN query actually touch? Asked of MeTTa, not
    reimplemented in Python — the point is that the engine decides."""
    p = os.path.join(HERE, "train.metta")
    open(p, "w").write("\n".join(facts(nodes))
                       + f"\n!(collapse (match &self {TRAIN} ($x $y)))\n")
    st, body = run(p)
    touched = {}
    for a, b in re.findall(r"\((\w+) (\w+)\)", body):
        touched[a] = touched.get(a, 0) + 1
        touched[b] = touched.get(b, 0) + 1
    return st, touched


def ecan(ids, stim):
    """G5's epoch, unchanged, with the stimulus swapped for the query's."""
    L = [f"; G7 ECAN, stimulus = TRAIN-query touch count"]
    for i in sorted(ids):
        L.append(f"(imp 0 {i} {SEED})")
        L.append(f"(stim {i} {stim.get(i, 0)})")
    for e in range(EPOCHS):
        L.append(f"!(let $rs (collapse (match &self (imp {e} $c $v) "
                 f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self (total-rent {e} "
                 f"(foldl-atom $rs 0 $a $b (+ $a $b)))))")
        L.append(f"!(let $ss (collapse (match &self (stim $c $s) $s)) "
                 f"(add-atom &self (total-stim {e} "
                 f"(foldl-atom $ss 0 $a $b (+ $a $b)))))")
        L.append(f"!(let $new (collapse (match &self (, (imp {e} $c $v) "
                 f"(stim $c $s) (total-rent {e} $tr) (total-stim {e} $ts)) "
                 f"(imp {e+1} $c (+ (- $v (/ (* $v {RENT}) {SCALE})) "
                 f"(/ (* $s $tr) $ts))))) (add-atoms &self $new))")
    L.append(f"!(collapse (match &self (imp {EPOCHS} $c $v) ($c $v)))")
    p = os.path.join(HERE, "ecan_g7.metta")
    open(p, "w").write("\n".join(L) + "\n")
    st, body = run(p)
    line = [l for l in body.strip().split("\n") if "(" in l][-1]
    return st, {k: int(v) for k, v in re.findall(r"\((\w+) (\d+)\)", line)}


def test(nodes, keep, tag):
    p = os.path.join(HERE, f"test_{tag}.metta")
    open(p, "w").write("\n".join(facts(nodes, keep))
                       + f"\n!(collapse (match &self {TEST} (at-risk $x $y)))\n")
    st, body = run(p)
    return st, set(re.findall(r"\(at-risk (\w+) (\w+)\)", body))


def main():
    g = json.load(open(GRAPH))
    nodes = g["nodes"]
    ids = [n["id"] for n in nodes]

    st, stim = query_stimulus(nodes)
    print(f"TRAIN query {TRAIN}")
    print(f"  status {st}   nodes touched {len(stim)} of {len(ids)}")

    st, imp = ecan(ids, stim)
    for i in ids:
        imp.setdefault(i, 0)
    print(f"ECAN        status {st}   importance computed for {len(imp)}\n")

    indeg = {i: 0 for i in ids}
    for n in nodes:
        for c in n["cites"]:
            if c in indeg:
                indeg[c] += 1

    st, base = test(nodes, set(ids), "full")
    print(f"TEST query  {TEST}")
    print(f"  baseline on full graph: {len(base)} findings {sorted(base)}\n")

    keep_n = len(ids) - len(ids) // 2
    arms = {
        "query_attention": sorted(ids, key=lambda i: (-imp[i], i))[:keep_n],
        "indegree":        sorted(ids, key=lambda i: (-indeg[i], i))[:keep_n],
        "keep_low":        sorted(ids, key=lambda i: (imp[i], i))[:keep_n],
        "arbitrary":       sorted(ids)[:keep_n],
    }

    print(f"forgetting {len(ids)//2} of {len(ids)} nodes (50%)\n")
    print(f"  {'arm':<18}{'found':>6}{'preserved':>11}")
    res = {}
    for name, keep in arms.items():
        _, f = test(nodes, set(keep), name)
        pres = len(f & base) / len(base) if base else 0.0
        res[name] = {"findings": len(f), "preserved": pres}
        print(f"  {name:<18}{len(f):>6}{pres:>10.0%}")

    qa, ind, lo, ar = (res[k]["preserved"] for k in
                       ("query_attention", "indegree", "keep_low", "arbitrary"))
    if qa > ar and qa > lo and qa > ind:
        v = "GENERALISES — query-driven attention beats in-degree, low and arbitrary"
    elif qa > ar and qa > lo:
        v = f"PARTIAL — beats the controls but not in-degree ({qa:.0%} vs {ind:.0%})"
    elif qa <= ar:
        v = "NO SIGNAL — no better than pruning by name order"
    else:
        v = "INVERTED — a control beat the treatment"
    print(f"\nVERDICT: {v}")

    json.dump({"train": TRAIN, "test": TEST, "touched": len(stim),
               "baseline": sorted(base), "arms": res, "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"arm": list(arms)}},
               "cites": ["G1_graph_ingest", "G5_ecan_metta", "G6_forgetting"]},
              open(os.path.join(HERE, "g7.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
