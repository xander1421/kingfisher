# S54 — the deployable configuration, and it is four cores

**Verdict: RED for every performance number in this workspace. A WorkManager background worker cannot reach the cores every one of them was measured on.**

An auditor of `out/LEDGER.md` flagged that Android's `background` cpuset excludes the prime cores. Verified on device:

```
background         0-1,4-5      <- a charge-time worker lives here
system-background  0-1,4-5
foreground         0-5
top-app            0-7          <- only a foreground app sees cpu6/cpu7
restricted         0-7
```

**A background worker gets four cores: 0, 1, 4, 5.** Not eight, not seven, and never a prime core — `sched_setaffinity(cpu7)` is silently overridden by the cgroup.

## What that invalidates
| number | measured on | reachable by the product? |
|---|---|---|
| S50's 49.8 GB/s single-core | cpu7 (prime) | **no** |
| the A-graded 2.018× prime NEON advantage | cpu6/7 | **no — unbankable** |
| S51's 115.8 GB/s at T=7 | cpu0–6 | **no** |
| the attacker's 67.9 GB/s at T=8 | all 8 | **no** |
| S53's coordinator on cpu7 | cpu7 | **no** |

Every headline throughput figure in the workspace is from a configuration a charge-time worker cannot enter. The `top-app` cpuset does span 0–7, so a *foreground* app can — but the entire scheduling premise (S6, charge-time, screen-off, idle) is that we are **not** the foreground app.

## Measured in the configuration that is actually deployable
Workers on cpu0,1,4,5; coordinator on cpu6 (outside the set, which a real worker would not have — see caveat).

| store | T=1 | T=2 | T=3 | T=4 |
|---|---|---|---|---|
| 12.8 MB | 16.00 | 16.17 | 16.24 | 18.73 |
| 25.6 MB | 16.88 | 16.23 | 16.90 | 19.24 |
| 51.2 MB | 16.02 | 16.43 | 16.95 | 20.87 |
| 102.4 MB | 15.94 | 16.13 | 17.25 | 21.73 |
| **residency factor** | **1.00×** | **1.00×** | **1.06×** | **1.16×** |

cycles/row, clock measured (coordinator 3,268 MHz vs sysfs 3,283, ratio 0.995; worker cluster 2,793 MHz).

## Consequences
1. **Peak deployable parallelism is 4 threads, not 7 or 8.** S51's T=7 (6.30× scaling) and the T=8 cliff are both academic for a background worker. The relevant number is T=4.
2. **Residency is worth 1.16× in the deployable configuration**, not 1.52× (T=6) and not the 1.80× I first claimed. The VTCM/NPU argument's CPU baseline shrinks accordingly — a background worker is further from saturating memory than any measurement so far suggested.
3. **The 2.018× prime-cluster NEON advantage is unreachable.** It is real silicon and irrelevant to this product. Any plan that budgets for prime cores is budgeting for a foreground app.
4. **The coordinator problem gets worse.** S51 established that a spin barrier needs a core for the coordinator. With only four cores available, dedicating one leaves **three** workers — so either the barrier must block rather than spin, or the useful width is 3.

## Caveat that matters
I pinned the coordinator to cpu6, which is *outside* the background set. A genuine background worker would have to place its coordinator inside 0,1,4,5 too, costing one of the four. The honest deployable number is therefore **3 workers + 1 coordinator**, or 4 workers with a blocking barrier, and neither is measured here. This spike establishes the constraint, not the final figure.

Also unmeasured: whether `adb shell` processes are themselves in a cpuset that differs from an app's, and whether Samsung's governor applies further per-cgroup frequency caps.
