# CLAIMS LEDGER v2 — what is actually true, 2026-08-17

v1 was audited and **the grading scheme itself was the defect**. Rewritten.

## Grading, fixed

| grade | meaning |
|---|---|
| **A** | measured on device, and a reviewer **specifically tried to break this claim** and failed |
| **B** | measured on device; nobody has attacked *this* claim |
| **C** | laptop only |
| **D** | projected, or composed from measured parts plus arithmetic |
| **E** | read from source or an API, never measured |

Three rules v1 broke:
1. **Being measured *by* an attacker is not surviving one.**
2. **Being used inside an attack is not being the target of one.**
3. v1 said *"nothing at grade A has fallen."* **Circular** — if A means "attacked and survived", the A set is the survivor set by construction. Deleted. Honest version: **two claims have been specifically attacked and survived.** n=2.

## ⚠ Read before any performance number below

**S54: Android's `background` cpuset is `0-1,4-5`.** A charge-time worker gets **four cores, never a prime core**; `sched_setaffinity(cpu7)` is silently overridden. `top-app` spans 0–7, but S6's whole premise is that we are not the foreground app.

Every throughput figure here — S50's 49.8 GB/s (cpu7), S51's 115.8 (T=7), the attacker's 67.9 (T=8), the 2.018× prime NEON advantage — is from a configuration **the product cannot enter**. Upper bounds on hardware, not estimates of the deliverable.

---

## LIVE — determinism (still the asset)

| claim | grade | note |
|---|---|---|
| MeTTa byte-identical across architectures, incl. evaluation order and fuel count | **B** | S15. `RETRACTIONS.md:28` says *"untouched by all three reviews"*; v1 graded it A |
| MORK 33/33 corpus byte-identical, incl. 48 MB dump | **B** | S16. Independently *replicated*, never attacked |
| Packed popcount bit-exact vs scalar and SDOT, both machines | **A** | S34. The UB sweep hunted unsequenced modification across every device program; `kernels.c` was clean |
| Determinism across build profiles (stock / LTO / oryon-1) | **B** | S30, 12/12 cells. Missing from v1 |
| Determinism across core types | **B, with an open finding against it** | `S52_attack_s50` scored: *digest proves repeatability, not correctness*; the kernel was **rewritten** for S50 so a regression would be invisible. v1 cited the confirming attacker, omitted the scoring one. Fix = one assertion: S45's 12-row ground truth through the new kernel |
| Determinism across thread counts and split strategies | **B** | S51 |
| `mork --timing` writes nanoseconds into the hashed space | **B** | S35 |
| MORK's space is a set, hyperon's `match` a bag | **B** | S35 |

## LIVE — architecture requirements

| claim | grade | note |
|---|---|---|
| **Stage 2 must run in-process** | **A** | S45 + S55/S56 + two attackers. Controlled pair, same session, same cores, `fork`+`execve`+`waitpid`, n=30: **7.07 ms spawned vs 0.247 ms resident = ~29×** |
| ~~"5.25 ms of the 5.66 is process creation, so MORK's own work is ~0.4 ms"~~ | **DEAD** | A rule-3 subtraction, and falsified two ways: `morkinproc` costs **more** as a process (7.12–7.33 ms) than `mork run` does (7.07) while doing strictly less work — the residual is binary size and ELF relocation, not engine work; and `mork run` on an **empty** program costs 6.98 vs 7.07 for the real one, a 0.09 ms gap against a per-sample sd of 0.45. **Process-level timing cannot resolve stage-2 work at all** |
| Stage 2 in-process = **0.25 ms** (12 processes × 3000 reps, background cpuset, sd 0.06, CV 23%, band 0.16–0.33) | **A** | Two independent attackers converged on it from separate binaries. Output byte-identical to `mork run` **and to S45's ground truth**, md5 `5befd44b…` — the rule fires: 12 facts + 1 `exec` in, 11 deduped triples + 11 derived `(Answer …)` out |
| ~~Any stage-2 engine swap is capped at ~1.06×~~ **RE-OPENED** | **D** | S44 computed this against a laptop prefilter and a numpy exact-match. Stage 2 is **~57% of the query, band 45–66%** — recomputed against S54's *own deployable shape* (T=3, 0.194 ms; I had used the T=4 cell S54 itself flags as having a free coordinator). **"Majority" is not supportable**: at the fast end of stage 2's spread against the T=3 prefilter it is 45%. What survives is decisive and weaker: **stage 2 is the same order of magnitude as the prefilter, so the 1.06× bound is dead.** Also a lower bound only — measured on 13 synthetic uniform triples and one query shape; S52 found real-KG shortlists reaching 95% of the store, and stage 2 scales with shortlist size while the prefilter does not |
| **Never size a spin-barrier pool to `nproc`** | **A** | S51: T=8 collapses 89×; S53 hit the same starvation at T=1 (14× error) one spike later. Corroborated twice, by accident |
| 4 background cores − 1 coordinator = **3 workers**, or the barrier must block | **B** | S54 |
| Custody is justified by **network fetch**, not bandwidth (~4,500 queries per 12.8 MB fetch) | **D** | S34. Retires S18's argument |

## LIVE — platform

| claim | grade | note |
|---|---|---|
| `background` cpuset = `0-1,4-5` | **B** | S54, read from `/dev/cpuset` on device |
| NNAPI exposes no accelerator on SM8750 | **A** | S31; a second agent independently searched HAL/VINTF — for a negative existence claim, an independent search *is* the attack |
| Rule: **scale ≥ 2·nnz(Q)/126** — pick the scale from the cutoff, not the observed range | **B** | S31. v1 had the symptom (recall 0/8), not the rule |
| Transmit the scale as an **exact rational**, never a float | **B** | S49: the boundary sat on .5, so float-vs-double splits two honest verifiers. `rint` in a spec is insufficient — rounding modes differ across Python/C/Go/JS |
| Pointer tagging aborts PathMap's `slim_ptrs` | **B** | S16; *used* in an attack, never targeted. v1 said A |
| Perf cluster 2 NEON ops/cycle, prime 4 (2.018×) | **B** | Attacker-produced, unattacked — **and unbankable**, prime is outside the background cpuset |
| MIT declared in MORK issue #2, file never committed | **B** | See the row below; `analysis/MORK_LICENCE_CHECK.md` |
| **MORK IS callable in-process** — `kernel/src/lib.rs` exports `pub mod space`; stage 2 in-process = **0.25 ms** (S55's "0.310 ms" was one draw at the ~80th percentile) | **B** | **S55.** v2 said the opposite at grade E and let it gate the query path. `Space::new` / `add_all_sexpr` / `metta_calculus` / `dump_all_sexpr` are all public, and an in-tree crate already uses them. **Blocker count goes 5→4, not 2→1** — licence, nightly, `/dev/shm`, and heap tagging all remain; `proposed/mork-license/README.md` said so before S55 and I contradicted my own artefact |
| ~~MORK ~31.6× faster on join work~~ | **D** | S35's two rows use **differently-bracketed timers**: MORK's internal `steps took` (excludes the 31% parse), hyperon's `run_ms` (includes it). Re-measured today: 8–9 ms vs 942–1001 ms = **~110×**, both moved >1.4× from S35. Direction robust, magnitude not quotable |
| **MORK in-process is ~10× hyperon in-process on stage 2, ~7.5× end-to-end** | **B** | **The denominator that decides anything**, and nobody had measured it until an attacker did. MORK ~0.19–0.32 ms vs hyperon ~3 ms (boot 23 ms, amortisable). S55's 18.3× used MORK-as-subprocess — a straw man nobody proposed shipping |
| **In-process MORK needs heap pointer tagging off, process-wide** | **E on the app route** | Bare binary aborts without `LD_PRELOAD=libnotag.so` (exit 134, verified). App route is `android:allowNativeHeapPointerTagging="false"` — attribute present on API 36, and the operator shipped it in another APK on this phone — but **never executed here**. Costs MTE agent-wide, permanently, with no per-allocation escape (PathMap's non-slim path does not compile) |
| MORK unlicensed at HEAD — **no licence file anywhere in the tree, no `license` key in any Cargo.toml**, remote HEAD `0653b50` | **B** | Promoted from E. `analysis/MORK_LICENCE_CHECK.md`, dated, reproducible, checked against remote not a local clone |

## LIVE — magnitude survives, mechanism did not

| claim | grade | note |
|---|---|---|
| Perf→prime core migration is worth **2.26×** | **B** | v1 buried this in DEAD; only the *mechanism* died. Third un-retraction |
| A **1.43× scheduling headroom** exists | **B** | Attacker's figure; v1 over-killed the claim and recorded nothing in its place |
| Single-thread throughput flat across size (**≤0.5%**) | **B** | S50/S53. v1 listed "flat within 1.8%" as DEAD and left no LIVE row saying flatness is real |

## LIVE — shaping, oracle labelled

| claim | grade | note |
|---|---|---|
| Shaping worth **1.43×–5.64×** on a real KG | **D** | S52. v1 wrote "4.1–5.6×", dropping the 1.43. **Composite**: measured prefilter + *computed* `shortlist × per_check`; **stage 2 never executed** (S47:60); `per_check` varies 2× run-to-run |
| Store checked: shaped **0.0–1.0%**, random **5.2–57.2%** | **B** | v1 dropped the 5.2%. **Not a time proxy**: 207× fewer rows buys 4.36×, implying a ~13 µs floor and an asymptotic cap near 5.7× |
| **The cutoff is oracle-fitted** — reads ground truth; ~18 ms to produce a "127.8 µs" query | **B** | Rule 5 requires this on the row; v1 relegated it to a gap |
| Worst mis-shaping 1.45× worse than random | **D** | Same composite caveat |
| Selective-query shards should not pay for shaping (1.2–1.45×) | **D** | S48 finding 3, replicated. A surviving *negative* result, absent from v1 |
| Exactness rule is **m ≥ 2 of 3 bound slots** | **B** | S10. `(p ?x ?x)` is inexpressible → ~10% scan |
| Layout buys CPU work at fixed recall, not recall | **B** | S17 |

## LIVE — residency

| claim | grade | note |
|---|---|---|
| **1.00× at T=1–2, 1.06× at T=3, 1.16× at T=4** in the deployable cpuset | **B** | S54. Supersedes S53's 1.52× and my earlier 1.80×, both on unreachable cores |
| Whole-SoC (unreachable): 1.17× at T=4, 1.52× at T=6 | **B** | S53 — **one run, thermal uncontrolled**, its own caveat which v1 omitted while reciting its strengths |

## DEAD

The seal's 13/13 · "prefix coverage is the driver" · "bad shaping == no shaping" *as argued in S48* · the *retraction* of "≤16% left" · "the headroom is scheduling" (mechanism only) · "59% of T=8 was pthread_create" (41%; subtraction invalid) · "stage 2 is 13 ms of exec()" (5.66 ms; control timed a SIGABRT tombstone) · "the read roof declines at 8 threads" (spawn inside my own timed region) · "22.6 GB/s/core at ~2 IPC" (DVFS artefact, IPC fitted) · "residency buys nothing" (true at T≤2 only) · "no defensible multi-thread number exists".

**Removed:** "core placement 2.26×" → magnitude survives. **Half-removed:** "bundling 54×" → the clustering half is superseded; **bundling's own magnitude has never been measured on real data** and moves below.

## NEVER MEASURED

| gap | note |
|---|---|
| **Bundling's magnitude on real data** | 54× was B=1→B=64 compression; S52 measured clustering-vs-random only. First link in the VTCM chain, so the NPU gap rests on a premise v1 believed retired |
| **`verifier2.py` untested by anyone but its author** | 17 self-authored cases — *exactly v1's evidentiary profile*, and v1's 13/13 contained a test that never called the verifier. Grade **E**, highest-risk artefact here |
| **`hyperjob_v1.proto` still declares `quant_scale` as `double`** | The schema cannot express the rational scale the fix depends on |
| **Commit registry has `close()` but no clock** | No real deadline |
| **Worst-case recall** | S17: 0.97 mean with a **0/100 minimum** — at least one query loses everything. Nobody has tuned for worst case |
| **S32's 5.87× / 28,700 jobs/s unadjudicated** | No RESULT.md; `tps.py` still prints it under "MEASURED"; S33/S34 consume it. S34's "1.2× short" inherits it, so its NPU-necessity conclusion is unsupported |
| **Any NPU code** | And **VTCM is 8 MB vs a 12.8 MB packed store — it does not fit**, so bundling is a *prerequisite* for residency |
| **Energy per job** | *diagnosis was wrong*: not root. Battery sat at 100% and plugged, so the charge counter is static. Needs wireless adb + physical unplug, or a USB power meter |
| **Whether an APK can actually disable heap pointer tagging** | Gates in-process MORK entirely (see platform table). Two-line manifest change, never executed — no APK has ever been built in this workspace (`M1.1`) |
| **Shard-parse vs query-parse** | S56 put parse at 31% of stage 2, the only amortisable part, but its 13-expression program cannot separate the two |
| **WorkManager limits** | ~10 min/worker, 6 h per 24 h dataSync |
| **Play Integrity 10k/day** | fleet attestation ceiling |
| **Sustained vs burst** | S30: 3.7× host:phone sustained (not 2.7×), ~60% of burst single-thread; multi-core never measured, S51 ended throttled to 1,996 MHz |
| **A fixed, non-oracle cutoff** | every bundling result fits the cutoff to the answer |
| **3 workers + 1 coordinator** | the deployable shape; S54 put the coordinator outside the background set |
| M1.1/1.3/1.5/1.7 | app, worker, shard store, transport |

## Standing rules

1. **Report cycles/row, not GB/s** — GB/s is a function of the governor. *Rows above still violating this are marked.*
2. **Read the compiler warnings.**
3. **Never subtract a separately-measured overhead** — measure the controlled pair.
4. **Measure the null and prove it can fire.** Mine was eliminated dead code.
5. **Label oracle-fitted parameters on the row, with their cost.**
6. **One draw is not a measurement, and one configuration is not either.**
7. **Never let a retracted instrument supply a comparand.** The 5.66 ms denominator came from the attack that retracted S45's 13 ms — and that attack disqualified its own harness two lines later (*"the harness doing nothing costs 6.0–6.9 ms"*). **5.66 is below the stated noise floor of the instrument that produced it**, it is listed in this ledger's own broken-controls line, and I hardcoded it as ground truth anyway.
8. **Variance can be process-scoped, and repetition cannot see it.** I diagnosed a 1.7× spread as DVFS; it survives a pinned, settled clock (0.302/0.275/0.170 at an identical 2,918,400 kHz). Within a process, CV ~3%; across processes, CV 23%. Rule 1's "report cycles" does **not** fix this — cycles inherit the process's placement. Sample **N processes**, not N iterations. A tight within-run MAD is evidence of nothing.
9. **Verify the control, gate it on plausibility.** **Five** were silently broken: an eliminated null loop; a clock calibration folded to a closed form (769,190,472 MHz); a `date`-bracketed timer costing two process spawns; a coordinator sharing a core; a null bracket understating by 1.3×.
10. **Finding a failure mode does not inoculate you against it.**
11. **Measure the configuration the product can reach, before optimising one it cannot.**
12. **A retraction must be applied to every file that carries the claim.** S55's correction landed in `LEDGER.md` and nowhere else; `LEDGER.md:63`, `GAP_MATRIX.md` row 7 and `proposed/mork-license/README.md` all still asserted "uncallable" hours later, the last of them being the artefact intended to go upstream. One-file retractions are how a dead claim keeps voting.
13. **An E-grade claim must never be load-bearing.** "MORK has no library surface" was flagged as unverified and still gated the largest cost in the query path for a week. If an unmeasured claim gates a decision, promote it to a measurement before deciding.
