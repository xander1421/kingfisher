# S5 — INT8 hypervector pre-filter + exact verification

**Verdict: GREEN, and the strongest result of the mission.** For the canonical variable query, the "approximate" NPU pre-filter turns out to be **exactly lossless with an analytically known cutoff** — recall 1.0 with **zero false positives**, at every dimension tested down to D=256.

Code: `hdc.py` (numpy only, ~180 lines). Runner: `.venv/bin/python hdc.py [D]`. Summary: `summarize.py`.

## Setup
- D = 10,000 bipolar (±1) INT8 hypervectors; `bind` = elementwise multiply, `bundle` = majority sum, `sim` = dot product.
- 100,000 synthetic triples `(pred subj obj)` over 10 predicates × 1,000 subjects × 1,000 objects.
- Triple: `T = sign(R_p ⊙ P[p] + R_s ⊙ S[s] + R_o ⊙ O[o])`. Three odd terms ⇒ the sum is odd ⇒ the majority never ties.
- Query `(p s ?x)`: `Q = R_p ⊙ P[p] + R_s ⊙ S[s]`, left unnormalised (values in {−2, 0, +2}).
- 100 queries, each drawn from `(p,s)` pairs that actually occur. Answers per query: min 2, max 21, mean 10.3 (1,031 true matches total).
- Seeded (`0xC0FFEE`); every array digested with SHA-256.

## The main result — the pre-filter is not approximate

For a triple that matches both bound slots, every dimension where the two bound role-filler products **agree** (`Q_d = ±2`) survives the majority sign and contributes exactly +2; every dimension where they **disagree** (`Q_d = 0`) contributes 0. So

> **score(matching triple) = 2 · |{d : Q_d ≠ 0}|, identically, for every match — and that number is computable from the query alone, before touching any data.**

Measured across all 100 queries and all 1,031 true matches:
```
every_match_scores_exactly_2x_nonzero_dims : true
recall_at_threshold                        : 1.0
false_positives_total                      : 0
true_matches_total                         : 1031
```
So the shortlist is not a heuristic top-k — it is `score ≥ threshold`, with recall provably 1.0 and (measured) no false positives to discard. The CPU stage confirms rather than rescues.

Score separation (query 0): matches **10,040** (all of them, exactly); non-matches mean 481, σ 1,525, **max 5,472** — a 1.8× gap between the worst non-match and the exact match score.

## Top-k behaviour (if you use a rank cutoff instead of the threshold)

| k | recall@k (mean) | recall@k (min) | queries at recall 1.0 | precision@k | candidate reduction |
|---|---|---|---|---|---|
| 10 | 0.8948 | 0.4762 | 56/100 | 0.877 | 10,000× |
| **50** | **1.0000** | **1.0000** | **100/100** | 0.206 | **2,000×** |
| 100 | 1.0000 | 1.0000 | 100/100 | 0.103 | 1,000× |
| 500 | 1.0000 | 1.0000 | 100/100 | 0.021 | 200× |

k=10 loses answers only because some queries have up to 21 answers — a rank cutoff below the answer count cannot be complete. k=50 covers the largest answer set here and is perfect. **The threshold rule dominates top-k**: it needs no k, adapts per query, and is exact.

## Dimension sweep — this fits on a phone

| D | INT8 store for 100k triples | threshold exact | false positives | recall@50 | worst non-match | threshold | matmul (100 queries × 100k triples) |
|---|---|---|---|---|---|---|---|
| 256 | **26 MB** | ✓ | 0 | 1.0000 | 192 | 214 | 0.09 s |
| 512 | 51 MB | ✓ | 0 | 1.0000 | 364 | 442 | 0.14 s |
| **1024** | **102 MB** | ✓ | 0 | 1.0000 | 656 | 960 | 0.37 s |
| 2048 | 205 MB | ✓ | 0 | 1.0000 | 1,266 | 1,922 | 0.15 s |
| 4096 | 410 MB | ✓ | 0 | 1.0000 | 2,360 | 3,932 | 1.32 s |
| 10000 | 1,000 MB | ✓ | 0 | 1.0000 | 5,472 | 9,746 | 7.73 s |

The exactness of the threshold is **independent of D** (it's algebraic, not statistical). What D buys is *margin*: the worst-non-match / threshold ratio is 0.90 at D=256 and 0.56 at D=10000. **D=1024 looks like the operating point** — 102 MB for a 100k-triple shard, a 0.68 margin, and a matmul small enough to be uninteresting.

## Determinism
Two consecutive runs, digests compared field by field:
```
codebooks  678375…  identical
triples    e2b291…  identical
encoded_T  1bd5b2…  identical
queries    de0245…  identical
scores     995dec…  identical
by_k identical · separation identical · only `timing_s` differs
```
Byte-identical. Note the matmul runs in float32 (numpy has no integer BLAS), but every reachable value is |score| ≤ 2D = 20,000, which float32 represents exactly — the result is integer-exact, and re-running reproduces it bit for bit. On a real NPU this is a native INT8 → INT32 accumulate, which is exact by construction.

## Throughput
Warm: 100 queries × 100k triples × D=10,000 = 2×10¹¹ MACs in 0.57 s ≈ **353 GOP/s** on the laptop CPU via Accelerate. Cold-cache runs measured 26–60 GOP/s; the variance is memory bandwidth on the 1 GB INT8 array, not arithmetic — which is exactly the argument for shrinking D and for locality-aware layout (§"the beak").

## What this does NOT show — stated plainly
1. **One vector per triple is not a compression scheme.** 100k triples at D=1024 costs 102 MB, versus a few MB for the raw triples. The win here is *throughput and dataflow* (one dense INT8 matmul the NPU can eat), not storage. The compressive version — bundling many triples into one vector per bucket — reintroduces superposition noise and is where recall actually starts to cost something. Not tested; it is the obvious next spike.
2. **Only one pattern class was tested**: exactly two bound slots, one free variable, no repeated variables, no nesting. Patterns with two free slots, repeated variables (`(likes $x $x)`), or nested expressions do not have this clean algebra and will be genuinely approximate.
3. **No NPU was involved.** This ran on a laptop CPU. The claim "an NPU can do this" rests on the operation being a plain INT8 GEMM with INT32 accumulate, which is the one thing every NPU does well — but the Core ML / LiteRT path is unmeasured (that is the S7/M2 work).
4. Uniform random triples are the easy case. Real knowledge graphs are power-law: a few subjects appear in a huge fraction of triples, which changes the answer-set-size distribution (and so the k needed, if one insisted on top-k) but not the threshold algebra.
