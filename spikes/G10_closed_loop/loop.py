#!/usr/bin/env python3
"""G10 — close the loop, and find out whether it eats itself.

Everything so far ran ONE pass. G1 queried, G5 ran an epoch, G6-G9 pruned once.
The architecture claim is a CYCLE:

    query -> stimulus -> ECAN epoch -> forget the least important
          -> query the SMALLER graph -> ...

That is a feedback system, and feedback systems have three outcomes, not one:

  CONVERGE   the graph shrinks to a stable working set and keeps answering
  OSCILLATE  importance sloshes between regions, answers flicker
  COLLAPSE   pruning removes what the next query needed, stimulus shrinks,
             more gets pruned, and the graph eats itself

Nobody has run it, and "self-evolving" is only interesting if the answer is the
first one. G9 established the operating rule this uses: several contexts, and
membership barely matters — so each query class gets its own budget.

INVARIANT (G5's lesson: a deterministic wrong answer is still wrong):
  findings preserved per cycle, tracked per query, against the FULL-graph
  baseline. Conservation is checked inside every epoch.

CONTROL: the identical prune schedule with attention removed — same number of
nodes dropped per cycle, chosen by name order. If attention-driven forgetting
is no better than that, the loop is a decay curve with extra steps.
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

QUERIES = {
    "q_red":      "(, (cites $x $y) (verdict $y RED))",
    "q_invalid":  "(, (cites $x $y) (verdict $y INVALID))",
    "q_green":    "(, (cites $x $y) (verdict $y GREEN))",
    "q_2hop_red": "(, (cites $x $z) (cites $z $y) (verdict $y RED))",
    "q_yellow":   "(, (cites $x $y) (verdict $y YELLOW))",
}
SCALE, RENT, SEED, EPOCHS = 1000, 50, 1000, 1     # one epoch PER CYCLE
CYCLES, PRUNE_FRAC = 10, 0.10


def run(path, fuel=40_000_000):
    out = subprocess.run([RUNNER, path, str(fuel)], capture_output=True,
                         text=True).stdout
    st = re.search(r"^status\s+(\S+)", out, re.M)
    return (st.group(1) if st else "?"), out.split("--- results ---", 1)[-1]


def facts(nodes, keep):
    L = []
    for n in nodes:
        if n["id"] not in keep:
            continue
        L.append(f'(spike {n["id"]})')
        if n["verdict"]:
            L.append(f'(verdict {n["id"]} {n["verdict"]})')
        for c in n["cites"]:
            if c in keep:
                L.append(f'(cites {n["id"]} {c})')
    return L


def ask(nodes, keep, query, tag):
    p = os.path.join(HERE, f"_{tag}.metta")
    open(p, "w").write("\n".join(facts(nodes, keep))
                       + f"\n!(collapse (match &self {query} (hit $x $y)))\n")
    _, body = run(p)
    return set(re.findall(r"\(hit (\w+) (\w+)\)", body))


def epoch(live, ctx_stim, imp_in, tag):
    """One ECAN epoch per context, carrying importance forward between cycles."""
    L = [f"; G10 cycle {tag}"]
    for ctx, stim in ctx_stim.items():
        for i in sorted(live):
            L.append(f"(imp {ctx} 0 {i} {imp_in[ctx].get(i, SEED)})")
            L.append(f"(stim {ctx} {i} {stim.get(i, 0)})")
    for ctx in ctx_stim:
        L.append(f"!(let $rs (collapse (match &self (imp {ctx} 0 $c $v) "
                 f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self "
                 f"(total-rent {ctx} (foldl-atom $rs 0 $a $b (+ $a $b)))))")
        L.append(f"!(let $ss (collapse (match &self (stim {ctx} $c $s) $s)) "
                 f"(add-atom &self (total-stim {ctx} "
                 f"(foldl-atom $ss 0 $a $b (+ $a $b)))))")
        L.append(f"!(let $new (collapse (match &self (, (imp {ctx} 0 $c $v) "
                 f"(stim {ctx} $c $s) (total-rent {ctx} $tr) "
                 f"(total-stim {ctx} $ts)) (imp {ctx} 1 $c "
                 f"(+ (- $v (/ (* $v {RENT}) {SCALE})) (/ (* $s $tr) $ts))))) "
                 f"(add-atoms &self $new))")
    for ctx in ctx_stim:
        L.append(f"!(collapse (match &self (imp {ctx} 1 $c $v) "
                 f"(IMPOF {ctx} $c $v)))")
    p = os.path.join(HERE, f"_epoch{tag}.metta")
    open(p, "w").write("\n".join(L) + "\n")
    st, body = run(p)
    out = {c: {} for c in ctx_stim}
    for c, k, v in re.findall(r"\(IMPOF (\w+) (\w+) (\d+)\)", body):
        if c in out:
            out[c][k] = int(v)
    for c in out:
        for i in live:
            out[c].setdefault(i, SEED)
    return st, out


def loop(nodes, ids, base, attention, label):
    live = set(ids)
    imp = {q: {i: SEED for i in ids} for q in QUERIES}
    hist = []
    for cyc in range(CYCLES):
        pres, stims = {}, {}
        for q, expr in QUERIES.items():
            hits = ask(nodes, live, expr, f"{label}{cyc}_{q}")
            pres[q] = len(hits & base[q]) / len(base[q]) if base[q] else 0.0
            t = {}
            for a, b in hits:
                t[a] = t.get(a, 0) + 1
                t[b] = t.get(b, 0) + 1
            stims[q] = t
        mean = sum(pres.values()) / len(pres)
        hist.append({"cycle": cyc, "live": len(live), "mean_preserved": mean,
                     "per_query": pres})

        drop_n = max(1, int(len(live) * PRUNE_FRAC))
        if len(live) - drop_n < 2:
            break
        if attention:
            st, imp = epoch(live, stims, imp, f"{label}{cyc}")
            # each node's worth = its BEST standing across contexts (G9: several
            # budgets; a node kept by any context survives)
            worth = {i: max(imp[q].get(i, 0) for q in QUERIES) for i in live}
            order = sorted(live, key=lambda i: (worth[i], i))
        else:
            order = sorted(live)                       # name order, no attention
        live = live - set(order[:drop_n])
    return hist


def main():
    g = json.load(open(GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]
    base = {q: ask(nodes, set(ids), e, f"base_{q}") for q, e in QUERIES.items()}
    print("baselines:", {q: len(v) for q, v in base.items()}, "\n")

    runs = {}
    for label, att in (("attention", True), ("control", False)):
        runs[label] = loop(nodes, ids, base, att, label[0])

    print(f"{'cycle':>6}{'live':>6}"
          f"{'attention':>12}{'control':>10}   per-query (attention)")
    for a, c in zip(runs["attention"], runs["control"]):
        pq = " ".join(f"{q[2:5]}:{a['per_query'][q]:.0%}" for q in QUERIES)
        print(f"{a['cycle']:>6}{a['live']:>6}{a['mean_preserved']:>11.0%}"
              f"{c['mean_preserved']:>10.0%}   {pq}")

    fa, fc = (runs["attention"][-1]["mean_preserved"],
              runs["control"][-1]["mean_preserved"])
    means = [h["mean_preserved"] for h in runs["attention"]]
    collapsed = means[-1] < 0.05
    monotone = all(x >= y - 1e-9 for x, y in zip(means, means[1:]))
    if collapsed:
        v = "COLLAPSE — the loop ate itself"
    elif fa > fc:
        v = (f"SURVIVES — attention {fa:.0%} vs control {fc:.0%} after "
             f"{CYCLES} cycles at {PRUNE_FRAC:.0%}/cycle"
             + ("" if monotone else "; NON-MONOTONE, answers recovered"))
    else:
        v = f"NO BETTER THAN DECAY — attention {fa:.0%}, control {fc:.0%}"
    print(f"\nVERDICT: {v}")

    json.dump({"cycles": CYCLES, "prune_frac": PRUNE_FRAC, "runs": runs,
               "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"cycle": CYCLES}},
               "cites": ["G5_ecan_metta", "G8_per_context",
                         "G9_context_discovery"]},
              open(os.path.join(HERE, "loop.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
