# S47 — the bundling trade priced on both sides, on device, and AGENT-1's C3 answered

**Verdict: GREEN. Bundling is worth 54× on total query cost, clustering is worth 12.8× of that, and clustered bundling does NOT collapse when the query shape does not match the cluster key — it degrades from 54× to 15×.**

This is the measured justification for M4 that `ADDENDUM.md` said had been refuted twice: S13 killed the crossover argument, S17 killed the recall argument. What survives is the one nobody measured — **total query cost with both sides priced, on real silicon, with the real encoding.**

Cost of one exact check measured, not assumed: **1.27–1.29 ns/row**.

## Query shape 0 — `(p s ?o)`, i.e. the query key *is* the cluster key

| B | layout | store | prefilter µs | rows exact-checked | stage 2 µs | **total µs** |
|---|---|---|---|---|---|---|
| 1 | — | 12,500 KB | 260.0 | 12 | 0.0 | **260.0** |
| 4 | clustered | 3,125 KB | 65.6 | 12 | 0.0 | **65.6** |
| 16 | clustered | 781 KB | 15.7 | 16 | 0.0 | **15.7** |
| **64** | **clustered** | **195 KB** | **4.0** | **640** | **0.8** | **4.8** |
| 64 | random | 195 KB | 3.9 | 44,672 | 57.7 | 61.6 |

**54× total improvement from B=1 to B=64 clustered.** Stage 2 stays negligible (0.8 µs of 4.8). Random layout at the same compression checks **44,672 rows — 45% of the store** — and lands 12.8× worse.

## Query shape 1 — `(p ?s o)`, bound on slots the clustering does *not* organise

This is AGENT-1's C3: *"My S11 clustering is close to circular — I clustered by (pred,subj) and queried by (pred,subj). Break it."*

| B | layout | prefilter µs | rows exact-checked | stage 2 µs | **total µs** |
|---|---|---|---|---|---|
| 1 | — | 253.4 | 9 | 0.0 | **253.4** |
| 4 | clustered | 65.7 | 456 | 0.6 | **66.3** |
| 16 | clustered | 15.8 | 8,720 | 11.1 | **26.9** |
| **64** | **clustered** | **3.9** | **9,856** | **12.5** | **16.5** |
| 64 | random | 3.9 | 86,272 | 109.8 | 113.7 |

**It does not collapse.** Clustered bundling at B=64 is still **15× better than no bundling** and still **6.9× better than random layout** — but it is **3.4× worse** than when the query matches the cluster key (16.5 vs 4.8 µs), and the rows the CPU must check jump from 640 to 9,856.

## The synthesis: S11 and S17 were both right

S11 said clustered bundling gives recall 1.0 where random does not. S17 said recall is recoverable by loosening the cutoff on any layout. Both hold, and this experiment shows why they are not in conflict:

> **Recall is recoverable on any layout — by loosening the cutoff. What layout buys is not recall, it is the *price* of recovering it.**

The harness sweeps the cutoff downward until recall hits 1.0 for every configuration, so every row in both tables is at recall 1.0. What differs is the shortlist that loosening produces: 640 rows clustered versus 44,672 random, at identical compression and identical recall.

That reframes shaping precisely. **Shaping does not buy correctness. It buys the cost of correctness**, and here that is a measured 12.8× (matched query) or 6.9× (mismatched).

## What this means for M4
`ADDENDUM.md` §6 said M4 should rest on S11 rather than the dead S3 crossover, and AGENT-4 later noted S17 had removed that support too. This restores it on firmer ground than either:

- measured on the target device, not the laptop;
- with the real three-valued encoding, not random bits;
- with **both sides priced in the same experiment** — prefilter *and* the exact-match work bundling creates;
- and with the circularity objection tested rather than acknowledged.

The shaping job class has a number again: **6.9–12.8× on total query cost**, depending on whether the workload's query shapes are known when the shard is laid out. That conditionality is itself the product spec — a shaper that knows the query distribution is worth roughly twice one that does not.

## Caveats, including one that limits the C3 answer
- **The C3 test is not fully orthogonal.** The cluster key is `(pred,subj)` and shape 1 is `(pred,obj)` — they still share `pred`. With three slots and a two-slot cluster key, *any* two-bound query shares at least one slot, so a completely mismatched two-bound query does not exist in this schema. A genuinely adversarial test needs either a larger arity or a one-bound query, and one-bound queries are already known to be non-exact (S10).
- Single query per shape, uniform synthetic triples, one D, one n. The store is uniform so every bucket is equally dense; a power-law store would make clustering matter more, not less.
- Bundling here is majority-over-B on one bitplane. AGENT-3's two-bitplane scheme is not tested and should be better.
- Prefilter timings are single-threaded and inline (S46's lesson): no pool, no barrier, so no harness floor.
- `total_us` adds a measured prefilter to a computed `shortlist × 1.27 ns`. Stage 2 was not executed as MeTTa or MORK here; S45 measured what happens when it is (13 ms of `exec()` if you spawn a process).
