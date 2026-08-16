# S11 — bundling: the 102 MB problem, and the first measured case for "the beak"

**Verdict: GREEN, and this is the most consequential of the new spikes.**
Clustered bundling gives **64× compression at recall 1.0000, 100/100 queries
perfect** — 102.4 MB → 1.6 MB per 100k triples. Random bundling at the same
ratio loses 3.7% of answers and forces the CPU stage to check 86% of the store.
Layout is worth more than compression, and this is the first number in the
workspace that measures it against the thing shards are actually *for*.

Code: `bundle.py`. Output: `bundling.json`, `bundling.log`. D=1024, 100k triples,
100 queries, cutoff `2·nnz(Q)/sqrt(B)`.

## Why this had to be run

S5 named it and skipped it:

> "One vector per triple is not a compression scheme. 100k triples at D=1024
> costs 102 MB … the compressive version — bundling many triples into one vector
> per bucket — reintroduces superposition noise and is where recall actually
> starts to cost something. Not tested; it is the obvious next spike."

102 MB per 100k triples is disqualifying, not merely inconvenient: a phone-sized
shard of a few million triples would be multiple gigabytes of INT8. Every
"a phone can hold a shard" claim in `out/STATE_OF_THE_UNION.md` depends on this
spike, and it had not been run.

## The result

`random` assigns triples to buckets arbitrarily. `clustered` packs triples
sharing a `(pred, subj)` key into the same bucket — i.e. the output a shaping job
would produce.

| B | store | vs B=1 | layout | recall (mean / min) | perfect | CPU rows checked | tie rate |
|---|---|---|---|---|---|---|---|
| 1 | 102.4 MB | 1× | — | 1.0000 / 1.0000 | 100/100 | 0.01% | 0.000 |
| 2 | 51.2 MB | 2× | random | 0.0913 / 0.0000 | 0/100 | 0.00% | 0.486 |
| 2 | 51.2 MB | 2× | **clustered** | 0.9957 / 0.8889 | 95/100 | 0.01% | 0.262 |
| 4 | 25.6 MB | 4× | random | 0.2245 / 0.0000 | 0/100 | 0.36% | 0.355 |
| 4 | 25.6 MB | 4× | **clustered** | **1.0000** / 1.0000 | 100/100 | 6.87% | 0.190 |
| 8 | 12.8 MB | 8× | random | 0.4845 / 0.0000 | 1/100 | 3.96% | 0.246 |
| 8 | 12.8 MB | 8× | **clustered** | **1.0000** / 1.0000 | 100/100 | 10.08% | 0.124 |
| 16 | 6.4 MB | 16× | random | 0.6897 / 0.3333 | 5/100 | 18.89% | 0.162 |
| 16 | 6.4 MB | 16× | **clustered** | **1.0000** / 1.0000 | 100/100 | 10.10% | 0.064 |
| 32 | 3.2 MB | 32× | random | 0.8564 / 0.4000 | 33/100 | 52.02% | 0.101 |
| 32 | 3.2 MB | 32× | **clustered** | **1.0000** / 1.0000 | 100/100 | 10.12% | 0.024 |
| 64 | 1.6 MB | 64× | random | 0.9635 / 0.6364 | 76/100 | 85.80% | 0.058 |
| 64 | 1.6 MB | 64× | **clustered** | **1.0000** / 1.0000 | 100/100 | 11.82% | 0.005 |

Three things fall out at once:

1. **The storage blocker is gone.** 64× at recall 1.0 turns a multi-gigabyte
   phone shard into tens of megabytes. D=1024 with B=64 clustered costs
   **16 bytes per triple** of pre-filter index.
2. **Layout beats compression, measurably.** At every B ≥ 4, clustered holds
   recall 1.0 while random degrades. At B=64 the CPU-side difference is 11.82%
   versus 85.80% of the store — random bundling at high B is a full scan wearing
   a pre-filter costume.
3. **The tie rate is the saturation signal.** Random bundling's tie rate
   (dimensions where the bucket sum is exactly 0, i.e. the superposition
   cancelled) starts at 0.486 and stays high; clustered falls to 0.005 by B=64,
   because co-clustered triples share role-filler products and reinforce rather
   than cancel. This is a cheap, local, *computable-at-shaping-time* metric —
   a better candidate for `ShardManifest`'s "layout quality" field
   (`out/PORT_PLAN.md` M4.1) than block density, because it is measured on the
   representation the NPU actually consumes.

## The honest caveats

- **The clustering key is the query key.** Triples were clustered by
  `(pred, subj)` and queried by `(pred, subj)`. That is close to circular. Real
  workloads mix patterns and cannot cluster by all of them at once; the
  interesting unmeasured question is what a *multi-pattern* workload costs, and
  whether shaping becomes a per-query-class decision. This is the same trap S5
  fell into and it is not yet escaped, only named.
- **The cutoff is a guess above B=1.** `2·nnz(Q)/sqrt(B)` reduces to the exact
  rule at B=1 and is a heuristic thereafter. The clustered CPU-check figure
  plateauing at ~10% regardless of B is evidence the cutoff is far too
  permissive, not that the data demands that much checking. A properly
  calibrated per-B cutoff should cut CPU work substantially — the obvious next
  tuning knob, and it makes the numbers above a **floor**.
- **Compression trades against CPU work.** B=1 checks 0.01% of the store; B=64
  clustered checks 11.82%. That is ~1,000× more exact-match work for 64× less
  storage. On a phone, where the exact stage is `interpret_step` and not a numpy
  comparison, that trade needs measuring before an operating point is picked.
  B=4–8 clustered (25.6/12.8 MB, 6.87/10.08% CPU) looks more balanced than B=64.

## What this changes upstream
`analysis/GAP_MATRIX.md` row 17 calls the shaping job class **BUILD / L** with
"nothing anywhere" as prior art and justifies it solely with S3's sparse-vs-dense
density crossover — a number about SpGEMM cost that says nothing about recall.
This spike supplies a direct argument: **shaping converts into recall and into
CPU-stage work on the pre-filter path**, independent of any SpGEMM claim. That is
a stronger and much cheaper-to-verify basis for M4 than the crossover, which
S13 shows was itself mis-baselined.
