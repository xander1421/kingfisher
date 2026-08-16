# S53 — residency, as a surface, in cycles/row

**Verdict: GREEN. Residency is worth 1.00× at one thread and 1.52× at six. Both S46's retraction and my un-retraction of it were right about their own configuration and wrong to generalise.**

I un-retracted S46's residency chain on a four-point sweep at *one* thread count on *one* day, then flagged that in the ledger as too thin to overturn a retraction. This is the version that settles it: four thread counts × four sizes, in the governor-invariant unit.

## Measured — cycles/row (per core, workers on the perf cluster, coordinator alone on cpu7)

| store | T=1 | T=2 | T=4 | T=6 |
|---|---|---|---|---|
| 12.8 MB | 15.81 | 16.22 | 18.08 | 21.86 |
| 25.6 MB | 15.80 | 16.13 | 21.13 | 27.18 |
| 51.2 MB | 15.88 | 16.07 | 20.64 | 29.44 |
| 102.4 MB | 15.74 | 15.87 | 21.19 | 33.14 |
| **residency factor** | **1.00×** | **0.98×** | **1.17×** | **1.52×** |

Clocks measured, not read: cpu7 3,266 MHz against sysfs 3,283 (ratio 0.995); worker cluster 2,763 MHz.

## What it settles
**Residency is a function of thread count, not of the workload.** At one core the kernel needs 15.8 cycles/row and the memory system is never the limit — flat to 0.4% across an 8× size range, which is S46's finding, correct and correctly measured for the first time. Add cores and the shared path starts to bind: 1.17× at four, **1.52× at six**, growing monotonically.

So both positions were locally right and both over-generalised:
- S46: "residency buys nothing" — true at T=1–2, false above.
- my un-retraction: "residency is worth 1.80×" — right in direction, and the figure was inflated by mixing a prime core into a perf-cluster measurement and by using GB/s. The honest number on one cluster is **1.52×**.

**For the NPU argument this is the useful form:** residency pays exactly to the degree that a unit can saturate memory. Six perf cores can, one cannot. Whether HVX can is N2, unchanged — but the question is now quantitative rather than binary, and the CPU gives the scale to beat.

## Two harness bugs found and fixed here, both self-inflicted
1. **The clock calibration returned 769,190,472 MHz.** `for (i..) x += i;` has a closed form and clang emitted it. Replaced with inline asm the optimiser cannot fold, plus a plausibility gate that aborts outside 500–5000 MHz and a cross-check against sysfs. Fourth unverified control in this workspace.
2. **The coordinator was pinned to cpu0 and worker 0 was also on cpu0.** The spinning coordinator timesliced against a worker; T=1 read 222 cyc/row against a true 15.8 — a 14× error. This is precisely the coordinator-starvation effect S51 discovered at T=8, walked into at T=1 one spike later.

## Caveats
- Workers are all perf-cluster, so this says nothing about mixing clusters; the prime cores issue NEON at twice the width (attacker's measurement) and were deliberately excluded to keep cycles/row meaningful.
- One run. The sweep is a surface in (threads × size) but a point in time; thermal state is uncontrolled.
- 15.8 cyc/row here vs the attacker's 16.85 on cpu0 — 6% apart, different day, different clock, same order.
