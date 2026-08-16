#!/usr/bin/env python3
"""S43 — bit-pack the bipolar store; popcount instead of float32 matmul.

Claimed in chat.log 17:20Z, extended by AGENT-4 17:35Z with the ternary identity.
Nobody had run it. This runs it.

The identity, for a,b in {-1,+1}^D:

    dot(a,b) == D - 2 * hamming(a,b)

so a 1-bit-per-dimension store returns the IDENTICAL int32 score. Not a
quantisation trade -- exact. `spikes/hdcore.py:91` instead stores one int8 per
+-1 value and then materialises a float32 copy of the whole shard per call,
because numpy has no integer BLAS.

For the bundled store S11 uses sign(sum), and sign(0) is a third value, so a
bundled shard is ternary. AGENT-4's two-bitplane identity, with
m = (x != 0), p = (x < 0):

    dot(a,b) == popcount(m_a & m_b & ~(p_a ^ p_b))
              - popcount(m_a & m_b &  (p_a ^ p_b))

Both identities are asserted against an int32 reference before anything is
timed. A timing run whose exactness gate failed is not reported.

usage: pack.py [n] [D]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bench  # noqa: E402
import hdcore  # noqa: E402


# ---------------------------------------------------------------- contention

def contention():
    """S9's lesson, made mandatory. Same shape as S30's duel.py."""
    load = os.getloadavg()
    ps = subprocess.run(["ps", "-Ao", "comm"], capture_output=True, text=True).stdout
    names = [ln.rstrip().rsplit("/", 1)[-1].lower() for ln in ps.splitlines()]
    busy = sorted({n for n in names
                   if n in ("cargo", "rustc", "mork", "ninja", "clang", "fuelrun")
                   or n.startswith("python")})
    return {"loadavg_1m": round(load[0], 2), "loadavg_5m": round(load[1], 2),
            "competing": busy}


# ------------------------------------------------------------------- packing

def pack_bipolar(T):
    """T int8 in {-1,+1} (n,D) -> (n, D/8) uint8. Bit set == +1."""
    return np.packbits(T > 0, axis=1)


def pack_ternary(T):
    """T int8 in {-1,0,+1} -> (mask, sign) bitplanes, each (n, D/8) uint8."""
    return np.packbits(T != 0, axis=1), np.packbits(T < 0, axis=1)


def score_bipolar(Qb, Tb, D, tile=4096):
    """Exact int32 scores from packed bipolar operands.

    Tiled so a tile of the store stays resident across every query -- the
    numpy stand-in for the VTCM residency the NPU design depends on.
    """
    out = np.empty((Qb.shape[0], Tb.shape[0]), dtype=np.int32)
    for i in range(0, Tb.shape[0], tile):
        Tt = Tb[i:i + tile]
        for k in range(Qb.shape[0]):
            h = np.bitwise_count(Tt ^ Qb[k]).sum(axis=1, dtype=np.int32)
            out[k, i:i + tile] = D - 2 * h
    return out


def score_ternary(Qm, Qp, Tm, Tp, tile=4096):
    """Exact int32 scores from packed ternary operands (AGENT-4's identity)."""
    out = np.empty((Qm.shape[0], Tm.shape[0]), dtype=np.int32)
    for i in range(0, Tm.shape[0], tile):
        tm, tp = Tm[i:i + tile], Tp[i:i + tile]
        for k in range(Qm.shape[0]):
            both = tm & Qm[k]
            diff = tp ^ Qp[k]
            pos = np.bitwise_count(both & ~diff).sum(axis=1, dtype=np.int32)
            neg = np.bitwise_count(both & diff).sum(axis=1, dtype=np.int32)
            out[k, i:i + tile] = pos - neg
    return out


# ------------------------------------------------------------ exactness gate

def gate(rng, D, n=2000):
    """Assert both identities against a true int32 reference. Loud on failure."""
    T = hdcore.bipolar(rng, n, D)
    Q = hdcore.bipolar(rng, 8, D)
    ref = Q.astype(np.int32) @ T.astype(np.int32).T
    got = score_bipolar(pack_bipolar(Q), pack_bipolar(T), D)
    assert np.array_equal(ref, got), "bipolar popcount identity FAILED"

    # ternary: a bundled store, built the way S11 builds one
    Tt = np.sign(hdcore.bipolar(rng, n, D).astype(np.int16)
                 + hdcore.bipolar(rng, n, D)
                 + hdcore.bipolar(rng, n, D)).astype(np.int8)
    Qt = np.sign(hdcore.bipolar(rng, 8, D).astype(np.int16)
                 + hdcore.bipolar(rng, 8, D)).astype(np.int8)
    ref_t = Qt.astype(np.int32) @ Tt.astype(np.int32).T
    Tm, Tp = pack_ternary(Tt)
    Qm, Qp = pack_ternary(Qt)
    got_t = score_ternary(Qm, Qp, Tm, Tp)
    assert np.array_equal(ref_t, got_t), "ternary bitplane identity FAILED"
    ties = float((Tt == 0).mean())
    return n, ties


# ----------------------------------------------------------------------- main

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    D = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    rng = np.random.default_rng(hdcore.SEED)

    c0 = contention()
    print(f"S43 bit-pack  n={n:,} D={D}")
    print(f"contention at start: {c0}\n")

    gn, ties = gate(rng, D)
    print(f"EXACTNESS GATE  bipolar OK, ternary OK  ({gn} vectors, "
          f"ternary zero-rate {ties:.4f})\n")

    T = hdcore.bipolar(rng, n, D)
    Tb = pack_bipolar(T)
    store_i8 = T.nbytes / 1e6
    store_pk = Tb.nbytes / 1e6
    print(f"store  int8 {store_i8:8.1f} MB   packed {store_pk:8.1f} MB   "
          f"{store_i8 / store_pk:.1f}x smaller\n")

    # --- the machine's actual streaming roof, so "memory-bound" is measurable
    r = bench.run(lambda: np.sum(T, dtype=np.int64), reps=5)
    roof_i8 = T.nbytes / r["warm_median_s"] / 1e9
    r2 = bench.run(lambda: np.sum(Tb, dtype=np.int64), reps=5)
    roof_pk = Tb.nbytes / r2["warm_median_s"] / 1e9
    print(f"STREAM roof  int8 store {roof_i8:6.1f} GB/s   "
          f"packed store {roof_pk:6.1f} GB/s")
    print("  (a kernel far below this is not memory-bound, whatever it claims)\n")

    ops = 2 * n * D  # per query, the S18 convention
    print(f"{'q':>5}{'float32 (S18)':>16}{'packed':>12}{'speedup':>10}"
          f"{'GOP/s f32':>12}{'GOP/s pk':>11}{'ms/query pk':>13}")

    rows = []
    for q in (1, 4, 16, 64, 256):
        Q = hdcore.bipolar(rng, q, D)
        Qb = pack_bipolar(Q)

        rf = bench.run(lambda: hdcore.score(Q, T), reps=5)
        rp = bench.run(lambda: score_bipolar(Qb, Tb, D), reps=5)
        f_ms, p_ms = rf["warm_median_s"] * 1e3, rp["warm_median_s"] * 1e3
        rows.append((q, f_ms, p_ms, rf["warm_rsd_pct"], rp["warm_rsd_pct"]))
        print(f"{q:>5}{f_ms:>13.1f} ms{p_ms:>9.1f} ms{f_ms / p_ms:>9.2f}x"
              f"{bench.gops(ops * q, rf['warm_median_s']):>12.1f}"
              f"{bench.gops(ops * q, rp['warm_median_s']):>11.1f}"
              f"{p_ms / q:>12.3f}")

    # one honest cross-check: same scores from both paths at q=16
    Q = hdcore.bipolar(rng, 16, D)
    same = np.array_equal(hdcore.score(Q, T), score_bipolar(pack_bipolar(Q), Tb, D))
    print(f"\nfloat32 path == packed path on the full {n:,} store: {same}")

    c1 = contention()
    print(f"contention at end:   {c1}")
    if c0["competing"] or c1["competing"]:
        print("!! competing processes present - these numbers are soft")
    return 0


if __name__ == "__main__":
    sys.exit(main())
