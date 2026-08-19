#!/usr/bin/env python3
"""G94 F3 — is the per-key argmax MANUFACTURING the ensemble gain?

The AGENT-2 lane's falsifier, and stronger than either of mine: F1 and F2 both
compare the mix to a baseline, and neither can distinguish

    "the arms carry the gain"   from   "the argmax over routing keys makes it".

G81 already measured that 97.75% of G77's +0.0067 sat inside valid-picked
DistMult keys and 2.85% in the 210-key default, so the selector holds the mass —
and it has never been nulled. G56 nulled G54 against a random MASK (0/1000 >=
0.2313, median 0.2031), but a K-way argmax over per-(predicate, direction) keys
has strictly MORE selection freedom than a mask.

THE NULL: shuffle the ARM LABELS within each routing key, re-select, repeat.
The arms keep their per-query ranks; only which arm each key is allowed to call
"best" is permuted. If the shuffled selector reaches the real selector's score,
the gain is the freedom to choose, not the thing chosen.

V1 WAS DEGENERATE AND THE TELL WAS sd = 0.000000 OVER 200 DRAWS. It permuted
the rows of R per key and then took argmax over all of them. argmax picks the
best arm regardless of which index it sits at, so the permutation was a no-op:
null mean == real == 0.347511 exactly, 200/200. A randomisation that leaves the
statistic bit-identical is not a randomisation, and "the null reaches the real
score" was true by construction rather than by measurement. It would have read
as F3 FIRING with maximum confidence.

V2 WAS ALSO A NO-OP, PROVABLY. It permuted the A-evidence vector, took argmax,
then mapped the winner back through the SAME permutation:
perm[k][argmax(ev[perm[k]])] == argmax(ev). Identity. The sd fell from exactly
0.000000 to 0.000026 — tie-breaking noise only — and it still "fired" 144/200.
Two different no-op nulls both reported F3 FIRING with confidence.

THE LESSON, and it is the reason this file carries its own history: a label
permutation that the statistic is INVARIANT UNDER is not a null. The check is
not "did I shuffle something" but "can the shuffle change the answer" — and both
v1 and v2 failed it while producing a decisive-looking p.

V3 REMOVES THE EVIDENCE INSTEAD OF RELABELLING IT. Real: each key picks the arm
with the best half-A reciprocal rank, scored on half B. Null: each key picks an
arm UNIFORMLY AT RANDOM, scored on half B. That asks the actual question — is
the half-A evidence informative about half B, or does having K arms to choose
between carry the gain on its own?

V2 SPLIT THE QUERIES. Selection happens on half A, scoring on half B, so the
selector's choice is made on data it is not scored against. Now a label shuffle
in A genuinely changes which arm each key picks, and the permutation can bite.
This also removes v1's oracle inflation.

THIS SELECTS ON TEST, deliberately. Selecting on test and scoring on test is
ORACLE selection and is inflated by construction — that is the point. It is the
CEILING of what a selector can extract. If even the ceiling is matched by
shuffled labels, no valid-selected version can be carrying arm quality either.
Reported as a ceiling, never as an achievable score.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 0xC0FFEE
DRAWS = 200

z = np.load(os.path.join(HERE, "ranks_pd.npz"), allow_pickle=True)
arms = {"distmult": z["dm"].astype(np.float64),
        "g51": z["g51"].astype(np.float64),
        "prior": z["prior"].astype(np.float64)}
dirs = z["pg_dirs"]
test_p = z["test_p"]
n = len(next(iter(arms.values())))
# ranks are per (query, direction); test_p is per test triple. Two directions
# per triple, so the key array must be built to match the rank length.
preds = np.repeat(test_p, 2) if n == 2 * len(test_p) else test_p[:n]
side = (dirs if len(dirs) == n else np.tile([0, 1], len(test_p))[:n])
keys = np.array([f"{p}|{d}" for p, d in zip(preds, side)])

def mrr(r):
    r = np.asarray(r, dtype=np.float64)
    ok = r > 0
    return float(np.where(ok, 1.0 / np.maximum(r, 1), 0.0).sum() / len(r))

names = list(arms)
R = np.vstack([arms[a] for a in names])          # (K, n)
print(f"arms {names}  queries {n}  routing keys {len(set(keys))}")
for a in names:
    print(f"  {a:<10}{mrr(arms[a]):.6f}")

uk = {k: np.where(keys == k)[0] for k in set(keys)}

rr = np.where(R > 0, 1.0 / np.maximum(R, 1), 0.0)     # (K, n) reciprocal ranks
rng0 = np.random.default_rng(SEED)
half = rng0.random(n) < 0.5                            # A = select, B = score

def select_score(perm):
    """perm=None -> real selector (argmax on half A). perm[k]=arm -> null."""
    tot = cnt = 0.0
    for k, idx in uk.items():
        a = idx[half[idx]]
        b = idx[~half[idx]]
        if len(a) == 0 or len(b) == 0:
            continue
        if perm is None:                                 # REAL: use A-evidence
            pick = int(np.argmax(rr[:, a].sum(axis=1)))
        else:                                            # NULL: ignore it
            pick = int(perm[k])
        tot += rr[pick, b].sum()
        cnt += len(b)
    return tot / cnt if cnt else 0.0

real = select_score(None)
print(f"\nper-key selector, chosen on half A and scored on half B: {real:.6f}")
best_single = max(rr[i][~half].sum() / (~half).sum() for i in range(len(names)))
print(f"best single arm on the SAME half B                       : {best_single:.6f}")
print(f"selector gain over best single                           : {real-best_single:+.6f}")

rng = np.random.default_rng(SEED)
null = []
for i in range(DRAWS):
    perm = {k: int(rng.integers(len(names))) for k in uk}
    null.append(select_score(perm))
null = np.array(null)
ge = int((null >= real).sum())
print(f"\nF3 NULL — each key assigned a RANDOM arm (A-evidence discarded), {DRAWS} draws")
print(f"  null mean {null.mean():.6f}  sd {null.std():.6f}  "
      f"min {null.min():.6f}  max {null.max():.6f}")
print(f"  >= real: {ge}/{DRAWS}   p = {(ge+1)/(DRAWS+1):.4f} "
      f"(floor {1/(DRAWS+1):.4f})")
fired = ge > 0.05 * DRAWS
print(f"\nF3 {'FIRES' if fired else 'does NOT fire'} — random per-key assignment "
      f"{'matches' if fired else 'does NOT match'} evidence-based selection, so the "
      f"gain is {'the freedom to choose, not the half-A evidence' if fired else 'carried by the arms, not by selector freedom'}")
json.dump({"arms": {a: mrr(arms[a]) for a in names}, "oracle_selector": real,
           "best_single": best_single, "gain": real - best_single,
           "null_mean": float(null.mean()), "null_max": float(null.max()),
           "ge": ge, "draws": DRAWS, "p": (ge + 1) / (DRAWS + 1),
           "f3_fired": bool(fired), "seed": SEED,
           "note": "test-selected oracle ceiling, not an achievable score"},
          open(os.path.join(HERE, "f3.json"), "w"), indent=1)
