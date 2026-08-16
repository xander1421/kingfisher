# S60 — bisection commitment cost. **RED. Every headline number was wrong, and the central finding was inverted.**

Original verdict was AMBER: *"commitment costs 11.6%; step-level bisection is impossible on hyperon's public API."* Adversarial review destroyed both halves, and I reproduced each defect before rewriting.

## The root cause: the benchmark timed a program aborting on an assertion failure

`main.rs` built `Metta::new(None)` **once** and reused it across every timed iteration. Iteration 1 ran against a clean space; every subsequent iteration ran against a space already holding iteration 1's atoms, hit an error atom at the 7th `!` expression, and terminated early. Verified:

```
SHARED Metta (what S60 did):        FRESH Metta each iteration (correct):
  iter 0: 50794 steps, 21 results     iter 0: 50794 steps, 21 results
  iter 1:  5709 steps,  7 results     iter 1: 50794 steps, 21 results
  iter 2:  5709 steps,  7 results     iter 2: 50794 steps, 21 results
```

The abort is **silent by design** — `mod.rs:1044-1046`:
```rust
if error { self.i_wrapper.mode = MettaRunnerMode::TERMINATE; return Ok(()); }
```
so my `if st.run_step().is_err() { break }` could never fire. The benchmark ran hundreds of iterations, so essentially every number came from the 5,709-step aborted re-run — 8.9× less work than the program. **"5,796 steps/run" and "7.0 changes/run" — and therefore 825 = 5796/7 — are artefacts of this.**

## Claim (B) was backwards: step-level bisection **is** available

`lib/src/metta/runner/mod.rs:527-534`:
```rust
impl std::fmt::Debug for RunnerState<'_, '_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RunnerState")
            .field("mode", &self.i_wrapper.mode)
            .field("interpreter_state", &self.i_wrapper.interpreter_state)
            .finish()
    }
}
```
`InterpreterState` derives `Debug` and holds `plan: Vec<InterpretedAtom>`. **A public trait impl is public API.** Measured: the debug string changes on **50,786 of 50,794 steps**; across the corpus the per-step change fraction is min 0.959, **median 1.0000**. There is no 825-step blind spot.

Two further routes I missed: `hyperon::metta::interpreter` exports `interpret_init` / `interpret_step` / `InterpreterState::has_next`, letting you drive the interpreter with full state in hand; and `Metta::space()` mutates on every ADD-mode step, covering the pure-ADD programs with zero result changes.

So *"the alternative is patching hyperon… a maintained fork"* was wrong. The real obstacles are that the only public **serialization** is a 90 KB `Debug` string costing **200×**, and that it is not reproducible. Both are engineering problems with known fixes, not API limits.

## The cost was misattributed: it is `to_string()`, not hashing

New modes: `strbuild` (build the string, hash nothing) and `lazyv` (O(1) `results.len()` probe first — sound because `results` is append-only, `mod.rs:1043` is the only mutation and it is a `push`).

**Honest harness, fresh `Metta`, real 50,794-step run:**

| mode | steps/s | cost |
|---|---|---|
| `plain` | 1,196,307 | — |
| **`lazyv`** (O(1) probe) | 1,146,668 | **4.1%** |
| `strbuild` (no hashing at all) | 773,364 | 35.3% |
| `lazy` (what I measured) | 746,774 | **37.6%** |
| `chain` | 655,031 | 45.2% |
| `dbglazy` (true per-step granularity) | 5,966 | **99.5% — 200×** |

`strbuild ≈ lazy` to within 0.2 points: **the SHA-256 is free, and ~94% of the "commitment cost" was serialization.** An O(1) change probe removes it.

## "A floor, not an estimate" was exactly backwards — the cost is O(n²)

`results_string()` rebuilds the **entire accumulated result set** every step. `c1`'s results total 60 bytes, which is the only reason 11.6% looked small. On a program with a real payload (300 × `collapse`/`superpose`, 1.47 M steps):

```
block    1  us_per_step   1.099  resultlen     0
block 2935  us_per_step 262.788  resultlen 73148
total: 194.8 s  vs  plain 1.155 s   ->  169x
```

Per-step cost tracks accumulated result length linearly, so quadratic over the run. `lazy` on that program costs **24.8×**. Only `lazyv` is workload-independent (4.1–4.6% on both).

## Two more refutations

**The digest is not reproducible**, which makes the whole thing the cost of computing a random number. Three runs of `!(new-space)`, identical step and change counts, three different digests. And the *fine-grained* debug commitment is unstable even where the results digest is stable — from two causes: raw code pointers (`ret: 0x100c44640`) **and**, after masking every `0x…`, 386 remaining diff hunks from `Variables({…})` hash-set iteration order. That second cause is new — `proposed/hyperon-nondeterminism/` covers addresses and `intersection-atom`, not hash-set ordering in `Variables`.

**`lazy` cannot bisect at all.** It folds only on result change, so the step index never enters the chain. Three different programs, three different step counts, one digest:
```
!(+ 1 1)                            115 steps   8fab64db85605193
!(+ 1 (- 3 2))                      226 steps   8fab64db85605193
!(+ (* 1 1) (- (+ 2 1) (* 1 2)))    559 steps   8fab64db85605193
```
It commits to the final value, not the trace. **So I priced the cheap mode, called the positional one "a trap", and the cheap one buys nothing for bisection.**

## Chain vs Merkle — the data structure question I never asked
A hash chain is adequate for a **two-party interactive** dispute (both sides bisect their own chains, the game finds first divergence — Arbitrum-style). It is fatal for the shape R-NEW describes, where a prover posts one root and later opens "state at step *k*" to a verifier who never replayed: a chain has no opening at position *k*. That needs a Merkle/vector commitment — ~2N hashes and **32N bytes retained (1.6 MB per 50 k-step run)**. Neither the extra hashing nor the retention was measured.

## 825 was one draw, and a low one
Corpus sweep, `steps / result_changes`, the 19 programs with ≥3,000 steps and ≥2 changes:
```
min 598   p25 1013   median 1161   p75 1545   max 7558      spread 12.6x
```
`c1_grounded_basic` on its **real** run is **2,419** — the spike's own program disagrees with the spike by 2.9× once the harness is fixed. `mkdocs.metta` hit a 2 M-step cap with **1** change: bisection there resolves to the entire run. And 46 of 67 programs have ≤1 result change, so a results-only commitment cannot bisect them at all.

## What survives
- Hashing on change beats hashing every step — **direction right, magnitude wrong, cause misattributed.**
- The commitment is paid by every job, disputed or not.
- Results-only granularity is coarse — it simply is not the only option available.
- The `plain` control was **fair**: `strbuild` lands between `plain` and `lazy` in both harnesses and both programs, which is only possible if the string work is real in all three. The error was attribution, not the baseline.

## Corrected verdict
> **RED.** Step-level bisection *is* reachable on the public API. The commitment cost is unpriced: `lazyv` suggests ~4.1%, a true per-step plan commitment costs 200×, and nothing in between has been measured with a sound digest. Re-price with `FRESH=1`, an O(1) change probe, an **incremental stack hash** instead of `format!("{:?}")`, a stable atom encoding, a Merkle root instead of a chain, and the 19 corpus programs that actually run.

## The methodological lesson, which is the real output
The Caveats section of v1 named three of these defects — n=1, `to_string()` unsoundness, workload dependence — and the verdict proceeded as if none of them fired. **Each one, when actually run, flipped a headline number.** A caveat that would change the verdict if true is not a caveat; it is an unfinished experiment. `GUARDRAILS.md` gets this as a rule.

And the 1.02× spread I cited as validating GUARDRAILS A1 was real but irrelevant: it was tight precision around the **wrong workload**. Reproducibility is not accuracy.
