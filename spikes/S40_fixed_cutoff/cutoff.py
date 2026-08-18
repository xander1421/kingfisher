#!/usr/bin/env python3
"""S40 — what does the oracle cutoff cost? Fixed-vs-fitted, both sides priced.

out/LEDGER.md, "NEVER MEASURED": *"A fixed (non-oracle) cutoff — every bundling
result uses a cutoff fitted to the ground truth. A deployed prefilter cannot."*

RETRACTIONS records what that concealed: at cut=-58 a reported "recall 1.0" was
a 95% SCAN, visible only because the cutoff knew the answer. So every bundling
and shaping magnitude in this tree -- including S52's real-KG 4.1-5.6x -- rests
on a threshold no deployed prefilter could pick.

This measures the gap directly. Two cutoffs, same store, same queries:

  ORACLE  swept downward until recall == 1.0.   USES GROUND TRUTH. Undeployable.
  FIXED   computed from the QUERY ALONE, before touching data. Deployable.

S5/S10 give the fixed form at B=1 and it is exact, not heuristic: a matching
triple scores exactly nnz(Q) on the halved ternary query, known before any data
is read. Above B=1 the bundle is sign(sum of B members), the target's
contribution is diluted, and the honest analytic estimate is a random-walk one,
nnz(Q)/sqrt(B) -- which is S11's rule, and S17 called it "a guess above B=1".
This asks what that guess costs.

FALSIFIER, STATED BEFORE RUNNING: if FIXED holds recall >= 0.99 at every B with
rows-checked within ~2x of ORACLE, then the oracle was a convenience and the
tree's magnitudes stand as reported. If FIXED loses recall, or holds recall only
by checking a far larger share of the store, then the published numbers are
oracle-assisted and the deployable figure is the one in the FIXED column.

usage: cutoff.py [n] [D]
"""
import sys, json
import numpy as np

def build(rng, n, D, n_pred=10, n_subj=1000, n_obj=1000):
    bip = lambda r: (rng.integers(0, 2, size=(r, D), dtype=np.int8) * 2 - 1).astype(np.int8)
    R, P, S, O = bip(3), bip(n_pred), bip(n_subj), bip(n_obj)
    tp = rng.integers(0, n_pred, n); ts = rng.integers(0, n_subj, n); to = rng.integers(0, n_obj, n)
    acc = (R[0]*P[tp]).astype(np.int16) + R[1]*S[ts] + R[2]*O[to]
    T = np.sign(acc).astype(np.int8)
    return R, P, S, O, tp, ts, to, T

def cluster(tp, ts, to):
    """S11/S17's layout: sort by (pred,subj) so a bucket's members share slots."""
    return np.lexsort((to, ts, tp))


def bundle(T, B):
    """sign(sum) over consecutive runs of B. B=1 is the identity."""
    if B == 1: return T.copy()
    n, D = T.shape
    m = (n // B) * B
    return np.sign(T[:m].reshape(-1, B, D).astype(np.int16).sum(axis=1)).astype(np.int8)

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000
    D = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    rng = np.random.default_rng(0xC0FFEE)
    R, P, S, O, tp, ts, to, T = build(rng, n, D)

    NQ = 60
    print(f"S40  n={n:,} D={D}  queries={NQ}  store={T.nbytes/1e6:.1f} MB\n")
    print(f"{'B':>4}{'buckets':>9} | {'ORACLE (fitted to truth)':^34} | {'FIXED (query only)':^30}")
    print(f"{'':>4}{'':>9} | {'cut':>6}{'recall':>9}{'checked%':>10}{'':>9} | {'cut':>6}{'recall':>9}{'checked%':>10}")
    rows = []
    for B, lay in [(b, l) for b in (1, 4, 16, 64) for l in ("random", "clustered")]:
        if lay == "clustered":
            order = cluster(tp, ts, to); Ts, tps, tss = T[order], tp[order], ts[order]
        else:
            Ts, tps, tss = T, tp, ts
        Tb = bundle(Ts, B); nb = Tb.shape[0]
        o_rec = o_chk = f_rec = f_chk = 0.0
        for _ in range(NQ):
            i = int(rng.integers(0, n))
            p, s = int(tps[i]), int(tss[i])
            Q = ((R[0]*P[p] + R[1]*S[s]) // 2).astype(np.int8)   # ternary
            nnz = int(np.count_nonzero(Q))
            truth_rows = np.flatnonzero((tps == p) & (tss == s))
            truth_b = np.unique(truth_rows // B)
            truth_b = truth_b[truth_b < nb]
            if truth_b.size == 0: continue
            sc = (Q.astype(np.int32) @ Tb.astype(np.int32).T)

            # ORACLE: the highest cut that still retrieves every answer bucket.
            # This is the fitted threshold, and it needs truth to compute.
            cut_o = int(sc[truth_b].min())
            sel_o = sc >= cut_o
            o_rec += 1.0                                   # recall 1.0 by construction
            o_chk += 100.0 * sel_o.sum() / nb

            # FIXED: from the query alone. nnz(Q) at B=1 is S5/S10's exact bound.
            cut_f = int(round(nnz / np.sqrt(B)))
            sel_f = sc >= cut_f
            f_rec += float(np.isin(truth_b, np.flatnonzero(sel_f)).mean())
            f_chk += 100.0 * sel_f.sum() / nb
        o_chk/=NQ; f_rec/=NQ; f_chk/=NQ
        rows.append(dict(B=B, layout=lay, buckets=nb, oracle_checked_pct=round(o_chk,4),
                         fixed_recall=round(f_rec,4), fixed_checked_pct=round(f_chk,4)))
        print(f"{B:>4} {lay:<10}{nb:>7} | {'swept':>6}{1.0:>9.4f}{o_chk:>10.4f}{'':>6} | "
              f"{'nnz/√B':>6}{f_rec:>9.4f}{f_chk:>10.4f}")
    json.dump(rows, open(__file__.replace('cutoff.py','cutoff.json'),'w'), indent=2)
    print("\nORACLE recall is 1.0 BY CONSTRUCTION -- it is defined as the cut that")
    print("retrieves every answer. Its only informative column is checked%.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
