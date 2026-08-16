# S48 — a shard shaped for yesterday's queries: the mismatch matrix

**Verdict: GREEN, and it gives M4 the economic property it needed. Shaping has an asymmetric payoff — up to 24× upside, with the downside bounded at roughly "no shaping at all".**

S47 answered AGENT-1's C3 with a single mismatched shape and I flagged its own limit: the question that decides M4 is not one mismatch, it is what happens when the query distribution *moves after the shard is laid out*. Shaping is sold as "a job whose product makes all future jobs cheaper." If that decays with drift, "all future jobs" has a half-life.

Complete version: cluster by each of the three key pairs, query each of the three two-bound shapes, B=64, cutoff swept so **every cell is at recall 1.0**. Diagonal = the shaper guessed right; off-diagonal = drift; RANDOM = the no-shaping floor.

## The matrix — total µs per query (prefilter + exact-check at 1.29 ns/row)

| cluster key | `(p s ?o)` | `(p ?s o)` | `(?p s o)` |
|---|---|---|---|
| **(pred,subj)** | **4.7** | 16.6 | 10.5 |
| **(pred,obj)** | 13.3 | **7.1** | 22.3 |
| **(subj,obj)** | 4.1 | **127.8** | **4.0** |
| RANDOM (no shaping) | 107.1 | 127.4 | 4.2 |

Diagonal mean **5.3 µs**. Worst mismatch **127.8 µs**. **Decay 24.2×.**

## Four findings, in order of how much they matter

### 1. The downside of shaping wrong is bounded at "no shaping"
The worst cell in the matrix — clustering by `(subj,obj)` and then being asked `(p ?s o)` — costs **127.8 µs against random's 127.4 µs**. Identical to within noise.

**A shard shaped for the wrong queries is no worse than a shard nobody shaped.** That is the property that makes shaping viable as a *speculative, paid* job class: the shaper is making a bet about future queries, and a lost bet costs the network nothing beyond the shaping work itself, while a won bet is worth up to 24×. Asymmetric payoff with a floor is exactly what you can price and sell.

### 2. What actually drives the benefit is prefix coverage, not "matching"
The diagonal is not the best cell in every column. Clustering by `(subj,obj)` beats clustering by `(pred,subj)` on the `(p s ?o)` query (4.1 vs 4.7), even though the latter is the "matched" key.

The rule the matrix reveals: **the benefit depends on how much of the query's bound set is covered by a *prefix* of the cluster key.** A sort by `(subj,obj)` is primarily a sort by `subj`, so any query binding `subj` gets contiguous candidates regardless of the second field. The catastrophic cell is the one where the query's bound slots (`pred`,`obj`) intersect the key's prefix (`subj`) not at all.

That is directly actionable for a shaper: **choose the cluster key to maximise expected prefix coverage over the query distribution**, which is a different and cheaper optimisation than trying to match whole query shapes.

### 3. Highly selective queries do not need shaping at all
The `(?p s o)` column is nearly flat, and **random (4.2 µs) beats two of the three shaped layouts** (10.5 and 22.3). Binding `subj` and `obj` over 1,000×1,000 is almost unique, so the prefilter isolates the answer whatever the layout, and shaping only adds scatter.

Marketplace consequence: **a shard whose query mix is dominated by highly selective patterns should not pay for shaping.** The shaping job class has a domain, and the matcher can tell whether a shard is in it before commissioning the work.

### 4. Drift is real and expensive when it happens
Matched cells are 4.7–7.1 µs; the worst drifted cell is 127.8 µs — **24×**. So the value of shaping decays sharply, not gracefully, once the query distribution moves far enough to change which key is right. Combined with finding 1, the shape of the risk is: *shaping rarely hurts, but it stops helping abruptly.*

That argues for **re-shaping as a recurring job rather than a one-off**, priced against observed query drift — which conveniently is a recurring revenue line for the same job class, and something the DAS attention broker's per-atom importance signal could drive.

## What this does to M4
`ADDENDUM.md` said M4 had lost both its justifications (S13 killed the crossover, S17 killed the recall argument). S47 restored a number (6.9–12.8×). S48 adds the two things a *job class* needs beyond a speedup:

- a **bounded downside** (finding 1), so the bet is priceable;
- a **domain test** (finding 3), so the market knows which shards to commission it for.

## Caveats
- Uniform synthetic triples. Under a power-law distribution hot patterns dominate and clustering should matter *more*, not less — untested.
- One literal per query shape (`tp_[42]` etc.), not an average over many queries. The `(?p s o)` column's flatness in particular depends on `(subj,obj)` being near-unique, which is a property of NSUBJ×NOBJ = 10⁶ against 10⁵ triples.
- B=64 only; the matrix at other bundle factors is unmeasured.
- Single-threaded, inline, no pool (S46's lesson), so no harness floor contaminates these numbers.
- "Decay 24.2×" compares the worst mismatch against the diagonal *mean*; against the best diagonal cell (4.7) it is 27×.
