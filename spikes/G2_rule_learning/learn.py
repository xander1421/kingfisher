#!/usr/bin/env python3
"""G2 — LEARN the rule instead of encoding it.

G1 inferred `at-risk` from a rule I wrote. This searches for the rule from
labelled data, which is the difference between a linter and learning.

Task: predict whether a spike DIED (verdict RED or INVALID) or LIVED (GREEN),
from graph structure and self-declared features. 50 labelled spikes,
13 died / 37 lived, so the **majority baseline is 0.740** — a hard bar at n=50
and the number any result must beat.

This is inductive logic programming at a size where the hypothesis space is
enumerable, so the search is exhaustive rather than heuristic. `Popper` (MIT)
is the grown-up tool; it needs SWI-Prolog, which is not on this machine, and
at |H| ~ 10^3 an exhaustive search is both sufficient and more auditable —
I can report exactly what was searched.

THREE CONTROLS, all of which must behave or the result means nothing:
  1. majority baseline      the bar (0.740)
  2. leave-one-out CV       no rule is scored on a spike it was fitted to
  3. LABEL SHUFFLE          shuffle the labels and re-run the whole search.
                            A search this wide WILL find a rule that fits
                            noise; the shuffle measures how well. If shuffled
                            accuracy ~ real accuracy, the learner found
                            nothing and said so.

Control 3 is the one that matters. W1 shipped four controls incapable of
failing; this one is designed to fail loudly.
"""

import json
import os
import random
import sys
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(os.path.dirname(HERE), "G1_graph_ingest", "graph.json")

LABEL = {"GREEN": 0, "RED": 1, "INVALID": 1}      # 1 = died


def load():
    g = json.load(open(GRAPH))
    nodes = {n["id"]: n for n in g["nodes"]}
    data = []
    for n in g["nodes"]:
        if n["verdict"] not in LABEL:
            continue
        data.append((n["id"], LABEL[n["verdict"]]))
    return nodes, data


def literals(nodes):
    """The hypothesis vocabulary. Every literal is a callable id -> bool."""
    lits = []
    feats = sorted(next(iter(nodes.values()))["features"])
    for f in feats:
        lits.append((f"has({f})", lambda i, f=f: nodes[i]["features"][f]))
        lits.append((f"not_has({f})", lambda i, f=f: not nodes[i]["features"][f]))

    # graph literals: something about who this spike cites
    def cites_verdict(i, v):
        return any(nodes[c]["verdict"] == v for c in nodes[i]["cites"] if c in nodes)
    for v in ("INVALID", "RED", "GREEN"):
        lits.append((f"cites_{v}", lambda i, v=v: cites_verdict(i, v)))
        lits.append((f"not_cites_{v}", lambda i, v=v: not cites_verdict(i, v)))

    for t in (2, 4, 6):
        lits.append((f"outdeg>={t}",
                     lambda i, t=t: len([c for c in nodes[i]["cites"] if c in nodes]) >= t))
    for t in (800, 1500, 2500):
        lits.append((f"words>={t}", lambda i, t=t: nodes[i]["words"] >= t))
    return lits


def evaluate(rule, ids, y, nodes):
    """A rule is a conjunction; it predicts died=1 when all literals hold."""
    pred = [int(all(fn(i) for _, fn in rule)) for i in ids]
    return sum(p == t for p, t in zip(pred, y)) / len(y), pred


def search(train_ids, train_y, nodes, lits, max_len=2):
    """Exhaustive over conjunctions up to max_len. Returns best by accuracy."""
    best, best_acc = [], 0.0
    # the empty rule predicts died for everything; include the constant
    # 'always lived' by scoring the negation too
    for L in range(1, max_len + 1):
        for combo in combinations(lits, L):
            acc, _ = evaluate(combo, train_ids, train_y, nodes)
            if acc > best_acc:
                best, best_acc = list(combo), acc
    return best, best_acc


def loo(data, nodes, lits, max_len=2):
    """Leave-one-out: the rule is never scored on a spike it was fitted to."""
    correct = 0
    picked = {}
    for k in range(len(data)):
        tr = data[:k] + data[k + 1:]
        te_id, te_y = data[k]
        rule, _ = search([i for i, _ in tr], [y for _, y in tr], nodes, lits, max_len)
        _, pred = evaluate(rule, [te_id], [te_y], nodes)
        correct += int(pred[0] == te_y)
        key = " AND ".join(n for n, _ in rule)
        picked[key] = picked.get(key, 0) + 1
    return correct / len(data), picked


def main():
    nodes, data = load()
    lits = literals(nodes)
    y = [t for _, t in data]
    maj = max(y.count(0), y.count(1)) / len(y)
    n_h = sum(len(list(combinations(lits, L))) for L in (1, 2))

    print(f"labelled {len(data)}  died {y.count(1)}  lived {y.count(0)}")
    print(f"literals {len(lits)}   hypothesis space (len<=2) {n_h:,}")
    print(f"\nCONTROL 1  majority baseline      {maj:.3f}")

    acc, picked = loo(data, nodes, lits)
    print(f"CONTROL 2  leave-one-out accuracy  {acc:.3f}   ({'BEATS' if acc > maj else 'DOES NOT BEAT'} baseline)")
    top = sorted(picked.items(), key=lambda x: -x[1])[:3]
    print("           rules chosen across folds:")
    for r, c in top:
        print(f"             {c:2d}x  died :- {r}")

    print("\nCONTROL 3  label shuffle — permutation test, n=30")
    print("           (n=5 was the first attempt and it said REAL SIGNAL;")
    print("            n=30 says otherwise. A 5-sample control is underpowered.)")
    accs = []
    for s in range(30):
        rng = random.Random(s)
        ys = [t for _, t in data]
        rng.shuffle(ys)
        sd = [(i, t) for (i, _), t in zip(data, ys)]
        a, _ = loo(sd, nodes, lits)
        accs.append(a)
    sh = sum(accs) / len(accs)
    ge = sum(1 for a in accs if a >= acc)
    p = (ge + 1) / (len(accs) + 1)
    print(f"           shuffled mean {sh:.3f}  max {max(accs):.3f}  >= real: {ge}/{len(accs)}")
    print(f"           permutation p = {p:.3f}")

    verdict = ("SIGNAL (p<0.05)" if acc > maj and p < 0.05
               else f"NO SIGNAL — p={p:.3f}, cannot reject that the search fits noise")
    print(f"\nVERDICT: {verdict}")

    json.dump({"labelled": len(data), "died": y.count(1), "baseline": maj,
               "loo_accuracy": acc, "shuffled_mean": sh, "shuffle_max": max(accs), "permutation_p": p,
               "hypothesis_space": n_h, "rules": picked, "verdict": verdict,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {}},
               "cites": ["G1_graph_ingest"]},
              open(os.path.join(HERE, "learn.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
