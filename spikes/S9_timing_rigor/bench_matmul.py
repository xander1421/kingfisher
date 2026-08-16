#!/usr/bin/env python3
"""S9 — re-measure the S5 pre-filter matmul with a real timing methodology.

S5 reported 352.9 GOP/s (run2.json) and 25.9 GOP/s (run1.json) for the SAME
D=10000 workload, same seed, byte-identical outputs, and put the warm number
in the headline while the D-sweep table carried cold numbers.  A 13.6x
methodology artefact was presented as a throughput result.

This re-runs the sweep with `bench.run`: N repetitions per D, the cold sample
reported separately from the warm median, and the spread printed so a soft
number cannot masquerade as a hard one.

Usage: ./.venv/bin/python bench_matmul.py [reps]
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench                                    # noqa: E402
import hdcore                                   # noqa: E402

DIMS = (256, 512, 1024, 2048, 4096, 10000)
N_TRIPLES = 100_000
N_QUERIES = 100


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rows = []

    for D in DIMS:
        rng = np.random.default_rng(hdcore.SEED)
        R, P, S, O = hdcore.codebooks(rng, D)
        tp, ts, to = hdcore.triples(rng, N_TRIPLES)

        t0 = time.perf_counter()
        T = hdcore.encode(R, P, S, O, tp, ts, to, D)
        t_encode = time.perf_counter() - t0

        truth = {}
        for row, (p, s) in enumerate(zip(tp.tolist(), ts.tolist())):
            truth.setdefault((p, s), []).append(row)
        keys = sorted(truth)
        pick = rng.choice(len(keys), size=N_QUERIES, replace=False)
        qkeys = [keys[i] for i in sorted(pick.tolist())]

        Q = np.empty((N_QUERIES, D), dtype=np.int8)
        for i, (p, s) in enumerate(qkeys):
            Q[i] = R[hdcore.PRED] * P[p] + R[hdcore.SUBJ] * S[s]

        flops = 2 * N_QUERIES * N_TRIPLES * D
        # scale=False: one call already costs >> 50 ms at every D here, and the
        # inner-repeat trick would only hide the cold/warm effect we are after.
        r = bench.run(lambda: hdcore.score(Q, T), reps=reps, scale=False)

        print(bench.fmt(f"matmul D={D}", r, flops), flush=True)
        rows.append({
            "D": D,
            "T_bytes": int(T.nbytes),
            "encode_s": round(t_encode, 4),
            "cold_s": round(r["cold_s"], 4),
            "warm_median_s": round(r["warm_median_s"], 4),
            "warm_rsd_pct": round(r["warm_rsd_pct"], 2),
            "cold_over_warm": round(r["cold_over_warm"], 2),
            "cold_gops": round(bench.gops(flops, r["cold_s"]), 1),
            "warm_gops": round(bench.gops(flops, r["warm_median_s"]), 1),
            "all_s": [round(x, 4) for x in r["all_s"]],
        })
        del T, Q

    # Arithmetic intensity is constant in D for this kernel: ops = 2*q*n*D,
    # bytes touched = n*D, so ~2*q ops/byte regardless of D.  Any GOP/s trend
    # across D is therefore a GEMM-efficiency effect (short k), not bandwidth.
    out = {
        "methodology": {
            "reps_per_D": reps,
            "cold_sample": "first rep, reported separately",
            "warm_statistic": "median of reps 2..N",
            "note": "arithmetic intensity is constant in D (~2*n_queries "
                    "ops/byte); GOP/s variation across D is GEMM efficiency "
                    "at short inner dimension, not memory bandwidth",
        },
        "config": {"n_triples": N_TRIPLES, "n_queries": N_QUERIES,
                   "seed": hdcore.SEED},
        "rows": rows,
    }
    Path("timing.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote timing.json")


if __name__ == "__main__":
    main()
