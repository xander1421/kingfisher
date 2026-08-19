#!/usr/bin/env python3
"""H247 F1/F2 — is the null's insensitivity to the same-pair leak a MEASUREMENT
or a property of its form? ATTACKER-1, 2026-08-19.

Reuses G104's `prior_scores`/`evaluate_prior` and G34's loader UNCHANGED -- the
attack must run the instrument under test, not a retyped copy of it (family C).
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
for d in (os.path.join(SPIKES, "harness"),
          os.path.join(SPIKES, "G34_length1_and_constants"),
          os.path.join(SPIKES, "G48_pairdisjoint_split"),
          os.path.join(SPIKES, "G104_null_in_the_loop")):
    sys.path.insert(0, d)

import length1_constants as L                     # noqa: E402
from run import prior_scores, evaluate_prior      # noqa: E402  (G104's, unmodified)

t0 = time.time()
_nt, _npred, nent, tri, train, _dev, test = L.load_dataset()
true_sp, true_po = L.build_filter_index(tri)

# G106's own definition of the leak, copied from its `same_pair_leak`.
pairs = {(s, o) for _p, s, o in train} | {(o, s) for _p, s, o in train}
leaked = [t for t in test if (t[1], t[2]) in pairs]
clean = [t for t in test if (t[1], t[2]) not in pairs]

head, tail = prior_scores(train, None)
full = evaluate_prior(test,   head, tail, true_sp, true_po, nent)
lk   = evaluate_prior(leaked, head, tail, true_sp, true_po, nent)
cl   = evaluate_prior(clean,  head, tail, true_sp, true_po, nent)

# F1's DECISIVE ARM, and it is stronger than comparing subsets: rebuild the null
# from a train set with EVERY leak-creating edge removed. If the null's score on
# a FIXED test set is unchanged when the leak is deleted from what it learned
# from, then no leak of this kind can ever reach it -- the insensitivity is the
# model's form, not an observation about this dataset.
test_pairs = {(s, o) for _p, s, o in test} | {(o, s) for _p, s, o in test}
train_noleak = [t for t in train if (t[1], t[2]) not in test_pairs]
h2, t2 = prior_scores(train_noleak, None)
full_noleak = evaluate_prior(test, h2, t2, true_sp, true_po, nent)

obs = {
    "n_test": len(test), "n_leaked": len(leaked), "n_clean": len(clean),
    "leak_rate": round(len(leaked) / len(test), 4),
    "null_mrr_full_test": round(full["mrr"], 6),
    "null_mrr_leaked_subset": round(lk["mrr"], 6),
    "null_mrr_clean_subset": round(cl["mrr"], 6),
    "subset_gap": round(lk["mrr"] - cl["mrr"], 6),
    "n_train": len(train), "n_train_leak_edges_removed": len(train) - len(train_noleak),
    "null_mrr_same_test_leakfree_train": round(full_noleak["mrr"], 6),
    "null_delta_when_leak_deleted_from_train":
        round(full_noleak["mrr"] - full["mrr"], 6),
    "elapsed_sec": round(time.time() - t0, 2),
}
print("OBS F1 " + json.dumps(obs))
json.dump(obs, open(os.path.join(HERE, "f1.json"), "w"), indent=1, sort_keys=True)
