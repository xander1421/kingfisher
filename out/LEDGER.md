# CLAIMS LEDGER — what is actually true, 2026-08-17

Four adversarial rounds have left the workspace with a pile of claims, retractions, two un-retractions, and five deliverables citing dead numbers. This is the single place to look.

**Evidence grades**, because "measured" has meant four different things here:

| grade | meaning |
|---|---|
| **A** | measured on the target device, and survived an adversarial attack that specifically tried to break it |
| **B** | measured on the target device, not yet attacked |
| **C** | measured on the laptop only |
| **D** | simulated, projected, or arithmetic from other numbers |
| **E** | asserted from reading source, never measured |

**Grade B is the risk category.** Every claim that has died so far died at B or C. Nothing at A has fallen.

---

## LIVE — the determinism chain (the asset)

| claim | grade | evidence |
|---|---|---|
| MeTTa reduction is byte-identical across macOS/Apple-Silicon and Android/Snapdragon, including **evaluation order** and the **fuel count to the step** | A | S15: `fuel_used 100,082`, `raw_hash c2940ab5…` both sides; a non-terminating job stopped at exactly 2,000,000 steps on both with identical partial state |
| MORK: 33/33 corpus programs byte-identical across the two architectures, incl. a 48 MB dump | A | S16; AGENT-1 re-verified independently, read-only |
| Packed popcount is bit-exact against scalar and SDOT, on both machines | A | S34: six kernel/machine combinations, one digest. `kernels.c` is the one device file with **zero** unsequenced-UB warnings |
| Determinism holds across **core types** | A | S50: identical digests cpu0 vs cpu7 at every size; attacker confirmed |
| Determinism holds across **thread counts and split strategies** | B | S51: identical digest T=1…8, static and dynamic |
| `mork run --timing` writes a nanosecond count into the hashed space | B | S35; two runs differ in the artifact consensus would hash |
| MORK's space is a set, hyperon's `match` is a bag — cross-engine needs canonicalisation | B | S35: 380 results for 365 distinct facts |

This is the only claim group nothing has dented in four rounds, and it is what the proposal should lead with.

## LIVE — platform facts

| claim | grade | evidence |
|---|---|---|
| NNAPI exposes **no accelerator** on SM8750 — one device, `nnapi-reference`, type CPU | A | S31; independently confirmed by another agent's HAL/VINTF check |
| The quantisation scale **is** pinnable via NNAPI operand types | B | S31 |
| A naive int8 output scale silently returns **recall 0/8** — the cutoff lands on the saturation boundary | B | S31; and the boundary itself sat exactly on .5, decided by C float-vs-double |
| Android heap pointer tagging aborts PathMap's `slim_ptrs` on first `free()` | A | S16; invisible in every build, only appears on device |
| MORK has **no library surface** — CLI only, so it cannot be a per-query in-process engine | E | `kernel/src/main.rs`; read, not measured |
| MORK is unlicensed at HEAD; the author declared MIT in issue #2 (2025-05-21) and never committed the file | A | verified three ways + `gh api … .license` = null |
| The perf cluster issues **2 NEON ops/cycle**, the prime cluster **4** — 2.018× in cycles, invariant | A | attacker's dependency-free `cnt` probe, zero memory traffic |
| Stage 2 as a subprocess is ~96% of a query | B | corrected: **5.66 ms**, of which ~5.25 ms is generic Android process creation and ~0.4 ms is MORK |

## LIVE — but the magnitude only, not the mechanism

| claim | grade | note |
|---|---|---|
| Shaping is worth **4.1–5.6×** on a real KG; shaped layouts check 0.0–1.0% of the store, random checks 41–57% | B | S52 on FB15k-237, 120 queries/cell. **Supersedes the 54× and 12.8× from synthetic data, which were artefacts** |
| Worst mis-shaping on real data is **1.45×** worse than random; shaping beats random in 4 of 6 off-diagonal cells | B | S52. Un-retracts S48's claim D at a tenth of the size |
| The prefilter is at **92% of the 8-thread streaming roof, 8% left** | A | attacker's multi-thread measurement. **Vindicates S45b's "≤16% left", which I wrongly retracted** |
| Residency is worth **1.80×** multi-threaded (128.5 GB/s at 12.8 MB → 71.5 at 102 MB, 7 threads) | B | mine, just measured. **Un-retracts S46's chain: single-core is flat only because one core is too slow to see the memory system** |
| MORK is ~31.6× faster than hyperon end-to-end on join-shaped work | B | S35, 400 nodes/1200 edges. Not generalisable past join work |

## DEAD

| claim | killed by |
|---|---|
| "the seal defeats the echo attack, 13/13" | seal bound a value the verdict never used; no commit-before-reveal; unprefixed preimage collides. Fixed in `verifier2.py` |
| "bundling 54×, clustering 12.8×" | synthetic artefact; real KG gives 4.1–5.6× |
| "prefix coverage is the driver" | the one comparison reverses at B=4, B=16, and two of five reseeds |
| "bad shaping == no shaping" *as argued in S48* | falsified on synthetic 5/5; **conclusion happens to hold on real data for a different reason** |
| "86% of roof, ≤16% left" **retraction** | the retraction was wrong; the original claim is vindicated at 92%/8% |
| "core placement is worth 2.26×" | it is NEON issue width × clock, ~0% scheduling |
| "the headroom is scheduling, not instruction selection" | exactly inverted — the gap *is* instruction throughput |
| "59% of T=8 was pthread_create" | 41%, and subtraction is invalid because spawn overlaps work |
| "stage 2 is 13 ms of exec()" | 5.66 ms; my control lacked `LD_PRELOAD` so I timed a SIGABRT tombstone |
| "the read roof declines at 8 threads" | `pthread_create` inside my own timed region |
| "22.6 GB/s/core, ~2 IPC" | DVFS artefact of an unpinned process; the IPC was fitted to it |
| "flat within 1.8%" | below the instrument's resolution (52.08 ns tick) |
| "residency buys nothing" | true single-core, false multi-core (1.80×) |
| "no defensible multi-thread number exists" | S51 and the attacker both produced one |

## NEVER MEASURED — the gaps that matter

| gap | status |
|---|---|
| **Any NPU code** | nothing has ever run on the Hexagon. N2 (HVX popcount width) is still the single unknown the NPU case reduces to — and residency being worth 1.80× multi-core makes VTCM interesting again |
| **Energy per job** | blocked: `current_now` needs root, `dumpsys` gives level/temp only. Gates the entire "users opt in" story |
| **WorkManager's real limits** | ~10 min per worker, 6 h/24 h dataSync cap on Android 15. `SCHEDULER_SPEC` has neither, and every fleet projection assumes long runs |
| **Play Integrity's 10k/day quota** | an attestation ceiling nobody had costed |
| **Sustained vs burst, multi-core** | S51 ended with cores at 1,996/1,958 MHz against 3,532/4,474 maxima. Every multi-core number is a throttled floor |
| **A fixed (non-oracle) cutoff** | every bundling result uses a cutoff fitted to the ground truth. A deployed prefilter cannot |
| M1.1/1.3/1.5/1.7 | app, worker, shard store, transport — still nothing built |

## Standing methodological rules, earned the hard way

1. **Report cycles/row, not GB/s.** GB/s on this device is a function of the governor; cycles/row held to three digits across every clock and thermal state.
2. **Read the compiler warnings.** Nine unsequenced-UB warnings sat unread in files whose headline was bit-exactness.
3. **Never subtract a separately-measured overhead.** Measure the controlled pair. 59% became 41%.
4. **Measure the null and prove it can fire.** Mine was eliminated dead code.
5. **A parameter fitted to ground truth is an oracle** — label it and report its cost.
6. **One draw is not a measurement**, and one *configuration* is not either: both un-retractions came from generalising from a setup that could not see the effect.
7. **Grade the evidence.** Nothing at grade A has fallen; almost everything that died was B or C presented as if it were A.
