#!/usr/bin/env python3
"""G14 — discovery by exact ablation. The first GENERATIVE spike in the series.

Thirteen spikes measured retention. Not one produced a new atom, so "it does not
learn" was never established — only "it does not learn by pruning".

The unused asset: byte-exact replay makes ablation an EXACT experiment. Remove
one atom, re-run, diff the output. Perfect attribution, zero variance, no
confound. Ablation studies exist in ML but are statistical there because a
weight's contribution cannot be isolated. Exhaustive per-unit ablation with
byte-identical replay is not a thing anyone does, and it is what this substrate
is uniquely able to do.

MECHANISM: ablate every node, record which findings change. That change-set is
the node's SIGNATURE.

  identical non-empty signature  -> the nodes are functionally equivalent in
                                    every context tested. That is a CATEGORY
                                    discovered rather than declared, and merging
                                    them emits an atom that was not in the input.
  large signature                -> a load-bearing hub the graph depends on
                                    without naming it.

HYPOTHESIS, stated before running so it can fail:
  (a) nodes with identical NON-EMPTY signatures exist above chance, and
  (b) merging them preserves all findings while shrinking the graph.

THE TRAP, named first: most ablations change nothing, so most signatures are
EMPTY and collide trivially. "Both change nothing" is not equivalence. Empty
signatures are excluded from every equivalence claim and counted separately.

CONTROL: a random-signature null with the same signature-size distribution.
Collisions happen by birthday effect alone; the null measures how many.
"""

import json
import os
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict

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


def ask_all(nodes, keep, tag):
    """All queries in ONE program — one process per ablation, not five."""
    body = "\n".join(facts(nodes, keep))
    qs = "\n".join(f'!(collapse (match &self {e} ({q} $x $y)))'
                   for q, e in QUERIES.items())
    p = os.path.join(HERE, f"_{tag}.metta")
    open(p, "w").write(body + "\n" + qs + "\n")
    out = subprocess.run([RUNNER, p, "40000000"], capture_output=True,
                         text=True).stdout
    tail = out.split("--- results ---", 1)[-1]
    return frozenset(re.findall(r"\((q_\w+) (\w+) (\w+)\)", tail))


def main():
    g = json.load(open(GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]
    full = set(ids)

    base = ask_all(nodes, full, "base")
    print(f"baseline findings across {len(QUERIES)} queries: {len(base)}")

    sigs = {}
    for i, nid in enumerate(ids):
        after = ask_all(nodes, full - {nid}, f"abl{i}")
        # the node's own findings vanish trivially; the SIGNATURE is what
        # changes among findings that do not mention it
        delta = {f for f in (base ^ after) if nid not in f}
        sigs[nid] = frozenset(delta)

    empty = [n for n in ids if not sigs[n]]
    nonempty = [n for n in ids if sigs[n]]
    print(f"empty signatures  {len(empty)}/{len(ids)}  "
          f"(ablation changes nothing beyond the node's own findings)")
    print(f"non-empty         {len(nonempty)}\n")

    groups = defaultdict(list)
    for n in nonempty:
        groups[sigs[n]].append(n)
    real = {k: v for k, v in groups.items() if len(v) > 1}
    n_pairs = sum(len(v) * (len(v) - 1) // 2 for v in real.values())

    print(f"equivalence classes (size>1, non-empty): {len(real)}")
    for k, v in sorted(real.items(), key=lambda x: -len(x[1]))[:6]:
        print(f"  {sorted(v)}   |sig|={len(k)}")

    sizes = Counter(len(sigs[n]) for n in nonempty)
    print(f"\nsignature sizes: {dict(sorted(sizes.items()))}")
    hubs = sorted(nonempty, key=lambda n: -len(sigs[n]))[:5]
    print("largest signatures (load-bearing hubs):")
    for h in hubs:
        print(f"  {h:<6} |sig|={len(sigs[h])}")

    # ---- CONTROL: same signature-size distribution, random contents ----
    universe = sorted({f for s in sigs.values() for f in s})
    rng = random.Random(0xC0FFEE)
    null_pairs = []
    for t in range(200):
        rs = defaultdict(list)
        for n in nonempty:
            rs[frozenset(rng.sample(universe, len(sigs[n])))].append(n)
        null_pairs.append(sum(len(v) * (len(v) - 1) // 2
                              for v in rs.values() if len(v) > 1))
    ge = sum(1 for x in null_pairs if x >= n_pairs)
    p = (ge + 1) / (len(null_pairs) + 1)
    print(f"\nCONTROL random signatures, same size distribution, 200 draws")
    print(f"  observed equivalent pairs {n_pairs}")
    print(f"  null mean {sum(null_pairs)/len(null_pairs):.1f}  "
          f"max {max(null_pairs)}  >= observed {ge}/200   p = {p:.3f}")

    v = ("ABOVE CHANCE — functional equivalence classes are real"
         if n_pairs > 0 and p < 0.05 else
         "NOT ABOVE CHANCE — collisions explained by the birthday effect"
         if n_pairs > 0 else
         "NO CLASSES — every non-empty signature is unique; nothing to abstract")
    print(f"\nVERDICT: {v}")

    json.dump({"baseline": len(base), "empty": len(empty),
               "nonempty": len(nonempty), "classes": len(real),
               "pairs": n_pairs, "p": p,
               "class_members": {str(sorted(v)): len(k) for k, v in real.items()},
               "hubs": {h: len(sigs[h]) for h in hubs}, "verdict": v,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"ablated_node": len(ids)}},
               "cites": ["G1_graph_ingest", "G10_closed_loop"]},
              open(os.path.join(HERE, "ablate.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
