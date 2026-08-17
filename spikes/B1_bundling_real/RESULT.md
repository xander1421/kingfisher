# B1 — bundling compression vs recall on a real KG. The VTCM premise is met at B=16.

**Verdict: GREEN. The unmet link in the NPU chain is now measured, and it holds. Bundling to B=16 fits an 800k-triple shard inside VTCM at a p90 cost of 0.2% of the store checked. The requirement was never 54×; it is 16×.**

The LEDGER recorded this as unmeasured: *"Bundling's magnitude on real data: 54×
was B=1→B=64 compression; S52 measured clustering-vs-random only."* It is the
**first link in the VTCM chain**, and S72b made it decisive — a bandwidth-bound
kernel cuts toward the NPU *only* through on-chip residency, and residency needs
the store to fit 8 MB.

Reports **ratios and recall, never a duration** — runs through a refused host
gate, same property as S61 and Q1. Artefacts: `bundling.py` (stdlib, seed
20260817), `bundling.json`.

## Measured — FB15k-237, 272,115 triples, D=1024, `(pred,subj)` clustering

| B | bundles | store MB | compression | % store checked (median) | p90 |
|---|---|---|---|---|---|
| 1 | 272,115 | 34.83 | 1× | 0.00% | 0.0% |
| 4 | 68,029 | 8.71 | 4× | 0.00% | 0.0% |
| 8 | 34,015 | 4.35 | 8× | 0.00% | 0.2% |
| 16 | 17,008 | 2.18 | 16× | 0.00% | 0.2% |
| 32 | 8,504 | 1.09 | 32× | 0.00% | 0.5% |
| **64** | 4,252 | 0.54 | 64× | **0.17%** | 1.2% |
| 128 | 2,126 | 0.27 | 128× | 0.50% | 3.2% |

**Provenance check:** B=1 gives 34.83 MB for 272,115 triples. S11 reported
102.4 MB for 800,000. `102.4 × 272115/800000 = 34.83`. Exact. And B=64 gives a
median 0.17% store checked against **S52's measured 0.2%** for the same
clustering and shape — an independent cross-check on a different instrument.

## The answer, scaled to the shard the 12.8 MB figure means
The LEDGER's "12.8 MB packed store" is a **B=8 index over 800,000 triples**.
Scaling:

| B | 800k-triple store | fits 8 MB VTCM |
|---|---|---|
| 8 | 12.79 MB | no |
| **16** | **6.40 MB** | **YES** |
| 32 | 3.20 MB | YES |

> **B=16 fits VTCM, and costs a p90 of 0.2% of the store checked.**

So the premise is met at **16× compression, not the 54× the LEDGER treats as the
open question**. The compression/recall curve is nearly flat to B=32 — the
target bundle is the top scorer in the median case all the way out — and only
starts to bite at B=128.

## Consequence for the NPU descope
S72b made the NPU *conditionally* relevant again, on an unmeasured premise.
**The premise now holds.** The chain is:

```
kernel is bandwidth-bound at 4 workers   (S72b, measured)
  -> only on-chip residency helps        (S18's point, unchanged)
    -> residency needs the store in 8 MB VTCM
      -> B=16 puts an 800k shard at 6.40 MB   (B1, measured)  <- was the gap
```

This does **not** revive the NPU. The ladder argument is untouched — no SDK, no
vendor delegate, no scale pinning, no QNN licence, no cross-vendor
requantisation measurement, and the prefilter still costs ~50 µs inside a query
that is ~57% symbolic. What changed is that the *throughput* counter-argument now
has no unmeasured link in it, and the descope rests on the ladder alone with no
remaining technical objection unanswered.

## The instrument defect, caught before publication
The first metric was *"does the target bundle score above the median of 64
random bundles?"* — **100% at every B**, unable to discriminate. It is trivially
true of a bundle that contains the answer. Replaced with the rank-based quantity
S52 actually reports: what fraction of the store the exact stage must check.
Same failure shape as the W1 controls, caught by the curve being flat rather
than by the number being wrong.

## Controls, with failing inputs (D6)
| control | fails if |
|---|---|
| B=1 store matches S11 scaled | ≠ 34.83 MB — would mean a different encoding than S11 measured |
| B=64 median matches S52 | ≠ ~0.2% — would mean a different query or clustering than S52 |
| curve is monotone in B | non-monotone means the metric is not measuring compression cost |
| B=1 checks 0% of store | if B=1 required checking anything, the scoring is broken |

All four hold.

## Caveats
- Recall proxy is rank against a 600-bundle sample, not an exhaustive rank.
- Queries are S52's uniform-over-triples draw — the `Δ` artefact, again.
- One clustering, one corpus, D=1024 only.
- Fitting VTCM is necessary for residency, **not sufficient**: nothing here shows
  an HVX kernel exists, and no NPU code has run in this workspace.

---

# B1b — the ternary/sign(0) hazard. Real, and worst at the B I recommended.

**Checked after a reviewer flagged it. Bits-per-dimension is correct; tie-handling is not benign, and it moves the recommendation from B=16 to B=32.**

## Bits per dimension — verified, no ternary hazard in the store
`store_bytes = nb * WORDS * 8` = 128 B per bundle at D=1024 = **1 bit/dim**. It
reconciles all three published figures exactly:

| source | computed | published |
|---|---|---|
| S11 B=1, 800k triples | 102.4 MB | 102.4 |
| S11 B=8, 800k triples | 12.80 MB | 12.8 |
| S34 B=1, 100k rows packed | 12.8 MB | 12.8 |

And the store needs no second bit: `realkg.c:80` is
`vandq_u64(veorq_u64(t,s), m)` where `t` is the store, `s` the query sign and
**`m` the query mask**. The mask is query-side only. If the store were ternary
and needed 2 bits/dim, every figure above would double and **B=16 would not fit
VTCM** — so this was the right thing to check.

## sign(0) — the tie-break is biased, and the bias peaks where it matters
`bundling.py:77` is `if ones * 2 > m: v |= 1 << bit`, so an exact tie resolves to
**0**. Measured over 300 bundles per B, sampling 1 bit in 8:

| B | tie rate | set-bit fraction | imbalance vs 0.5 |
|---|---|---|---|
| 4 | 19.60% | 0.411 | 0.089 |
| 8 | 12.34% | 0.444 | 0.056 |
| **16** | **7.66%** | **0.454** | **0.046** |
| 32 | 3.15% | 0.486 | 0.014 |
| 64 | 1.00% | 0.503 | 0.003 |

At **B=16 — the value I recommended — 7.66% of dimensions are ties, all broken
one way**, giving a 4.6-point sign imbalance. It is the worst of the
VTCM-viable options.

### What it does and does not break
- **Ranking: unharmed, and measured.** The bias shifts every bundle by roughly
  the same constant, so the rank-based recall in B1 above is unaffected — B=16
  still showed median 0% / p90 0.2%.
- **A fixed cutoff: harmed.** A constant score offset is exactly what a fixed
  threshold cannot absorb, and S52 already records that *a fixed cutoff cannot
  reach recall 1.0 on a bundled store*. This adds to that problem rather than
  being independent of it.
- **Determinism: fine.** Breaking ties always to 0 is reproducible, which is
  what Tier A needs. A random tie-break would be worse.

## Revised recommendation: B=32, not B=16

| | B=16 | **B=32** |
|---|---|---|
| 800k-triple store | 6.41 MB | **3.20 MB** |
| fits 8 MB VTCM | yes | **yes, with 2× headroom** |
| tie rate | 7.66% | **3.15%** |
| sign imbalance | 0.046 | **0.014** |
| p90 store checked | 0.2% | 0.5% |

B=32 costs 0.3 points of p90 shortlist and buys **2.4× fewer ties, 3× less
imbalance, and twice the VTCM headroom**. The VTCM conclusion is unchanged and
strengthened — the premise holds with room, not marginally.

## The proper fix, not applied here
Break ties by a **content-derived rule** — e.g. bit *i* of a hash of
`(bundle_id, dim)` — rather than always to 0. That removes the bias while
staying deterministic. Not applied because it changes the encoding, which is a
D2 canonical-form decision, not a measurement change.

---

# B1c — the encoding was a choice, and B1 asserted it without saying so

**The arithmetic is right for the encoding implemented. The encoding itself is a design decision B1 never flagged, and under any ternary-preserving alternative B=16 stops fitting VTCM. B=32 fits under all three.**

## What the reference engine actually stores — verified
`realkg.c:152-162`:
```c
for(int bit=0;bit<64;bit++){
    int ones=0;
    for(int k=lo;k<hi;k++) ones += (base[order[k]*WORDS+w]>>bit)&1ULL;
    if(ones*2>m) out |= 1ULL<<bit;          // ties -> clear
}
bundle[b*WORDS+w]=out;                       // uint64_t: 1 bit/dim
```
`bundling.py` reproduces this construction exactly, so **B1's store sizes are a
correct model of what is implemented**, and the S11 provenance check passing at
B=1 was not luck.

## But `sign(Σ)` is ternary, and the implementation discards the third state
A bundle is `sign(Σ)`, and `sign(0)` is a **third value**. The reference collapses
it to −1. That is a legitimate encoding choice, and B1 presented `1 bit/dim` as
a fact rather than as the consequence of that choice. Two alternatives preserve
the zero, at these costs on an 800k-triple shard using **B1b's measured tie
rates on FB15k-237**:

| B | binary (implemented) | + sparse zero-mask | full second plane | fits 8 MB VTCM |
|---|---|---|---|---|
| 8 | 12.80 MB | 28.60 MB | 25.60 MB | no / no / no |
| **16** | **6.40 MB** | **11.30 MB** | **12.80 MB** | **YES / no / no** |
| **32** | **3.20 MB** | **4.21 MB** | **6.40 MB** | **YES / YES / YES** |
| 64 | 1.60 MB | 1.76 MB | 3.20 MB | yes / yes / yes |

**So "satisfiable at 16×" was encoding-dependent. "Satisfiable at 32×" is not.**

Note the sparse zero-mask only beats a full second plane below a ~10% tie rate
(10 bits per zero index vs 1 bit per dimension), which is why it is worse than
two-plane at B=8 and better at B≥16.

## Two independent routes reached B=32
B1b moved off B=16 because of **sign-bias** (7.66% ties, 4.6pt imbalance). B1c
moves off it because of **encoding robustness**. Same answer, unrelated reasons —
which is the kind of convergence that was manufactured in S70 and is genuine
here, because the two arguments share no input.

## Tie rates: mine differ from S11's
The reviewer cited S11's 0.064 / 0.024 / 0.005 at B=16/32/64. B1b measured
**0.0766 / 0.0315 / 0.0100** on FB15k-237 — consistently higher. B1b's are the
real-data numbers and are the ones used above; the discrepancy is unexplained
and worth a line if S11's construction is ever revisited.

## What is unaffected
The NPU descope. It never depended on this, and B=32 still closes the residency
link with 2× headroom under the most pessimistic encoding.
