#!/usr/bin/env python3
"""S17 — attacking S11. Does clustered bundling survive a multi-pattern workload?

S11 got 64x compression at recall 1.0000 by bundling triples into buckets and
clustering those buckets by (pred, subj) -- then querying by (pred, subj).
That is close to circular, and S11's own caveat section says so:

    "The clustering key is the query key ... Real workloads mix patterns and
     cannot cluster by all of them at once; the interesting unmeasured
     question is what a multi-pattern workload costs."

This is the measurement. The stake, stated before running:

  If clustered bundling only holds when the layout matches the query pattern,
  then shaping is not a shard-level product -- it is a per-query-class index.
  M4 ("shaping as a paid job class", the differentiator, GAP row 17) would
  then be a much smaller claim, and it would already have lost its other
  justification when S13 showed the sparse/dense crossover was mis-baselined.

Design: bundle once under a fixed layout, then query that ONE store with every
pattern class from S10. A shard is built once and serves many query shapes; the
honest test is one store against many patterns, not one store per pattern.

Layouts compared:
  random          -- no shaping, the control
  by_pred_subj    -- S11's layout, aligned with C1 only
  by_pred_obj     -- aligned with C2 only
  by_subj         -- aligned with C5, partially with C1/C3
  interleaved     -- alternating (pred,subj) and (pred,obj) runs, an honest
                     attempt at a compromise layout serving two patterns

Usage: ./.venv/bin/python multipattern.py [D] [B]
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdcore                                   # noqa: E402

N_TRIPLES = 100_000
N_QUERIES = 100

# (label, bound slots) -- the exact-threshold classes from S10 (m >= 2)
PATTERNS = (
    ("C1_(p s ?o)", (hdcore.PRED, hdcore.SUBJ)),
    ("C2_(p ?s o)", (hdcore.PRED, hdcore.OBJ)),
    ("C3_(? s o)",  (hdcore.SUBJ, hdcore.OBJ)),
    ("C6_(p s o)",  (hdcore.PRED, hdcore.SUBJ, hdcore.OBJ)),
)


def bundle(T, assign, n_buckets):
    D = T.shape[1]
    acc = np.zeros((n_buckets, D), dtype=np.int32)
    np.add.at(acc, assign, T.astype(np.int32))
    return np.where(acc >= 0, 1, -1).astype(np.int8), float((acc == 0).mean())


def layouts(rng, tp, ts, to, B, n_buckets):
    """assignment vectors: triple index -> bucket id."""
    n = len(tp)
    out = {}
    out["random"] = rng.permutation(n) % n_buckets

    for name, keys in (("by_pred_subj", (ts, tp)),
                       ("by_pred_obj", (to, tp)),
                       ("by_subj", (ts,))):
        order = np.lexsort(keys)
        a = np.empty(n, dtype=np.int64)
        a[order] = np.arange(n) // B
        out[name] = a

    # interleaved: sort by (pred,subj), then by (pred,obj), and alternate
    # runs of B/2 from each -- a deliberate attempt at a compromise layout.
    o1, o2 = np.lexsort((ts, tp)), np.lexsort((to, tp))
    half = max(1, B // 2)
    mixed, seen = [], np.zeros(n, dtype=bool)
    i1 = i2 = 0
    while len(mixed) < n:
        for src, idx in ((o1, "1"), (o2, "2")):
            taken = 0
            while taken < half and (i1 if idx == "1" else i2) < n:
                p = i1 if idx == "1" else i2
                r = int(src[p])
                if idx == "1":
                    i1 += 1
                else:
                    i2 += 1
                if not seen[r]:
                    seen[r] = True
                    mixed.append(r)
                    taken += 1
            if len(mixed) >= n:
                break
    a = np.empty(n, dtype=np.int64)
    a[np.asarray(mixed)] = np.arange(n) // B
    out["interleaved"] = a
    return out


def eval_pattern(V, members, Q, thr, truth, qkeys, B, n_triples, div=None):
    scores = hdcore.score(Q, V)
    recalls, checked = [], []
    for qi, key in enumerate(qkeys):
        gold = set(truth[key])
        # same cutoff rule as S11, so the comparison is like-for-like
        t = thr[qi] / (div if div else np.sqrt(B))
        cand = set()
        for b in np.flatnonzero(scores[qi] >= t).tolist():
            cand.update(members[b])
        recalls.append(len(gold & cand) / len(gold))
        checked.append(len(cand))
    return (round(float(np.mean(recalls)), 4), round(float(np.min(recalls)), 4),
            int(sum(1 for r in recalls if r >= 1.0)),
            round(100 * float(np.mean(checked)) / n_triples, 2))


def main():
    D = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    # S17 finding: sqrt(B) is too strict. B is the calibrated divisor.
    DIV = {"sqrt": None, "B": float(B)}[sys.argv[3] if len(sys.argv) > 3 else "B"]
    rng = np.random.default_rng(hdcore.SEED)
    R, P, S, O = hdcore.codebooks(rng, D)
    tp, ts, to = hdcore.triples(rng, N_TRIPLES)
    T = hdcore.encode(R, P, S, O, tp, ts, to, D)
    codes = {hdcore.PRED: P, hdcore.SUBJ: S, hdcore.OBJ: O}
    cols = {hdcore.PRED: tp, hdcore.SUBJ: ts, hdcore.OBJ: to}

    # build every pattern's queries + exact cutoff once
    prepared = {}
    for name, bound in PATTERNS:
        truth = {}
        for row, key in enumerate(zip(*(cols[b].tolist() for b in bound))):
            truth.setdefault(key, []).append(row)
        keys = sorted(truth)
        pick = rng.choice(len(keys), size=min(N_QUERIES, len(keys)), replace=False)
        qkeys = [keys[i] for i in sorted(pick.tolist())]
        Q = np.zeros((len(qkeys), D), dtype=np.int8)
        for i, key in enumerate(qkeys):
            acc = np.zeros(D, dtype=np.int8)
            for slot, val in zip(bound, key):
                acc += R[slot] * codes[slot][val]
            Q[i] = acc
        thr = (np.abs(Q.astype(np.int32)).sum(axis=1) if len(bound) == 3
               else 2 * np.count_nonzero(Q, axis=1))
        prepared[name] = (Q, thr, truth, qkeys)

    n_buckets = (N_TRIPLES + B - 1) // B
    lay = layouts(rng, tp, ts, to, B, n_buckets)
    rows = []

    print(f"D={D}  B={B}  buckets={n_buckets}  store "
          f"{T.nbytes/1e6:.1f} MB -> {T.nbytes/1e6/B:.1f} MB ({B}x)\n")
    print(f"{'layout':<14}{'pattern':<14}{'recall':>9}{'min':>8}{'perfect':>9}{'cpu%':>8}")

    for lname, assign in lay.items():
        V, tie = bundle(T, assign, n_buckets)
        members = [[] for _ in range(n_buckets)]
        for row, b in enumerate(assign.tolist()):
            members[b].append(row)
        for pname, _ in PATTERNS:
            Q, thr, truth, qkeys = prepared[pname]
            rec, rmin, perf, cpu = eval_pattern(
                V, members, Q, thr, truth, qkeys, B, N_TRIPLES, DIV)
            rows.append({"layout": lname, "pattern": pname, "tie_rate": round(tie, 4),
                         "recall_mean": rec, "recall_min": rmin,
                         "perfect_queries": perf, "cpu_rows_checked_pct": cpu})
            print(f"{lname:<14}{pname:<14}{rec:>9.4f}{rmin:>8.4f}"
                  f"{perf:>6}/{len(qkeys):<3}{cpu:>8.2f}", flush=True)
        print()

    # the verdict: does ANY single layout hold recall across ALL patterns?
    verdict = {}
    for lname in lay:
        rs = [r for r in rows if r["layout"] == lname]
        verdict[lname] = {
            "worst_recall_across_patterns": min(r["recall_mean"] for r in rs),
            "worst_cpu_pct": max(r["cpu_rows_checked_pct"] for r in rs),
            "patterns_at_recall_1": sum(1 for r in rs if r["recall_mean"] >= 1.0),
            "n_patterns": len(rs),
        }
    print("VERDICT — one store, all patterns")
    for k, v in verdict.items():
        print(f"  {k:<14} worst_recall {v['worst_recall_across_patterns']:.4f}  "
              f"worst_cpu {v['worst_cpu_pct']:6.2f}%  "
              f"recall-1.0 on {v['patterns_at_recall_1']}/{v['n_patterns']} patterns")

    Path("multipattern_%s.json" % ("B" if DIV else "sqrt")).write_text(json.dumps(
        {"config": {"D": D, "B": B, "n_triples": N_TRIPLES,
                    "n_queries": N_QUERIES, "seed": hdcore.SEED,
                    "cutoff_rule": ("2*nnz(Q)/B (calibrated)" if DIV else "2*nnz(Q)/sqrt(B) (S11 original)")},
         "rows": rows, "verdict": verdict}, indent=2) + "\n")
    print("\nwrote multipattern_%s.json" % ("B" if DIV else "sqrt"))


if __name__ == "__main__":
    main()
