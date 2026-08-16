#!/usr/bin/env python3
"""S11 — bundling: can the pre-filter store fit on a phone at all?

S5's own "what this does NOT show" section names this as the obvious next
spike and never runs it:

    "One vector per triple is not a compression scheme.  100k triples at
     D=1024 costs 102 MB, versus a few MB for the raw triples.  The
     compressive version -- bundling many triples into one vector per bucket
     -- reintroduces superposition noise and is where recall actually starts
     to cost something."

That 102 MB is per 100k triples.  A phone-sized shard of a few million triples
is multiple gigabytes of INT8 -- which is not a shard, it is a disqualification.
So the deployable question is not "does the exact threshold work" (S10 answers
that) but "how much recall does bundling cost, and is the trade ever worth it".

Bundle B triples into one bucket vector V = sign(sum of the B triple vectors).
Query scores against BUCKETS, the CPU then checks every triple in every
surviving bucket.  Storage falls by B; the CPU stage inflates by roughly B per
surviving bucket; recall falls because superposition noise grows as sqrt(B).

Two bucket assignments are compared, because this is the entire argument for
"the beak":
  random    -- triples assigned to buckets arbitrarily
  clustered -- triples sharing a (pred, subj) key packed into the same bucket,
               i.e. what a shaping job would produce

If clustered bundling holds recall where random bundling loses it, that is a
direct, measured argument that layout is worth paying for -- which is what M4
asserts on the strength of a sparse-vs-dense crossover that says nothing about
recall.

Usage: ./.venv/bin/python bundle.py [D]
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdcore                                   # noqa: E402

N_TRIPLES = 100_000
N_QUERIES = 100
BUNDLE_SIZES = (1, 2, 4, 8, 16, 32, 64)


def bundle(T, assign, n_buckets):
    """V[b] = sign(sum of the triple vectors assigned to bucket b).

    Ties (an even number of +-1 terms summing to 0) are broken to +1, which is
    arbitrary but deterministic -- and the tie rate is reported, because a high
    tie rate is itself evidence the bundle is saturated.
    """
    D = T.shape[1]
    acc = np.zeros((n_buckets, D), dtype=np.int32)
    np.add.at(acc, assign, T.astype(np.int32))
    ties = int((acc == 0).sum())
    V = np.where(acc >= 0, 1, -1).astype(np.int8)
    return V, ties / acc.size


def main():
    D = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    rng = np.random.default_rng(hdcore.SEED)
    R, P, S, O = hdcore.codebooks(rng, D)
    tp, ts, to = hdcore.triples(rng, N_TRIPLES)
    T = hdcore.encode(R, P, S, O, tp, ts, to, D)

    truth = {}
    for row, (p, s) in enumerate(zip(tp.tolist(), ts.tolist())):
        truth.setdefault((p, s), []).append(row)
    keys = sorted(truth)
    pick = rng.choice(len(keys), size=N_QUERIES, replace=False)
    qkeys = [keys[i] for i in sorted(pick.tolist())]

    Q = np.empty((N_QUERIES, D), dtype=np.int8)
    for i, (p, s) in enumerate(qkeys):
        Q[i] = R[hdcore.PRED] * P[p] + R[hdcore.SUBJ] * S[s]
    # the S10/S5 exact cutoff, unchanged -- the question is whether it still
    # separates once triples are superposed
    thr = 2 * np.count_nonzero(Q, axis=1)

    # clustered assignment: consecutive triples of the same (pred,subj) key
    # land in the same bucket -- the output a shaping job would produce
    order = np.lexsort((ts, tp))
    rows = []

    for B in BUNDLE_SIZES:
        n_buckets = (N_TRIPLES + B - 1) // B
        for layout in ("random", "clustered"):
            if layout == "random":
                assign = rng.permutation(N_TRIPLES) % n_buckets
            else:
                assign = np.empty(N_TRIPLES, dtype=np.int64)
                assign[order] = np.arange(N_TRIPLES) // B

            V, tie_rate = bundle(T, assign, n_buckets)
            members = [[] for _ in range(n_buckets)]
            for row, b in enumerate(assign.tolist()):
                members[b].append(row)

            scores = hdcore.score(Q, V)
            recalls, checked, kept_frac = [], [], []
            for qi, key in enumerate(qkeys):
                gold = set(truth[key])
                row = scores[qi]
                # at B=1 the cutoff is exact; above that it is a heuristic, so
                # scale it by the same 1/sqrt(B) the noise grows by
                t = thr[qi] / np.sqrt(B)
                hits = np.flatnonzero(row >= t)
                cand = set()
                for b in hits.tolist():
                    cand.update(members[b])
                found = len(gold & cand)
                recalls.append(found / len(gold))
                checked.append(len(cand))
                kept_frac.append(found / max(1, len(cand)))

            rows.append({
                "bundle_size": B,
                "layout": layout,
                "store_bytes": int(V.nbytes),
                "store_mb": round(V.nbytes / 1e6, 1),
                "compression_vs_B1": round(T.nbytes / V.nbytes, 1),
                "tie_rate": round(tie_rate, 4),
                "recall_mean": round(float(np.mean(recalls)), 4),
                "recall_min": round(float(np.min(recalls)), 4),
                "perfect_recall_queries": int(sum(1 for r in recalls if r >= 1.0)),
                "cpu_rows_checked_mean": round(float(np.mean(checked)), 1),
                "cpu_rows_checked_pct": round(100 * float(np.mean(checked)) / N_TRIPLES, 2),
                "precision_mean": round(float(np.mean(kept_frac)), 4),
            })
            r = rows[-1]
            print(f"B={B:<3} {layout:<10} {r['store_mb']:>6.1f} MB "
                  f"({r['compression_vs_B1']:>5.1f}x)  recall {r['recall_mean']:.4f} "
                  f"(min {r['recall_min']:.4f}, perfect {r['perfect_recall_queries']}/{N_QUERIES})  "
                  f"cpu_checks {r['cpu_rows_checked_pct']:>6.2f}% of store  "
                  f"ties {r['tie_rate']:.3f}", flush=True)

    out = {
        "config": {"D": D, "n_triples": N_TRIPLES, "n_queries": N_QUERIES,
                   "seed": hdcore.SEED,
                   "threshold_rule": "2*nnz(Q) / sqrt(B)"},
        "baseline_store_mb": round(T.nbytes / 1e6, 1),
        "rows": rows,
    }
    Path("bundling.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote bundling.json")


if __name__ == "__main__":
    main()
