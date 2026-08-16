#!/usr/bin/env python3
"""S10 — does S5's "exactly lossless" pre-filter generalise past one pattern?

S5 tested exactly one query shape: two bound slots, one free variable, no
repeated variables, no nesting -- and reported recall 1.0 with zero false
positives.  Its own caveat section says the other shapes "will be genuinely
approximate" but never measured them.  The whole rung-2 design rests on that
untested generalisation, so measure it.

The algebra, worked out before running (the run either confirms or kills it):

  A triple is T_d = sign(b_d + u_d) where b_d is the sum of the m BOUND
  role-filler products and u_d the sum of the (3-m) unbound ones.
  The query is Q_d = b_d.  A matching triple scores sum_d Q_d * sign(Q_d+u_d).

  m=2: Q_d in {-2,0,2}, u_d in {-1,+1}.  |Q_d| beats |u_d| whenever Q_d != 0,
       so the sign always follows Q.  score = 2 * nnz(Q).      EXACT
  m=3: u_d = 0, Q_d in {-3,-1,1,3}.  score = sum_d |Q_d|.      EXACT
  m=1: Q_d in {-1,+1}, u_d in {-2,0,+2}.  When u_d opposes Q_d the sign flips
       and that dimension contributes -1.  Data dependent.     APPROXIMATE

So the prediction is that the S5 headline extends to every 2-bound pattern and
to fully-ground lookups, and collapses for 1-bound patterns.  If that holds,
the useful statement is not "the pre-filter is exact" but "the pre-filter is
exact iff the bound slots outvote the free ones".

Also measured: Zipf-skewed data (S5 used uniform, which is the easy case) and
a repeated-variable pattern (p ?x ?x), which this encoding cannot express as a
query vector at all and must degrade to 1-bound plus a CPU equality filter.

Usage: ./.venv/bin/python patterns.py [D]
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdcore                                   # noqa: E402

N_TRIPLES = 100_000
N_QUERIES = 100
KS = (10, 50, 100, 500, 1000, 5000)

# name -> (bound slots, predicted-exact, threshold rule)
CLASSES = (
    ("C1_(p s ?o)", (hdcore.PRED, hdcore.SUBJ), True,  "2*nnz"),
    ("C2_(p ?s o)", (hdcore.PRED, hdcore.OBJ),  True,  "2*nnz"),
    ("C3_(? s o)",  (hdcore.SUBJ, hdcore.OBJ),  True,  "2*nnz"),
    ("C4_(p ?s ?o)", (hdcore.PRED,),            False, "none"),
    ("C5_(? s ?o)", (hdcore.SUBJ,),             False, "none"),
    ("C6_(p s o)",  (hdcore.PRED, hdcore.SUBJ, hdcore.OBJ), True, "sum|Q|"),
)


def build(D, zipf_a=None):
    rng = np.random.default_rng(hdcore.SEED)
    R, P, S, O = hdcore.codebooks(rng, D)
    tp, ts, to = hdcore.triples(rng, N_TRIPLES, zipf_a=zipf_a)
    T = hdcore.encode(R, P, S, O, tp, ts, to, D)
    return rng, (R, P, S, O), (tp, ts, to), T


def slot_arrays(tp, ts, to):
    return {hdcore.PRED: tp, hdcore.SUBJ: ts, hdcore.OBJ: to}


def run_class(name, bound, predicted_exact, rule, D, books, ids, T, rng):
    R, P, S, O = books
    tp, ts, to = ids
    cols = slot_arrays(tp, ts, to)
    codes = {hdcore.PRED: P, hdcore.SUBJ: S, hdcore.OBJ: O}

    # ground truth: rows agreeing with the query on every bound slot
    key_cols = [cols[b] for b in bound]
    truth = {}
    for row, key in enumerate(zip(*(c.tolist() for c in key_cols))):
        truth.setdefault(key, []).append(row)

    keys = sorted(truth)
    n_q = min(N_QUERIES, len(keys))
    pick = rng.choice(len(keys), size=n_q, replace=False)
    qkeys = [keys[i] for i in sorted(pick.tolist())]

    Q = np.zeros((n_q, D), dtype=np.int8)
    for i, key in enumerate(qkeys):
        acc = np.zeros(D, dtype=np.int8)
        for slot, val in zip(bound, key):
            acc += R[slot] * codes[slot][val]
        Q[i] = acc

    scores = hdcore.score(Q, T)

    if rule == "2*nnz":
        thr = 2 * np.count_nonzero(Q, axis=1)
    elif rule == "sum|Q|":
        thr = np.abs(Q.astype(np.int32)).sum(axis=1)
    else:
        thr = None

    exact_ok = True
    fp_total = matches_total = 0
    match_min, match_max, nonmatch_max = [], [], []
    recalls_thr = []
    shortlist = []
    by_k = {k: [] for k in KS}

    for qi, key in enumerate(qkeys):
        gold = np.asarray(truth[key])
        row = scores[qi]
        gs = row[gold]
        matches_total += len(gold)
        match_min.append(int(gs.min()))
        match_max.append(int(gs.max()))

        mask = np.ones(len(row), dtype=bool)
        mask[gold] = False
        nonmatch_max.append(int(row[mask].max()))

        if thr is not None:
            t = int(thr[qi])
            if not (gs == t).all():
                exact_ok = False
            above = int((row >= t).sum())
            shortlist.append(above)
            fp_total += above - int((gs >= t).sum())
            recalls_thr.append(float((gs >= t).sum()) / len(gold))

        for k in KS:
            if k >= len(row):
                continue
            cand = np.argpartition(-row, k)[:k]
            hit = np.isin(cand, gold).sum()
            by_k[k].append(float(hit) / len(gold))

    answers = [len(truth[k]) for k in qkeys]
    res = {
        "class": name,
        "bound_slots": len(bound),
        "predicted_exact": predicted_exact,
        "threshold_rule": rule,
        "n_queries": n_q,
        "answers_per_query": {"min": min(answers), "max": max(answers),
                              "mean": round(sum(answers) / len(answers), 2),
                              "pct_of_store": round(
                                  100 * sum(answers) / len(answers) / N_TRIPLES, 3)},
        "match_score": {"min": min(match_min), "max": max(match_max),
                        "constant": min(match_min) == max(match_max)},
        "worst_nonmatch": max(nonmatch_max),
        "recall_at_k": {k: round(float(np.mean(v)), 4)
                        for k, v in by_k.items() if v},
    }
    if thr is not None:
        res["threshold"] = {
            "every_match_hits_threshold_exactly": exact_ok,
            "recall_at_threshold": round(float(np.mean(recalls_thr)), 4),
            "false_positives_total": fp_total,
            "true_matches_total": matches_total,
            "shortlist_mean": round(float(np.mean(shortlist)), 1),
            "shortlist_max": int(max(shortlist)),
            "candidate_reduction_mean": round(N_TRIPLES / max(1, np.mean(shortlist)), 1),
        }
    return res


def repeated_variable(D, books, ids, T, rng):
    """(p ?x ?x) -- subject and object must be the SAME entity.

    This encoding has no way to express "these two slots are equal" in a query
    vector: the constraint is between two free slots, not between a slot and a
    constant.  The honest fallback is to pre-filter on the predicate alone
    (a 1-bound query, i.e. approximate) and let the CPU stage enforce s == o.
    Measured here: how much work that actually pushes onto the CPU.
    """
    R, P, S, O = books
    tp, ts, to = ids
    same = np.flatnonzero(ts == to)
    if len(same) == 0:
        return {"note": "no (p x x) triples in the sample"}

    preds = sorted(set(tp[same].tolist()))
    Q = np.stack([R[hdcore.PRED] * P[p] for p in preds]).astype(np.int8)
    scores = hdcore.score(Q, T)

    rows = []
    for qi, p in enumerate(preds):
        gold = np.asarray(sorted(set(same.tolist()) & set(np.flatnonzero(tp == p).tolist())))
        if len(gold) == 0:
            continue
        row = scores[qi]
        # predicate-only prefilter: everything sharing the predicate is a
        # candidate, and the CPU must check s==o on all of them
        pred_rows = int((tp == p).sum())
        best = np.argsort(-row)
        # how deep must the shortlist go to contain every true answer
        rank = {int(r): i for i, r in enumerate(best.tolist())}
        depth = max(rank[int(g)] for g in gold) + 1
        rows.append({"pred": int(p), "answers": len(gold),
                     "rows_sharing_pred": pred_rows,
                     "depth_for_full_recall": depth,
                     "depth_pct_of_store": round(100 * depth / N_TRIPLES, 2)})
    return {
        "pattern": "(p ?x ?x)",
        "expressible_as_query_vector": False,
        "fallback": "1-bound prefilter on predicate + CPU equality filter",
        "per_predicate": rows,
        "worst_depth_pct_of_store": round(
            max(r["depth_pct_of_store"] for r in rows), 2) if rows else None,
    }


def main():
    D = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    out = {"config": {"D": D, "n_triples": N_TRIPLES, "n_queries": N_QUERIES,
                      "seed": hdcore.SEED}}

    for label, zipf_a in (("uniform", None), ("zipf_a1.0", 1.0)):
        rng, books, ids, T = build(D, zipf_a)
        results = []
        for name, bound, pe, rule in CLASSES:
            r = run_class(name, bound, pe, rule, D, books, ids, T, rng)
            results.append(r)
            thr = r.get("threshold", {})
            print(f"[{label}] {name:<14} m={r['bound_slots']} "
                  f"ans/q={r['answers_per_query']['mean']:>8.1f} "
                  f"exact={thr.get('every_match_hits_threshold_exactly', '-')!s:<5} "
                  f"recall@thr={thr.get('recall_at_threshold', '-')!s:<6} "
                  f"fp={thr.get('false_positives_total', '-')!s:<7} "
                  f"r@100={r['recall_at_k'].get(100, '-')}", flush=True)
        out[label] = results
        if label == "uniform":
            out["repeated_variable"] = repeated_variable(D, books, ids, T, rng)
        del T

    Path("patterns.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote patterns.json")


if __name__ == "__main__":
    main()
