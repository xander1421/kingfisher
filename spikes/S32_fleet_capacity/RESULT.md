# S32 — fleet capacity projection

**Verdict: RED as a citation source. Written 2026-08-16, long after the fact, because this spike shipped without a RESULT.md and was then cited in ten documents. Mission §8 requires one. Its headline figure is a projection from a hypothetical 10,000-device fleet, not a measurement, and two of its inputs have since been falsified.**

## What is actually in this directory
`parallel.sh`, `sustained.sh`, `tps.py`, `tps.json`. No verdict, no caveats, no
grade — which is how its numbers travelled unqualified into `out/LEDGER.md`,
`out/RISKS.md`, `out/RETRACTIONS.md`, S33, S34, S35, S45, S50, S51 and S61.

## The measured base (`tps.json`)
```
job_steps                          100,082      the S15 query job
single_thread_sustained             383,000 steps/s
eight_way_burst                   2,954,450 steps/s
eight_way_sustained (used)        2,300,000 steps/s   (range 1.96M-3.87M)
host_single_thread (M4 Pro)       1,440,000 steps/s
```

## Where "28,700 jobs/s" comes from — and it is not a device measurement
| fleet size | optimistic+audit | **2-of-2 quorum** | conservative |
|---|---|---|---|
| 1,000 | 5,223 | 2,873 | 1,094 |
| **10,000** | 52,230 | **28,726** | 10,943 |
| 100,000 | 522,299 | 287,264 | 109,434 |

**`28,726` is 10,000 hypothetical devices under a 2-of-2 quorum.** Per device the
figure is **~2.9 jobs/s**.

This matters directly to `out/RISKS.md` R-NEW, which measures a settlement
ceiling of 8.6 jobs/s against "S32's 28,700 device-side" and reports a **3,353×
shortfall**. That comparison is *a measured chain throughput against a
ten-thousand-device projection*. The shortfall is real in the sense that a fleet
would outrun the chain, but the ratio is not device-vs-chain and R-NEW should say
so. Against **one** device at 2.9 jobs/s, an 8.6 jobs/s settlement layer is
*ahead*, and the crossover is around **3 devices**.

## Internal inconsistency
`tps.py:11` states *"8-way burst — 5.87x scaling"*. `tps.json` gives
burst/single = **7.71×** and sustained/single = **6.01×**. The 5.87 figure is not
derivable from the data file in this directory. Unresolved.

## Falsified inputs
- **The 8-way premise is dead.** S51 measured 6.30× at T=7 and **0.07× at T=8** —
  a collapse, not scaling. S54 then found Android's `background` cpuset is
  `0-1,4-5`, so a charge-time worker gets **four cores and never a prime core**.
  Every "eight_way" row describes a configuration the product cannot enter.
- **Sustained is a single estimate inside a 1.97×-wide band.** `2,300,000` was
  chosen from a measured range of 1,963,190–3,867,536. The choice is undocumented.

## Consumers that inherit this
`S34`'s "1.2× short" — and therefore its conclusion that an NPU is *necessary* —
multiplies through S32. `S33` and `tps.py` still print these numbers under a
"MEASURED" heading.

## Verdict
**Do not cite S32 as a measurement.** The per-device base (383k steps/s
single-thread sustained) is measured and may be cited as such. Everything
labelled "fleet" is arithmetic over an assumed device count, and everything
labelled "eight_way" is on cores the deployable configuration cannot reach.

The honest deployable figure needs re-deriving from S54's 4-core background
cpuset, and nobody has done it.
