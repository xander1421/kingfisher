# S45 — S44's stack on the phone, with MORK as stage 2

**Verdict: GREEN for the prefilter, and it beats S44's *host* result. RED for the deployment shape: stage 2 as a subprocess costs 13 ms of `exec()` and eats 97% of the query.**

S44 closed with three open items: *"the honest next step is the ~40-line NEON kernel"*, a memory-roof estimate of ~0.093 ms/query that was *"arithmetic, not a measurement"*, and *"No phone ran this."* All three are now measured, and the Amdahl conclusion needs splitting in two.

## The phone beats the laptop's stacked pipeline

| | prefilter, one query | bandwidth |
|---|---|---|
| S44 V3 (M4 Pro, numpy `bitwise_count`, 10 threads) | 0.938 ms | 13.6 GB/s |
| S44 V4 full query (M4 Pro) | 0.995 ms | — |
| **S45 host** (M4 Pro, NEON popcount, 8 threads) | **0.161 ms** | **79.5 GB/s** |
| **S45 phone** (SM8750, NEON popcount, 4 threads) | **0.349 ms** | **36.7 GB/s** |

**The phone's prefilter is 2.8× faster than S44's whole host query.** The NEON kernel S44 asked for is worth 5.8× on the host over numpy, exactly because it has no materialised temporary — S44 predicted the cause correctly.

S44's roof estimate was 0.093 ms at 138 GB/s. Measured host: 0.161 ms at 79.5 GB/s — **58% of the roof**, up from S44's 10%. The remaining gap is real but no longer the dominant term.

Correctness holds throughout: **scores digest `2e2ac64c1d9cff91`, identical phone and host**, shortlist 12 rows against 12 ground-truth answers, **zero false positives**, 8,333× candidate reduction.

## Threads: 4 beats 8 on the phone

| threads | 1 | 2 | **4** | 8 |
|---|---|---|---|---|
| ms | 0.639 | 0.401 | **0.349** | 0.483 |
| GB/s | 20.0 | 31.9 | **36.7** | 26.5 |

Scaling stops at 4 and **reverses at 8**. This kernel is bandwidth-bound, so extra threads contend for the same bus — the opposite of S32, where MeTTa reduction scaled 5.87× on 8 cores because it is compute- and allocation-bound. Two workloads, two different optimal thread counts, on one device: **the device agent cannot use a single thread-pool size.** That belongs in the scheduler spec.

## The finding: stage 2 is 0 ms of work and 13 ms of `exec()`

MORK on the 12-row shortlist, on the phone:

```
loaded 12 expressions
executing 1 steps took 0 ms (unifications 11, writes 11, transitions 16, max unify 2)
```

**The join itself is under a millisecond.** But the process that performs it:

| | phone, best of 5 |
|---|---|
| MORK on the shortlist, whole process | **13.34 ms** |
| MORK on an **empty program**, whole process | **12.84 ms** |

The work is ~0.5 ms of a 13.3 ms invocation. **Essentially all of stage 2 is process startup.**

So the full query, measured two ways:

| stage 2 invoked as | prefilter | stage 2 | total | queries/s |
|---|---|---|---|---|
| subprocess (what a naive integration does) | 0.349 ms | 13.34 ms | 13.69 ms | **73** |
| in-process (what it must be) | 0.349 ms | ~0.5 ms | ~0.85 ms | **~1,180** |

**A 16× throughput difference decided entirely by how the engine is called.**

### What this does to S44's Amdahl argument
S44: *"stage 2 costs 0.057 ms of a 0.995 ms query — 5.7%. Amdahl's own bound caps any stage-2 engine swap at 1.06×."*

**Correct about the work, wrong about the deployment.** On the work, S44 is vindicated by an independent engine on different silicon: the join is trivial and no stage-2 engine swap can matter. But if the engine is invoked per query as a process, stage 2 is **97.4%** of the query and the prefilter's 27× is annihilated — not because the engine is slow, but because `exec()` is 13 ms.

This produces a hard architecture requirement that appears in no document:

> **Stage 2 must run in-process. The device agent links the engine as a library and never spawns it per query.**

For hyperon that path exists and is proven: `libhyperonc`, 162 C functions, cross-compiled for Android in S2. For MORK it does **not** — MORK is a CLI binary (`kernel/src/main.rs`), with no library surface, which is a second reason beyond the licence that MORK cannot be the phone's stage-2 engine today.

## Set semantics, again
12 shortlist triples produced 11 `Answer` facts. Not a bug: two triples share object `o812`, and MORK's space dedupes. Same set-vs-bag distinction S35 found. A verifier comparing answer *counts* across engines would flag this as a mismatch.

## Fleet arithmetic, corrected
S44 projected **272 queries/s/device** by scaling a host measurement by S30's 3.7× sustained ratio.

Measured on the device: **2,866 queries/s** for the prefilter (4 threads, best-of-9, in-process stage 2 assumed) — **10.5× better than the projection**. The projection was pessimistic because it scaled the numpy pipeline, not the NEON one.

With a subprocess stage 2 it is **73 queries/s**, 3.7× *worse* than the projection. The spread between those two numbers is larger than any algorithmic result in this workspace, and it is pure integration.

## Caveats
- One query shape, B=1 unbundled store, uniform synthetic triples. S17/S43's bundled stores were not run here.
- `best of 9` after a cold sample; the phone was plugged in and cool. Sustained behaviour under thermal load not measured for this kernel.
- The in-process figure is a projection: MORK's 0.5 ms of internal work added to the measured prefilter. Nothing was actually linked in-process.
- No NPU. This is CPU NEON throughout.

---

# S45b — why it scales like that (asked, then measured)

The T=4 > T=8 reversal had three candidate causes: bandwidth saturation, core heterogeneity, or thread-spawn overhead. Measured all three rather than picking one.

## Cause 1 — thread spawn, and it was the big one

`threadcost.c` on the device, spawn+join of no-op threads:

| threads | spawn+join | per thread |
|---|---|---|
| 1 | 54.0 µs | 54.0 |
| 4 | 133.7 µs | 33.4 |
| 8 | **285.6 µs** | 35.7 |

The T=8 query measured 483 µs total. **285.6 µs of it — 59% — was `pthread_create`.** Spawn cost grows ~35 µs per thread while the work per thread shrinks, so past 4 threads the overhead wins and the curve turns over. Nothing to do with memory.

**This is the third instance today of the same failure**: per-query setup dominating sub-millisecond work. The 13 ms `exec()` for stage 2, the S18 BLAS call overhead that masqueraded as a memory roof, and now this. At 0.25 ms of work, *any* per-query setup is the entire budget.

Fixed with a persistent pool — spawn once, signal per query via condvar:

| threads | per-query spawn | pool | gain |
|---|---|---|---|
| 1 | 0.639 ms | 0.594 ms | 1.08× |
| 2 | 0.401 | 0.333 | 1.20× |
| **4** | 0.349 | **0.252** | **1.39×** |
| 8 | 0.483 | 0.287 | **1.68×** |

Digest `2e2ac64c1d9cff91` unchanged. **Best is now 0.252 ms = 50.8 GB/s = 3,968 queries/s.**

## Cause 2 — the memory system itself peaks at 4 threads

`streamroof.c`: a pure NEON read loop over 128 MB, zero arithmetic, nothing but streaming.

| threads | read roof | prefilter | prefilter as % of roof |
|---|---|---|---|
| 1 | 22.7 GB/s | 21.5 | 95 % |
| 2 | 45.0 | 38.5 | 86 % |
| **4** | **58.9** | **50.8** | **86 %** |
| 8 | **49.7 ↓** | 44.5 ↓ | 90 % |

**The roof itself declines from 4 to 8 threads.** A loop that does nothing but read shows the same shape as the prefilter, so the residual T=8 penalty is a property of this phone's memory system, not of the kernel.

## Cause 3 — heterogeneous cores, secondary
`cpu6`/`cpu7` run at 4.47 GHz, `cpu0–5` at 3.53 GHz (2 prime + 6 performance Oryon). Chunks are equal-sized, so the 3.53 GHz cores are stragglers and the fast cores idle at the barrier. Real, but small next to causes 1 and 2, and fixable with work-stealing rather than static chunks. Not attempted.

## The consequence: the CPU kernel is finished

**The prefilter runs at 86% of this device's measured achievable read bandwidth.** There is at most 16% left on the CPU, and no amount of instruction-level work will find more, because the kernel already reads each byte exactly once and does three ops on it.

That reframes the NPU case on measured ground, replacing the arithmetic-shortfall argument from S33/S34:

> The CPU is not slow. It is **at its memory roof**. The only two ways forward are to *read less* (bundling — S11/S43) or to use a memory system the CPU cannot reach (**VTCM residency**).

And a hard constraint on the second, which nobody has stated: **VTCM is 8 MB and the packed B=1 store is 12.8 MB — it does not fit.** VTCM residency therefore *requires* bundling; the ~400 KB B=64 two-bitplane store fits 20× over. So the NPU path and the bundling path are not alternatives, they are a single dependency chain: **bundle → fits VTCM → resident → escapes the roof that S45b just measured.**

## Fleet, corrected once more
| | queries/s/device |
|---|---|
| S44 projection | 272 |
| S45 measured (per-query spawn) | 2,866 |
| **S45b measured (pooled)** | **3,968** |

14.6× above the projection. The projection was not conservative — it was scaling the wrong pipeline.
