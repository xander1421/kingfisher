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

**And this covers measurements, not only tuned constants.** S32's headline 5.87×
is `2,954,450 / 502,924` and is entirely correct — but the denominator appeared
nowhere in the spike directory. It lived in a chat message, so for weeks the
figure looked un-derivable from its own artefact and was written off as an
internal inconsistency. It was a missing field, not a wrong number. **A measured
value cited in a result must have every input present in the artefact**, or the
result is unfalsifiable by anyone who was not in the room.

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

We claim branch (1), **conditionally**. Cited correctly: **S57** (grade B, 2026-08-16)
— aarch64-macOS / x86_64-macOS / aarch64-Android, **67/67 identical fuel counts,
66/67 identical results, 360,847 terminating steps**. *Not* S15, which compared
aarch64-macOS to aarch64-**Android** — same ISA — and whose "across architectures"
wording is struck through at `LEDGER.md:39`.

**The condition is not optional.** S57's corpus contains **zero transcendental
calls**, so it would not have caught S59, which measured real divergence:
11/197 evaluations differ arm64-vs-x86-64 and 14/197 macOS-vs-bionic, max 2 ULP.
Branch (1) therefore holds only under the S58+S59 ban list — no `flip`, `&rng`,
`reset-random-generator`, `sin/cos/tan/asin/acos/atan-math` — and with a seeded,
version-pinned RNG.

Under those conditions this is **still the single most valuable property this
project has**: BOINC needs an entire host-classification subsystem (`sched/hr.cpp`)
that we get to delete. Guardrail: any feature that puts floating point — or an
unpinned libm call — into the reduction path costs us `hr.cpp`, and must be priced
that way.

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
| ~~**NPU / HVX**~~ | **FALSIFIED 2026-08-16, row removed from this table.** `elders/executorch/backends/qualcomm/` names **SM8750** (39 mentions) and HTP (716) — our exact SoC — and `backends/samsung/` exists too. `GAP_MATRIX` row 6 is rewritten to PORT. This row was cover in a section whose first line promises not to be. |
| **shaping as a job class** | `GAP_MATRIX` row 17 — genuinely novel, nothing to copy. |
| **content-addressed Atomspace shards** | *Partially stale.* `GAP_MATRIX` row 9 was re-scoped: `iroh-blobs` may supply this outright, collapsing M1.5 and M1.7, and S14 found MORK's `server` branch already ships a canonical `.paths` format. The residual gap is smaller than this row implied. |

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
- [ ] **B2**: add `INVALID` to the `LEDGER` grade scale; INVALID rows are deleted, not demoted. **Still open — LEDGER v2 rewrote the grading scheme from scratch and still shipped A/B/C/D/E with no INVALID. The rewrite was the moment to land this and it passed.**
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

### A13. A9 is mechanised, because stating it five times did not work.
`spikes/claimcheck.py` — run it, do not remember it.

A9 has been stated, widened and re-stated, and fired five times anyway: S15
(cross-OS fitted, cross-ISA asserted), S32a (separate-process -> in-process),
S72 (single-core -> cpuset), W1 (key-lookup -> similarity-search), B1 (B=1
bipolar -> B>1 ternary). **A rule that fails five times is a mechanism problem,
not a discipline problem.** A10 already made this move for A5: `quiet.sh` does
not ask you to declare the machine quiet, it refuses.

A spike opts in by emitting `conditions` (and optionally `cites`) in its JSON:

```json
"conditions": {"platforms": [["macos","aarch64"],["android","aarch64"]],
               "concurrency": "separate-processes", "workers": 4,
               "cpuset": "0-1,4-5", "encoding": "binary-1bit",
               "data": "real:FB15k-237", "swept": {"B": [8,16,32]}},
"cites": ["S11_bundling"]
```

Three checks, ordered by what each has cost:

1. **VOCABULARY** — a claim word in `RESULT.md` that asserts a condition the
   artifact does not record. *"cross-architecture"* requires two distinct
   arch values; *"deployable"* requires the cpuset obtained; *"real data"*
   requires `data` not to start with `synthetic`. Catches S15, S32a.
2. **DEGENERACY** — a metric constant across a swept axis is not measuring
   that axis. Catches W1's four controls incapable of failing and B1's first
   recall metric (100% at every B). **Four of the last five defects were
   caught by a human noticing the shape was flat or non-monotone; this is
   that observation, automated.**
3. **INHERITANCE** — when a spike cites another, diff their `conditions` and
   report every field that differs. This is A9 in general form. Verified
   against the real B1 case: it emits
   `conditions.encoding 'binary-1bit-BIPOLAR-B1-ONLY' -> 'binary-1bit'`,
   which is precisely the premise that stopped holding.

Load-insensitive — it reads files and compares strings, so it runs through a
refused host gate exactly as S61 and Q1 do. `--demo` asserts 5 controls, hit
**and** miss on both discriminating checks; a checker whose controls cannot
fail is the defect it exists to find.

Absent fields report as UNDECLARED. Nothing is assumed.

> **Adoption:** new spikes emit `conditions`. No retrofit of the 59 existing
> dirs — the cost is not worth it and the check is only load-bearing going
> forward. `claimcheck.py` reports how many are opted in, so the coverage is
> visible rather than assumed.

---

## Provenance

All 15 spot-checkable citations above were verified line-by-line against the
cloned trees on 2026-08-16 (`analysis/` commit). BOINC is LGPL-3.0: **these are
rules read from it, not code copied from it** — no BOINC source enters our tree,
per the §7 licence gate. MORK is unlicensed; `differential/run.py` is likewise
read for its design, not copied.

---

### A9. A guardrail that cites a claim must carry that claim's grade and date. A citation you did not re-check is not a citation.

This document cites `GAP_MATRIX` rows and spikes by bare number. Four of those
citations went stale within days — §C2 rested on a **retracted** S15, §D's NPU row
was **falsified** by a clone already on disk, §D's shard row was re-scoped, and an
§E checklist item was silently skipped by the very rewrite that should have landed
it. **All four were invisible from inside the document**; you had to leave it to
discover the rule was standing on a withdrawn claim.

**A9's widest form: a formula inherits the preconditions of the case it was
fitted to, and reusing it silently re-asserts them.** Five instances now — S15's
"cross-architecture" (cross-OS fitted, cross-ISA asserted), S32a's co-tenancy
(separate processes fitted, in-process asserted), S72's 15.2× (single-core
fitted, cpuset asserted), W1's read set (key-lookup fitted, similarity-search
asserted), and B1's `1 bit/dim` (**B=1 bipolar fitted, B>1 ternary asserted**).
The tell is never a wrong number — it is a premise that quietly stopped holding
while the formula carried on. **Before reusing a formula, name the case it was
derived from and check that case still obtains.**

**A9's third axis: claims whose scope is fixed by an ambiguous word.** Four
instances now — S15's "cross-architecture" (cross-OS read as cross-ISA), S35's
"31.6×" (two differently-bracketed timers), S45's 5.66 ms comparand (from a
disqualified instrument), and S32a's digest column read as corroborating S51
(independent copies read as thread decomposition). In every case the conflation
survived review because nobody asked what the noun meant. **Before citing a
claim, state the property in a sentence that does not reuse its label.**

Guardrails are the highest-leverage place for staleness precisely because their
function is to stop people re-checking. This is A7 applied one level up: **A7 says a
caveat you did not run is not a caveat; A9 says a citation you did not re-check is
not a citation.** Every citation here now carries grade and date, and a retracted
or rewritten source invalidates the guardrail until re-derived.

---

### A10. A benchmark harness records machine state and REFUSES to run when the machine is not quiet.

A5 says *abort if the environment is not controlled*. That was a habit, and the
habit failed three times — S9, S18, and S62/S63, whose own commit message records
*"I contended with my own adversarial agent on the same device."*

The structural gap: spikes declared contention using `uptime`, **and `uptime` does
not show containers.** A machine can read loadavg 1.2 with eleven services
resident holding memory and cache. Checked while writing this rule: loadavg 3.94,
**11 containers up** from an unrelated project, and `rustc` at 100% — during the
window in which S62 and S63 were measured and committed.

`spikes/quiet.sh` implements it. It refuses if loadavg > ncores/4, **or any
container is up**, or a compiler is in the top 3 by CPU, and `--json` emits the
capture (loadavg, container names, top-3 processes, thermal state) so the refusal
criteria stay auditable after the fact. `QUIET_ALLOW_CONTAINERS=1` overrides and
is recorded in the output.

**Not "declare contention" — refuse.** Every spike that produces a timing number
calls it first and embeds the `--json` capture in its results.

**`--device` mode, added 2026-08-17 after finding the hole.** The gate checked
only the host, so **every device measurement in this workspace ran ungated** —
S34, S50–S54, S57, S62, S63, including the ones written *after* A10. `sh
spikes/quiet.sh --device` refuses on device loadavg > cores/4, thermal > 45 °C,
**or the phone not charging** (S6's deployable configuration is charge-time; a
discharging phone is the wrong configuration, not merely a noisy one).

Checked on introduction: device loadavg **9.26 on 8 cores** and `AC powered:
false`. Every device number taken today was taken under that.

**Scope, added after S65:** A10 gates **timing**. Counts, digests and
determinism comparisons do not move with load, and a spike measuring only those
may proceed on a busy machine — provided it says so and still records the
capture. A rule that blocks valid work gets routed around; one that names its
own scope gets obeyed.

---

### A11. Accumulate wide, round canonically, update synchronously.

The determinism law, stated once, covering every rung.

Integer *addition* is associative, so thread order is harmless — **but additions
were never the danger.** The neural rung taught it first: integer matmul is fine,
**requantization rounding** is where implementations diverge. The same law
governs the attention broker: decay, rent and spreading are multiplications by
rates in [0,1], and fixed-point multiply rounds, so `(a·r) + (b·r) ≠ (a+b)·r`.

So "use fixed point" is never the whole fix. The fix is:
**accumulate wide** (int64/128 intermediates), **round only at canonical points**
(one rounding site, one pinned mode), and **update synchronously** (BSP
double-buffered epochs; read state *t*, write *t+1*), with fold order keyed by
content hash and never by pointer.

**Acceptance oracle, for any parallel component: N threads and 1 thread must
produce an identical state hash.** If that test does not exist, the component is
not known to be deterministic — it is merely untested.

---

### A12. When a design depends on something unmeasurable, price *removing the dependency* before pricing the measurement.

Three descopes in a row, all the same move, and each time the replacement was
already measured or free:

| dependency | unmeasurable part | retired by |
|---|---|---|
| phone NPU | cross-vendor requantisation bit-exactness (grade E, never run) | **removal** — the CPU has `asimddp`+`i8mm` and does the kernel bit-exactly |
| zkVM dispute path | a reproducible interpreter-state commitment (S68, RED, one contaminant still unidentified) | **quorum** — majority-of-3 needs only S57, which exists |
| static ban list | decidability under `py-atom`'s runtime string resolution | **build** — unregistered ops are unreachable by any path |

Each carried a component whose cost was unknown and whose necessity was assumed.
In all three the honest answer to *"what would it cost to measure this?"* was
larger than the answer to *"what would it cost to not need it?"*

**The asymmetry, conceded (C5):** A12 compares a *measured* removal cost against
an *unmeasured* measurement cost, which biases it toward deletion. It is safe
only when the **replacement is already measured** — as it was in all three cases
above (`asimddp`+`i8mm`, S57's byte-identical results, unregistered-means-
unreachable). When the replacement is itself assumed, A12 is a licence to delete
whatever is inconvenient. State the replacement's grade when invoking it.

**Ask the second question first.** The ladder's first rung — *does this need to
exist at all?* — applies to architecture, not only to code, and it has now paid
three times running. The tell is a grade-D or grade-E claim sitting on the
critical path: that is a design smell before it is an evidence problem.

---

### A14. A spin barrier must escalate, and the rule needs to be code, not prose.

`LEDGER` has carried *"4 background cores − 1 coordinator = 3 workers, **or the
barrier must block**"* through three occurrences of the same collapse — S51 at
T=8, S53 at T=1, N1 at T=4 (**337× slower**). The prose was correct every time
and prevented nothing.

The production form is `crossbeam-utils/src/backoff.rs` (Apache-2.0):
`SPIN_LIMIT = 6`, `YIELD_LIMIT = 10`, `spin()` → `snooze()` → park, with
`is_completed()` reporting when spinning has stopped paying. That is the
escalation our sentence describes.

Until a harness adopts it, the minimum is a **construction-time refusal** —
`if (T >= ncpus_in_cpuset) refuse;` — which `N1/pf.c` now does. Same move as
A10: refuse rather than remind.

### A15. Include a configuration the treatment cannot affect. Its spread is your noise floor.

N1c padded barrier atomics to 128 bytes and measured no effect. The claim
"no effect" is only as good as the resolution, and the resolution came free:
**padding cannot change single-threaded performance**, so the T=1 delta between
the two builds — 15.56 vs 16.48 cycles/bundle, **5.9%** — is pure noise.

The honest claim is therefore *no false-sharing effect larger than ~6%*, not
*no effect*. A control the treatment cannot reach costs one extra row and turns
a null result into a bounded one.

**Corrected by N1d: a negative control bounds resolution; only a POSITIVE
control shows the instrument can see the effect at all. Both are required.**
N1c shipped the negative one and read its null as evidence. The positive control
— atomics forced onto one line — then failed to fire at every granularity down
to 5 cycles per crossing, because the forced build creates **true** sharing
(barrier state every core must observe), not false sharing. Padding separates
*unrelated* data; there was nothing unrelated to separate. The null was
unfalsifiable as constructed, and one control could not reveal that.
### A16. Arms must share the nuisance state, not merely be measured against it.

N1e A/B-tested two builds of `S51/mcx.c` — barrier atomics padded vs sharing a
line with the work-stealing cursor — and included a within-run control
(static mode never touches the cursor). That control normalises DVFS *inside*
a run. It says nothing about **which arm ran while the device was hot**.

The device dropped into the low DVFS state between two arms and stayed there
(T=1: 572 -> 940 us). The fast regime ended up holding **three control arms and
one treatment arm**. The apparent 20 pp effect came from that imbalance; the
balanced regime gives 4.4 pp.

**A control that normalises a nuisance variable within an arm does not
randomise or pair that variable across arms.** Those are different jobs. When
between-run drift can exceed the effect — thermal, DVFS, cache warmth, page
placement, allocator state — the arms must be interleaved at the finest
granularity the harness allows, ideally inside one process so the nuisance
state is shared by construction, and paired differences used as the estimator.

Separate binaries are the failure mode: two builds are two runs, and two runs
are two thermal histories. Compile both layouts into one binary and switch per
iteration.

Corollary: log a per-arm nuisance readout (here, T=1 wall time) and check arm
balance across its range *before* computing any effect. N1e's imbalance was
visible in the raw table and was not looked for.

### A17. A claim decays when it is retold. Cite the ledger row, not the sentence.

`LICENSE_LEDGER:34` recorded a narrow, verified, checkable fact:
*"golemfactory/yagna — repository removed from GitHub (404)."* True today.

`THE_BRAIN.md` retold it as **"Golem built one and deleted the repository"**,
which then did rhetorical work in a CEO report as evidence that *demand does not
scale into existence*. The `golemfactory` org has 100 repos and pushed code two
days before that report was written. The network is alive; only the monorepo is
gone from public view.

**No measurement failed here.** The ledger was right. The error entered when a
scoped observation was restated one document downstream as an unscoped
conclusion, and then a third document treated the conclusion as evidence.

Rules:
1. When a document repeats a finding from another, it **quotes the ledger row
   and its scope**, or it links to it. It does not paraphrase into a stronger
   verb. "404s" is not "deleted"; "deleted a repo" is not "the project failed".
2. A fact that is load-bearing in an argument gets **re-verified at the time the
   argument is made**, not inherited. Repository state, licences, upstream
   activity and prices all drift; a 404 is a snapshot.
3. Absence of a public artifact is evidence about the artifact, never about the
   organisation. Check the org, not the URL.
4. **An unpopulated value is not a measurement.** `stats.golem.network` renders
   "0 providers computing" before its JS runs, and `api.stats.golem.network`
   does not resolve. Neither is a utilisation figure. Same shape as the
   `da39a3ee` empty-string hash that faked agreement in S57/S58/S60/S62/S63 —
   the fifth and sixth appearances of "nothing there" read as "zero".

Corollary, and the reason this rule is worth its length: the corrected fact was
**more** interesting than the false one. A marketplace still running while
visibly reweighting toward a database product is a live competitor and a real
signal about compute demand. Inflating it into a corpse destroyed information.

**A17 corollary — `pushed_at` is not "last commit".** The GitHub REST field
`pushed_at` advances on any ref update (branch deletes, tags, bot activity), so
it overstates liveness. `golemfactory/ya-runtime-wasi`: `pushed_at` 2026-08-15,
last commit **2023-09-13** — a three-year gap. Use
`/repos/{o}/{r}/commits?per_page=1` for activity, and check it per repo rather
than sorting an org listing.

This bit twice in one hour: a false claim ("Golem deleted the repo") was replaced
by a claim resting on a misread field, and only a reader pointing at one specific
repository exposed it. **A correction is a new claim and inherits no credibility
from the error it replaces.** Verify it to the same standard, including the
metadata field you are reading.

### A18. One point is not a rate. Fit the intercept before you extrapolate.

M1.5 measured 173 KiB crossing to a device in ~40 ms. Dividing gives 4.21 MB/s,
and that rate priced B1's deployable shards at **22–120x** the compute they feed.

Sweeping the same code path from 64 KiB to 32 MiB shows the apparent rate rising
**monotonically by 32x** — 1.1 to 35.2 MB/s. A bandwidth cannot depend on
transfer size, so the single-point model was refuted by its own units. The real
shape is `63.2 ms fixed + 37.9 MB/s marginal`, and the extrapolation was
6.5–8.4x too high because the measured point sat in the fixed-cost regime.

**Before dividing a cost by a size, check which regime the measurement is in.**
Any quantity with a per-call setup — network transfers, syscalls, process spawn,
kernel launches, DB round trips — needs at least two points spanning an order of
magnitude, and the reported result is the pair `(intercept, slope)`, never the
quotient.

Then attribute the intercept. Here ~47 of 63.2 ms was **three separate `adb`
invocations in the harness**, not a property of the system — so publishing 63 ms
as a system constant would have seeded exactly the kind of inherited figure N1
had to retract.

Note what the error did *not* do: the reviewer's qualitative conclusion (transfer
dominates compute; pre-stage rather than fetch during a job) held at 3.4–14x just
as it did at 22–120x. **A wrong magnitude does not imply a wrong direction** —
correct the number without discarding the finding.

**A18, second instance — it caught its author one spike later.** M1.5b
established that ~47 of a 63.2 ms transfer intercept was three `adb`
invocations in the rig, and A18 was written to say: *attribute the intercept
before publishing it.* M1.3 then measured preflight at 35.1 ms over
`adb`+`dumpsys`, and published *"per-job preflight is not viable"* — the
harness cost, read as the system's, exactly as prohibited. Its own
decomposition already showed the whole 35.1 ms was 16.2 adb + 18.9 dumpsys.
The native floor is **8.4 µs**, 4,180x cheaper.

Two tells were available before any new measurement, and both were ignored:

1. **The decomposition already attributed itself.** When every term of a cost
   names a component of the rig, the total is the rig.
2. **The conclusion contradicted the specification being implemented.**
   `SCHEDULER_SPEC` marks the per-job checks *Residue: yes* — required. A
   measurement that says a spec is impossible is far more likely to be
   measuring the wrong thing than to have found a broken spec. **Treat
   contradiction-with-spec as an instrument alarm, not a finding.**

### A19. Record the state a third party could re-derive, before the run — not the state you assume.

Five failures in the M1 series were all pre-run state, invisible to any
write-up audit:

| what happened | what would have caught it |
|---|---|
| built and shipped a **patched** `elders/hyperon-experimental` while the result claimed `3f76dc4` | `git status --porcelain` recorded next to HEAD |
| positive control read STABLE because **our own patch had silenced it** | control declared up front and required to fire |
| three probes returned empty / unevaluated, all reading STABLE | one sample output logged per probe |
| harness cost published as system cost, twice (A18) | component attribution recorded with the number |
| a rate extrapolated from one point in the fixed-cost regime | two points spanning an order of magnitude |

**`HEAD` is not provenance.** A dirty tree at `HEAD=X` is not X. Record the
commit, the porcelain status, and a hash of `git diff HEAD` — together those let
anyone reconstruct the exact tree. Record the **sha256 of the artifact actually
executed**, not the source it was supposed to come from; the `.so` in the APK is
the ground truth, the build command is a claim about it.

Prefer facts an outsider can check over facts only our data supports: commit
hashes, binary digests, `ro.build.fingerprint`, toolchain version strings. A
number defended only by our own notes is not verifiable, it is asserted.

**A positive control that does not fire voids the run — it does not produce a
negative.** Declare it before the run with the reason it must fire, and treat
"did not fire" as an instrument fault. Three dead controls in one session all
read as clean nulls: `(flip)` was a Python-ext atom absent from the Rust stdlib,
`(random-int &rng ...)` had an unbound generator, and a probe matched an atom
never added to the space. Each echoed or returned empty, which hashes stably.

Implemented in `spikes/harness/provenance.py`; it refuses to certify a run with
an unacknowledged dirty dependency or a control that did not fire.
`allow_dirty=True` exists so a deliberate patched build is *recorded*, never
silent.

### A20. A control lives in the artefact, or it does not exist. And a null must be able to contain the thing you claim to detect.

Reported from the G-series after an adversary destroyed G15, and it applies here
unchanged.

**Pre-registering a hypothesis is not enough if the control is pre-registered in
prose.** G15 named its null in advance, computed it inline, reported
"real 0.394 vs null 0.055–0.104" — and never saved it. Nobody can recheck a
number that exists only in a sentence. Every input present in the artefact, or
the result is unfalsifiable.

`spikes/harness/provenance.py` now enforces it: `Control.observe()` **requires
the observations**, not a verdict, and refuses a bare boolean at the point of
call. A control with no persisted data blocks certification exactly as a control
that failed to fire does.

**Second, and less obvious: check that the null CAN produce the structure.**
G15's degree-preserving shuffle destroys cliques and near-inverse pairs — which
were precisely the structures generating the signal. A null that cannot contain
the effect will always be beaten, and "beats null" then reduces to "the real
graph has cliques and the shuffle does not." The control was not merely absent,
it was **incapable**, which is A15's failure one level up: not a control that
cannot fail, but a *baseline* that cannot succeed.
`Control(null_must_contain=...)` exists to make that explicit in the record.

**Third — the number can be right while the UNIT is wrong.** G15's `ho_n`
counted 2-hop *paths* and the confidence was asserted about *pairs*: one pair
contributed 245 of 489 denominator entries and all 245 hits, so a coin flip
became 0.501 by path weighting. Every figure reproduced exactly; the
denominator was measuring something else. Same family as A18 (a cost divided by
a size that was in the wrong regime) and as N1's normalised numerator over an
unnormalised denominator — **third occurrence, so state the unit of the
denominator next to the ratio, always.**

### A21. Check the test can express your verdict before you run it.

A permutation test with `n` draws reports `p = (k+1)/(n+1)`, so the smallest p
it can ever produce is `1/(n+1)`:

```
n=10  ->  min p = 0.0909   alpha=0.05 UNREACHABLE, whatever the data
n=19  ->  min p = 0.0500   reachable
n=99  ->  min p = 0.0100
```

G17 observed 0 of 10 null draws at or beyond the real value — a 12.2 sd effect —
and computed p = 0.091. Reporting that as "not significant" would have been
exactly as wrong as reporting it as significant: **the test could not have
produced the verdict before it ran.**

This is the third form of the same defect, and the family is now worth naming:

| | the instrument cannot |
|---|---|
| A15 | ...fire when the effect IS present (positive control) |
| A20 | ...contain the effect in the baseline (null incapable) |
| **A21** | ...express the verdict at any data (test underpowered by construction) |

In each case a null result is uninformative rather than negative, and in each
case that is decidable **before** the run from the design alone.

`spikes/harness/power.py` implements it: `check()` returns `UNDERPOWERED` rather
than `NOT_SIGNIFICANT` when `1/(n+1) > alpha`, and `draws_needed(alpha)` gives
the minimum. Note also the add-one in `(k+1)/(n+1)`: without it a finite sample
can report p exactly 0, which is never true.

### A22. A party must not supply the input to a check applied to itself.

Not a credibility rule — a **conflict-of-interest** rule. None of the three
instances below is a trust claim as such; each is an input to a gate applied to
the party that wrote it.

| field | gated decision | supplied by |
|---|---|---|
| S62 `backend_class` | which results are compared | the worker **INVALID** |
| M1.5 binary hash | admission | the worker |
| M1.8d domain key | quorum independence | the worker |

**The test, applied per field:** *who benefits if this value is wrong, and did
they write it?* Same party -> the value must be **attested or observed**, never
declared.

Two properties make this stronger than "distrust the worker":

1. **Cross-checking covers only fields where lying causes DISAGREEMENT.** In our
   pipeline `status`, `fuel_used` and the result hash are in the quorum
   agreement key, so a lone liar is caught by construction. Everything outside
   the key is unchecked: `n_results`, `wall_ms`, `arch`, `os`, `bytes_pushed`.
   Being worker-supplied is only a defect for fields nothing compares.
2. **The absence of a field is not safety.** `hyperjob_v0` has no field for a
   device's cache contents, yet `prefer_cached_cids` (`:114`) makes locality
   matching depend on knowing it. When someone implements that, the natural
   shape is the device declaring what it holds — *a worker telling the matcher
   which jobs it should win*. The rule has to be applied at design time, or it
   arrives as a default.

Full field audit in `spikes/M1_8_quorum3/COI_AUDIT.md`.

**Note the mismatch detector fired benignly on its first run** — honest workers
declare `operator:self`, the coordinator credits `UNATTESTED`, and the
difference is reported. A control that fires on honest input has proved it is
live *before* anything depended on it. This workspace has found four dead
controls; a control demonstrated live at introduction is the rarer event and
worth preserving as the pattern.

### A23. The instrument changes what it looks at. Pair the arms or say so.

Distinct from A15/A20/A21, which are about an instrument that **cannot see** the
effect. This is an instrument that **perturbs** it.

Four instances, all this session:

- **M1.1c is a literal observer effect.** "Does job N differ from job 1?" was
  measured by running the program 40 times in one process — and *running it* is
  what advances `NEXT_VARIABLE_ID`. The measurement produced the divergence it
  detected.
- **N1e was ruined by one.** Arm A heated the device into a different DVFS band,
  so arm B ran under conditions arm A created. That is the whole reason it is
  UNRESOLVED.
- **Preflight sits inside its own measurement** — reading device state costs
  device state (98.5 us against a 68.8 ms job).
- **The inverse**: a backgrounded run redirected without `python -u`, so the
  progress it needed to observe was buffered away. The thing worth observing was
  the thing the setup did not record.

Unlike quantum measurement this is **classical and fixable**: the state has a
definite value and observation from outside, or in a fresh process, does not
disturb it. So:

1. Make observation cheap and idempotent where you can.
2. Where you cannot, **pair the arms** so both share the perturbation (A16).
3. Where the observation *is* the treatment — you cannot measure whether a
   reused process drifts without reusing the process — say so. The answer there
   is not a better instrument; it is stating that measurement and mechanism are
   the same act.

### A24. A digest pins WHICH artifact. Only a build from a recorded tree pins WHAT IS IN IT.

Both agents on this project hit this independently, within hours, from opposite
directions:

- **G18** measured a `fuelrun` built the previous afternoon against a tree that
  had since been patched, and produced a real symptom with a wrong attribution —
  a "1022 match ceiling" and a head-plus-wrapper explanation invented to fit a
  number the stale binary produced.
- **M1** ran its entire chain on the same two stale binaries. Its provenance file
  recorded **the correct sha256 of the wrong binary**, which is the failure in
  one line: an accurate hash of a stale artifact is indistinguishable from an
  accurate hash of a fresh one.

Disclosing it ("prebuilt from an unconfirmed commit") is better than hiding it
and is **not** the same as closing it.

Rules:
1. Build the artifact from the tree you are recording, in the run you are
   recording, or state plainly that the measurement is about a different tree.
2. Record the artifact's **mtime** next to its digest. `provenance.py` now
   compares it against the newest source mtime in each declared dependency and
   refuses to certify when an artifact **predates the source it claims to come
   from** — it cannot have been built from it.
3. Prebuilt binaries kept for convenience are a standing hazard: `S30/bin/`
   held `fuelrun.v2.*` for months and every spike that used them inherited an
   unrecorded commit. Known-provenance builds now live in `S30/bin/known/`.

The check is cheap and mechanical, which is the point — this class of error
survives careful reading indefinitely and dies instantly to a timestamp
comparison.

**A18, third instance — a RATIO also has an operating point.** The rule was
written about a cost divided by a size. It applies just as directly to a
speedup: *"7.07 ms spawned vs 0.247 ms resident = ~29×"* is not a property of
process spawning, it is `1 + spawn/work` evaluated at one workload. Spawn
overhead is a fixed ~6.82 ms, so the same comparison gives **1.09× at 59 ms of
work and 1.00× at 5,004 ms** — measured, not argued.

The claim was correct and was stated without its operating point, which is how a
true measurement becomes a false rule. **Any ratio between a fixed cost and a
variable one carries the variable's value in it; state that value beside the
ratio, always.**

Audit note: the same sweep produced one anomalous row (a 0.11× "in-process is
slower") which is an artifact of the in-process harness doing extra work per
program, not a real inversion. Recorded rather than dropped — a sweep that
produces one implausible point has not been understood, and the honest response
is to exclude it explicitly and say why.

**A18, fourth instance — and the opposite error.** Having over-extrapolated a
rate, I then over-retracted one. `units.affine_range` settles both by reporting
the largest subrange where the slope is stable rather than a binary verdict:

```
USB   affine 173 KiB - 32 MiB   57.3 ms + 37.5 MB/s
WiFi  affine  16 KiB -  1 MiB   25.1 ms +  9.4 MB/s
```

The USB fit was valid over 2.3 decades and I called it void; the WiFi regime
ends an order of magnitude below the shard sizes that matter.

**A rate is only a rate inside the range where the slope is stable, and the
range travels with the number.** Reporting a rate without its range and
withdrawing a rate that was valid within one are the same defect — the range was
never stated, so there was nothing to check it against.

Corollary for the tool: a checker that returns only pass/fail teaches you to
discard data. `check_affine` said "not affine" for a curve with a wide stable
regime; `affine_range` says where it holds. Prefer a checker that localises the
failure to one that only announces it.

---

*A25–A30 were declared in `HANDOFF.md` as they were earned on 2026-08-17 and
never landed here, so every citation to them across the harness resolved to
nothing while reading as satisfied — exactly the H4/§12.4 defect. Found
mechanically by `spikes/harness/refcheck.py` on its first live run, not by eye.
The text below is EXTRACTED from the HANDOFF entries that earned them, not
rewritten: retyping a guardrail into a new form is how a claim decays across
documents.*

### A25. An ablation that removes more than it names cannot measure the named part.

G24's `no_death` arm also removed uniform-parent-choice, `MAX_POP`, and every use
of the importance balance, so "carrying capacity is what makes fitness
differential" was measured against a baseline **with no fitness at all**. Check
what an `if flag:` guard actually gates before naming the arm after one of them.

### A26. A knob is not a mechanism.

A difference between arms is only about the mechanism if the constants around it
were **measured, not chosen**. G25's coverage gap was 51–85% `WAGE_POOL`, a
number picked by hand.

### A27. A hold-out drawn from one end of the key order is not a sample of the key space.

Shuffle before splitting. S73's scaling arm took the lexicographic tail as probes
and the lexicographic prefix as base, so **every probe diverged at the root** and
single-insert cost read **293 B flat across a 10× space range**. The flatness
looked structural; it was the cost of inserting *outside* the occupied range, and
the real figure is 6× larger.

### A28. An enforcement field that is recorded but never read is documentation.

`provenance.py` stored `null_must_contain` for the whole project without ever
checking it, and `deps=()` silently disabled the entire staleness path. Same class
as A26's hand-picked constant: **it looks like a mechanism from the outside.**

### A29. A probe that cannot show it reached its target has produced no evidence.

ATTACK cycle 4's A4 probe aimed at two unreachable branches, was blocked from
reaching them *by the very bug it was hunting*, and reported SURVIVES on a clean
null. "No FATAL" from a probe that missed is not a pass. **Reaching the target is
a precondition of the verdict, not a detail of it.**

### A30. A name grep cannot tell a word from a concept.

S75's control searched `fn (prove|verify|proof|witness)` in `pathmap`, matched 14
Rust **borrow** witnesses (`-> Self::WitnessT`, several `-> ()`), and therefore
did not fire. **Test the property, not the vocabulary**: "depends on no
cryptographic hash" cannot collide on a name, and it settled the same question in
one line.
