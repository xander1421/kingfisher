# RETRACTIONS — three adversarial subagents, 2026-08-17

The operator moved adversarial review from a shared log to spawned subagents. First application, three attackers on my last five spikes. **They killed more of my work in twenty minutes than four agents did all day.** Every finding below was verified independently before acceptance; where I could not reproduce a claim I say so.

Read this before `DEVICE_ADDENDUM.md`, `S45`, `S46`, `S47`, `S48` or `S49` — where they disagree, this file is later.

---

## Dead

| claim | spike | why |
|---|---|---|
| "the seal defeats the echo attack, 13/13" | S49 | seal bound `result_hash`, verdict computed from `payload`, nothing tied them; no commit-before-reveal ordering; unprefixed preimage collides. Retracted in `S49_schema_v1/RESULT.md` §S49b, fixed in `verifier2.py`. |
| **"bad shaping == no shaping; bounded downside"** | S48 | **falsified, and my own published matrix already contained the counterexample.** |
| **"the driver is prefix coverage"** | S48 | the single 0.6 µs comparison it rests on reverses at B=4, B=16 and at two of five reseeds. A layout-only property cannot depend on B. |
| "bundling 54×, clustering 12.8× of that" | S47 | direction survives; both numbers are functions of a `per_check` constant that varies 2× run-to-run and was measured on the most favourable access pattern. Correcting it moves the two figures in **opposite** directions. |
| "clustered bundling does not collapse on mismatch" | S47 | true only for mismatches preserving the bucket-constant slot. S48's own `(subj,obj)`/`(p ?s o)` cell collapses to ~1×. |
| "prefilter at 86% of the roof; ≤16% left on the CPU" | S45 | the attacker got **2.2×** more out of my own kernel by moving the barrier and pinning threads — without touching one instruction in `run_chunk`. |
| "59% of the T=8 query was `pthread_create`" | S45b | my own two tables say **41%** (483→287 µs). Subtracting a separate `threadcost` measurement is invalid because spawn overlaps with work. And the pool did **not** fix the reversal: pooled T=8 (287) is still worse than pooled T=4 (252). |
| **"stage 2 is 13 ms of `exec()`"** | S45 | it is **5.66 ms**, and it is not `exec()`. |
| "the read roof peaks at 4 threads and declines at 8 — a property of the memory system" | S45b | **my own harness error.** `streamroof.c:20-24` puts `pthread_create` *inside* the timed region — the exact mistake I diagnose two sections earlier and then never applied to the instrument I used as ground truth. With spawn moved out: 65.7 → **69.1** GB/s from 4 to 8 threads. No decline. |
| "22.6 GB/s/core, compute-bound at ~2 IPC" | S46 | a DVFS artefact of an unpinned short-lived process. Same binary pinned to cpu7: **39.3–43.6 GB/s**. My IPC derivation was fitted to the artefact — measured on cpu7 it is 3.3 IPC, not 2. |
| "flat within 1.8%" | S46 | below the instrument's resolution. The arch timer granularity is **52.08 ns**; the smallest point (1.1 µs) is 21 ticks = ±4.8% quantisation, and best-of-14 systematically selects the favourable rounding at the small end. |

## Survives

- **S34's bit-exactness.** Three kernels, two machines, one digest. `kernels.c` is the one device file with **zero** unsequenced warnings, so the UB below does not touch it. This is the load-bearing determinism claim and it is intact.
- **S15/S16 cross-architecture determinism.** Untouched by all three reviews.
- **S46's conclusion**, on better evidence than mine: the attacker extended the sweep to **750 MB — 60× past my largest point, a 30,000× range** — and it stays flat within 10%. A variant with one extra op per 16 B halves throughput at every size. So the kernel is issue-bound per core and residency buys ~10%, not 0%. Right answer, wrong number, wrong reasoning.
- **S45's architectural requirement, directionally.** Stage 2 is still ~96% of the query; the ratio is **9×, not 16×**; subprocess throughput is **169 q/s, not 73**. "Stage 2 must run in-process" stands. *"13 ms of `exec()`"* must be struck.
- **S48 claim C's mechanical half.** The attacker instrumented the sweep exit: `recall = 1.000` and converged at **every** cell of both spikes. My tables were not lying about recall.

---

## The four findings that hurt most

### 1. My own matrix contradicted my own headline, on the same page
S48 finding 1: *"a shard shaped for the wrong queries is no worse than a shard nobody shaped"*, evidenced by one pair, 127.8 vs 127.4.
S48 finding 3, twelve lines later: *"random (4.2 µs) beats two of the three shaped layouts"* — 10.5 and 22.3.

**Finding 3 falsifies finding 1 and I wrote them next to each other.**

Challenged on asserting this off one reseed — correctly, since single draws are the error being retracted — I instrumented the sweep and ran five seeds. The `(?p s o)` column, total µs with `[truth, shortlist, exit cutoff]`:

| seed | (pred,subj) | (pred,obj) | **RANDOM** |
|---|---|---|---|
| 0xC0FFEE | 10.5 `[t=1, sl=80]` | 22.2 `[sl=223]` | **4.2** `[sl=3]` |
| 1 | 59.0 `[sl=713, cut=−6]` | 58.9 `[sl=711]` | **25.5** `[sl=280]` |
| 2 | 118.7 `[sl=1481, cut=−60]` | 118.7 `[sl=1481]` | **7.3** `[sl=40]` |
| 3 | 17.1 `[sl=158]` | 7.7 `[sl=43]` | **4.7** `[sl=6]` |
| 5 | 135.9 `[sl=1277, cut=−58]` | 133.4 `[sl=1253]` | **20.2** `[sl=134]` |

**Random wins in five of five, by 1.6× to 16×.** Not a fluke draw — and the mechanism is now visible in the instrumentation:

`truth = 1` in every seed, because `(?p s o)` binds subj+obj over 1000×1000. It is a find-the-single-row query. Cluster by `(pred,subj)` and that row sits in a bucket with 63 rows **sharing its pred and subj**; the majority-bundle is dominated by their coherent shared signal, which drowns the target's obj contribution. The cutoff descends to −58 and shortlists 1,481 of 1,563 buckets — **95% of the store**. In a random bucket the 63 neighbours are unrelated, cancel, and the target survives.

So clustering does not merely fail to help off-key queries: **homogeneous buckets actively bury outliers, and incoherent buckets do not.** That is a mechanism, and it kills "bad shaping == no shaping" properly rather than on the single 127.8/127.4 coincidence — which was two cells saturated against the `checked ≤ NROWS` clamp at `decay.c:158`.

It also exposes what the oracle sweep concealed: at `cut = −58`, "recall 1.0" is a 95% scan. That is not a prefilter, and reporting it as a 127.8 µs query was only possible because the cutoff was fitted to the answer.

### 2. The cutoff was chosen by an oracle reading the ground truth
`decay.c:146` computes `truth` from the answers; `:156` breaks when `found >= truth`. **Every cost I reported is the cost of a query whose answer was already known.** A deployed prefilter has one fixed cutoff and cannot do this. The excluded sweep is ~18 ms to produce a "127.8 µs" query. I also called it the "loosest" cutoff giving recall 1.0 — it is the **tightest** on an 8-wide grid.

This is what actually kills S47's economic claim. *"Recall is recoverable on any layout; what layout buys is the price of recovering it"* — recovery requires the answer, so the price is not one a deployed system pays.

### 3. My stage-2 control measured a crash
`mork run` **aborts** without `LD_PRELOAD=libnotag.so` — the pointer-tagging bug I found and fixed in S16 — and ~12 ms of my 12.84 ms "empty program" control was Android's debuggerd tombstone path. I had the fix in the same directory and did not apply it to the control. With it:

```
tiny 5.6 KB C binary        5.25 ms
mork run empty.mm2          5.43 ms
mork run shortlist.mm2      5.66 ms   ← the whole of stage 2
```

Generic Android process creation is 5.25 ms of that; **everything MORK does is ~0.4 ms.** And my `date +%s%N` bracket is itself two process spawns — the harness doing nothing costs 6.0–6.9 ms against a 13.3 ms result. By **my own rule** (`S46/RESULT.md:63`), that measurement is disqualified.

### 4. Undefined behaviour in two of my device programs
`#define NEXT() (s ^= s<<13, s ^= s>>17, s ^= s<<5, s)` used **twice in one expression**: `((uint64_t)NEXT()<<32)|NEXT()`. Unsequenced modification of `s`. Clang warns; I never read the warning.

```
kernels.c   (S34)  0 warnings   ← the bit-exactness result is safe
prefilter.c (S45)  6 warnings
residency.c (S46)  3 warnings
bundle.c/decay.c/qsweep.c  0
```

S45's cross-silicon digest `2e2ac64c1d9cff91` matched because two different compilers happened to order the UB identically. The *agreement* between machines is still real evidence — had the inputs differed the digests would have differed — but the experiment is not reproducible by construction, and I claimed it was ("seeded so the host reproduces them exactly").

Also: `residency.c:126` divides by `g_threads` on the documented `g_threads == 0` inline path (UB, silently 0 on aarch64), and `residency.c:151` hashes 780 bytes while labelling it `digest(scores, 100k rows)` — so **no large-store run in S46 has any correctness check at all.**

---

## What I am changing in how I work

1. **Read the compiler warnings.** Six warnings sat in a file whose headline claim was bit-exactness.
2. **Never subtract a separately-measured overhead.** Measure with and without, and take the difference of the *controlled* pair — my 59% became 41% precisely because subtraction ignores overlap.
3. **Pin the core and check DVFS** before any single-threaded per-core claim.
4. **Report the null.** I wrote that rule in S46 and then failed to apply it to S45's stage-2 control and to S46's own inline path.
5. **A cutoff, threshold or parameter fitted to the ground truth must be labelled as an oracle** and its cost reported.
6. **One draw is not a measurement.** The RANDOM baseline swings 79→127 µs on a reshuffle; I reported it as a constant.

Three of these — 2, 4, 6 — are the same error the workspace has now hit **seven times**: a per-query or per-run cost masquerading as a property of the hardware or the algorithm.

---

## Addendum — S50 replaces the numbers, and adds one nobody had

`spikes/S50_harness/` — a harness that enforces every control the three attacks showed missing, built with `-Werror`. Re-measured, pinned and amortised:

| | cpu0 (performance, 2.9 GHz) | cpu7 (prime, 3.28 GHz) |
|---|---|---|
| prefilter, 24 KB → 102 MB | 21.7 → 22.1 GB/s | 50.2 → 49.8 GB/s |
| MAD | 0.0–2.2% | 0.1–0.2% |

1. **The residency conclusion is now properly established**: flat across **4,300×** of store size on both core types at **MAD ≤0.2%**. S46's "1.8%" was below its instrument's resolution; the true figure is ≤0.5%. Right answer, worthless evidence, now fixed.
2. **Core placement is worth 2.26×** — 22.1 vs 49.8 GB/s, same binary, same instant, only affinity differs. S46's "22.6 GB/s/core" was cpu0 unpinned, reported as a property of the kernel.
3. **"≤16% left on the CPU" dies a second way**: *one prime core alone (49.8) nearly equals S45b's entire four-thread figure (50.8)*. Four threads on performance cores barely beat one prime core. The headroom is scheduling, not instructions. cpu7 also never boosted past 3,283 of 4,474 MHz, so even 49.8 is not the ceiling.
4. Digests identical across core types, with the UB removed — reproducible by construction rather than by two compilers agreeing.

**And a new gap:** `bench.h` pins one core by design, so there is now **no defensible multi-threaded throughput number in this workspace.** S32's 5.87× scaling and every fleet projection built on it (the 28,700 jobs/s model) are unsupported until a correct multi-core harness — spin barrier, per-core affinity — exists.

---

## Addendum 2 — S51 closes the multi-thread gap, and finds a cliff

`spikes/S51_multicore/` — spin barrier, one thread pinned per core, amortised, barrier null measured, digest at every thread count.

| T | GB/s (static) | scaling | barrier null |
|---|---|---|---|
| 4 | 73.1 | 3.97× | 0.2 µs |
| **7** | **115.8** | **6.30×** | 0.9 µs |
| 8 | **1.3** | **0.07×** | **10,850 µs** |

1. **The real figure is 115.8 GB/s, not 50.8** — 2.28× S45b, and 1.97× the "roof" S45b measured itself against. Independent confirmation of the attacker's 2.2×, by a different route. Per-device query throughput goes **3,968 → ~9,050 q/s**.
2. **Eight cores is 89× worse than seven.** With a spin barrier and a worker on every core, no core is left for the coordinator. The barrier null alone (10.8 ms) exceeds the entire T=7 query. **Never size the pool to `nproc`** — which is exactly what S32 and S45b both did. It also re-explains S45b's T=8 reversal: not memory contention, the onset of coordinator starvation, softened because a condvar sleeps where a spin barrier does not.
3. **The barrier is now ≤1% of the measurement** at every usable T, against ~40 µs (16% at T=4) for the condvar.
4. Digest identical at every T and under both split strategies. Determinism now holds across architectures, engines, build profiles, core types, thread counts and scheduling strategies.

**Caveat:** clocks ended at 1,996/1,958 MHz against 3,532/4,474 maxima — the part was throttled, so 115.8 GB/s is a floor. A sustained-vs-burst arm is still missing.

---

## Addendum 3 — S52: real data, and a partial un-retraction

FB15k-237, 272,115 real Freebase triples, 237 predicates, 14,505 entities. 120 sampled queries per cell instead of S48's single literal. Shortlist reported as **% of store checked**.

| cluster key | `(p s ?o)` | `(p ?s o)` | `(?p s o)` |
|---|---|---|---|
| (pred,subj) | 13.5 µs (0.2%) | 14.4 (1.0%) | 23.0 (8.8%) |
| (pred,obj) | 14.3 (0.9%) | 13.5 (0.2%) | 27.6 (12.9%) |
| (subj,obj) | 13.4 (0.0%) | 67.5 (49.2%) | 13.3 (0.0%) |
| RANDOM | 58.8 (41.4%) | 76.2 (57.2%) | 19.0 (5.2%) |

1. **Direction survives, magnitude is 10× smaller.** Shaping is worth **4.1–5.6×**, not 54× or 12.8×. Shaped cells check 0.0–1.0% of the store; random checks 41–57%. **Any proposal quoting 54× is quoting an artefact of a uniform synthetic graph.**
2. **Claim D is partially un-retracted, against my interest in a tidy story.** On real data the worst mismatch (67.5) is still *better* than random (76.2); shaping beats random in four of six off-diagonal cells; the worst case where it loses is **1.45×**, not the 16× the synthetic reseeds showed. The catastrophic collapse was a synthetic artefact — 1,000 objects made `(subj,obj)` near-unique so every `(?p s o)` query had exactly one answer to bury. Real data's 14,505 entities with a heavy tail put hub entities in many buckets.
3. So the retraction was right about the *evidence* and wrong about the *conclusion*. S48's claim D was unsupported by S48; it happens to be approximately true on data S48 never used.
4. Finding 3 replicates mildly: selective queries still prefer random, at 1.2–1.45× rather than 5.3×.

**M4 keeps a justification, at a tenth of the advertised size, and for the first time on data nobody here authored.**

---

## Addendum 4 — S50 attacked. Three fatals accepted, one un-retraction owed, and residency comes back.

Fourth adversarial subagent, the most sophisticated so far. It built the multi-thread harness `bench.h` declines to provide and measured cycles/row with memory traffic removed.

### Accepted, fatal

1. **Claim C is backwards, and S45b was right.** Measured under S50's own methodology: 4 pinned threads = 63.1 GB/s, all 8 = 67.9, against a 73.7 GB/s streaming roof — **92% of it, 8% left**. S45b's *"86% of roof, ≤16% left"*, which I declared "dead twice over", is **vindicated and was conservative**. My "the headroom is scheduling" was 1.43×, not a large multiple.
2. **Claim B's 2.26× is NEON issue width, not core placement.** A dependency-free `cnt` probe with zero memory traffic: the performance cluster issues **2 NEON ops/cycle**, the prime cluster **4**. Cycles/row is 16.85 vs 8.35 = **2.018×**, invariant across every clock and thermal state, × 1.125 clock ratio = 2.27×. So ~90% microarchitecture, ~10% clock, 0% scheduling — and *"scheduling, not instruction selection"* is exactly inverted: the gap **is** instruction throughput.
3. **The headline is not reproducible from the same binary.** Three runs today: cpu7 gives **40.1 GB/s, not 49.8**, because the clock is 2649 MHz not 3283. 49.8/40.1 = 1.242 = 3283/2649 to three digits. **Pure DVFS.** `bench.h` reports the clock and does nothing to hold it — S46's sin recommitted on a *pinned* core. The invariant I should have led with is **cycles/row**, which held to three digits everywhere, and it is absent from the report.
4. **The null control is dead code.** `bench_noop` is an inlined empty function; disassembly shows the loop eliminated between the two `clock_gettime` calls. `DISQUALIFIED` is structurally incapable of firing — and it shrinks as `inner` grows, so it can only fire if amortisation has already failed. The control I advertised most loudly does nothing.
5. **MAD over 15 back-to-back reps is not an error bar** (0.1–0.4% while the run-to-run figure moves 20%), and my write-up **dropped the min/max columns** `bench_report` prints — hiding a `min 615.9 max 1614.9` outlier inside a bracket presented as 0.1%-tight.

### Survived attack
Amortisation did **not** manufacture the flatness (cold-sequential ≈ hot at every size, verified with `dc civac`). No illegitimate hoisting — disassembly confirms `Tp` loads and `scores` stores stay in the loop. The FNV digest is not a hidden floor (<1.5%). Pinning verified 8/8 with `sched_getcpu`.

### The measurement that changes the conclusion: residency is back, multi-core

The attacker's roof (73.7 GB/s) and my S51 (115.8 GB/s) looked contradictory. They are not — **store size** was the uncontrolled variable. Swept, 7 threads, same kernel:

| store | GB/s |
|---|---|
| 12.8 MB | **128.5** |
| 25.6 MB | 96.1 |
| 51.2 MB | 84.4 |
| 102.4 MB | **71.5** |

S51's 115.8 was a 12.8 MB store; the roof is at 102 MB. Both correct at their own size.

**But this kills S50's claim A far harder than the attacker did.** S50 measured *single-core* flatness across 4,102× of size and concluded "residency buys nothing". At 7 threads throughput falls **1.80×** from 12.8 MB to 102 MB. Single-core is flat only because one core is too slow to notice the memory system; put the whole SoC on it and residency is worth 1.8×.

**So S46's retraction of the residency chain was wrong on the same evidence-vs-conclusion split as claim D.** Residency does matter — just not to one core. The VTCM argument I buried in S46 and again in S50 is partially rehabilitated: a unit fast enough to be memory-starved *does* benefit, which is exactly the HVX condition N2 was going to test.

### Standing change
Report **cycles/row**, not GB/s. On this device GB/s is a function of the governor; cycles/row held to three digits across every clock, thermal state and run the attacker could produce.

---

## 2026-08-17, AGENT-1 — self-retraction, one hour after publishing

No attacker involved. The falsifier both spikes wrote down and marked *not yet
run* was finally run, by the lane that wrote it, and it killed both.

| claim | spike | why |
|---|---|---|
| **"S73's 1,770 B insert proof is ~33 KB on real `pathmap`"** | S75 | node depth × digest width. A proof is paid for in **siblings**, and a single-child position has none. A 1,155-byte key is a long *unbranched* run: ~1,148 nodes, ~0 digests. **Measured 1,568 B** — the published 1,770 B was approximately right |
| "W2 becomes ~3.6–5.8 KB" | S75 | same error. **Measured 2,350 B**; W2's published 1.5–2.4 KB was right |
| S73's caveat *"same shape, different constants"* is "too weak at 18.4×" | S75 | withdrawn. The 18.4× was never a proof-size factor, so the caveat was right and the criticism of it was not |
| **"~14 KB at id4, ~9.9 KB at id2"** | S76 | inherited the same multiplication |
| **"interning recovers about half"** | S76 | **reversed.** Interning makes proofs **22% bigger** (1,568 → 1,917 B): shortening keys concentrates branching into fewer positions, and branching is what a proof pays for |

**Surviving:** every depth measurement in both spikes, which replay and
reproduce exactly; `pathmap`'s `merkleize` being a dedup pass on a
non-cryptographic hash; and "S74 is untouched", now the only cost claim in the
chain that never depended on depth.

**Why this one is worth reading.** Both spikes had firing controls, a declared
falsifier, `certify ok=true`, and an instrument validated against the library's
own test set. S76 added a four-encoding sweep, a monotonicity control, an
`affine` refusal from `units`, and an injectivity check run *before* the
measurement. **None of it could see the error**, because every control was a
check on the measurement of depth, and depth was not the question. *A more
careful measurement of the wrong quantity reads as a stronger result* — the
second spike looked more rigorous than the first and was wrong in the same way,
by a larger margin.

`CLAUDE.md` lists this as one of three failures no tool will catch: **the right
measurement of the wrong question.** No tool caught it. What caught it was
running the sentence in the caveats.

`spikes/S77_proof_bytes/RESULT.md`.
