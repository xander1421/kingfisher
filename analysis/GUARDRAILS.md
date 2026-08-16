# GUARDRAILS — rules taken from production elder code, not invented here

Every rule below is lifted from code that has run in production against untrusted
consumer hardware, with a `file:line` citation. Each one is paired with the
specific mistake in this workspace that it would have prevented.

This exists because the last three spikes produced numbers that adversarial review
destroyed — not because the experiments were careless, but because I was inventing
measurement methodology while measuring. BOINC has been benchmarking heterogeneous
untrusted consumer devices continuously since 2002. The methodology is a solved
problem and I should not have a house style for it.

---

## A. Measurement

### A1. Never time an event shorter than seconds. Time a fixed window and count work.
`boinc/client/cs_benchmark.cpp:77-81` — the benchmark is a **10-second window**
(`FP_START 2` → `FP_END 12`), a 5-second settle gap, then a second 10-second window
(`INT_START 17` → `INT_END 27`), `OVERALL_END 30`.

Nothing in BOINC times a millisecond. It runs a fixed wall-clock window and counts
iterations completed inside it. Frequency drift, scheduler preemption and cache
state all average out inside a 10-second window; they dominate completely inside a
0.25 ms one.

> **Prevented:** S55's `0.310 ms`, S56's `0.19–0.32 ms`. Both timed a ~250 µs event
> and reported three significant figures. The true spread was 2.1×.

### A2. Discard a measurement that did not get enough CPU. Do not scale it.
`boinc/client/cs_benchmark.cpp:83-85` — `MIN_CPU_TIME 2`: *"if the CPU time
accumulated during one of the 10-sec segments is less than this, ignore the
benchmark."* If the process got under 2 s of CPU in a 10 s window — i.e. under 20%
of a core — the sample is thrown away, not normalised.

> **Prevented:** the coordinator-starvation errors twice (S51 at T=8, S53 at T=1,
> a 14× error). Both produced a number from a thread that barely ran. A CPU-time
> floor would have rejected both automatically instead of requiring me to notice.

### A3. Benchmark under contention, because that is the deployed condition.
`boinc/client/cs_benchmark.cpp:20-22` — *"we must run parallel benchmarks and
ensure that they run more or less concurrently."* One benchmark process per CPU,
synchronised by touching `do_fp` / `do_int` files so the measurement windows
overlap. Memory bandwidth and cache are shared resources; a single-threaded number
measured on an idle machine does not predict fleet behaviour.

> **Prevented:** the whole S50/S51/S53 confusion about whether throughput was flat.
> Single-thread flat, multi-thread not — measured separately and reconciled late.

### A4. On failure, substitute a conservative default and say which direction is safe.
`boinc/client/cs_benchmark.cpp:69-75` — *"defaults in case benchmarks fail or time
out. **better to err on the low side so hosts don't get too much work**"*, then
`DEFAULT_FPOPS 1e9`. There is also a hard timeout
(`MAX_CPU_BENCHMARKS_SECONDS`) after which defaults are used.

The rule is not "have a default" — it is **name the direction in which being wrong
is safe, and default that way.** For us, underestimating a device's speed means it
gets less work; overestimating means missed deadlines and wasted fleet capacity.

### A5. Abort the measurement if the environment is not controlled. Do not correct for it.
`boinc/client/cs_benchmark.cpp:396-400` — if applications cannot be suspended,
the client logs *"Failed to stop applications; aborting CPU benchmarks"* and
**aborts**. It does not measure-and-subtract.

> **Prevented:** every one of the five broken controls in `LEDGER` standing rule 9,
> all of which were measure-then-subtract.

### A6. Variance can be process-scoped. Sample N processes, not N iterations.
Not from an elder — this is the one thing an attacker found here that BOINC's
design sidesteps rather than states, and it is worth writing down because BOINC's
architecture makes it structurally impossible to hit: BOINC forks a **fresh process
per benchmark** and the whole client re-benchmarks only every 30 days
(`cs_benchmark.cpp:98`, `BENCHMARK_PERIOD (SECONDS_PER_DAY*30)`, *"rerun CPU benchmarks this often (hardware may have been upgraded)"*).

Measured here: within one process CV ≈ 3%; across 12 processes CV ≈ 23%, and it
survives a pinned, settled clock (0.302 / 0.275 / 0.170 ms at an identical
2,918,400 kHz). Best-of-N wandered non-monotonically in N, which is proof the
between-process term dominates.

**Corollary — criterion is not sufficient.** `hyperon-experimental/hyperon-space/Cargo.toml:17`
uses `criterion = "0.7"` with `harness = false`, and criterion does warmup, outlier
detection and confidence intervals — all **within one process**. It would have
reported a tight CI around whichever placement that process happened to get. Use
criterion for A/B comparisons inside a process; never for an absolute figure.

---

## B. Trusting a number from a device

### B1. Do not derive a per-platform constant from fewer than 100 samples.
`boinc/sched/credit.h:25-28` — `MIN_HOST_SAMPLES 10` (*"use host scaling only if
have this many samples for host"*), `MIN_VERSION_SAMPLES 100` (*"update a version's
scale only if it has this many samples"*).

A "version" in BOINC is a binary + platform + plan class — exactly our
`aarch64-android + kernel build` unit. BOINC will not adjust that unit's scale
factor until it has **100 completed jobs**.

> **Prevented:** every speedup this workspace has published. 54×, 12.8×, 31.6×,
> 5.87×, 2.26×, 18.3× — all from n=1 to n=3 invocations. Under BOINC's own rule
> none of them would have been allowed to change a scale factor.

### B2. Grade every derived value by how it was obtained, and have an INVALID grade that discards.
`boinc/sched/credit.cpp:191-207` — four levels: `PFC_MODE_NORMAL` (properly
computed), `PFC_MODE_APPROX` (*"approximated, but still reflects the size of the
particular job"*), `PFC_MODE_WU_EST` (*"a last resort, and can be way off"*), and
`PFC_MODE_INVALID` (*"exceeded max granted credit — ignore"*).

Our `out/LEDGER.md` A–E scale is the same idea, arrived at independently and worse:
it has no INVALID. A claim that fails a plausibility check should be **dropped**,
not demoted to E and left in the table where it can still be cited.

### B3. Clamp against an absolute ceiling that is independent of the reported work.
`boinc/sched/credit.cpp:910-919` — *"max_granted_credit trumps rsc_fpops_bound; the
latter may be set absurdly high"*. When the claim exceeds the ceiling it logs
`"Credit too high"`, clamps, **and marks the sample INVALID so it does not
contribute to any average.** Two actions, not one.

> **Prevented:** the 769,190,472 MHz clock calibration. I eventually added a
> plausibility gate (S53) — after being burned. The gate belongs on every derived
> quantity from the start, and it must both clamp and poison the sample.

### B4. Normalise against the fleet, not against a self-report.
`boinc/sched/credit.cpp:252` — `av.pfc_scale = avg / av.pfc.get_avg()`, where `avg`
is the minimum average across all app versions with enough samples. No device's
own claim about its speed is trusted; every version is scaled against the most
efficient one observed across the fleet.

### B5. Constants carry their provenance and their bias, inline.
`boinc/sched/credit.cpp:284-289`:
```c
#define DEFAULT_GPU_SCALE   0.1
// if there are no CPU versions to compare against, multiply pfc_scale of GPU
// versions by this. This reflects the average lower efficiency of GPU apps.
// The observed values from SETI@home and Milkyway are 0.05 and 0.08.
// We'll be a little generous and call it 0.1
```
Where it came from, what was actually observed, and which way they rounded. **Every
tuned constant in our tree gets this comment or it does not ship.**

> **Prevented:** the oracle-fitted cutoff, which sat unlabelled through six spikes
> before `LEDGER` rule 5 forced it onto the row.

---

## C. Determinism and verification

### C1. Byte-identical comparison requires a declared canonical form. Name every excluded byte.
`boinc/sched/sample_bitwise_validator.cpp:25-27` — with `--is_gzip`, *"the 10-byte
gzip header is skipped (it has stuff like a timestamp and OS code that can differ
even if the archive contents are the same)"*.

This is precisely the S35 finding — `mork --timing` writes nanoseconds into the
hashed space — rediscovered here 20 years late. BOINC's answer is not "don't use
timing"; it is **the validator owns a canonicalisation step, and what it strips is
part of the spec.**

> Our `hyperjob` schema needs an explicit canonical form with a named exclusion
> list, and the verifier must strip before hashing. Currently
> `spikes/S49_schema_v1/verifier2.py` has canonical forms (VERBATIM / SORTED_SET /
> SORTED_BAG) but no exclusion list.

### C2. Bitwise validation is only sound under no-float **or** homogeneous redundancy. State which.
`boinc/sched/sample_bitwise_validator.cpp:17-22` — *"useful only if either 1) your
application does no floating-point math, or 2) you use homogeneous redundancy."*

We claim branch (1): MeTTa reduction is integer/symbolic, and S15 measured
byte-identical output plus identical fuel counts across aarch64 and x86-64. That is
the correct branch **and it is the single most valuable property this project has**
— BOINC needs a whole host-classification subsystem (`sched/hr.cpp`) that we get to
delete. Guardrail: any feature that introduces floating point into the reduction
path costs us `hr.cpp`, and must be priced that way.

### C3. If a host's class cannot be determined, exclude it. Fail closed.
`boinc/sched/hr.cpp:132,144` — `hr_class()` carries *"call this ONLY if
hr_unknown_class() returns false"*, and `hr_unknown_class()` returns true for any
unrecognised OS or CPU. Unknown hardware is not guessed at; it is excluded from
replication entirely.

### C4. Differential-test two independent implementations, and pin the step count too.
`MORK/differential/run.py:2-9` — runs every corpus program through **two builds**
(ProductZipper reference and leapfrog join) and compares *"byte for byte, the space
each one dumps **as well as the number of steps each one reports executing**"*.
Programs may also carry a checked-in expected space, so the corpus doubles as a
regression suite when only one engine is available.

Two features worth stealing verbatim:
- **Pin the fuel count, not just the output.** Two engines can agree on a result
  while disagreeing on work done — which for us is a billing and verification bug,
  not a cosmetic one.
- Directives live in ordinary `;` comments so *"a program stays a runnable
  program"*. Test metadata never makes the artefact non-executable.

### C5. Quorum before adjudication, and majority rather than pairwise agreement.
`boinc/sched/validator.cpp:454` — nothing is validated until
`viable_results.size() >= wu.min_quorum`. Results accumulate; the comparison
happens once there are enough of them.

`boinc/sched/sample_bitwise_validator.cpp:17-18` states the rule precisely: it
*"requires a **majority** of results to be bitwise identical"*. Not "two agree" —
a majority of a quorum. Two colluding devices echoing one hash cannot carry a
quorum of three, which is the same property `PORT_PLAN`'s commit/reveal seal
exists to provide and is cheaper.

> This is the answer to the gap `GAP_MATRIX` §46 names as the one the mission's
> capability list missed. BOINC gets it from quorum size; we were going to build
> it from cryptography. Do both, but size the quorum first — it is free.

---

## D. What the elders do *not* give us

Being honest about the boundary, so this document is not used as cover.

| need | why no elder covers it |
|---|---|
| **short-event in-process timing** | BOINC never does it (A1). Our stage-2 figure is ~250 µs and there is no production precedent for measuring that on a phone. Own methodology required — which is exactly where the failures were. |
| **NPU / HVX** | Nothing in any elder targets a phone NPU. Confirmed in `GAP_MATRIX` row 6. |
| **shaping as a job class** | `GAP_MATRIX` row 17 — genuinely novel, nothing to copy. |
| **content-addressed Atomspace shards** | `GAP_MATRIX` row 9 — DAS addresses atoms by handle inside a database, not shards by hash. |

For the first row the honest guardrail is A1's contrapositive: **if the quantity is
too short to measure BOINC's way, restructure the experiment until it isn't.**
Measure 10 seconds of back-to-back stage-2 invocations and divide, across ≥12
processes — do not measure one and report it.

---

## E. Adoption checklist

Rules that can be enforced mechanically, in the order they should land.

- [ ] **A6/B1**: benchmark runner takes ≥12 processes × ≥10 s each; refuses to print a figure otherwise.
- [ ] **A2**: every worker reports CPU time consumed; samples under 20% of a core are dropped, and the drop is logged with a count.
- [ ] **B3**: every derived quantity gets a plausibility interval; violations clamp **and** poison the sample.
- [ ] **B2**: add `INVALID` to the `LEDGER` grade scale; INVALID rows are deleted, not demoted.
- [ ] **B5**: audit every tuned constant in `spikes/` for a provenance comment.
- [ ] **C1**: `hyperjob` canonical form gains an explicit exclusion list; `verifier2.py` strips before hashing.
- [ ] **C4**: stand up a differential corpus for our own engine wrapper — two builds, byte-compare, pinned fuel.
- [ ] **A4**: name the safe direction for every default in the scheduler.
- [ ] **C5**: set `min_quorum` ≥ 3 and require a majority, before any seal work.

### A7. A caveat that would change the verdict if true is not a caveat — it is an unfinished experiment.
S60 v1 listed three caveats (n=1, unsound digest, workload dependence) and delivered its verdict as if none fired. **Each one, run, flipped a headline number.** Before publishing, take every caveat in the draft and ask: if this is true, does the headline change? If yes, it is not ready. Writing the limitation down does not discharge it.

### A8. Reuse of expensive setup across benchmark iterations is a correctness bug, not an optimisation.
S60 v1 built one `Metta` and reused it, so iterations 2+ ran against a polluted atomspace and aborted at 5,709 of 50,794 steps — silently, because the abort path returns `Ok(())`. **Construct fresh state per iteration and exclude setup from the clock**; if that is too slow, the window is too short. Assert the work done per iteration is constant, and print it.

---

## Provenance

All 15 spot-checkable citations above were verified line-by-line against the
cloned trees on 2026-08-16 (`analysis/` commit). BOINC is LGPL-3.0: **these are
rules read from it, not code copied from it** — no BOINC source enters our tree,
per the §7 licence gate. MORK is unlicensed; `differential/run.py` is likewise
read for its design, not copied.
