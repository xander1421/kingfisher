# S46 — residency buys nothing on the CPU, and that kills my own S45b claim

**Verdict: RED for the residency half of the chain, GREEN for bundling by a different mechanism than anyone stated.**

S45b closed with a chain the NPU plan depends on:

> bundle → fits VTCM (8 MB) → resident → escapes the DRAM roof

The middle link is testable without a DSP: a bundled store is small, small stores fit in cache, and cache is a memory system the DRAM roof does not apply to. So sweep the store size and find where the prefilter stops being DRAM-bound.

**It never was.** Single-threaded, inline, no barrier:

| rows | store | best µs | **GB/s** | q/s |
|---|---|---|---|---|
| 100,000 | 12,500 KB | 569.1 | **22.5** | 1,757 |
| 25,000 | 3,125 KB | 142.8 | **22.4** | 7,002 |
| 6,250 | 781 KB | 35.4 | **22.6** | 28,236 |
| 3,125 | **391 KB** ← the B=64 size | 17.7 | **22.6** | 56,469 |
| 780 | 98 KB | 4.4 | **22.8** | 228,571 |
| 195 | **24 KB** ← fits L1 | 1.1 | **22.8** | 914,066 |

**Bandwidth is flat to within 1.8% across a 512× range of store sizes.** A 24 KB store that lives entirely in L1 runs at exactly the same bytes/second as a 12.5 MB store streamed from DRAM. There is no residency effect to capture.

## Why: single-threaded, this kernel is compute-bound, not memory-bound

The coincidence that hid this: `streamroof` measured single-thread DRAM read at **22.7 GB/s**, and the prefilter runs at **22.6 GB/s**. Identical, so it looked memory-bound. It is not — an L1-resident store gives the same number, which a memory-bound kernel could not do.

Per 16 bytes the kernel issues load / XOR / AND / `vcntq_u8` / accumulate. At 3.53 GHz and ~2 IPC that lands at ~22.6 GB/s, and that is the ceiling regardless of where the bytes come from.

The two regimes, now separated:

| | limit | evidence |
|---|---|---|
| 1 thread | **compute**, ~22.6 GB/s/core | flat across 512× of store size |
| 4 threads | **memory**, 50.8 GB/s of a 58.9 roof | 12.7 GB/s/thread — *worse* per thread than running alone |

Per-thread throughput *falls* from 22.6 to 12.7 GB/s when four threads run, which is what memory contention looks like. So the kernel is compute-bound alone and memory-bound in aggregate, and S45b's "86% of the roof" is only true in the multi-threaded configuration.

## What this does to my own S45b conclusion

S45b said:

> "The CPU is not slow. It is at its memory roof. The only two ways forward are to read less (bundling) or use a memory system the CPU cannot reach (VTCM residency)."

**The second half is wrong on the CPU.** Residency — cache or VTCM — cannot help a kernel that is already compute-bound per core. Making the data closer does nothing when the bottleneck is the instruction stream.

The first half survives, but by a different mechanism than "escaping the roof":

> **Bundling helps because there is less to scan, not because the scan gets faster per byte.**

At B=64 the store is 391 KB instead of 12.5 MB, and the query takes **17.7 µs instead of 569 µs — 32×**, exactly proportional to the size reduction, at unchanged bandwidth. That is a large, real win. It is arithmetic, not architecture.

## What it means for VTCM and the NPU
The chain is not dead, it is **conditional on the consuming unit being compute-rich enough to starve.** The CPU is not: it saturates its own pipeline at 22.6 GB/s/core long before memory matters. HVX has far more popcount throughput per cycle, so on HVX the balance can flip and VTCM residency can pay. On the CPU it provably does not.

So N3 (VTCM residency) should not be justified by "the CPU is at its memory roof" — I said that and it was wrong. It should be justified by "HVX is compute-rich enough that it *would* be memory-starved without VTCM", which is a claim about HVX's popcount width, and is exactly the unknown N2 exists to answer. **N2 must come before N3, and N3's justification depends on N2's answer.**

## A fourth instance of the same failure, in my own harness
The first pass of this sweep used the S45b thread pool and produced a *decreasing* bandwidth curve — 50.4 GB/s at 12.5 MB falling to 0.6 GB/s at 24 KB — which would have been reported as "residency hurts". It was the condvar round trip: `best_us` floored at 37–75 µs no matter how small the store got, so at 391 KB the barrier *was* the measurement.

That is now the fourth time today the same shape of error has appeared: S18's BLAS call overhead, stage 2's 13 ms `exec()`, the 285 µs `pthread_create`, and now a ~40 µs condvar barrier. Each one masqueraded as a property of the hardware. The rule the workspace should adopt:

> **Before reporting any per-query number below ~1 ms, measure the harness doing nothing and subtract it.** If the null measurement is within an order of magnitude of the result, the result is the harness.

## Caveats
- Synthetic random store; the digest line in the tool is mislabelled (`digest(scores, 100k rows)` actually hashes 780 bytes) — cosmetic, does not affect the sweep.
- Inline arm is single-threaded by construction; a multi-threaded residency sweep would need a spin-barrier costing <1 µs, which was not built.
- 15 reps, best-of, phone plugged in and cool. No sustained/thermal arm.
- This says nothing about HVX, where the compute/memory balance is different by design.
