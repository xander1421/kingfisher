#!/usr/bin/env python3
"""S13 — replicate MORK's sparse/dense crossover independently, and put the
headline number back in proportion.

S3 reported "~9,800x faster" for CSR SpGEMM vs dense BLAS at n=1024, 0.01%
density.  Two problems with quoting that:

  1. The CSR side was 2 us.  A 2 us sample with no visible repetition count is
     at the edge of what a single perf-counter delta can resolve.
  2. The baseline is a strawman.  Nobody runs dense sgemm on a matrix that is
     99.99% zeros; the ratio mostly measures how much useless work the dense
     side was asked to do.  The load-bearing number is the CROSSOVER density
     (S3: 5.62 / 5.15 / 8.64% at n = 256 / 512 / 1024), because that is what
     tells a shaping job when it has done enough.

This re-measures both with scipy's SMMP CSR kernel -- an implementation with
no relationship to MORK's, so agreement is replication rather than repetition.
Every point is timed through `bench.autoscale`, so the fastest kernels are
measured as N x t, never as one tick.

It also marks where our OWN workload sits.  The S5 synthetic graph is 100k
triples over 10 predicates x 1000 subjects x 1000 objects, i.e. ~1% density
per predicate slice -- near the crossover, not out at 0.01% where the
four-digit speedup lives.

Usage: ./.venv/bin/python spgemm.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench                                    # noqa: E402

NS = (256, 512, 1024)
DENSITIES = (0.0001, 0.0002, 0.0003, 0.0006, 0.0010, 0.0018, 0.0032, 0.0056,
             0.0100, 0.0178, 0.0316, 0.0562, 0.1000, 0.1778, 0.3162)
SEED = 0xC0FFEE

# what S3 reported, for a like-for-like comparison
MORK_CROSSOVER = {256: 5.624, 512: 5.149, 1024: 8.638}

# S5's synthetic graph: 100k triples / (1000 subj x 1000 obj) per predicate
OUR_DENSITY = 100_000 / 10 / (1_000 * 1_000)


def sparse_mat(rng, n, density):
    nnz = max(1, int(round(n * n * density)))
    idx = rng.choice(n * n, size=nnz, replace=False)
    rows, cols = np.divmod(idx, n)
    vals = rng.standard_normal(nnz).astype(np.float32)
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=np.float32)


def main():
    rng = np.random.default_rng(SEED)
    results = []

    for n in NS:
        # dense baseline is density-independent; measure it once per n
        Ad = rng.standard_normal((n, n)).astype(np.float32)
        Bd = rng.standard_normal((n, n)).astype(np.float32)
        dense = bench.run(lambda: Ad @ Bd, reps=7)
        dense_s = dense["warm_median_s"]
        print(f"\nn={n}  dense sgemm warm_median {dense_s*1e6:9.1f} us  "
              f"(cold {dense['cold_s']*1e6:.1f} us, rsd {dense['warm_rsd_pct']:.1f}%, "
              f"inner {dense['inner_reps']})", flush=True)
        print(f"{'density':>9} {'nnz':>9} {'csr_us':>10} {'rsd%':>6} {'inner':>7} "
              f"{'blas_us':>10} {'ratio':>8} {'speedup':>10}")

        crossover = None
        prev = None
        for d in DENSITIES:
            A = sparse_mat(rng, n, d)
            B = sparse_mat(rng, n, d)
            r = bench.run(lambda: A @ B, reps=7)
            csr_s = r["warm_median_s"]
            ratio = csr_s / dense_s
            row = {
                "n": n, "density": d, "nnz": int(A.nnz),
                "csr_us": round(csr_s * 1e6, 3),
                "csr_rsd_pct": round(r["warm_rsd_pct"], 1),
                "csr_inner_reps": r["inner_reps"],
                "blas_us": round(dense_s * 1e6, 3),
                "sparse_over_dense": round(ratio, 4),
                "speedup": round(1 / ratio, 1),
            }
            results.append(row)
            print(f"{d:>9.4f} {A.nnz:>9} {row['csr_us']:>10.3f} "
                  f"{row['csr_rsd_pct']:>6.1f} {r['inner_reps']:>7} "
                  f"{row['blas_us']:>10.1f} {ratio:>8.4f} {row['speedup']:>9.1f}x",
                  flush=True)

            if crossover is None and prev and prev[1] < 1.0 <= ratio:
                # log-linear interpolation between the bracketing densities
                (d0, r0), (d1, r1) = prev, (d, ratio)
                f = (1.0 - r0) / (r1 - r0)
                crossover = float(np.exp(np.log(d0) + f * (np.log(d1) - np.log(d0))))
            prev = (d, ratio)

        mork = MORK_CROSSOVER[n]
        here = crossover * 100 if crossover else None
        print(f"  -> n={n} scipy crossover {here:.3f}% | MORK reported {mork:.3f}% | "
              f"ratio {here/mork:.2f}x" if here else f"  -> n={n} no crossover in range")
        results.append({"n": n, "crossover_pct": round(here, 3) if here else None,
                        "mork_reported_pct": mork,
                        "agreement_ratio": round(here / mork, 2) if here else None})

    out = {
        "methodology": {
            "kernel": "scipy.sparse SMMP csr@csr, float32, single-threaded",
            "baseline": "numpy float32 dense @ via Accelerate",
            "timing": "bench.autoscale, >=50ms per sample, 7 reps, warm median",
            "why": "independent replication of S3's crossover; scipy shares no "
                   "code with MORK's linalg, so agreement is evidence the "
                   "crossover is a property of the hardware, not of MORK",
        },
        "our_workload_density": OUR_DENSITY,
        "our_workload_note": (
            "S5's synthetic graph is ~%.4f%% density per predicate slice -- "
            "near the crossover, NOT at the 0.01%% point where S3's ~9,800x "
            "headline lives" % (OUR_DENSITY * 100)),
        "rows": results,
    }
    name = f"crossover{sys.argv[1] if len(sys.argv) > 1 else ''}.json"
    Path(name).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {name}")


if __name__ == "__main__":
    main()
