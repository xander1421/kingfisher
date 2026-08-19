#!/usr/bin/env python3
"""H253 F1 — H247's test transferred to WN18RR. ATTACKER-1, 2026-08-19.

Is G105's 0.0256 null blind to the 34.97% same-pair leak in WN18RR's official
split, the way FB15k-237's null was blind to its 30.01%? Reuses G105's own
`pack` / `build_filter_index` / `evaluate_frequency_null` UNMODIFIED -- the
attack must drive the instrument under test, not a retyped copy of it.

TUPLE ORDER IS RESOLVED FROM THE CODE, NEVER BY EYE. `load_split` returns text
`(s, r, o)`; `pack` interns AND transposes to `(p, s, o)`. Every arm below reads
`(t[1], t[2])` as `(s, o)` on PACKED triples for exactly that reason.
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "G105_wn18rr_frequency_null"))
import null_wn as W                                   # noqa: E402

t0 = time.time()
tr_t, va_t, te_t = (W.load_split(n) for n in ("train.txt", "valid.txt", "test.txt"))
train, valid, test, npred, nent = W.pack(tr_t, va_t, te_t)
true_sp, true_po = W.build_filter_index(train + valid + test)

pairs = set()
for _p, s, o in train:
    pairs.add((s, o)); pairs.add((o, s))
leaked = [t for t in test if (t[1], t[2]) in pairs]
clean = [t for t in test if (t[1], t[2]) not in pairs]

base = W.evaluate_frequency_null(test, train, true_sp, true_po, nent)
lk = W.evaluate_frequency_null(leaked, train, true_sp, true_po, nent)
cl = W.evaluate_frequency_null(clean, train, true_sp, true_po, nent)

# THE DECISIVE ARM: delete every leak-creating edge from what the null LEARNS
# from, and hold the EVALUATION POPULATION fixed. If the null does not move,
# no leak of this kind can reach it and its stability is the model's form.
test_pairs = set()
for _p, s, o in test:
    test_pairs.add((s, o)); test_pairs.add((o, s))
train_noleak = [t for t in train if (t[1], t[2]) not in test_pairs]
noleak = W.evaluate_frequency_null(test, train_noleak, true_sp, true_po, nent)

obs = {
    "n_test": len(test), "n_leaked": len(leaked), "n_clean": len(clean),
    "leak_rate": round(len(leaked) / len(test), 4),
    "null_mrr_full_test": base["mrr"],
    "null_mrr_leaked_subset": lk["mrr"], "null_mrr_clean_subset": cl["mrr"],
    "n_train": len(train),
    "n_train_leak_edges_removed": len(train) - len(train_noleak),
    "null_mrr_same_test_leakfree_train": noleak["mrr"],
    "null_delta_when_leak_deleted_from_train": round(noleak["mrr"] - base["mrr"], 6),
    "null_delta_population_change": round(cl["mrr"] - base["mrr"], 6),
    "g105_published_null": 0.0256,
    "reproduces_g105": abs(base["mrr"] - 0.0256) < 5e-4,
    "elapsed_sec": round(time.time() - t0, 2),
}
print("OBS NULL " + json.dumps(obs))
json.dump(obs, open(os.path.join(HERE, "null.json"), "w"), indent=1, sort_keys=True)
