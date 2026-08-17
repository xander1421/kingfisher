# S72 (C3) — packed popcount on the deployable cpuset. My prediction was wrong by 6×.

**Verdict: AMBER. Exactness holds perfectly; throughput is far worse than I predicted, and this is the one finding of the five charges that argues *against* my own NPU descope rather than for it. The descope still stands, on the ladder argument, which was stated load-independently for exactly this contingency.**

C3 charged that the NPU descope's arithmetic used S34's **8-way** throughput,
while S54 established a charge-time worker gets `0-1,4-5` and never a prime core.
**My prediction, on record:** *"marginal cost roughly doubles from ~0.05 ms and
'1.2× short' becomes ~2.4× short. The descope survives anyway."*

## Gate — device, both sides
```
{"quiet":true,"device_cpu_busy_pct":0.6,"device_limit_pct":15,
 "device_cores":8,"thermal_m":34300,"battery":"status=5 level=100","refusals":""}
```
First S34-family measurement in this workspace taken behind a device gate.

## Measured — `taskset 33` (cores 0,1,4,5), D=1024, 100,000 rows

**Exactness — unchanged and perfect:**
```
K0 scalar    fnv f4e64fb7d70b9b0c
K1 SDOT      fnv f4e64fb7d70b9b0c   IDENTICAL
K2 popcount  fnv f4e64fb7d70b9b0c   IDENTICAL
```
The same digest S34 recorded on two machines. Grade A stands.

**Throughput:**

| q | K0 scalar | K1 SDOT | K2 popcount | K2 GOP/s |
|---|---|---|---|---|
| 1 | 9.1 ms | 4.3 | **0.6** | 329.4 |
| 4 | 36.4 | 17.3 | 2.4 | 334.6 |
| 100 | 911.3 | 432.0 | 62.1 | 329.5 |
| 256 | 2336.2 | 1111.9 | 159.6 | 328.6 |

> at q=100 the roof needs 5.0 TOP/s; K2 reaches 0.33 TOP/s — **15.2× short**

## My prediction was wrong by 6.3×
I predicted ~2.4× short. Measured **15.2×**. The gap is not subtle and I should
record why I got it wrong: I reasoned from "8-way → ~4-way, so roughly double the
marginal cost", treating the shortfall as linear in worker count. It is not — the
shortfall is against a *memory roof* that does not move when you take cores away,
so losing 8-way parallelism widens the gap multiplicatively, not additively.

## Does the descope survive? Yes, and it is the weaker answer than it sounds
**This finding argues against my descope, not for it.** A CPU 15.2× short of the
roof makes the NPU's measured 14.6× prefill advantage look more relevant, not
less.

What holds it up is the part that was deliberately stated without reference to
throughput:
- the prefilter it would accelerate costs **~50 µs** in a query S56 measured as
  ~57% symbolic work an NPU cannot touch;
- the CPU runs the kernel **bit-exactly** with `asimddp`+`i8mm` verified present;
- and the costs avoided are unconditional — no SDK, no vendor delegate, no
  quantisation-scale pinning (S12's 46% silent recall loss, S31's recall 0/8),
  no QNN redistribution question, no untested cross-vendor requantisation.

**S34's own "1.2× short" is INVALID** in the LEDGER for inheriting S32's
projection, so neither the old figure nor this one can carry an NPU-necessity
argument. What this measurement establishes is narrower: **at the deployable
operating point the CPU kernel is compute-bound and far from the memory roof**,
which is a fact about headroom, not about necessity.

I said the descope was independent of throughput. It is — but I should not have
predicted a number and then treated the descope's survival as confirmation of
the prediction. Those were two claims and only one survived.

## Caveats
- Single-threaded kernel under `taskset 33`; the cpuset grants 4 cores and the
  binary uses one. A 4-worker version is the missing measurement, and S71 shows
  near-linear scaling (3.95×) for independent processes.
- One thermal state, 34.3 °C at gate. Not a soak.
- "Roof" is the binary's own model of the memory bound; it has not been
  independently re-derived here.

---

# S72b — the missing 4-worker measurement. Two of my claims were wrong, in opposite directions.

**Run 2026-08-17, device gate green before and after. Harness: `k4.sh` (shipped — the previous four spikes shipped none).**

S72 said, of itself: *"Single-threaded kernel under `taskset 33`; the cpuset
grants 4 cores and the binary uses one. A 4-worker version is the missing
measurement."* Here it is.

## Measured — P concurrent `kernels`, all pinned to `0-1,4-5`, q=100

| workers | per-instance GOP/s | aggregate | scaling | short of 5 TOP/s |
|---|---|---|---|---|
| 1 | 329.3 | 329.3 | 1.00× | 15.2× |
| 2 | 326.2 | 652.4 | 1.98× | 7.7× |
| 3 | 266.5 | 799.5 | 2.43× | 6.3× |
| 4 | **220.2** | **880.9** | **2.68×** | **5.7×** |

## 1. "15.2× short" was single-core and is corrected to 5.7×
My prediction was ~2.4×. S72 recorded the miss as 6.3×. **The real miss is 2.4×**
— bad, but not what S72 said, and S72 knew the measurement was missing when it
published the number.

## 2. The kernel is bandwidth-bound, and S34 says it is compute-bound
**Per-instance throughput falls 329 → 220 GOP/s as workers are added.** That is
the signature of memory-bandwidth saturation: adding cores does not add
bandwidth. Scaling is **2.68×** on four cores, against **3.95×** S71 measured for
independent MeTTa jobs on the same cpuset — the difference is exactly what
distinguishes a bandwidth-bound kernel from a compute-bound one.

S34's surviving conclusion is *"13.9× faster **while staying compute-bound**"*.
At four workers on the deployable cpuset it is not. **S34's compute-bound claim
is scoped to single-core and should say so.**

## 3. This cuts toward the NPU **conditionally**, and the condition is unmet
**Bandwidth-bound normally cuts AWAY from the NPU** — S18's original point: the
NPU shares the same DRAM bus, so a bandwidth-limited kernel is not helped by
moving it to a different compute unit on the same memory system.

It cuts *toward* the NPU only through **on-chip residency**, and that chain has
an unmet link already recorded:

```
LEDGER  VTCM is 8 MB vs a 12.8 MB packed store — it does not fit,
        so bundling is a prerequisite for residency
LEDGER  Bundling's magnitude on real data: 54x was B=1->B=64 compression;
        S52 measured clustering-vs-random only.  UNMEASURED
```

So S72b makes the NPU **conditionally relevant again, on a premise nobody has
measured**. That is a real change from where the descope stood and it is *not*
a revival. The honest position on the descope is now:

- the **ladder argument is untouched** — no SDK, no delegate, no scale pinning,
  no QNN licence, no requantisation assumption, and the prefilter still costs
  ~50 µs inside a query that is ~57% symbolic;
- but the **throughput argument has moved against it twice**: 5.7× short at the
  deployable operating point, and now a bandwidth bound that VTCM exists to fix.
- **VTCM is 8 MB against a 12.8 MB packed store**, so bundling remains a
  prerequisite — already in the LEDGER as a gap.

The descope stands on the ladder. It no longer has throughput support of any
kind, and I should stop implying it does.

## Controls, with their failing inputs (D6)
| control | fails if |
|---|---|
| gate green before **and** after | `quiet.sh --device --json` non-quiet either side — thermal drift would invalidate the scaling curve |
| per-instance GOP/s reported by the binary, not derived | a derived figure would hide the bandwidth effect, which is visible only per-instance |
| exactness digest unchanged | any kernel differing from `f4e64fb7d70b9b0c` means the concurrent run altered results |
| monotone aggregate | aggregate falling with more workers would indicate the pin is not honoured |
