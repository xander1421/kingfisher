#!/usr/bin/env python3
"""B2 — what the bundling prefilter costs when the cutoff does NOT read the answer.

B1 publishes "% store checked" per B. `bundling.py:99-103`:

    pos    = order.index(row) // B        # the bundle CONTAINING THE ANSWER
    target = score(bundles[pos])          # the ANSWER's score
    beat   = |{sampled bundles : score >= target}| / SAMP

That is the per-query ORACLE MINIMUM: the smallest shortlist that happens to
contain this query's answer, computed by looking the answer up. A deployed
prefilter has no `pos`. `out/RETRACTIONS.md` rule 5 says a parameter fitted to
the ground truth must be labelled an oracle and its cost reported; B1's number
is that cost, unlabelled.

WHAT THIS SPIKE DOES, and it deliberately does NOT build a second scorer.
The per-query oracle minima ARE the recall curve: for a fixed budget b chosen in
advance (no per-query oracle), recall(b) = |{queries : frac_q <= b}| / NQ. So the
honest deployed statement is a (budget, recall) pair, and B1's published median
and p90 are two points on that curve read as if they were the whole of it.

FALSIFIER, STATED BEFORE THE RUN: if the budget required at a fixed non-oracle
recall target lands within the spread of B1's published figures, the oracle was
decorative and B1 stands as written. If it does not, B1's live GREEN claim needs
the caveat on the claim.

CONTROL C1 (REGENERATION EQUIVALENCE, and it is what licenses the copied
scorer): this file reproduces B1's published median and p90 for all 7 values of
B, byte-for-byte against bundling.json. If the copy drifted, that control fails
and every number below is void. It CAN fail: change SEED, the clustering key,
SAMP, or a role vector and it does.

usage: python3 nonoracle.py          (from this directory)
"""
import json, random, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
B1 = os.path.join(HERE, '..', 'B1_bundling_real')

# Pinned to B1's values. Not re-chosen -- a different seed would make the
# equivalence control vacuous, which is the only thing licensing the copy.
SEED = 20260817
D = 1024
WORDS = D // 64
NQ = 120
SAMP = 600
VTCM_BYTES = 8 * 1024 * 1024
BS = [1, 4, 8, 16, 32, 64, 128]


def load(path):
    import struct
    with open(path, 'rb') as f:
        NT, NP, NE = struct.unpack('<III', f.read(12))
        data = struct.unpack(f'<{3*NT}I', f.read(12 * NT))
    return [tuple(data[3*i:3*i+3]) for i in range(NT)], NT, NP, NE


def rng_hv(r):
    return [r.getrandbits(64) for _ in range(WORDS)]


def popcount(x):
    return bin(x).count('1')


def quantile(xs, q):
    """Same convention as B1: sorted(v)[int(q*(len(v)-1))], and for q=0.5
    sorted(v)[len(v)//2]. Reproduced rather than improved, because the control
    compares against B1's published numbers and a 'better' quantile silently
    breaks the comparison instead of the code."""
    s = sorted(xs)
    return s[len(s)//2] if q == 0.5 else s[int(q * (len(s) - 1))]


def main():
    r = random.Random(SEED)
    triples, NT, NP, NE = load(os.path.join(B1, '..', 'S52_realkg', 'triples.bin'))
    assert NT == 272115, f"corpus changed: {NT}"

    Rp, Rs, Ro = rng_hv(r), rng_hv(r), rng_hv(r)
    P = [rng_hv(r) for _ in range(NP)]
    E = [rng_hv(r) for _ in range(NE)]
    order = sorted(range(NT), key=lambda i: (triples[i][0], triples[i][1]))

    # VERBATIM from B1's bundling.py:50-54. My first draft RECONSTRUCTED this
    # from a truncated read and invented a two-term form; control C1 caught it
    # (B=64 median 76% vs B1's 0.17%). It is a 3-way majority binding.
    def base(i):
        p, s, o = triples[i]
        return [((Rp[w] ^ P[p][w]) & (Rs[w] ^ E[s][w]))
                | ((Rp[w] ^ P[p][w]) & (Ro[w] ^ E[o][w]))
                | ((Rs[w] ^ E[s][w]) & (Ro[w] ^ E[o][w])) for w in range(WORDS)]

    qrows = [order[r.randrange(NT)] for _ in range(NQ)]
    pos_of = {row: i for i, row in enumerate(order)}   # O(1); B1 used .index()

    out = {"seed": SEED, "corpus_triples": NT, "D": D, "NQ": NQ, "SAMP": SAMP,
           "B": {}}
    for B in BS:
        # VERBATIM from B1's bundling.py:61-79. Also invented in my first draft
        # (bitwise OR); it is a MAJORITY VOTE PER BIT, which is a different
        # operator and a different cost.
        nb = (NT + B - 1) // B
        store_bytes = nb * WORDS * 8
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

        frac = []
        for row in qrows:
            p, s, o = triples[row]
            a = [Rp[w] ^ P[p][w] for w in range(WORDS)]
            b2 = [Rs[w] ^ E[s][w] for w in range(WORDS)]
            Qm = [~(a[w] ^ b2[w]) & ((1 << 64) - 1) for w in range(WORDS)]
            Qs = [a[w] & Qm[w] for w in range(WORDS)]
            nnz = sum(popcount(Qm[w]) for w in range(WORDS))
            pos = pos_of[row] // B if B > 1 else pos_of[row]

            def score(bv):
                return 2*nnz - 4*sum(popcount((bv[w] ^ Qs[w]) & Qm[w])
                                     for w in range(WORDS))
            target = score(bundles[pos])
            beat = sum(1 for _ in range(SAMP)
                       if score(bundles[r.randrange(nb)]) >= target)
            frac.append(beat / SAMP)

        out["B"][str(B)] = {
            "bundles": nb, "store_mb": store_bytes / 1e6,
            "median": quantile(frac, 0.5), "p90": quantile(frac, 0.9),
            "p99": quantile(frac, 0.99), "max": max(frac),
            "frac_all": frac,
        }

    # --- CONTROL C1: regeneration equivalence against B1's published artifact.
    b1 = json.load(open(os.path.join(B1, 'bundling.json')))
    mism = []
    for B in BS:
        pub = b1["B"][str(B)]
        got = out["B"][str(B)]
        for pk, gk in (("store_frac_checked_median", "median"),
                       ("store_frac_checked_p90", "p90")):
            if pub[pk] != got[gk]:
                mism.append(f"B={B} {pk}: B1={pub[pk]} B2={got[gk]}")
    out["C1_regeneration_equivalence"] = {
        "compared": 2 * len(BS), "mismatches": mism, "pass": not mism,
        "why_it_can_fail": "change SEED, SAMP, the clustering key or a role "
                           "vector and the reproduced quantiles move",
    }

    # --- The non-oracle reading: budget chosen in advance, recall measured.
    # recall(b) = fraction of queries whose oracle minimum is <= b, i.e. the
    # fraction a fixed shortlist of size b actually catches.
    grid = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.0]
    for B in BS:
        f = out["B"][str(B)]["frac_all"]
        out["B"][str(B)]["recall_at_budget"] = {
            str(b): sum(1 for x in f if x <= b) / len(f) for b in grid}

    json.dump(out, open(os.path.join(HERE, 'nonoracle.json'), 'w'), indent=1)

    print(f"B2 — non-oracle cutoff on B1's instrument. seed {SEED}, "
          f"NQ={NQ}, SAMP={SAMP}")
    print(f"C1 regeneration equivalence vs B1: "
          f"{'PASS' if not mism else 'FAIL ' + '; '.join(mism)} "
          f"({out['C1_regeneration_equivalence']['compared']} compared)")
    print()
    print(f"{'B':>4} {'store MB':>9} {'median':>8} {'p90':>8} {'p99':>8} "
          f"{'MAX':>8}   <- oracle minimum per query")
    for B in BS:
        d = out["B"][str(B)]
        print(f"{B:>4} {d['store_mb']:>9.2f} {d['median']:>8.2%} "
              f"{d['p90']:>8.2%} {d['p99']:>8.2%} {d['max']:>8.2%}")
    print()
    print("recall at a budget FIXED IN ADVANCE (no per-query oracle):")
    hdr = "   ".join(f"{b:>7.1%}" for b in grid)
    print(f"{'B':>4}  {hdr}")
    for B in BS:
        rw = out["B"][str(B)]["recall_at_budget"]
        print(f"{B:>4}  " + "   ".join(f"{rw[str(b)]:>7.1%}" for b in grid))
    return 0 if not mism else 1


if __name__ == '__main__':
    sys.exit(main())
