#!/usr/bin/env python3
"""G6 — attention-driven forgetting, with a two-sided control.

G5 computed importance. This asks what importance is FOR: deciding what the
graph keeps. That is the self-evolving claim — a graph that shrinks itself and
still answers the same questions.

The question the pruned graph must still answer is G1's, because G1's answer is
independently verified: three spikes carrying a GREEN verdict (B1, N1, Q1) rest
on W1, which is INVALID.

    !(match &self (, (cites $x $y) (verdict $y INVALID)) (at-risk $x $y))

TWO-SIDED CONTROL, and both sides must behave or the result is meaningless:

  KEEP-HIGH   drop the lowest-importance nodes   -> findings must SURVIVE
  KEEP-LOW    drop the highest-importance nodes  -> findings must DIE
  ARBITRARY   drop the same NUMBER, chosen by name order, no importance
              -> the honest null. If arbitrary pruning preserves as much as
                 attention-driven pruning, attention did nothing and the
                 result is that it did nothing.

MeTTa has no RNG, so "arbitrary" is alphabetical — deterministic, reproducible,
and not chosen to flatter. The KEEP-LOW arm exists because a one-sided control
cannot distinguish "attention works" from "this graph is robust to any pruning".
That is the S72/N1c lesson: a negative control bounds resolution, only a
positive control establishes the instrument sees the effect at all.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
GRAPH = os.path.join(SPIKES, "G1_graph_ingest", "graph.json")
ECAN = os.path.join(SPIKES, "G5_ecan_metta", "ecan.metta")
RUNNER = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")

QUERY = "!(collapse (match &self (, (cites $x $y) (verdict $y INVALID)) (at-risk $x $y)))"


def run(path, fuel=20_000_000):
    out = subprocess.run([RUNNER, path, str(fuel)], capture_output=True, text=True).stdout
    status = re.search(r"^status\s+(\S+)", out, re.M)
    fuel_used = re.search(r"^fuel_used\s+(\d+)", out, re.M)
    body = out.split("--- results ---", 1)[-1]
    return (status.group(1) if status else "?",
            int(fuel_used.group(1)) if fuel_used else -1, body)


def importance():
    """Run G5's ECAN and read the final importance per node."""
    _, _, body = run(ECAN)
    pairs = re.findall(r"\((\w+) (\d+)\)", body)
    # last result line holds the (id value) list; the totals are bare ints
    return {k: int(v) for k, v in pairs}


def emit(name, keep, graph):
    """A pruned graph plus the verified query."""
    lines = [f"; G6 {name}: {len(keep)} of {len(graph['nodes'])} nodes kept"]
    for n in graph["nodes"]:
        if n["id"] not in keep:
            continue
        lines.append(f'(spike {n["id"]})')
        if n["verdict"]:
            lines.append(f'(verdict {n["id"]} {n["verdict"]})')
        for c in n["cites"]:
            if c in keep:                       # an edge needs both endpoints
                lines.append(f'(cites {n["id"]} {c})')
    lines.append(QUERY)
    p = os.path.join(HERE, f"{name}.metta")
    open(p, "w").write("\n".join(lines) + "\n")
    return p


def findings(body):
    return set(re.findall(r"\(at-risk (\w+) (\w+)\)", body))


def main():
    graph = json.load(open(GRAPH))
    ids = [n["id"] for n in graph["nodes"]]
    imp = {k: v for k, v in importance().items() if k in set(ids)}
    missing = [i for i in ids if i not in imp]
    if missing:
        print(f"WARNING {len(missing)} nodes had no importance: {missing[:5]}")
    for i in missing:
        imp[i] = 0

    # baseline on the FULL graph
    full = emit("full", set(ids), graph)
    st, fu, body = run(full)
    base = findings(body)
    print(f"baseline   {len(ids)} nodes  status {st}  fuel {fu:,}  "
          f"findings {len(base)}")
    print(f"  {sorted(base)}\n")

    drop = len(ids) // 2          # forget half the graph
    keep_n = len(ids) - drop
    by_imp = sorted(ids, key=lambda i: (-imp[i], i))
    arms = {
        "keep_high": set(by_imp[:keep_n]),                    # drop lowest imp
        "keep_low":  set(sorted(ids, key=lambda i: (imp[i], i))[:keep_n]),
        "arbitrary": set(sorted(ids)[:keep_n]),               # name order
    }

    print(f"forgetting {drop} of {len(ids)} nodes (50%)\n")
    print(f"  {'arm':<12}{'kept':>5}{'status':>9}{'fuel':>12}{'found':>7}"
          f"{'preserved':>11}")
    res = {}
    for name, keep in arms.items():
        st, fu, body = run(emit(name, keep, graph))
        f = findings(body)
        pres = len(f & base) / len(base) if base else 0.0
        res[name] = {"kept": len(keep), "status": st, "fuel": fu,
                     "findings": len(f), "preserved": pres}
        print(f"  {name:<12}{len(keep):>5}{st:>9}{fu:>12,}{len(f):>7}"
              f"{pres:>10.0%}")

    hi, lo, ar = (res["keep_high"]["preserved"], res["keep_low"]["preserved"],
                  res["arbitrary"]["preserved"])
    print()
    if hi > ar and hi > lo:
        v = "SIGNAL — attention-driven forgetting preserves more than arbitrary"
    elif hi == ar:
        v = ("NO SIGNAL — attention preserves exactly what arbitrary does; "
             "importance added nothing")
    else:
        v = "INVERTED — arbitrary or keep-low beat attention"
    print(f"VERDICT: {v}")

    json.dump({"baseline_findings": sorted(base), "drop": drop, "arms": res,
               "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"arm": list(arms)}},
               "cites": ["G1_graph_ingest", "G5_ecan_metta"]},
              open(os.path.join(HERE, "forget.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
