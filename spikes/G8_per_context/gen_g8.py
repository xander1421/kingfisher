#!/usr/bin/env python3
"""G8 — per-context attention, the form DAS ships. Tested as a 2x2.

G7 established that a conservative attention field is zero-sum across tasks:
stimulating what one query touches necessarily demotes everything else, so a
single global field serves one query at the cost of the others. DAS avoids this
with `select_hebbian_network(context)` — a map of Hebbian networks keyed by
context (`AttentionBrokerServer.cc:369-375`). G8 builds that shape.

Importance becomes `(imp <context> <epoch> <node> <v>)`. Two contexts, each
stimulated by its own query.

THE TEST IS A 2x2, not a single number, because "it preserves everything" and
"it preserves the right things" look identical from one cell:

                        test RED-query    test INVALID-query
    prune by ctx_RED         HIGH               low
    prune by ctx_INVALID      low               HIGH

A **diagonal** pattern is the signal — each context keeps what its own query
needs and discards what it does not. If both rows look alike, contexts are
decorative and the honest report is that they are decorative. If both rows are
high, pruning is not actually removing anything load-bearing and the experiment
is degenerate.

Controls carried forward: `arbitrary` (name order) is the null, and `keep_low`
is the two-sided arm that turned G6 and G7 from null results into mechanisms.
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

CONTEXTS = {
    "ctxRED":     "(, (cites $x $y) (verdict $y RED))",
    "ctxINVALID": "(, (cites $x $y) (verdict $y INVALID))",
}
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


def touched(nodes, query, tag):
    p = os.path.join(HERE, f"stim_{tag}.metta")
    open(p, "w").write("\n".join(facts(nodes))
                       + f"\n!(collapse (match &self {query} ($x $y)))\n")
    st, body = run(p)
    t = {}
    for a, b in re.findall(r"\((\w+) (\w+)\)", body):
        t[a] = t.get(a, 0) + 1
        t[b] = t.get(b, 0) + 1
    return st, t


def ecan_multi(ids, stims):
    """One program, ALL contexts. Each context is an independent conservative
    field; they share the space but never each other's atoms."""
    L = ["; G8 — per-context ECAN, DAS's select_hebbian_network shape"]
    for ctx, stim in stims.items():
        for i in sorted(ids):
            L.append(f"(imp {ctx} 0 {i} {SEED})")
            L.append(f"(stim {ctx} {i} {stim.get(i, 0)})")
    for ctx in stims:
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
    for ctx in stims:
        L.append(f"!(collapse (match &self (imp {ctx} {EPOCHS} $c $v) ($c $v)))")
        # conservation control per context, per G5
        L.append(f"!(let $vs (collapse (match &self (imp {ctx} {EPOCHS} $c $v) $v)) "
                 f"(< (foldl-atom $vs 0 $a $b (+ $a $b)) {int(SEED*len(ids)*1.05)}))")
    p = os.path.join(HERE, "ecan_g8.metta")
    open(p, "w").write("\n".join(L) + "\n")
    st, body = run(p)
    lines = [l for l in body.strip().split("\n") if "(" in l and "at-risk" not in l]
    out, cons = {}, []
    for ctx, ln in zip(stims, [l for l in lines if l.count("(") > 3]):
        out[ctx] = {k: int(v) for k, v in re.findall(r"\((\w+) (\d+)\)", ln)}
    cons = re.findall(r"\b(True|False)\b", body)
    return st, out, cons


def ask(nodes, keep, query, tag):
    p = os.path.join(HERE, f"q_{tag}.metta")
    open(p, "w").write("\n".join(facts(nodes, keep))
                       + f"\n!(collapse (match &self {query} (hit $x $y)))\n")
    _, body = run(p)
    return set(re.findall(r"\(hit (\w+) (\w+)\)", body))


def main():
    g = json.load(open(GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]

    stims = {}
    for ctx, q in CONTEXTS.items():
        st, t = touched(nodes, q, ctx)
        stims[ctx] = t
        print(f"{ctx:<12} {q}\n             status {st}  touched {len(t)}/{len(ids)}")

    st, imp, cons = ecan_multi(ids, stims)
    print(f"\nper-context ECAN status {st}   conservation controls {cons}")
    for ctx in imp:
        for i in ids:
            imp[ctx].setdefault(i, 0)

    base = {ctx: ask(nodes, set(ids), q, f"base_{ctx}")
            for ctx, q in CONTEXTS.items()}
    print("\nbaselines on the full graph:")
    for ctx, b in base.items():
        print(f"  {ctx:<12} {len(b)} findings")

    keep_n = len(ids) - len(ids) // 2
    arms = {f"prune_by_{c}": sorted(ids, key=lambda i: (-imp[c][i], i))[:keep_n]
            for c in imp}
    arms["keep_low_ctxINVALID"] = sorted(
        ids, key=lambda i: (imp["ctxINVALID"][i], i))[:keep_n]
    arms["arbitrary"] = sorted(ids)[:keep_n]

    print(f"\nforgetting {len(ids)//2} of {len(ids)} nodes (50%)\n")
    hdr = f"  {'prune by':<24}" + "".join(f"{c:>16}" for c in CONTEXTS)
    print(hdr)
    grid = {}
    for name, keep in arms.items():
        row = {}
        for ctx, q in CONTEXTS.items():
            f = ask(nodes, set(keep), q, f"{name}_{ctx}")
            row[ctx] = len(f & base[ctx]) / len(base[ctx]) if base[ctx] else 0.0
        grid[name] = row
        print(f"  {name:<24}" + "".join(f"{row[c]:>15.0%}" for c in CONTEXTS))

    d1 = grid["prune_by_ctxRED"]["ctxRED"]
    o1 = grid["prune_by_ctxRED"]["ctxINVALID"]
    d2 = grid["prune_by_ctxINVALID"]["ctxINVALID"]
    o2 = grid["prune_by_ctxINVALID"]["ctxRED"]
    arb = max(grid["arbitrary"].values())
    diagonal = (d1 > o1) and (d2 > o2)
    beats_null = (d1 > arb) and (d2 > arb)
    if diagonal and beats_null:
        v = "DIAGONAL — each context preserves its own query and not the other's"
    elif beats_null and not diagonal:
        v = "NON-SPECIFIC — both contexts beat the null but do not separate"
    elif not beats_null:
        v = "NO SIGNAL — no better than pruning by name order"
    else:
        v = "INVERTED"
    print(f"\nVERDICT: {v}")

    json.dump({"contexts": CONTEXTS, "grid": grid, "conservation": cons,
               "baselines": {k: sorted(v) for k, v in base.items()},
               "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"arm": list(arms)}},
               "cites": ["G5_ecan_metta", "G6_forgetting", "G7_query_attention"]},
              open(os.path.join(HERE, "g8.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
