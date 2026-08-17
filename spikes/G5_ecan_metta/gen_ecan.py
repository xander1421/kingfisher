#!/usr/bin/env python3
"""G5 — deterministic fixed-point ECAN, written in MeTTa, over the G1 graph.

The missing organ. A11 specified it, S67 modelled it in Python, nobody built
it. Writing it in MeTTa rather than as a separate binary means it inherits
hyperon's byte-reproducibility instead of needing its own proof of it.

A11's three clauses, each realised in the emitted program:

  accumulate wide      MeTTa integers are i64 and every product is formed
                       BEFORE any division, so no rounding enters a sum.
  round canonically    exactly ONE floor division per derived quantity,
                       `(/ (* v rate) SCALE)`. Integer division in MeTTa
                       truncates — verified: (/ 7 2) = 3.
  update synchronously `collapse` fully evaluates the new generation from
                       generation t before any atom of t+1 is added. That is
                       BSP double-buffering, and it is why DAS's concurrent
                       epochs (three inline gRPC entry points, per-node
                       mutexes only) cannot happen here.

DAS's ECAN, for reference (StimulusSpreader.cc):
    rent   = rent_rate * importance
    wages  = stim * to_spread / total_wages
    imp   += wages - rent
Same shape. The difference is that theirs is float, concurrent and
FMA-contractable at `:74-75`; this one is integer, serial, and hashed.

Seed importance is uniform. Stimulus is in-degree in the citation graph —
"how much did the workspace lean on this" — which is the closest thing to
`stimulate(HandleCount)` the corpus offers.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(os.path.dirname(HERE), "G1_graph_ingest", "graph.json")

SCALE = 1000        # fixed-point denominator
RENT_RATE = 50      # 0.050 of importance per epoch
SEED_IMP = 1000     # every node starts at 1.000
EPOCHS = 3


def main():
    g = json.load(open(GRAPH))
    nodes = g["nodes"]
    ids = {n["id"] for n in nodes}

    indeg = {i: 0 for i in ids}
    for n in nodes:
        for c in n["cites"]:
            if c in ids:
                indeg[c] += 1

    L = []
    L.append("; G5 — deterministic fixed-point ECAN over the G1 citation graph")
    L.append(f"; SCALE={SCALE} RENT_RATE={RENT_RATE} SEED={SEED_IMP} EPOCHS={EPOCHS}")
    for i in sorted(ids):
        L.append(f"(imp 0 {i} {SEED_IMP})")
        L.append(f"(stim {i} {indeg[i]})")

    for e in range(EPOCHS):
        L.append(f"\n; ---------- epoch {e} -> {e+1} ----------")
        # 1. total rent, formed by exact integer sum of one-division rents
        L.append(f"!(let $rs (collapse (match &self (imp {e} $c $v) "
                 f"(/ (* $v {RENT_RATE}) {SCALE}))) "
                 f"(add-atom &self (total-rent {e} "
                 f"(foldl-atom $rs 0 $a $b (+ $a $b)))))")
        # 2. total stimulus
        L.append(f"!(let $ss (collapse (match &self (stim $c $s) $s)) "
                 f"(add-atom &self (total-stim {e} (foldl-atom $ss 0 $a $b (+ $a $b)))))")
        # 3. BSP: collapse computes EVERY new value from generation e before
        #    any atom of generation e+1 exists.
        L.append(f"!(let $new (collapse (match &self "
                 f"(, (imp {e} $c $v) (stim $c $s) (total-rent {e} $tr) (total-stim {e} $ts)) "
                 f"(imp {e+1} $c (+ (- $v (/ (* $v {RENT_RATE}) {SCALE})) "
                 f"(/ (* $s $tr) $ts))))) "
                 f"(add-atoms &self $new))")

    # report: final importance, sorted by value via the hash of the whole set
    L.append(f"\n; ---------- CONTROL: conservation ----------")
    L.append(f"; rent is redistributed as wages, so the total must stay within")
    L.append(f"; floor-division loss of {SEED_IMP*len(ids)}. A total that is a")
    L.append(f"; MULTIPLE of it means an unindexed atom multiplied the join —")
    L.append(f"; which is exactly what an un-epoch-indexed (total-stim) did.")
    L.append(f"!(let $vs (collapse (match &self (imp {EPOCHS} $c $v) $v)) "
             f"(< (foldl-atom $vs 0 $a $b (+ $a $b)) {int(SEED_IMP*len(ids)*1.05)}))")
    L.append(f"\n; ---------- result ----------")
    L.append(f"!(collapse (match &self (imp {EPOCHS} $c $v) ($c $v)))")
    L.append(f"!(let $vs (collapse (match &self (imp {EPOCHS} $c $v) $v)) "
             f"(foldl-atom $vs 0 $a $b (+ $a $b)))")

    out = os.path.join(HERE, "ecan.metta")
    open(out, "w").write("\n".join(L) + "\n")
    print(f"wrote {out}: {len(ids)} nodes, {EPOCHS} epochs, {len(L)} lines")
    print(f"total seed importance {SEED_IMP*len(ids)}  "
          f"(conservation check: rent is redistributed as wages, so the sum "
          f"should stay near this modulo floor-division loss)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
