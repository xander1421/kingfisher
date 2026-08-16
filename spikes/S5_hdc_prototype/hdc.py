#!/usr/bin/env python3
"""S5 — INT8 hypervector pre-filter over a synthetic triple store.

The mission's compute split, in miniature:

  phone NPU  : one giant INT8 matmul, Q (few queries) x T^T (all triples)
               -> approximate shortlist
  phone CPU  : exact pattern match, but only over the shortlist
               -> end-to-end lossless

Encoding (classic VSA / HDC):
  atomic vectors are bipolar +-1, D = 10000
  bind   = elementwise multiply
  bundle = majority sum (sign of the sum; with 3 odd terms there are no ties)
  sim    = dot product

  triple (p s o)  ->  T = sign(Rp*P[p] + Rs*S[s] + Ro*O[o])
  query  (p s ?)  ->  Q =      Rp*P[p] + Rs*S[s]           (left unnormalised)

A triple matching both bound slots scores ~2D/3 against Q; everything else
scores ~0.  Ranking by that score is the pre-filter.

Standard library + numpy only.  Everything is seeded; run twice and the
SHA-256 digests printed at the end must be identical.
"""

import hashlib
import json
import sys
import time

import numpy as np

D = 10_000          # hypervector dimension
N_TRIPLES = 100_000
N_PRED = 10
N_SUBJ = 1_000
N_OBJ = 1_000
N_QUERIES = 100
KS = (10, 50, 100, 500, 1000)
SEED = 0xC0FFEE
CHUNK = 10_000      # triples per matmul chunk (keeps the f32 copy ~400 MB)


def bipolar(rng, rows, dim):
    """rows x dim matrix of +-1 as int8."""
    return (rng.integers(0, 2, size=(rows, dim), dtype=np.int8) * 2 - 1).astype(np.int8)


def sha(*arrays):
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def main():
    global D, CHUNK
    if len(sys.argv) > 1:                      # optional: hdc.py <D>
        D = int(sys.argv[1])
        CHUNK = max(1000, min(100_000, 100_000_000 // D))
    t_all = time.perf_counter()
    rng = np.random.default_rng(SEED)

    # ---- codebooks ---------------------------------------------------------
    R = bipolar(rng, 3, D)          # role vectors: predicate, subject, object
    P = bipolar(rng, N_PRED, D)
    S = bipolar(rng, N_SUBJ, D)
    O = bipolar(rng, N_OBJ, D)

    # ---- the synthetic knowledge graph ------------------------------------
    # 100k triples like (likes alice bob), uniformly drawn.
    tp = rng.integers(0, N_PRED, N_TRIPLES)
    ts = rng.integers(0, N_SUBJ, N_TRIPLES)
    to = rng.integers(0, N_OBJ, N_TRIPLES)

    t0 = time.perf_counter()
    T = np.empty((N_TRIPLES, D), dtype=np.int8)
    for i in range(0, N_TRIPLES, CHUNK):
        j = min(i + CHUNK, N_TRIPLES)
        acc = (R[0] * P[tp[i:j]]).astype(np.int8)
        acc += R[1] * S[ts[i:j]]
        acc += R[2] * O[to[i:j]]
        # 3 odd terms -> the sum is odd -> sign is never 0, majority is exact
        T[i:j] = np.sign(acc, dtype=np.int8, casting="unsafe")
    t_encode = time.perf_counter() - t0

    # ---- ground truth ------------------------------------------------------
    # exact index (p,s) -> set of row ids.  This is what the CPU stage checks
    # the shortlist against, and what recall is measured against.
    truth = {}
    for row, (p, s) in enumerate(zip(tp.tolist(), ts.tolist())):
        truth.setdefault((p, s), []).append(row)

    # ---- queries -----------------------------------------------------------
    # sample (p,s) pairs that actually occur, so every query has answers
    keys = sorted(truth.keys())
    pick = rng.choice(len(keys), size=N_QUERIES, replace=False)
    qkeys = [keys[i] for i in sorted(pick.tolist())]

    Q = np.empty((N_QUERIES, D), dtype=np.int8)
    for i, (p, s) in enumerate(qkeys):
        Q[i] = R[0] * P[p] + R[1] * S[s]      # values in {-2,0,2}, fits int8

    # ---- the "NPU" stage: one big matmul -----------------------------------
    # int8 x int8 -> int32 conceptually.  numpy has no integer BLAS, so the
    # multiply runs in float32, which represents every reachable value
    # (|score| <= 2D = 20000) exactly -- the result is integer-exact.
    Qf = Q.astype(np.float32)
    scores = np.empty((N_QUERIES, N_TRIPLES), dtype=np.int32)
    t0 = time.perf_counter()
    for i in range(0, N_TRIPLES, CHUNK):
        j = min(i + CHUNK, N_TRIPLES)
        scores[:, i:j] = (Qf @ T[i:j].astype(np.float32).T).astype(np.int32)
    t_matmul = time.perf_counter() - t0
    flops = 2 * N_QUERIES * N_TRIPLES * D

    # ---- the "CPU" stage: exact verification of the shortlist --------------
    results = {k: {"recall": [], "precision": [], "checked": 0, "kept": 0} for k in KS}
    t0 = time.perf_counter()
    for qi, (p, s) in enumerate(qkeys):
        gold = set(truth[(p, s)])
        row = scores[qi]
        for k in KS:
            # argpartition = the shortlist the NPU hands to the CPU
            cand = np.argpartition(-row, k)[:k]
            # exact match, the lossless half: is this row really (p s ?)
            hit = [c for c in cand.tolist() if tp[c] == p and ts[c] == s]
            r = results[k]
            r["recall"].append(len(hit) / len(gold))
            r["precision"].append(len(hit) / k)
            r["checked"] += k
            r["kept"] += len(hit)
    t_verify = time.perf_counter() - t0

    # ---- analytic threshold ------------------------------------------------
    # For a triple that matches both bound slots, every dimension where the two
    # bound role-filler products agree (Q_d = +-2) survives the majority sign,
    # so it contributes exactly 2; every dimension where they disagree
    # (Q_d = 0) contributes 0.  The score of a *matching* triple is therefore
    # exactly 2 * |{d : Q_d != 0}| -- the same value for every match, and known
    # from the query alone, before touching the data.  That turns the
    # "approximate" pre-filter into an exact-recall filter with a computable
    # cutoff.  Verify that claim on all queries.
    thresholds = 2 * np.count_nonzero(Q, axis=1)
    exact_hits, false_pos, thr_ok = [], [], True
    for qi, (p, s) in enumerate(qkeys):
        gold = np.array(sorted(truth[(p, s)]))
        thr = int(thresholds[qi])
        if not (scores[qi][gold] == thr).all():
            thr_ok = False
        above = int((scores[qi] >= thr).sum())
        exact_hits.append(len(gold))
        false_pos.append(above - len(gold))

    q0p, q0s = qkeys[0]
    gold0 = np.array(sorted(truth[(q0p, q0s)]))
    mask = np.ones(N_TRIPLES, dtype=bool)
    mask[gold0] = False
    sep = {
        "match_mean": float(scores[0][gold0].mean()),
        "match_min": int(scores[0][gold0].min()),
        "nonmatch_mean": float(scores[0][mask].mean()),
        "nonmatch_max": int(scores[0][mask].max()),
        "nonmatch_std": float(scores[0][mask].std()),
    }

    # ---- report ------------------------------------------------------------
    answers = [len(truth[k]) for k in qkeys]
    out = {
        "config": {"D": D, "n_triples": N_TRIPLES, "n_pred": N_PRED,
                   "n_subj": N_SUBJ, "n_obj": N_OBJ, "n_queries": N_QUERIES,
                   "seed": SEED},
        "answers_per_query": {"min": min(answers), "max": max(answers),
                              "mean": sum(answers) / len(answers)},
        "timing_s": {"encode": round(t_encode, 3), "matmul": round(t_matmul, 3),
                     "verify": round(t_verify, 3),
                     "total": round(time.perf_counter() - t_all, 3)},
        "matmul_gops": round(flops / t_matmul / 1e9, 1),
        "int8_bytes_scanned": int(T.nbytes),
        "separation": sep,
        "analytic_threshold": {
            "every_match_scores_exactly_2x_nonzero_dims": thr_ok,
            "threshold_min": int(thresholds.min()),
            "threshold_max": int(thresholds.max()),
            "false_positives_total": int(sum(false_pos)),
            "true_matches_total": int(sum(exact_hits)),
            "recall_at_threshold": 1.0 if thr_ok else None,
        },
        "by_k": {},
        "digests": {
            "codebooks": sha(R, P, S, O),
            "triples": sha(tp, ts, to),
            "encoded_T": sha(T),
            "queries": sha(Q),
            "scores": sha(scores),
        },
    }
    for k in KS:
        r = results[k]
        out["by_k"][k] = {
            "recall_at_k_mean": round(float(np.mean(r["recall"])), 4),
            "recall_at_k_min": round(float(np.min(r["recall"])), 4),
            "perfect_recall_queries": int(sum(1 for x in r["recall"] if x >= 1.0)),
            "precision_at_k_mean": round(float(np.mean(r["precision"])), 4),
            "candidate_reduction": round(N_TRIPLES / k, 1),
            "exact_checks_per_query": k,
        }

    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
