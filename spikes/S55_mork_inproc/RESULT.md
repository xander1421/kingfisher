# S55 — MORK in-process: my grade-E claim was false, and it gated the query path

**Verdict: GREEN on the yes/no question, and CORRECTED on every magnitude by S56 the same day.**

> **S56 supersedes the numbers below.** 0.310 ms was one point in a **1.66× DVFS band (0.19–0.32 ms)** reported to three digits; the speedup is **18–30×**, not 18.3×; and the caveat at the bottom of this file — *"a resident agent would amortise it"* — is **false**: `Space::new()` is 0.83 µs, 0.3% of stage 2. What survives is the claim that matters: **MORK is callable in-process, and `LEDGER` line 41 is disproven by execution.**

I wrote: *"MORK has no library surface — CLI only, so it cannot be a per-query in-process engine"*, graded it **E** (read, not measured), and let it gate the biggest cost in the query path. A reviewer checked and found `kernel/src/lib.rs` exporting `pub mod space`, with `experiments/unification_test_laws` already calling `mork::space::Space::new()` in-process. I had read `main.rs` and never looked for `lib.rs`.

## Measured
`Cargo.toml: mork = { path = "../../elders/MORK/kernel" }`, cross-compiled for `aarch64-linux-android`, run on the S25 Ultra:

```
loaded      13 expressions
dumped      22 expressions
best of 20  0.310 ms    (Space::new + add_all_sexpr + metta_calculus(1) + dump_all_sexpr)

S45 subprocess: 5.66 ms, of which ~5.25 ms was generic Android process creation
speedup:        18.3x
```

The API is entirely public: `Space::new()`, `add_all_sexpr(&[u8])`, `metta_calculus(steps)`, `dump_all_sexpr(&mut W)`. Binary is 2.1 MB. The build needed the same three fixes as S16 (CMake toolchain wrapper, `libgcc` shim, `+aes,+neon`) and nothing else.

## What changes

1. **The architectural requirement is satisfiable with MORK, not only hyperon.** "Stage 2 must run in-process" now has two engines that can honour it.
2. **MORK's blocker count drops from two to one.** It was *fast, unshippable, and uncallable*. It is fast, unshippable (licence), and **callable**. Only `M0.1` stands between MORK and use.
3. **A grade-E claim gated a measured architectural conclusion.** The E grade did its job — it flagged the claim as unverified — but nobody acted on the flag for a week. The lesson is not "read more carefully"; it is that **an E-grade claim must not be load-bearing**. If it gates a decision, it has to be promoted to a measurement before the decision is made.

## And it re-opens the Amdahl question
S44 put stage 2 at 5.7% of a query and bounded any engine swap at 1.06×. Against the **deployable** prefilter (S54: 18.73 cyc/row, T=4, 12.8 MB, 2.793 GHz → **0.168 ms**):

```
prefilter  0.168 ms   (35%)
stage 2    0.310 ms   (65%)
total      0.478 ms
```

**In the deployable configuration, in-process stage 2 is the majority of the query, not 5.7% of it.** The 1.06× bound was computed against a laptop prefilter and a numpy exact-match; it does not survive the move to real hardware and a real engine.

**Caveat, and it may swallow the whole result:** the 0.310 ms includes constructing a fresh `Space` and re-parsing the program *every query*. A resident device agent would build the space once per shard and reuse it, so the marginal per-query cost could be far lower — and the correct comparison for a shard host is amortised, not per-query. That is unmeasured and is the obvious next spike.

## Ledger corrections owed
- Line 41 "MORK has no library surface" → **false**, delete.
- Line 44's "5.25 ms is process creation" → still true of the *subprocess* path, but the path is avoidable.
- The 1.06× Amdahl bound → **re-open**; it is not valid for the deployable configuration.
