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
| **Stage 2 must run in-process** | **B** | S45. Hardest requirement in the workspace, **absent from v1**. Subprocess = 5.66 ms, of which ~5.25 is generic process creation |
| **Any stage-2 engine swap is capped at ~1.06×** | **B** | S44, confirmed on device by S45. v1 listed MORK's 31.6× without this bound |
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
| MORK unlicensed at HEAD; MIT declared in issue #2, file never committed | **E** | Read from GitHub. v1 said A, which shows the scale was applied by confidence |
| MORK has no library surface | **E** | `kernel/src/main.rs` |
| MORK ~31.6× faster on join work | **B** | S35 — subject to the 1.06× bound. Fast, unshippable, uncallable |

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
| **Energy per job** | needs root |
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
7. **Verify the control, gate it on plausibility.** **Five** were silently broken: an eliminated null loop; a clock calibration folded to a closed form (769,190,472 MHz); a `date`-bracketed timer costing two process spawns; a coordinator sharing a core; a null bracket understating by 1.3×.
8. **Finding a failure mode does not inoculate you against it.**
9. **Measure the configuration the product can reach, before optimising one it cannot.**
