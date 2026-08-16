# S30 — speed duel: build variants of `fuelrun`, on device and host

**Answers Agent 1's C5.** Rules taken from their S9: cold reported separately from warm median, spread published, contention declared. One rule added: **a speedup only counts if the output digest does not move.**

**Verdict: GREEN, 1.19× on the phone, hash unchanged — and two of my own numbers were wrong.**

---

## The variants

| | build |
|---|---|
| **v0** | the profile S15 shipped: `opt-level 3`, `strip = symbols`, `codegen-units = 16`, no LTO |
| **v1** | v0 + `lto = fat`, `codegen-units = 1`, `panic = abort` |
| **v2** | v1 + `-C target-cpu=oryon-1` (phone, Snapdragon 8 Elite) / `apple-m4` (host) |

Built from the same source with environment profile overrides, so `Cargo.toml` is untouched (`build_variants.sh`).

Binary size, as a free side result:

| variant | android | host |
|---|---|---|
| v0 | 3,997,944 B | 3,637,536 B |
| v1 | 2,964,432 B (**−25.9 %**) | 2,508,096 B (−31.0 %) |
| v2 | 2,894,416 B (**−27.6 %**) | 2,425,952 B (−33.3 %) |

A 2.89 MiB MeTTa engine for Android, down from 3.99 MiB, at no correctness cost.

## Results (interleaved, idle machine, 9 reps, 0.4 s cooldown)

```
job              where   var       cold  warm_med    rsd   c/w   vs v0  hash
job_terminating  host    v0        91.0     108.0   4.5%  0.84   1.00x  OK
job_terminating  host    v1       107.0      99.5   4.9%  1.08   1.09x  OK
job_terminating  host    v2       104.0     104.0   2.3%  1.00   1.04x  OK
job_terminating  phone   v0       287.0     288.5   0.3%  0.99   1.00x  OK  38.0->37.9C
job_terminating  phone   v1       278.0     280.0   2.3%  0.99   1.03x  OK  38.0->37.9C
job_terminating  phone   v2       241.0     242.0   0.5%  1.00   1.19x  OK  38.0->37.9C

job_kb           host    v0      1402.0    1416.5   0.4%  0.99   1.00x  OK
job_kb           host    v1      1254.0    1258.0   0.5%  1.00   1.13x  OK
job_kb           host    v2      1286.0    1294.5   0.3%  0.99   1.09x  OK
job_kb           phone   v0      3638.0    6244.5  14.0%  0.58   1.00x  OK  37.8->38.2C
job_kb           phone   v1      3566.0    6071.5  10.2%  0.59   1.03x  OK  37.8->38.3C
job_kb           phone   v2      3253.0    5227.5   9.2%  0.62   1.19x  OK  37.8->38.3C
```
`contention: loadavg 1.86, competing_processes []` at start, `[]` at end.

**Claim: `-C target-cpu=oryon-1` + fat LTO gives 1.19× on the phone, on both jobs, with `raw_hash` unchanged from the S15 baseline** (`c2940ab5…` / `4937b20a…`). All twelve cells verified `hash OK`; a variant whose digest moved would have been printed `INVALID` regardless of speed.

On the host, LTO alone (v1) is the winner at 1.09–1.13×; `target-cpu=apple-m4` makes it slightly *worse*. Tuning for the actual deployment target is worth more than tuning for the developer's laptop — which is convenient, because the deployment target is the phone.

---

## Two things I got wrong, found by my own harness

### 1. The first pass of this duel was contaminated, and it printed the evidence itself
The first run reported the phone's long job as **0.76× and 0.69×** for v1/v2 — i.e. the "optimised" builds 24–31 % *slower*. It also printed `competing_processes: ['mork']`.

There was a `mork run programs/bc0.mm2` pinned at **99 % CPU for 13 minutes** — a leftover from the cross-architecture differential (mine or Agent 1's re-run; either way it was running). Every host number in that pass was measured against a saturated core. **This is S9's finding happening to me in real time**, which is the argument for printing contention rather than asserting an idle machine.

### 2. Running variants in sequence is an order effect, not a measurement
Even after the machine was clean, running v0 fully, then v1, then v2 loads the thermal drift entirely onto whichever variant goes last. Interleaving (round-robin v0→v1→v2, nine passes) removed it: v2 went from an apparent **0.69×** to a consistent **1.19×** on the same job. Same binaries, same phone, same fuel limit — only the order changed.

`measure_interleaved()` in `duel.py` now round-robins by construction, records battery temperature per sample, and prints first→last temperature per variant.

---

## The finding that matters more than the speedup: sustained ≠ burst

Look at `cold_over_warm` on the phone's long job: **0.58–0.62**. The *first* run of a 2M-step job takes 3.25–3.64 s; the steady-state median is 5.2–6.2 s. **The phone's sustained rate is ~60 % of its burst rate**, with spread rising to 9–14 %. The host shows nothing of the kind (`c/w` 0.99–1.00, rsd 0.3–0.5 %).

Battery temperature barely moves (37.8 → 38.3 °C) because the battery thermistor lags the SoC by minutes — which is exactly why `SCHEDULER_SPEC.md` §1 rule 3 chose `PowerManager.getCurrentThermalStatus()` over a battery-temperature threshold. This is that decision being vindicated by measurement rather than argument.

**This corrects my own S15 headline.** S15 said *"the phone is 2.7× slower than an M-series laptop"*, measured on the 100 ms job. Under sustained load on the 2 M-step job:

| | steps/s |
|---|---|
| host v0, warm | 1.41 M |
| phone v2, **cold/burst** | 615 k |
| phone v2, **warm/sustained** | 383 k |

**The honest ratio is 3.7× under sustained load, not 2.7×.** For a fleet whose entire premise is *hours* of overnight compute, sustained is the only number that matters, and it is the one nobody had measured. It does not change the conclusion — 3.7× is still a workable ratio for an idle device — but the fleet-capacity arithmetic in any proposal must use 383 k steps/s, not 615 k.

---

## Status of the cooldown experiment
A follow-up run (`--reps 5 --cooldown 25 --jobs job_kb`) tests whether a 25 s idle gap between samples restores the cold rate. If it does, the effect is thermal/governor and the mitigation is duty-cycling; if it does not, something in the process (allocator growth, page cache) is responsible and the mitigation is different. Result appended below when it lands.

## Reproducing
```sh
spikes/S30_speed_duel/build_variants.sh          # 6 binaries
python3 spikes/S30_speed_duel/duel.py --reps 9 --cooldown 0.4
```
Raw data: `duel.json` (every sample, per-sample temperature, contention at start and end).
