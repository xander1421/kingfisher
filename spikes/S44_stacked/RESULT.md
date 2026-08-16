# S44 — everything stacked: 27× on a full query, exact, and Amdahl was a bundling artefact

**Verdict: GREEN. 26.847 ms → 0.995 ms for a complete two-stage query, byte-identical answers, on an idle machine with no competing processes.**

Run after the operator asked what the ceiling looks like with every optimisation stacked and licences set aside. `stacked.py`, log `stacked.log`. n=100,000, D=1024, 10 P-cores, M4 Pro. `contention: loadavg 1.46 → 1.58, competing: []` — **the first measurement in this workspace taken with a clean competing-process list.**

## The gate, first

```
GATE  v0==v1==v2==v3 exactly;  stage2 recovers 11/11 answers, 0 false positives
      prefilter shortlist = 11 rows = 0.0110% of store  (9,091x reduction)
```

Every variant produces the *identical int32 score vector*, not merely the same answer set. The 9,091× candidate reduction independently reproduces S10's 9,578× for this pattern class.

## The stack

```
variant                              wall        per query      throughput      rate     rsd
V0 float32 GEMM (S18/S5)         26.847 ms    26.847 ms/q      7.6 GOP/s     37.2 q/s   0.5%
V1 packed popcount u8             4.887 ms     4.887 ms/q     41.9 GOP/s    204.6 q/s   0.5%
V2 packed popcount u64            3.221 ms     3.221 ms/q     63.6 GOP/s    310.5 q/s   0.8%
V3 V2 x 10 threads                0.938 ms     0.938 ms/q    218.4 GOP/s   1066.6 q/s   0.9%
V4 V3 + stage2 (full query)       0.995 ms     0.995 ms/q    205.9 GOP/s   1005.3 q/s   1.2%
B  float32 GEMM q=256 (batch)    50.787 ms     0.198 ms/q   1032.3 GOP/s   5040.7 q/s   2.2%
```

```
V0->V1 pack 5.5x | V1->V2 u64 lanes 1.5x | V2->V3 threads 3.4x | stage2 +0.057 ms
stacked total: 27.0x
```

Nothing here is a new algorithm. It is three mechanical changes — store one bit per ±1 instead of one byte, accumulate in 64-bit lanes instead of 8-bit, and use the cores that were already there.

## The finding: S18's Amdahl objection is a bundling artefact, not a design flaw

S18 argued the two-stage design has the NPU accelerating the cheap stage while the expensive stage is symbolic work an NPU cannot touch, citing S17's 10–22% of store checked by the CPU.

Measured end to end at B=1: **stage 2 costs 0.057 ms of a 0.995 ms query — 5.7%.** The prefilter is 94% of the work. Amdahl points the *other* way.

The reconciliation is that S17's 10–22% is measured on a **bundled** store. So the real dial, in one line:

| | store | shortlist | exact-match work |
|---|---|---|---|
| B=1 | 102.4 MB (12.8 packed) | 0.011% | negligible — 5.7% of query |
| B=64 clustered | 1.6 MB (~400 KB packed) | 11.8% | ~1,000× more |

**Bundling trades 64× of memory for ~1,000× of exact-match work.** Nobody had priced both sides of that trade in the same experiment, and every argument about M2/M4 has been made from one side of it or the other. With packing, the B=1 store is 12.8 MB — which a phone with 11 GB holds without difficulty, so the compression that created the Amdahl problem may not be needed at all on this class of device.

## Where the ceiling actually is

V3 moves 12.8 MB in 0.938 ms = **13.6 GB/s**, against this machine's measured 138.8 GB/s copy bandwidth (S43 `stream.log`). So even after threading, ~10× of headroom remains, and it is sitting in `np.bitwise_count`'s materialised temporary. A NEON `vcntq_u8` kernel with no temp should approach the streaming roof:

```
measured today            0.995 ms/query    27x
memory-roof estimate     ~0.093 ms/query   ~290x   (12.8 MB at 138 GB/s)
```

That estimate is arithmetic, not a measurement, and the honest next step is the ~40-line NEON kernel that turns it into one.

## Stacking MORK does not multiply this

Licences set aside, MORK's contribution lands on stage 2 — the join and the symbolic reduction. Stage 2 is 5.7% of a query at B=1. **Amdahl's own bound caps any stage-2 engine swap at 1.06× for this query shape**, no matter how fast the engine is.

MORK earns its place on the things this measurement does not cover: multi-pattern joins (WCO leapfrog), bulk shard operations, and the MeTTa reduction itself (383k steps/s sustained on the phone, S30). It is not a query-latency lever.

## Fleet arithmetic

```
full machine, one query at a time        1,005 queries/s
batch regime (q=256, GEMM)               5,041 queries/s
phone projection @3.7x sustained (S30)     272 queries/s/device
```

```
  1,000 devices     ~272k queries/s
 10,000 devices     ~2.7M queries/s
```

Phone figures are projections from a host measurement scaled by S30's sustained ratio. **No phone ran this.** They are also floor numbers: no SIMD, no NPU, no batching on device.

## What this does NOT show

- One machine, one D, one n, one query shape, uniform synthetic data.
- Threads scale 3.4× on 10 P-cores — 34% efficiency. Not investigated.
- The packed path was never combined with batching; B and V3 are separate arms, so the true ceiling for a shard host is unmeasured.
- Bundled (B=64) stores were exactness-checked in S43 but never timed here.
- Nothing ran on the phone, and nothing ran on an NPU.

## Reproducing

```sh
./spikes/S5_hdc_prototype/.venv/bin/python spikes/S44_stacked/stacked.py 100000 1024 10
```
