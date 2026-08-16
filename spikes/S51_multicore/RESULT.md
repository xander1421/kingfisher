# S51 — the multi-core number, measured properly for the first time

**Verdict: GREEN. 115.8 GB/s at 7 threads — 2.28× S45b's figure — and using all 8 cores is catastrophic, by a factor of 89.**

S50 closed by declaring that no defensible multi-threaded throughput number existed in this workspace: S32's 5.87×, S45b's 50.8 GB/s and the 28,700 jobs/s fleet model all descend from harnesses with `pthread_create` inside the timed region, a ~40 µs condvar barrier, and no pinning. This closes that gap.

Spin barrier (two atomics, no futex), one thread pinned per core, amortised over many passes, digest over every row at every thread count, and the barrier's own cost measured with an empty kernel as the null.

## Measured — 12.8 MB store

| T | static µs | GB/s | scaling | dynamic µs | GB/s | scaling | barrier null | digest |
|---|---|---|---|---|---|---|---|---|
| 1 | 695.8 | 18.4 | 1.00× | 572.7 | 22.4 | 1.00× | 0.1 µs | OK |
| 2 | 292.5 | 43.8 | 2.38× | 337.0 | 38.0 | 1.70× | 0.1 | OK |
| 3 | 192.0 | 66.7 | 3.62× | 232.7 | 55.0 | 2.46× | 0.1 | OK |
| 4 | 175.1 | 73.1 | 3.97× | 180.9 | 70.8 | 3.17× | 0.2 | OK |
| 5 | 154.6 | 82.8 | 4.50× | 151.8 | 84.3 | 3.77× | 0.2 | OK |
| 6 | 139.7 | 91.6 | 4.98× | 143.4 | 89.3 | 3.99× | 1.0 | OK |
| **7** | **110.5** | **115.8** | **6.30×** | **107.2** | **119.4** | **5.34×** | 0.9 | OK |
| 8 | 9,793.8 | 1.3 | 0.07× | 8,601.4 | 1.5 | 0.07× | **10,849.9** | OK |

## 1. The real number is 115.8 GB/s, not 50.8
S45b reported 50.8 GB/s at T=4 and called it 86% of a 58.9 GB/s "roof". At T=7 this measures **115.8 GB/s — 2.28× that figure, and 1.97× the supposed roof itself.** The roof was never a roof; it was a latency-bound loop with thread spawn inside the timed region.

Independent confirmation of the attacker's 2.2×, reached by a different route (they used a spin barrier and static splits at 12 MB; this pins explicitly and sweeps thread count).

Per query on a 12.8 MB store: **110.5 µs → ~9,050 queries/s**, against the 3,968 q/s that S45b's number implied.

## 2. Using all 8 cores is 89× worse than using 7
The T=8 row is not noise. The barrier null alone is **10,849 µs** — the dispatch, with an *empty* kernel, costs more than the entire T=7 query. With a worker spinning on every core there is no core left for the coordinator, so the OS must timeslice a spin-waiting thread against eight spin-waiting threads.

This is a hard rule for the device agent: **with a spin barrier, never run one worker per core. Leave the coordinator a core.** The correct configuration on this 8-core part is 7 workers. Any thread-pool sized to `nproc` — the obvious default, and what S32 and S45b both did — lands exactly on the cliff.

It also explains a mystery: S45b saw T=8 (287 µs) come out *worse* than T=4 (252 µs) and attributed it to memory-system contention. With a condvar the workers sleep, so oversubscription degrades gracefully instead of collapsing; the reversal was the beginning of this same effect, not a property of DRAM.

## 3. The barrier is now free
0.1–1.0 µs against 110–695 µs of work, i.e. **≤1%** at every usable thread count. The condvar barrier S45b used cost ~40 µs, which at T=4's 252 µs was 16% of the measurement. Spin barrier is ~400× cheaper and the null is reported rather than assumed.

## 4. Static beats dynamic below 7 threads, dynamic wins at 7
Static equal chunks are ahead at T=2–4 (43.8 vs 38.0 at T=2) despite the SoC being heterogeneous, which contradicts the expectation that equal chunks would leave stragglers. Work-stealing's atomic cursor costs more than the imbalance it removes until enough cores are in play. At T=7 dynamic edges ahead (119.4 vs 115.8), which is where the two prime cores are finally included and the imbalance is real.

## 5. Parallelism does not change the answer
Digest identical at every thread count and under both split strategies. Combined with S34 (three kernels, two machines) and S50 (two core types), determinism now holds across architectures, engines, build profiles, core types, thread counts and scheduling strategies.

## Caveat that limits all of the above
Clocks after the run read **1,996 MHz on cpu0–5 and 1,958 MHz on cpu6–7** — roughly 56% and 44% of their 3,532 and 4,474 MHz maxima. The device was thermally throttled by the end of the sweep, so 115.8 GB/s is a *throttled* figure and the ordering between rows may shift on a cool device. Everything here is a floor, not a ceiling, and a sustained-vs-burst arm in the style of S30 is still missing.

## What this replaces
| dead | replacement |
|---|---|
| S45b "50.8 GB/s at T=4, 86% of a 58.9 roof" | **115.8 GB/s at T=7**, and the roof was an artefact |
| S32 "5.87× on 8 cores" | **6.30× at 7 cores; 8 cores is 0.07×** |
| "3,968 queries/s/device" | **~9,050 queries/s/device** on a throttled device |
| S45b "T=8 reversal is memory contention" | the onset of coordinator starvation |
