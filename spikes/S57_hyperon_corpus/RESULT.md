# S57 — hyperon's own corpus, three platforms, and the first real cross-ISA test

**Verdict: GREEN, and it both corrects and strengthens the workspace's most valuable claim.**

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

## 3. Fuel is deterministic even when output is not — and this is worth money
`test_gnd_conv` produced three different result hashes across the three platforms and **`fuel_used = 1012` on all three**, exactly. Randomness changed every value and did not change the work done by a single step.

So **the meter is separable from the result.** A job can be nondeterministic and still be billed, replicated and fuel-audited deterministically. Rung 1 verification (bisection over `interpret_step`) needs the *step count* to agree, not the values; this says that survives nondeterministic grounded atoms. Nothing in the workspace had established that, and the hyperjob fuel design was implicitly assuming determinism it did not need.

## Caveats
- **Rosetta, not native Intel.** The x86-64 binary is genuine x86-64 codegen — different instruction selection, different register allocation, SSE rather than NEON for any float — but it executes under Rosetta 2 translation on Apple Silicon. Rosetta is faithful on integer and IEEE-754 semantics, so a divergence would very likely have shown; but a native Intel or AMD host is the stronger test and has not been run. Grade this **B**, not A, until it has.
- 67 programs is hyperon's whole `.metta` corpus, but it is a *test* corpus: short programs, 560,847 steps total, mean ~8,400 steps. It is not a workload.
- Two files import Python modules (`python/sandbox/`), which under `fuelrun` fail their import and evaluate to fewer results than pytest would produce. They still run and still agree; they just exercise less than their name suggests.
- Nothing here tests 32-bit, big-endian, or a non-LLVM backend.

## What this changes
- `LEDGER` line 32 must be restated: S15 proved cross-OS on one ISA; **S57 proves cross-ISA**, on the elder's corpus, with a firing null control.
- The engine tested is **hyperon** — MIT, already builds for Android — i.e. the one we can legally ship. S16 established the same property for MORK, which we may not ship. The deliverable's engine now has the evidence.
