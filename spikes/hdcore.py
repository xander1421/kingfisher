#!/usr/bin/env python3
"""The S5 encoding, factored out so S9..S12 measure the same thing S5 did.

Lifted verbatim in behaviour from spikes/S5_hdc_prototype/hdc.py (same seed,
same construction) so that any divergence in results is a divergence in the
experiment, not in the setup.

  atomic vectors  bipolar +-1 int8
  bind            elementwise multiply
  bundle          majority sum (sign); 3 odd terms => no ties
  triple (p s o)  T = sign(Rp*P[p] + Rs*S[s] + Ro*O[o])
"""

import hashlib

import numpy as np

SEED = 0xC0FFEE
N_PRED, N_SUBJ, N_OBJ = 10, 1_000, 1_000

# Slot indices into the role codebook R.
PRED, SUBJ, OBJ = 0, 1, 2


def bipolar(rng, rows, dim):
    return (rng.integers(0, 2, size=(rows, dim), dtype=np.int8) * 2 - 1).astype(np.int8)


def sha(*arrays):
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def codebooks(rng, D, n_pred=N_PRED, n_subj=N_SUBJ, n_obj=N_OBJ):
    return (bipolar(rng, 3, D), bipolar(rng, n_pred, D),
            bipolar(rng, n_subj, D), bipolar(rng, n_obj, D))


def zipf_ids(rng, n, k, a):
    """n draws from a Zipf(a) distribution over k ids, most frequent = id 0.

    numpy's `zipf` is unbounded, so sample the normalised head directly.
    """
    w = 1.0 / np.arange(1, k + 1, dtype=np.float64) ** a
    return rng.choice(k, size=n, p=w / w.sum())


def triples(rng, n, n_pred=N_PRED, n_subj=N_SUBJ, n_obj=N_OBJ, zipf_a=None):
    """Uniform triples, or Zipf-skewed subjects/objects when zipf_a is set."""
    tp = rng.integers(0, n_pred, n)
    if zipf_a is None:
        ts = rng.integers(0, n_subj, n)
        to = rng.integers(0, n_obj, n)
    else:
        ts = zipf_ids(rng, n, n_subj, zipf_a)
        to = zipf_ids(rng, n, n_obj, zipf_a)
    return tp, ts, to


def encode(R, P, S, O, tp, ts, to, D, chunk=None):
    """T[i] = sign(Rp*P[tp_i] + Rs*S[ts_i] + Ro*O[to_i]), int8."""
    n = len(tp)
    chunk = chunk or max(1000, min(100_000, 100_000_000 // D))
    T = np.empty((n, D), dtype=np.int8)
    for i in range(0, n, chunk):
        j = min(i + chunk, n)
        acc = (R[PRED] * P[tp[i:j]]).astype(np.int8)
        acc += R[SUBJ] * S[ts[i:j]]
        acc += R[OBJ] * O[to[i:j]]
        T[i:j] = np.sign(acc, dtype=np.int8, casting="unsafe")
    return T


def score(Q, T, chunk=None):
    """Q @ T.T as int32.

    numpy has no integer BLAS, so this runs in float32.  Every reachable value
    is |v| <= 3*D; float32 holds integers exactly to 2**24, so the result is
    integer-exact for any D we can fit in memory.  S12 verifies that claim
    against a true int32 reference rather than asserting it.
    """
    n = T.shape[0]
    D = T.shape[1]
    chunk = chunk or max(1000, min(100_000, 100_000_000 // D))
    Qf = np.ascontiguousarray(Q, dtype=np.float32)
    out = np.empty((Q.shape[0], n), dtype=np.int32)
    for i in range(0, n, chunk):
        j = min(i + chunk, n)
        out[:, i:j] = (Qf @ T[i:j].astype(np.float32).T).astype(np.int32)
    return out
