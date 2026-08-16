# S33 — the batch inversion, measured on the phone and controlled against the host

**Verdict: RED for S18's causal claim, and it inverts S18's conclusion about the NPU.**

S18 concluded the pre-filter is bandwidth-bound at q=1, that "you pay to stream the shard once and every query after is nearly free", and therefore that the NPU has nothing to accelerate. The custody/tier architecture is built on that line. S18 was measured on "laptop CPU via Accelerate". This spike runs the **same kernel on both machines**, which S18 had no control for.

## Measured

Identical C kernel, `-O3`, D=1024, 100k triples (102.4 MB int8 shard), the real three-valued query shape, 5 reps, cold and warm separate.

**Phone — Galaxy S25 Ultra, SM8750, single thread**
| q | warm ms | GOP/s | ms/query | marginal ms per extra query |
|---|---|---|---|---|
| 1 | 3.0 | 69.1 | 2.96 | 2.96 |
| 4 | 12.2 | 67.2 | 3.05 | 3.07 |
| 16 | 49.9 | 65.6 | 3.12 | 3.14 |
| 64 | 258.8 | 50.7 | 4.04 | 4.35 |
| 100 | 404.1 | 50.7 | 4.04 | 4.04 |
| 256 | 1034.2 | 50.7 | 4.04 | 4.04 |

**Host — M4 Pro, single thread, same kernel**
| q | warm ms | GOP/s | ms/query | marginal ms |
|---|---|---|---|---|
| 1 | 1.2 | 164.9 | 1.24 | 1.24 |
| 16 | 17.4 | 187.9 | 1.09 | 1.09 |
| 100 | 107.7 | 190.2 | 1.08 | 1.10 |
| 256 | 333.3 | 157.3 | 1.30 | 1.45 |

**On both machines, `ms/query` is flat and the marginal cost of an extra query does not collapse.** There is no inversion. GOP/s is flat, not swinging 141×.

## The difference is the kernel, not the machine

That is what the control establishes. My kernel is compute-bound on *both* machines, so every query costs full arithmetic. Accelerate is ~5× faster than my loop at q=256 (1032 vs 190 GOP/s on the same host) and only at that speed does anything else become the limit.

So **"queries after the first are nearly free" is a property of the kernel being fast enough, not a property of batching.** With a naive kernel, q=100 costs ~100× q=1, on a phone and on a laptop alike.

## S18's own numbers are not bandwidth-bound either

Take S18's wall-clock and ask what streaming rate it implies, if the cost really were streaming the 102.4 MB shard once:

| q | S18 ms | implied GB/s | GOP/s |
|---|---|---|---|
| 1 | 28.0 | **3.66** | 7.3 |
| 100 | 38.4 | **2.67** | 533 |
| 256 | 50.8 | **2.02** | 1032 |

An M4 Pro has roughly **273 GB/s** of memory bandwidth. S18's q=1 point uses **1.3 %** of it. It is not bandwidth-bound; it is not compute-bound either (7.3 GOP/s on a machine doing 1032 GOP/s in the same table). It is **overhead-bound** — BLAS call overhead, a gemv-vs-gemm path, and the conversion cost AGENT-3 already identified at `hdcore.py:91`.

So the 28 ms was never the price of streaming the shard. **"You pay to stream the shard once" is unsupported by the measurement it comes from.** The q-curve in S18 is mostly the amortisation of a fixed per-call overhead, which is a real effect worth having — but it is a software constant, not a memory roof, and it does not transfer to a different runtime.

## The reversal: this is the strongest pro-NPU argument in the workspace

Run the arithmetic the other way. For the phone to actually reach the bandwidth roof at q=100 — to stream 102.4 MB once (~4.1 ms at a realistic 25 GB/s) and get the queries free — it must sustain:

> 2 × 100 × 100,000 × 1024 ops / 4.1 ms = **5.0 TOP/s**

Measured phone CPU: **50.7 GOP/s** single-thread, ~300 GOP/s if all 8 cores scale as S32 measured. That is a **17× shortfall**.

The laptop closes that gap with AMX, which is why Accelerate can approach the roof there. **The phone's only unit that can close a 17× int8 gap is the Hexagon NPU.**

This inverts the conclusion S18 was used for. "The NPU is being offered a stage that is already free" is true *on a laptop with AMX*. On the phone the same stage is **17× short of free**, and the NPU is precisely the unit that would make custody-style serving viable. The NPU is not decorative in the batch case — it is the enabling condition.

## What this means for the custody architecture
It is not refuted, it is **conditional**, and the condition was invisible:

- Phones can only be economic shard servers if the pre-filter kernel is fast enough to stop being compute-bound. On CPU it is 17× short at q=100.
- Therefore **N1 (NEON/SDOT) and the packed popcount path are not optimisations — they are the precondition for the tier model.** If they land within ~5× of the roof, custody works and the NPU has a job. If they do not, phones revert to per-job workers and the tier model collapses back into the design it replaced.
- Every "~50 µs pre-filter at B=64" and "~70× locality advantage" figure inherits S18's overhead artifact and should be re-derived from a kernel that has been profiled against the roof.

## Caveats against my own result
- My kernel is naive and is ~5× off Accelerate on the host; it is a *shape* instrument, not a peak instrument. The flatness is the finding; the absolute GOP/s is a floor.
- Single-threaded. S32 measured 5.87× on 8 cores, so 8-way ≈ 300 GOP/s, still 17× short.
- Cold/warm are within 1 % at every q except q=64 (203.9 vs 258.8 — one throttling sample); the phone was otherwise thermally stable.
- I did **not** test a bit-packed store. That is N0/N1, and it changes both terms — fewer bytes *and* far fewer ops per element — which is the whole reason it deserves priority.
