#!/usr/bin/env python3
"""S7 — a TOPLOC-style top-k polynomial commitment over S5's similarity scores.

TOPLOC (MIT, PrimeIntellect-ai/toploc) commits to the top-k largest-magnitude
activations of an LLM by interpolating a Newton polynomial through
(index, value) mod the prime 65497, and verifies by re-running the computation,
taking its own top-k, evaluating the committed polynomial there, and comparing
exponents exactly / mantissas approximately.

Our rung-2 output is an INT8xINT8->INT32 dot product.  Integer addition is
associative and exact, so a correct device's scores are bit-identical on any
hardware.  We therefore keep TOPLOC's *compression* (2 bytes per committed
point) and drop its *tolerance* (exact equality, not a mantissa-error
threshold).

Measures: proof size, build cost, verify cost, and whether a tampered result
is caught.  Reuses the exact hypervector construction from S5.

Pure stdlib + numpy.  Deterministic.
"""

import hashlib
import json
import random
import sys
import time

import numpy as np

sys.path.insert(0, "../S5_hdc_prototype")

D = 1024                # S5's recommended operating point
N_TRIPLES = 100_000
N_PRED, N_SUBJ, N_OBJ = 10, 1_000, 1_000
N_QUERIES = 20
SEED = 0xC0FFEE
# scores live in [-2D, 2D] = [-2048, 2048]; the modulus must exceed the value
# range *and* the index range so both are injective.  TOPLOC uses 65497 (the
# largest prime below 2^16); it works here unchanged.
MOD = 65497


# ---------------------------------------------------------------- Newton / GF(p)
def newton_coefficients(xs, ys, mod=MOD):
    """Divided differences mod p.  Mirrors toploc/C/csrc/ndd.cpp."""
    n = len(xs)
    dd = [y % mod for y in ys]
    for k in range(1, n):
        for i in range(n - 1, k - 1, -1):
            denom = (xs[i] - xs[i - k]) % mod
            dd[i] = (dd[i] - dd[i - 1]) * pow(denom, mod - 2, mod) % mod
    return dd


def newton_eval(coeffs, xs_nodes, x, mod=MOD):
    """Horner over the Newton basis."""
    acc = 0
    for i in range(len(coeffs) - 1, -1, -1):
        acc = (acc * (x - xs_nodes[i]) + coeffs[i]) % mod
    return acc


def is_prime(n):
    if n < 2 or n % 2 == 0:
        return n == 2
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


def find_injective_modulus(xs, start=MOD, require_prime=True):
    """TOPLOC's trick (poly.py:find_injective_modulus): walk down from the
    largest 16-bit prime until the committed indices stay distinct mod m.
    Triple indices run to 100k, so a search is mandatory here — unlike
    TOPLOC's activation indices, ours always exceed the modulus.

    require_prime is OURS, not TOPLOC's.  Their loop returns the first m with
    distinct residues whether or not m is prime, but the divided-difference
    recurrence inverts denominators with Fermat's little theorem, which needs
    a prime modulus.  With composite m the inverse is wrong (or undefined) and
    an honest proof fails to verify.  See RESULT.md."""
    for m in range(start, 2 ** 15, -1):
        if require_prime and not is_prime(m):
            continue
        if len({x % m for x in xs}) == len(xs):
            return m
    raise ValueError("no injective modulus found")


def build_commitment(indices, values, mod=None):
    ints = [int(i) for i in indices]
    mod = mod or find_injective_modulus(ints)
    xs = [i % mod for i in ints]
    ys = [int(v) % mod for v in values]
    return newton_coefficients(xs, ys, mod), xs, mod


def verify_commitment(coeffs, nodes, mod, indices, values):
    """Exact check: every recomputed (index, score) must sit on the polynomial."""
    for i, v in zip(indices, values):
        if newton_eval(coeffs, nodes, int(i) % mod, mod) != int(v) % mod:
            return False
    return True


# ---------------------------------------------------------------- the workload
def bipolar(rng, rows, dim):
    return (rng.integers(0, 2, size=(rows, dim), dtype=np.int8) * 2 - 1).astype(np.int8)


def workload():
    rng = np.random.default_rng(SEED)
    R = bipolar(rng, 3, D)
    P, S, O = bipolar(rng, N_PRED, D), bipolar(rng, N_SUBJ, D), bipolar(rng, N_OBJ, D)
    tp = rng.integers(0, N_PRED, N_TRIPLES)
    ts = rng.integers(0, N_SUBJ, N_TRIPLES)
    to = rng.integers(0, N_OBJ, N_TRIPLES)
    acc = (R[0] * P[tp]).astype(np.int8)
    acc += R[1] * S[ts]
    acc += R[2] * O[to]
    T = np.sign(acc, dtype=np.int8, casting="unsafe")

    truth = {}
    for row, (p, s) in enumerate(zip(tp.tolist(), ts.tolist())):
        truth.setdefault((p, s), []).append(row)
    keys = sorted(truth.keys())
    pick = rng.choice(len(keys), size=N_QUERIES, replace=False)
    qkeys = [keys[i] for i in sorted(pick.tolist())]

    Q = np.empty((N_QUERIES, D), dtype=np.int8)
    for i, (p, s) in enumerate(qkeys):
        Q[i] = R[0] * P[p] + R[1] * S[s]
    scores = (Q.astype(np.float32) @ T.astype(np.float32).T).astype(np.int32)
    return scores, T


def main():
    scores, T = workload()
    out = {"config": {"D": D, "n_triples": N_TRIPLES, "n_queries": N_QUERIES,
                      "modulus": MOD}, "by_k": {}}

    for k in (8, 16, 32, 64, 128):
        t_build = t_verify = 0.0
        sizes, ok, caught = [], 0, 0
        rng = random.Random(SEED)
        for qi in range(N_QUERIES):
            row = scores[qi]
            idx = np.argpartition(-row, k)[:k]
            idx = idx[np.argsort(-row[idx])]
            val = row[idx]

            t0 = time.perf_counter()
            coeffs, nodes, mod = build_commitment(idx, val)
            t_build += time.perf_counter() - t0
            # 2 B per coefficient + 2 B per node index + 2 B for the modulus
            sizes.append(2 * len(coeffs) + 2 * len(nodes) + 2)

            t0 = time.perf_counter()
            ok += verify_commitment(coeffs, nodes, mod, idx, val)
            t_verify += time.perf_counter() - t0

            # adversary: flip one score by 1 and re-verify
            bad = val.copy()
            bad[rng.randrange(k)] += 1
            caught += not verify_commitment(coeffs, nodes, mod, idx, bad)

        out["by_k"][k] = {
            "proof_bytes_mean": sum(sizes) / len(sizes),
            "full_scores_bytes": int(scores.shape[1] * 4),
            "compression_vs_full_scores": round(scores.shape[1] * 4 / (sum(sizes) / len(sizes)), 1),
            "build_ms_per_query": round(t_build / N_QUERIES * 1e3, 3),
            "verify_ms_per_query_excl_recompute": round(t_verify / N_QUERIES * 1e3, 3),
            "honest_accepted": f"{ok}/{N_QUERIES}",
            "tampered_rejected": f"{caught}/{N_QUERIES}",
        }

    # cost of the thing the verifier cannot avoid: recomputing the matmul
    t0 = time.perf_counter()
    _ = (np.ones((1, D), dtype=np.float32) @ T.astype(np.float32).T)
    out["recompute_ms_one_query"] = round((time.perf_counter() - t0) * 1e3, 2)
    out["digest_scores"] = hashlib.sha256(scores.tobytes()).hexdigest()
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
