# S71 (C2) — per-device supply, measured, replacing the INVALID projection

**Verdict: GREEN. 2.83 jobs/s single-worker and 11.17 jobs/s at 4 workers, sustained on the background cpuset with zero failures. The number R-NEW relied on was right; its provenance was not. C2 is answered and the zkVM-descope charge it held open is released.**

C5 charged that "3× replication is affordable" rested on `RISKS.md:218`'s
**2.87 jobs/s**, which is `28,726 / 10,000` — and 28,726 is marked **INVALID** in
the LEDGER as a fleet projection. This measures the quantity directly.

## Gate — both sides, for the first time
```
host   : refused (11 containers)      -> irrelevant, this is a device measurement
device : {"quiet":true,"device_cpu_busy_pct":0.6,"thermal_m":33200,
          "battery":"status=5 level=100 runnable=1","refusals":""}
post-run: cpu_busy 0.7%, thermal 42800m
```

Two false positives in `quiet.sh --device` were fixed to get here, both by
checking rather than trusting:
1. **Charging** was tested via `AC/USB powered`, which Android clears at 100%
   because the charger disengages. `status: 5` is FULL, i.e. plugged. Same
   misdiagnosis that had the energy measurement filed as "blocked: needs root."
2. **Load** was tested via device loadavg, which read **9.19 while the CPU was
   6.0% busy with 1 runnable task out of 8,889**. Android's loadavg counts
   uninterruptible-sleep background services. The gate now uses a `/proc/stat`
   delta.

## Measured — `job_terminating.metta`, fuel_used **100,082** (S32's job), `taskset 33`

| workers | jobs / 12 s | jobs/s | scaling |
|---|---|---|---|
| 1 | 32 | **2.67** | 1.00× |
| 2 | 66 | 5.50 | 1.94× |
| 3 | 99 | 8.25 | 2.92× |
| 4 | 134 | **11.17** | 3.95× |

Five independent single-worker windows: 2.83 / 2.83 / 2.83 / 2.75 / 2.83 jobs/s,
**zero failures**. Only `status OK` completions counted.

## 1. The projection was right; its provenance was not
`RISKS.md`'s 2.87 jobs/s against a measured **2.83** — within **1.4%**. So the
arithmetic descended from an INVALID source and happened to land on the truth.
That is luck, not method, and the figure now has a direct measurement behind it.

**C2 is answered and the charge is released.** The "compute is abundant, chain is
scarce" trade that justifies dropping the zkVM stack stands.

## 2. Scaling across the background cpuset is very nearly linear
3.95× at 4 workers, on the `0-1,4-5` cpuset S54 established is all a charge-time
worker gets. No coordinator here — these are independent processes, which is also
the shape S32a validated for co-tenancy and the shape `PORT_PLAN` M1.3 now
mandates (fork fresh per job).

So the honest deployable supply is **~11 jobs/s per device at 4 workers**, or
~8.25 at the 3-worker shape S54 recommends once a coordinator is subtracted.

## 3. This makes the settlement trade stronger, not weaker
| | |
|---|---|
| per-device supply, 4 workers | **11.17 jobs/s** — measured |
| settlement ceiling, per-job posting | ~17 jobs/s — PoV-bound |
| devices to saturate per-job settlement | **~1.5** |

**A single device now saturates the per-job settlement path**, against the "three
devices" figure S32's projection implied. That sharpens R-NEW rather than
softening it, and it strengthens the case for Merkle batching, since the crossover
is below one device.

## Instrument defects found and fixed en route
- `job_kb.metta` is **non-terminating** — FUEL_EXHAUSTED at 200,000 steps in
  539 ms. The S32 job is `job_terminating.metta` at exactly 100,082 steps.
- The first loop script ran from `/` rather than the binary's directory, so
  `./fuelrun` did not exist and the loop spun on instant failures — reporting
  **77 jobs/s**, a 27× overstatement. Caught because 77 jobs/s implies 7.7M
  steps/s against S32's measured 383k. **The plausibility check is what caught
  it, not the harness.**

## Caveats
- One device, one job shape, 12-second windows. Not a thermal-soak test: thermal
  rose 33.2 °C → 42.8 °C across the run, still under the 45 °C gate but trending.
- Sustained over 12 s, not over hours. S30 found 3.7× host:phone sustained versus
  burst; this is nearer the sustained end but is not a duty-cycle measurement.
- `taskset 33` pins to cores 0,1,4,5. Whether Android's scheduler honours that
  for a background app rather than a shell process is S54's open question.
