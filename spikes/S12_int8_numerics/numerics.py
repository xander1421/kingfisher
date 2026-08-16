#!/usr/bin/env python3
"""S12 — the INT8 exactness claim, tested as far as it can be without silicon.

S5/S7 both rest on one unmeasured assumption, which S7 states plainly:

    "the exactness claim assumes the phone NPU performs true INT8xINT8->INT32
     with no internal saturation, requantisation, or reduced-width
     accumulation.  Some NNAPI/Core ML paths do not."

A phone is not attached, so the on-device half (M2.1) stays open.  What CAN be
settled here, and is not, is everything upstream of the device:

  1. Is the float32 matmul S5 actually ran integer-exact?  S5 asserts it from
     the 2**24 argument but never checks against a true int32 reference.
  2. What is the real headroom?  Which (D, pattern) combinations stay inside
     int16 and which need int32 -- for the accumulator AND for every partial
     sum along the way, since a tiled NPU accumulates in tiles.
  3. What breaks first if the NPU is not ideal?  Simulate the three documented
     deviations -- narrow (int16) accumulation, saturating accumulation, and
     output requantisation to int8 -- and measure which of them destroys the
     exact-threshold rule that rung 2 depends on.

(3) is the one that matters.  If int8 output requantisation kills the rule,
then "the NPU produces a verifiable result" is false for any backend that
requantises, and the S7 envelope design must carry the quantisation parameters
or the whole rung collapses back to rung 1.

Usage: ./.venv/bin/python numerics.py
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdcore                                   # noqa: E402

N_TRIPLES = 20_000          # small enough for an exact int32 reference matmul
N_QUERIES = 32
DIMS = (256, 512, 1024, 2048, 4096, 10000)

INT16_MAX, INT8_MAX = 2 ** 15 - 1, 2 ** 7 - 1


def setup(D, n_bound=2):
    rng = np.random.default_rng(hdcore.SEED)
    R, P, S, O = hdcore.codebooks(rng, D)
    tp, ts, to = hdcore.triples(rng, N_TRIPLES)
    T = hdcore.encode(R, P, S, O, tp, ts, to, D)

    truth = {}
    for row, (p, s) in enumerate(zip(tp.tolist(), ts.tolist())):
        truth.setdefault((p, s), []).append(row)
    keys = sorted(truth)
    pick = rng.choice(len(keys), size=min(N_QUERIES, len(keys)), replace=False)
    qkeys = [keys[i] for i in sorted(pick.tolist())]

    Q = np.zeros((len(qkeys), D), dtype=np.int8)
    for i, (p, s) in enumerate(qkeys):
        v = R[hdcore.PRED] * P[p] + R[hdcore.SUBJ] * S[s]
        if n_bound == 3:
            v = v + R[hdcore.OBJ] * O[to[truth[(p, s)][0]]]
        Q[i] = v
    return Q, T, truth, qkeys


def exact_int32(Q, T):
    """Ground truth: integer matmul, no floats anywhere."""
    return Q.astype(np.int32) @ T.astype(np.int32).T


def max_partial(Q, T, tile):
    """Largest |running sum| over tiled accumulation order.

    An NPU accumulates a tile at a time.  The FINAL value fitting in int16
    does not mean every intermediate does, and a saturating accumulator
    clamps on the intermediate.
    """
    D = Q.shape[1]
    acc = np.zeros((Q.shape[0], T.shape[0]), dtype=np.int32)
    worst = 0
    for i in range(0, D, tile):
        acc += Q[:, i:i + tile].astype(np.int32) @ T[:, i:i + tile].astype(np.int32).T
        worst = max(worst, int(np.abs(acc).max()))
    return worst


def threshold_survives(scores, Q, truth, qkeys, scale=1.0):
    """Does 'every match scores exactly 2*nnz(Q)' still hold on these scores?

    `scale` rescales the analytic cutoff into the score's units.  Without it a
    requantised score array fails trivially because the units changed, which
    would prove nothing.  The question worth answering is whether matches and
    non-matches still SEPARATE, so recall and collisions are measured at the
    rescaled cutoff rather than the raw one.
    """
    thr = 2 * np.count_nonzero(Q, axis=1)
    ok, fp, tot, found = True, 0, 0, 0
    collisions = 0
    for qi, key in enumerate(qkeys):
        gold = np.asarray(truth[key])
        t = thr[qi] / scale
        gs = scores[qi][gold]
        if not (gs == np.rint(t)).all():
            ok = False
        above = int((scores[qi] >= t).sum())
        hit = int((gs >= t).sum())
        fp += above - hit
        found += hit
        tot += len(gold)
        # a collision is a NON-match landing on the exact score a match takes
        mask = np.ones(scores.shape[1], dtype=bool)
        mask[gold] = False
        if len(gs):
            collisions += int((scores[qi][mask] == gs[0]).sum())
    return {"exact_rule_holds": ok,
            "recall_at_threshold": round(found / tot, 4) if tot else None,
            "false_positives": fp, "true_matches": tot,
            "nonmatches_colliding_with_match_score": collisions}


def main():
    out = {"config": {"n_triples": N_TRIPLES, "n_queries": N_QUERIES,
                      "seed": hdcore.SEED}, "headroom": [], "deviations": {}}

    # ---- 1 & 2: exactness of the float path, and real headroom -------------
    for D in DIMS:
        Q, T, truth, qkeys = setup(D)
        f32 = hdcore.score(Q, T)
        i32 = exact_int32(Q, T)
        agree = bool((f32 == i32).all())
        peak = int(np.abs(i32).max())
        # 3-bound queries reach a strictly higher peak; check that too
        Q3, _, _, _ = setup(D, n_bound=3)
        peak3 = int(np.abs(exact_int32(Q3, T)).max())
        worst_partial = max_partial(Q, T, tile=64)

        row = {
            "D": D,
            "float32_path_matches_int32_reference": agree,
            "peak_abs_score_2bound": peak,
            "peak_abs_score_3bound": peak3,
            "worst_abs_partial_sum_tile64": worst_partial,
            "theoretical_max_3bound": 3 * D,
            "fits_int16_final": peak3 <= INT16_MAX,
            "fits_int16_partial": worst_partial <= INT16_MAX,
            "int16_headroom_pct": round(100 * peak3 / INT16_MAX, 1),
        }
        out["headroom"].append(row)
        print(f"D={D:<6} f32==i32 {str(agree):<5} peak2={peak:<6} peak3={peak3:<6} "
              f"partial={worst_partial:<6} int16_final={str(row['fits_int16_final']):<5} "
              f"int16_use={row['int16_headroom_pct']:>5.1f}%", flush=True)
        del T

    # ---- 3: what breaks when the NPU is not ideal --------------------------
    D = 1024
    Q, T, truth, qkeys = setup(D)
    ref = exact_int32(Q, T)
    base = threshold_survives(ref, Q, truth, qkeys)
    out["deviations"]["ideal_int32"] = base
    print(f"\nideal int32            {base}")

    # (a) int16 accumulation, wrapping
    acc16 = np.zeros(ref.shape, dtype=np.int16)
    for i in range(0, D, 64):
        acc16 += (Q[:, i:i + 64].astype(np.int32)
                  @ T[:, i:i + 64].astype(np.int32).T).astype(np.int16)
    r = threshold_survives(acc16.astype(np.int32), Q, truth, qkeys)
    r["differs_from_ideal"] = not bool((acc16.astype(np.int32) == ref).all())
    out["deviations"]["int16_wrapping_accum"] = r
    print(f"int16 wrapping accum   {r}")

    # (b) int16 saturating accumulation
    accsat = np.zeros(ref.shape, dtype=np.int32)
    for i in range(0, D, 64):
        accsat = np.clip(accsat + Q[:, i:i + 64].astype(np.int32)
                         @ T[:, i:i + 64].astype(np.int32).T,
                         -INT16_MAX - 1, INT16_MAX)
    r = threshold_survives(accsat, Q, truth, qkeys)
    r["differs_from_ideal"] = not bool((accsat == ref).all())
    out["deviations"]["int16_saturating_accum"] = r
    print(f"int16 saturating accum {r}")

    # (c) per-tensor requantisation of the OUTPUT back to int8 -- the common
    #     NNAPI / Core ML quantised-op behaviour
    scale = np.abs(ref).max() / INT8_MAX
    req = np.rint(ref / scale).astype(np.int8).astype(np.int32)
    r = threshold_survives(req, Q, truth, qkeys, scale=scale)
    r["differs_from_ideal"] = not bool((req == ref).all())
    r["distinct_score_values_before"] = int(len(np.unique(ref)))
    r["distinct_score_values_after"] = int(len(np.unique(req)))
    # The cutoff above is thr/scale, an irrational-in-general value compared
    # against an integer grid, so matches that round DOWN fall under it.  The
    # fix is to snap the cutoff onto the same grid.  Measure both, because the
    # gap between them is exactly the trap a device integrator would fall into.
    thr_r = np.rint(2 * np.count_nonzero(Q, axis=1) / scale)
    hit = fp = tot = 0
    for qi, key in enumerate(qkeys):
        gold = np.asarray(truth[key])
        above = int((req[qi] >= thr_r[qi]).sum())
        h = int((req[qi][gold] >= thr_r[qi]).sum())
        hit += h
        fp += above - h
        tot += len(gold)
    r["recall_at_rounded_cutoff"] = round(hit / tot, 4)
    r["false_positives_at_rounded_cutoff"] = fp
    r["note"] = ("threshold rule is stated in raw score units; after "
                 "requantisation the cutoff must be rescaled, and ties "
                 "between match and non-match become possible")
    out["deviations"]["int8_output_requantisation"] = r
    print(f"int8 output requant    {r}")

    Path("numerics.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\nwrote numerics.json")


if __name__ == "__main__":
    main()
