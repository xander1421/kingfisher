#!/usr/bin/env python3
"""H247 F3 — the measurement G106 did not make. ATTACKER-1, 2026-08-19.

G106 attributes +0.1300 to the leak with a DIFFERENCE OF DIFFERENCES across two
splits. This does it INSIDE ONE SPLIT: same train, same code, same filter index,
same seed -- the test set is partitioned into its leaked and non-leaked triples
and the full system is scored on each.

THE SYSTEM IS G34's, CALLED THROUGH THE SAME SEQUENCE `G48/split.py::run` USES,
not a retyped variant. The rule sets are mined ONCE from the shared train set, so
every arm below faces an identical model and differs only in which test triples
it is asked about.
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
for d in (os.path.join(SPIKES, "harness"),
          os.path.join(SPIKES, "G34_length1_and_constants"),
          os.path.join(SPIKES, "G104_null_in_the_loop")):
    sys.path.insert(0, d)

import length1_constants as L                     # noqa: E402
from run import prior_scores, evaluate_prior      # noqa: E402

t0 = time.time()
nt, npred, nent, tri, train, _dev, test = L.load_dataset()
assert (nt, npred, nent) == (272115, 237, 14505), (nt, npred, nent)

pairs = {(s, o) for _p, s, o in train} | {(o, s) for _p, s, o in train}
leaked = [t for t in test if (t[1], t[2]) in pairs]
clean = [t for t in test if (t[1], t[2]) not in pairs]

out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
true_sp, true_po = L.build_filter_index(tri)
sub, inv = L.mine_length1_rules(npred, byp, rev)
ct, ch = L.mine_constant_rules(npred, byp)
r2 = L.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev)

def system(subset):
    return L.evaluate_link_prediction_full(
        subset, out_adj, in_adj, true_sp, true_po, nent,
        rules_2hop=r2, rules_subsume=sub, rules_inverse=inv,
        rules_const_tail=ct, rules_const_head=ch)

head, tail = prior_scores(train, None)
def null(subset):
    return evaluate_prior(subset, head, tail, true_sp, true_po, nent)

arms = {}
for label, subset in (("full", test), ("leaked", leaked), ("clean", clean)):
    s = system(subset); n = null(subset)
    arms[label] = {"n": len(subset), "system_mrr": round(s["mrr"], 6),
                   "null_mrr": round(n["mrr"], 6),
                   "lift": round(s["mrr"] - n["mrr"], 6),
                   "system_hits10": round(s["hits10"], 6)}
    print(f"OBS ARM_{label} " + json.dumps(arms[label]), flush=True)

# G106's published pair, re-stated for the comparison, NOT recomputed here --
# and labelled as quoted so it is never mistaken for a measurement of mine.
quoted = {"pair_disjoint_system": 0.1358, "pair_disjoint_null": 0.1732,
          "pair_disjoint_lift": round(0.1358 - 0.1732, 6),
          "g106_leak_as_lift": 0.130026}
obs = {"arms": arms, "quoted_from_G106_not_measured_here": quoted,
       "within_split_leak_as_lift": round(arms["full"]["lift"] - arms["clean"]["lift"], 6),
       "clean_lift_vs_pairdisjoint_lift":
           round(arms["clean"]["lift"] - quoted["pair_disjoint_lift"], 6),
       "elapsed_sec": round(time.time() - t0, 2)}
print("OBS F3 " + json.dumps(obs))
json.dump(obs, open(os.path.join(HERE, "f3.json"), "w"), indent=1, sort_keys=True)
