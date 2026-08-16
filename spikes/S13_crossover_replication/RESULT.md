# S13 — replicating S3's sparse/dense crossover independently

**Verdict: RED for S3's numbers.** The crossover is real, but it sits at
**~1.1–1.8% density, not 5.1–8.6%**, and the "~9,800× faster" headline was
measured against a dense baseline that is **15× slower than the same machine's
actual single-threaded floor**. S3's OpenBLAS build was not using the AMX
coprocessor that Accelerate uses on Apple Silicon. The shaping target moves from
"push tiles below ~5–9% density" to "push tiles below ~1.5%" — materially harder.

Code: `spgemm.py` (scipy SMMP CSR, no relationship to MORK's kernel).
Output: `crossover.json`, `crossover_1thread.json`, and the two `.log` files.
Timing via `../bench.py`: ≥50 ms per sample, 7 reps, warm median, so no kernel is
measured near the clock's resolution.

## Why this had to be run

S3 reported "~9,800× faster" at n=1024, 0.01% density, from a CSR time of **2 µs**
against a BLAS time of 19,662 µs. Two problems:

1. A 2 µs sample with no visible repetition count is at the edge of what one
   `perf_counter` delta can resolve.
2. Nobody runs dense sgemm on a 99.99%-zero matrix. The ratio mostly measures how
   much useless work the dense side was asked to do. The load-bearing number is
   the **crossover density**, because that is the target a shaping job aims at.

## The dense baseline was the problem

Measured on this machine, float32 `n×n @ n×n`:

| n | S3's OpenBLAS (1 thread) | Accelerate (1 thread) | Accelerate (default) |
|---|---|---|---|
| 256 | — | 24.6 µs · 1,365 GFLOP/s | 24.6 µs · 1,362 GFLOP/s |
| 512 | — | 155.9 µs · 1,721 GFLOP/s | 97.1 µs · 2,765 GFLOP/s |
| 1024 | **19,662 µs · 109 GFLOP/s** | **1,308 µs · 1,641 GFLOP/s** | **680 µs · 3,158 GFLOP/s** |

At n=1024, S3's baseline is **15.0× slower than single-threaded Accelerate** and
**28.9× slower than default Accelerate** on the same hardware. This is not a
threading artefact — the 1-thread columns are like-for-like. OpenBLAS simply does
not target Apple's AMX units, and `brew install openblas` (`DECISIONS.log` entry
7) silently supplied a baseline a factor of fifteen below the machine's floor.

## Corrected crossovers

| n | S3 / MORK reported | scipy, 1 thread | scipy, default threads |
|---|---|---|---|
| 256 | 5.624% | **1.378%** (0.25×) | 1.103% (0.20×) |
| 512 | 5.149% | **1.816%** (0.35×) | 1.352% (0.26×) |
| 1024 | 8.638% | **1.534%** (0.18×) | 1.129% (0.13×) |

Apples-to-apples (both single-threaded), S3's crossover is **3–6× too high**.

And the headline ratio, recomputed against the real floor at n=1024, 0.01%
density: MORK's CSR at 2 µs against 1,308 µs (1-thread) is **~654×**, against
680 µs (default) is **~340×** — not 9,831×. Still a large number, and still the
right qualitative conclusion. Off by more than an order of magnitude.

## Where our own workload actually sits

S5's synthetic graph is 100k triples over 10 predicates × 1,000 subjects × 1,000
objects — **1.0% density per predicate slice**. That is *below but adjacent to*
the corrected crossover of ~1.5%, and far from the 0.01% point where the
four-digit speedup lives. Our workload is a near-crossover workload, not a
hypersparse one.

## What this changes upstream

- **`out/PORT_PLAN.md` M4.2 and `analysis/GAP_MATRIX.md` row 17** justify the
  shaping job class with "CSR beats dense BLAS below ~5–9% density and by
  ~10,000× at 0.01%". Both halves need restating: below ~1.5%, and by a few
  hundred ×.
- **The shaping target tightens by 3–6×.** Concentrating a tile below 5–9% local
  density is a much weaker requirement than below 1.5%. Whether Morton or
  community reordering can reach 1.5% on a real graph is now an open question the
  workspace has not answered.
- **S3's ARM-SIMD finding is reinforced, not weakened.** `linalg/src/blocked.rs`
  gating on `x86_64 + avx2 + fma` means MORK's blocked kernels are scalar on ARM,
  and its dense comparator was crippled too. Both sides of S3's benchmark were
  running below the hardware's capability.
- **S11 now carries M4.** The measured case for shaping should rest on S11's
  recall-and-CPU numbers, which are about the pre-filter path the fleet actually
  runs, rather than on a SpGEMM crossover that turned out to be mis-baselined.

## What this does NOT show
This is scipy's SMMP kernel, not MORK's. Agreement on the *shape* of the curve is
replication; the residual gap between scipy's crossover and MORK's could still be
partly a genuine difference in CSR implementation quality rather than entirely a
baseline artefact. Separating those two would need MORK's kernel re-benchmarked
against Accelerate — which needs the nightly toolchain and, for anything
publishable, a licence.
