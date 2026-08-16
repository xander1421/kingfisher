# S57 — hyperon's own corpus, three platforms, and the first real cross-ISA test

**Verdict: the S15 correction is right and important; the cross-ISA result is real but was overstated. Rewritten after adversarial review confirmed every one of its counts.**

> **Headline, corrected.** Across aarch64-macOS, x86_64-macOS (Rosetta) and aarch64-Android, hyperon's 67-program corpus produces **identical fuel counts on all 67** and identical results on 66 — **360,847 genuinely-terminating interpreter steps** (not 560,847), **235 passing `assertEqual` assertions** including exact-compared f64 arithmetic, and **29 identical `(Error …)` atoms**. 42 programs cannot resolve their Python imports and exercise only the module resolver. Result hashes are **low-entropy — 35 distinct values over 67 programs** — because the corpus's outputs are almost entirely `()` and error atoms; the discrimination comes from hyperon's own assertions, not from the hashing. **Evaluation-order reproducibility is not established by this corpus.** Grade **B**: Rosetta not native x86; no libm, no FMA, no float formatting.

### What the attack changed

| v1 said | corrected |
|---|---|
| 560,847 interpreter steps | **360,847.** `mkdocs.metta` never terminates — it does not terminate at 2M fuel either — so its 200,000 was a fuel cap agreeing with itself by construction |
| "byte-identical result hashes" | **35 distinct hashes over 67 programs.** 14 programs hash the empty string, 28 hash error text, 23 hash only `()`. `c3_pln_stv` (37,788 steps) and `b0_chaining_prelim` (4,647) collide because both emit five `()`. ~5.1 bits of discrimination, not 256 |
| "evaluation order included, `raw_hash` is order-sensitive" | **Vacuous.** Order can only be detected with ≥2 results of ≥2 distinct atoms. Exactly one *deterministic* program qualifies (`f1_imports`, n=3, 2 distinct). Claim deleted |
| "66/66 deterministic programs identical" | 66 rows match, but **14 match by emptiness and 28 by identical error text** |
| "hyperon's own corpus" as a quality signal | **63% of it can't run without CPython extensions.** 14 of the 34 files marked self-checking execute no assertion at all — they die on `import!` before reaching one |
| harness ran the same on three platforms | **It did not.** `#!/bin/bash`; Android has no bash, so the device TSV came from mksh + toybox awk. Fixed to `#!/bin/sh` |
| status column | **The script hardcoded `ok`** and discarded `fuelrun`'s real `status`, which is why the fuel cap went unnoticed. Now compared as a field |

**Fixed and re-run, all three platforms** (`v2_*.tsv`, `run_all.sh` v2): status compared, `n_unit` and `n_error` counted per program, fuel limit raised to 2M.

```
terminating programs                 : 66/67
genuinely-terminating steps compared : 360,847
fuel identical across all three      : 67/67
passing assertEqual results          : 235, identical on all three for 67/67 programs
(Error ...) atoms                    : 29, identical on all three for 67/67 programs
distinct raw_hash values             :  35/67   <- the hash is nearly information-free
```

### What is load-bearing after the attack
- **Fuel agreement across ISAs.** 360,847 steps, and by step-weight **98% comes from programs doing real symbolic evaluation**, not from the empty or error-only ones. This is the strongest cross-ISA determinism evidence in the workspace.
- **235 assertions pass identically on three platforms**, including exact-compared f64 chains in `c3_pln_stv` (`0.9*0.87 == 0.783`, `*0.9 == 0.7047`) and `c1_grounded_basic`.
- **The null control fires**, and `fuel = 1012` held **30/30 runs** across two ISAs with 18 distinct outputs.
- **The S15 correction** — S15 tested cross-OS on one ISA, not cross-ISA — which the reviewer called the most important thing in the document.

### Float coverage, narrowed rather than refuted
The corpus *does* exercise f64 (129 SSE float instructions in the x86-64 build, 105 in the arm64 build), so "no floats" was wrong. But it uses only `+ - * /`, which IEEE-754 requires to be correctly rounded and therefore bit-identical on any conformant unit — close to tautological. Absent entirely: `sqrt/pow/log/exp/sin/cos/tan-math`, i.e. every libm function where the two ISAs genuinely differ. Zero `fmadd`/`fmsub` in the arm64 binary, so no FMA contraction could diverge. And **no float ever reaches a hash as text** — every one is consumed inside an `assertEqual` — so float formatting is untested. **This test would not catch a libm divergence.**

Rosetta note: Rust/LLVM emits SSE2 for f64 on x86-64, never x87, so the 80-bit extended-precision hazard is structurally absent. A native Intel run is still worth doing — not for float reasons, but because translated code is not the code a real x86 host runs.

`out/LEDGER.md` line 32 said *"MeTTa byte-identical across architectures, incl. evaluation order and fuel count"*, grade B, sourced to S15, and `RETRACTIONS.md:28` noted it was *"untouched by all three reviews."*

**S15 never tested two architectures.** Its own RESULT.md:11,16 — Android `arm64-v8a, bionic` against *"macOS 15 / Apple Silicon arm64 / libSystem"*. Same ISA. What S15 proved was **cross-OS / cross-libc determinism on aarch64**, which is valuable and is not what the ledger claimed. Three reviews missed it because nobody asked what "architecture" meant.

This spike runs the test properly, on **hyperon's own 67-program `.metta` corpus** rather than data I wrote.

## Measured

| platform | build | programs | status |
|---|---|---|---|
| aarch64-macOS | `aarch64-apple-darwin`, libSystem | 67 | all ran |
| **x86_64-macOS** | `x86_64-apple-darwin`, **different ISA, different codegen** | 67 | all ran |
| aarch64-Android | `aarch64-linux-android`, bionic | 67 | all ran |

Four fields compared per program: `fuel_used`, `raw_hash` (results in interpreter order), `sorted_hash`, `n_results`.

```
identical across all three platforms : 66/67
divergent                            :  1/67   <- and it is a positive control, see below
fuel count identical across all three: 67/67
total interpreter steps compared     : 560,847
```

## 1. The claim survives a real cross-ISA test, and can now be stated correctly
**66 of 66 deterministic programs are byte-identical across aarch64 and x86-64, and across libSystem, bionic and two OSes** — evaluation order included, since `raw_hash` is order-sensitive and matches. 560,847 interpreter steps agreed.

This is the property that lets us delete BOINC's entire host-classification subsystem (`sched/hr.cpp`), per `GUARDRAILS.md` C2: bitwise validation is sound only under no-float **or** homogeneous redundancy, and we are on the no-float branch. That branch is now measured across ISAs instead of asserted.

## 2. The one divergence is the corpus's own positive control
`python__sandbox__test_gnd_conv.metta` calls `(flip)` — a coin flip. Same binary, same machine, five runs:

```
8f6f62d3…  c73d59ea…  be9291e0…  c6d5c9d1…  be9291e0…      <- 4 distinct hashes in 5 runs
3887fb43…  3887fb43…  3887fb43…  3887fb43…  3887fb43…      <- control program, stable 5/5
```

It diverges from **itself**, on one machine, so it is not an ISA finding. It is better than that: **the harness has a null control that fires.** `LEDGER` standing rule 4 says *"measure the null and prove it can fire"* — S50's null was dead code eliminated by the compiler. I did not have to construct this one; hyperon's corpus contained it. That is the argument for using elder corpora, made concrete.

## 3. Fuel is deterministic even when output is not — in the non-branching case only
`test_gnd_conv` produced three different result hashes across the three platforms and **`fuel_used = 1012` on all three**, exactly. Randomness changed every value and did not change the work done by a single step.

So **the meter is separable from the result.** A job can be nondeterministic and still be billed, replicated and fuel-audited deterministically. Rung 1 verification (bisection over `interpret_step`) needs the *step count* to agree, not the values; this says that survives nondeterministic grounded atoms. Nothing in the workspace had established that, and the hyperjob fuel design was implicitly assuming determinism it did not need.

**Scope it hard, per review.** `fuel = 1012` held 30/30 runs (20 on macOS, 10 on Android) with 18 distinct result hashes — stable, not coincidence. But read the program: four top-level `!` expressions and **nothing branches on the random value**, so the control-flow graph is fixed and the step count *cannot* vary. This is the trivial case. `(if (flip) (long-computation) 0)` would swing fuel by orders of magnitude. **Corrected claim: fuel is invariant under grounded-atom nondeterminism when that nondeterminism does not affect control flow — n=1 program, 30 runs. Whether fuel survives branching randomness is untested, and the hyperjob billing design needs that answer.**

## Caveats
- **Rosetta, not native Intel.** The x86-64 binary is genuine x86-64 codegen — different instruction selection, different register allocation, SSE rather than NEON for any float — but it executes under Rosetta 2 translation on Apple Silicon. Rosetta is faithful on integer and IEEE-754 semantics, so a divergence would very likely have shown; but a native Intel or AMD host is the stronger test and has not been run. Grade this **B**, not A, until it has.
- 67 programs is hyperon's whole `.metta` corpus, but it is a *test* corpus: short programs, 560,847 steps total, mean ~8,400 steps. It is not a workload.
- Two files import Python modules (`python/sandbox/`), which under `fuelrun` fail their import and evaluate to fewer results than pytest would produce. They still run and still agree; they just exercise less than their name suggests.
- Nothing here tests 32-bit, big-endian, or a non-LLVM backend.

## What this changes
- `LEDGER` line 32 must be restated: S15 proved cross-OS on one ISA; **S57 proves cross-ISA**, on the elder's corpus, with a firing null control.
- The engine tested is **hyperon** — MIT, already builds for Android — i.e. the one we can legally ship. S16 established the same property for MORK, which we may not ship. The deliverable's engine now has the evidence.
