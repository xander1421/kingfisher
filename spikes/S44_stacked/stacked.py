#!/usr/bin/env python3
"""S44 — everything stacked. What is the ceiling on this machine, licences ignored?

S43 measured one prefilter variant, single-threaded, in isolation. This measures
the full two-stage query the architecture actually specifies, with every
optimisation available stacked on top of each other:

  V0  the S18/S5 path                 float32 GEMM over an int8 store
  V1  packed popcount, uint8 lanes    S43's kernel
  V2  packed popcount, uint64 lanes   16 lanes/vector instead of 128 to reduce
  V3  V2 across P-cores               numpy drops the GIL on bitwise ops
  V4  V3 + stage 2                    exact match over the shortlist = a real query
  B   batch regime                    float32 GEMM at q=256, the shard-host case

Every variant is gated on producing the identical candidate set. A faster
variant that changes the answer is not a faster variant.

usage: stacked.py [n] [D] [threads]
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bench  # noqa: E402
import hdcore  # noqa: E402


def contention():
    load = os.getloadavg()
    ps = subprocess.run(["ps", "-Ao", "comm"], capture_output=True, text=True).stdout
    names = [ln.rstrip().rsplit("/", 1)[-1].lower() for ln in ps.splitlines()]
    busy = sorted({n for n in names if n in
                   ("cargo", "rustc", "mork", "ninja", "clang", "fuelrun")})
    return {"loadavg_1m": round(load[0], 2), "competing": busy}


# ------------------------------------------------------------------ the store

def build(rng, n, D):
    """A store and one honest 2-bound query, built exactly as S5/S10 build them."""
    R, P, S, O = hdcore.codebooks(rng, D)
    tp, ts, to = hdcore.triples(rng, n)
    T = hdcore.encode(R, P, S, O, tp, ts, to, D)
    # pattern (p s ?o): Q = Rp*P[p] + Rs*S[s], values in {-2,0,+2}
    p, s = int(tp[0]), int(ts[0])
    Q2 = (R[hdcore.PRED] * P[p] + R[hdcore.SUBJ] * S[s]).astype(np.int8)
    Q = (Q2 // 2).astype(np.int8)                    # ternary {-1,0,+1}
    truth = np.flatnonzero((tp == p) & (ts == s))    # the exact answer set
    return T, Q, (tp, ts, to), (p, s), truth


# --------------------------------------------------------------- the variants

def v0_float32(Q, T):
    """S18's path: float32 GEMM over the int8 store. Scores are on the Q/2 scale."""
    return hdcore.score(Q[None, :], T)[0]


def _pack(x):
    return np.packbits(x, axis=-1)


def v1_u8(qm, qp, Tp, D):
    """Packed popcount, uint8 lanes. T is bipolar so its mask is all-ones."""
    diff = Tp ^ qp
    pos = np.bitwise_count(qm & ~diff).sum(axis=1, dtype=np.int32)
    neg = np.bitwise_count(qm & diff).sum(axis=1, dtype=np.int32)
    return pos - neg


def v2_u64(qm64, qp64, Tp64):
    """Same identity, 64-bit lanes: 16 accumulator terms per vector, not 128."""
    diff = Tp64 ^ qp64
    pos = np.bitwise_count(qm64 & ~diff).sum(axis=1, dtype=np.int32)
    neg = np.bitwise_count(qm64 & diff).sum(axis=1, dtype=np.int32)
    return pos - neg


def v3_threads(qm64, qp64, Tp64, pool, nthreads):
    chunks = np.array_split(np.arange(Tp64.shape[0]), nthreads)
    outs = list(pool.map(lambda ix: v2_u64(qm64, qp64, Tp64[ix[0]:ix[-1] + 1]),
                         [c for c in chunks if len(c)]))
    return np.concatenate(outs)


def stage2(cand, tp, ts, ps):
    """The exact-match stage: verify each candidate really matches the pattern."""
    p, s = ps
    return cand[(tp[cand] == p) & (ts[cand] == s)]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    D = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    nthreads = int(sys.argv[3]) if len(sys.argv) > 3 else 10   # P-cores
    rng = np.random.default_rng(hdcore.SEED)

    print(f"S44 stacked  n={n:,} D={D} threads={nthreads}")
    c0 = contention()
    print(f"contention at start: {c0}\n")

    T, Q, (tp, ts, to), ps, truth = build(rng, n, D)
    cutoff = int(np.count_nonzero(Q))          # matching triples score exactly nnz(Q)
    print(f"query (p s ?o)  answers={len(truth)}  nnz(Q)={cutoff}  "
          f"store int8={T.nbytes/1e6:.1f} MB")

    Tp = _pack(T < 0)                          # sign bitplane, bipolar store
    qm, qp = _pack(Q != 0), _pack(Q < 0)
    Tp64 = np.ascontiguousarray(Tp).view(np.uint64)
    qm64, qp64 = qm.view(np.uint64), qp.view(np.uint64)
    print(f"packed store = {Tp.nbytes/1e6:.1f} MB  ({T.nbytes/Tp.nbytes:.1f}x smaller)\n")

    # ---------------------------------------------------------- correctness gate
    ref = v0_float32(Q, T)
    got1 = v1_u8(qm, qp, Tp, D)
    got2 = v2_u64(qm64, qp64, Tp64)
    pool = ThreadPoolExecutor(max_workers=nthreads)
    got3 = v3_threads(qm64, qp64, Tp64, pool, nthreads)
    assert np.array_equal(ref, got1), "v1 diverges"
    assert np.array_equal(ref, got2), "v2 diverges"
    assert np.array_equal(ref, got3), "v3 diverges"
    cand = np.flatnonzero(got3 >= cutoff)
    hits = stage2(cand, tp, ts, ps)
    assert np.array_equal(np.sort(hits), truth), "stage 2 lost answers"
    print(f"GATE  v0==v1==v2==v3 exactly;  stage2 recovers {len(hits)}/{len(truth)} "
          f"answers, 0 false positives")
    print(f"      prefilter shortlist = {len(cand)} rows = "
          f"{100*len(cand)/n:.4f}% of store  ({n/max(len(cand),1):,.0f}x reduction)\n")

    # ------------------------------------------------------------------ timings
    ops = 2 * n * D
    def row(name, fn, q=1):
        r = bench.run(fn, reps=7)
        ms = r["warm_median_s"] * 1e3
        print(f"{name:<34}{ms:9.3f} ms{ms/q:10.3f} ms/q"
              f"{bench.gops(ops*q, r['warm_median_s']):11.1f} GOP/s"
              f"{1000*q/ms:11.1f} q/s{r['warm_rsd_pct']:7.1f}%")
        return ms

    print(f"{'variant':<34}{'wall':>9}{'per query':>16}{'':>11}{'':>16}{'rsd':>10}")
    t0 = row("V0 float32 GEMM (S18/S5)", lambda: v0_float32(Q, T))
    t1 = row("V1 packed popcount u8", lambda: v1_u8(qm, qp, Tp, D))
    t2 = row("V2 packed popcount u64", lambda: v2_u64(qm64, qp64, Tp64))
    t3 = row(f"V3 V2 x {nthreads} threads",
             lambda: v3_threads(qm64, qp64, Tp64, pool, nthreads))
    t4 = row("V4 V3 + stage2 (full query)",
             lambda: stage2(np.flatnonzero(
                 v3_threads(qm64, qp64, Tp64, pool, nthreads) >= cutoff), tp, ts, ps))

    Qb = hdcore.bipolar(rng, 256, D)
    tb = row("B  float32 GEMM q=256 (batch)", lambda: hdcore.score(Qb, T), q=256)

    print(f"\nstacked speedup, full query vs S18 baseline: {t0/t4:.1f}x")
    print(f"  V0->V1 pack {t0/t1:5.1f}x | V1->V2 u64 lanes {t1/t2:4.1f}x | "
          f"V2->V3 threads {t2/t3:4.1f}x | stage2 costs {t4-t3:+.3f} ms")
    print(f"\nfull-machine query rate  {1000/t4:,.0f} queries/s")
    print(f"phone projection @3.7x sustained (S30)  {1000/(t4*3.7):,.0f} queries/s/device")
    print(f"batch regime  {tb/256:.4f} ms/query  = {256000/tb:,.0f} queries/s")

    c1 = contention()
    print(f"\ncontention at end: {c1}")
    if c0["competing"] or c1["competing"]:
        print("!! competing processes present - numbers are soft")
    pool.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
