#!/usr/bin/env python3
"""B1 — bundling compression vs recall on a REAL knowledge graph.

First link in the VTCM chain, and the one that decides whether the NPU comes
back: VTCM is 8 MB, the packed store is 12.8 MB, so bundling is a prerequisite
for on-chip residency. The LEDGER records the magnitude as UNMEASURED on real
data -- 54x was B=1 -> B=64 compression, and S52 measured clustering-vs-random
only, never the compression/recall tradeoff.

Reports RATIOS AND RECALL, never a duration, so it runs through a refused host
gate (same property as S61 and Q1).

Data: FB15k-237, 272,115 triples (S52's triples.bin).
Stdlib only. Seed fixed.

  python3 bundling.py [--json]
"""
import struct, random, sys, json

SEED = 20260817
D = 1024                 # hypervector dimension, as S5/S34
WORDS = D // 64
NQ = 120                 # queries per (B, shape) cell
VTCM_BYTES = 8 * 1024 * 1024

def load(path):
    f = open(path, 'rb')
    NT, NP, NE = struct.unpack('<3i', f.read(12))
    raw = f.read(NT * 12)
    return [struct.unpack_from('<3i', raw, i * 12) for i in range(NT)], NT, NP, NE

def rng_hv(r):
    return [r.getrandbits(64) for _ in range(WORDS)]

def popcount(x): return bin(x).count('1')

def main():
    r = random.Random(SEED)
    triples, NT, NP, NE = load('../S52_realkg/triples.bin')
    assert NT == 272115, f"corpus changed: {NT}"

    # role vectors + atom vectors, as S52's realkg.c
    Rp, Rs, Ro = rng_hv(r), rng_hv(r), rng_hv(r)
    P = [rng_hv(r) for _ in range(NP)]
    E = [rng_hv(r) for _ in range(NE)]

    # cluster by (pred,subj) -- S52's best layout
    order = sorted(range(NT), key=lambda i: (triples[i][0], triples[i][1]))

    def base(i):
        p, s, o = triples[i]
        return [((Rp[w] ^ P[p][w]) & (Rs[w] ^ E[s][w]))
                | ((Rp[w] ^ P[p][w]) & (Ro[w] ^ E[o][w]))
                | ((Rs[w] ^ E[s][w]) & (Ro[w] ^ E[o][w])) for w in range(WORDS)]

    # pre-pick the query set once so every B sees identical queries
    qrows = [order[r.randrange(NT)] for _ in range(NQ)]

    out = {"seed": SEED, "corpus_triples": NT, "D": D, "vtcm_bytes": VTCM_BYTES, "B": {}}
    for B in (1, 4, 8, 16, 32, 64, 128):
        nb = (NT + B - 1) // B
        store_bytes = nb * WORDS * 8
        # majority-bundle each block
        bundles = []
        for b in range(nb):
            lo, hi = b * B, min(b * B + B, NT)
            m = hi - lo
            acc = [0] * WORDS
            if B == 1:
                acc = base(order[lo])
            else:
                cols = [base(order[k]) for k in range(lo, hi)]
                for w in range(WORDS):
                    v = 0
                    for bit in range(64):
                        ones = sum((c[w] >> bit) & 1 for c in cols)
                        if ones * 2 > m: v |= 1 << bit
                    acc[w] = v
            bundles.append(acc)
        # recall: for each query, does the bundle containing the answer score
        # above the median bundle? (a shortlist the exact stage could reach)
        frac = []
        for row in qrows:
            p, s, o = triples[row]
            a = [Rp[w] ^ P[p][w] for w in range(WORDS)]
            b2 = [Rs[w] ^ E[s][w] for w in range(WORDS)]
            Qm = [~(a[w] ^ b2[w]) & ((1 << 64) - 1) for w in range(WORDS)]
            Qs = [a[w] & Qm[w] for w in range(WORDS)]
            nnz = sum(popcount(Qm[w]) for w in range(WORDS))
            pos = order.index(row) // B if B > 1 else order.index(row)
            def score(bv):
                return 2 * nnz - 4 * sum(popcount((bv[w] ^ Qs[w]) & Qm[w]) for w in range(WORDS))
            # Rank-based, not median-based. "Scores above the median of 64" is
            # trivially true for a bundle that CONTAINS the answer -- it gave
            # 100% at every B and could not discriminate. The quantity that
            # matters is the one S52 reports: what FRACTION OF THE STORE must
            # the exact stage check to be sure of catching the answer.
            target = score(bundles[pos])
            SAMP = 600
            beat = sum(1 for _ in range(SAMP)
                       if score(bundles[r.randrange(nb)]) >= target)
            frac.append(beat / SAMP)
        out["B"][B] = {"bundles": nb, "store_bytes": store_bytes,
                       "store_mb": store_bytes / 1e6,
                       "compression_vs_B1": (NT * WORDS * 8) / store_bytes,
                       "fits_vtcm": store_bytes <= VTCM_BYTES,
                       "store_frac_checked_median": sorted(frac)[len(frac)//2],
                       "store_frac_checked_p90": sorted(frac)[int(0.9*(len(frac)-1))],
                       "exact_rows_checked_median": sorted(frac)[len(frac)//2] * NT}

    if "--json" in sys.argv:
        print(json.dumps(out, indent=2)); return
    print(f"B1 bundling on FB15k-237 — {NT:,} triples, D={D}, seed {SEED}")
    print(f"  VTCM budget {VTCM_BYTES/1e6:.1f} MB\n")
    print(f"  {'B':>4} {'bundles':>9} {'store MB':>9} {'compr':>7} {'fits VTCM':>10} {'%store chk':>11} {'p90':>8} {'exact rows':>11}")
    for B, d in out["B"].items():
        print(f"  {B:>4} {d['bundles']:>9,} {d['store_mb']:>9.2f} {d['compression_vs_B1']:>6.0f}x "
              f"{'YES' if d['fits_vtcm'] else 'no':>10} {d['store_frac_checked_median']:>10.2%} "
              f"{d['store_frac_checked_p90']:>7.1%} {d['exact_rows_checked_median']:>11,.0f}")
main()
