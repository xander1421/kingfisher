#!/usr/bin/env python3
"""H253 F2 — is G92's 14.1x margin concentrated in WN18RR's leaked triples?
ATTACKER-1, 2026-08-19.

Trains G92's models ONCE with its own pinned SEED/DIM/EPOCHS and its own
`eval_test_hybrid`, then evaluates the SAME trained models and the SAME routing
on three test populations: full, the 1,096 same-pair-leaked triples, and the
2,038 clean ones. Nothing is retrained between arms, so the arms differ ONLY in
which triples the model is asked about -- the same construction H247 used on
FB15k-237, where the system went 0.5318 leaked against 0.1503 clean.
"""
from __future__ import annotations
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "G92_wn18rr_hybrid"))
import run as G                                        # noqa: E402

t0 = time.time()
train_raw = G.load_split_txt(G.CORPUS_WN / "train.txt")
valid_raw = G.load_split_txt(G.CORPUS_WN / "valid.txt")
test_raw = G.load_split_txt(G.CORPUS_WN / "test.txt")
e2i, r2i, entities, relations = G.build_vocab([train_raw, valid_raw, test_raw])
nent, npred = len(entities), len(relations)
train_tri = G.encode_triples(train_raw, e2i, r2i)
valid_tri = G.encode_triples(valid_raw, e2i, r2i)
test_tri = G.encode_triples(test_raw, e2i, r2i)

all_true_sp, all_true_po = defaultdict(list), defaultdict(list)
for p, s, o in train_tri + valid_tri + test_tri:
    all_true_sp[(s, p)].append(o)
    all_true_po[(p, o)].append(s)

pairs = set()
for _p, s, o in train_tri:
    pairs.add((s, o)); pairs.add((o, s))
leaked = [t for t in test_tri if (t[1], t[2]) in pairs]
clean = [t for t in test_tri if (t[1], t[2]) not in pairs]

rot_m = G.train_rotate_wn(train_tri, nent, npred, epochs=G.EPOCHS, lr=G.LR,
                          reg=G.REG, seed=G.SEED)
cx_m = G.train_complex_wn(train_tri, nent, npred, epochs=G.EPOCHS, lr=G.LR,
                          reg=1e-4, seed=G.SEED)
routing = G.eval_validation(valid_tri, rot_m, cx_m, all_true_sp, all_true_po, npred)

i2r = {v: k for k, v in r2i.items()}
arms = {}
per_rel = {}
for label, subset in (("full", test_tri), ("leaked", leaked), ("clean", clean)):
    mrr, h1, h3, h10, choices, rel_ranks = G.eval_test_hybrid(
        subset, rot_m, cx_m, routing, all_true_sp, all_true_po)
    arms[label] = {"n": len(subset), "mrr": round(mrr, 6),
                   "hits1": round(h1, 6), "hits10": round(h10, 6),
                   "n_queries": sum(len(v) for v in rel_ranks.values()),
                   "model_choices": dict(choices)}
    # Per-relation MRR is FREE -- `eval_test_hybrid` already returns rel_ranks and
    # the first version of this probe threw it away after counting its length.
    per_rel[label] = {i2r[p]: {"n_queries": len(rs),
                               "mrr": round(sum(1.0 / r for r in rs) / len(rs), 6),
                               "routed_to": routing[p][0]}
                      for p, rs in rel_ranks.items() if rs}
    print("OBS ARM_" + label + " " + json.dumps(arms[label]), flush=True)

# WHICH RELATIONS THE LEAK IS MADE OF. Without this the finding is a number with
# no mechanism, and a number with no mechanism is how a correct figure gets
# attached to the wrong cause.
comp = {}
for p, s, o in test_tri:
    r = i2r[p]
    d = comp.setdefault(r, {"leaked": 0, "clean": 0, "routed_to": routing[p][0]})
    d["leaked" if (s, o) in pairs else "clean"] += 1
for r, d in comp.items():
    d["leak_pct"] = round(100.0 * d["leaked"] / (d["leaked"] + d["clean"]), 1)
print("OBS RELATIONS " + json.dumps(comp))

NULL_FULL, NULL_LEAKED, NULL_CLEAN = 0.0256, 0.0018, 0.0383   # H253 probe_null.py
obs = {
    "arms": arms,
    "nulls_from_probe_null_py": {"full": NULL_FULL, "leaked": NULL_LEAKED,
                                 "clean": NULL_CLEAN},
    "margin_full": round(arms["full"]["mrr"] - NULL_FULL, 6),
    "margin_clean": round(arms["clean"]["mrr"] - NULL_CLEAN, 6),
    "multiple_full": round(arms["full"]["mrr"] / NULL_FULL, 2),
    "multiple_clean": round(arms["clean"]["mrr"] / NULL_CLEAN, 2),
    "g92_published_mrr": 0.3611,
    "reproduces_g92": abs(arms["full"]["mrr"] - 0.3611) < 5e-4,
    "per_relation_mrr": per_rel,
    "relation_leak_composition": comp,
    "elapsed_sec": round(time.time() - t0, 2),
}
print("OBS SYS " + json.dumps(obs))
json.dump(obs, open(os.path.join(HERE, "system.json"), "w"), indent=1, sort_keys=True)
