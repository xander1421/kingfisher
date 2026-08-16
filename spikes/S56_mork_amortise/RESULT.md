# S56 — decomposing stage 2, and retracting two things I wrote yesterday

**Verdict: the decomposition is solid, and it destroys the caveat I attached to S55 *and* the precision of S55's headline number.**

S55 measured in-process stage 2 at "0.310 ms" and I attached a caveat in my own favour: *"a resident device agent would build the space once per shard and reuse it, so the marginal per-query cost could be far lower."* This spike measures that. It is not lower. The caveat was wrong.

## Measured — 200 draws per phase, median ± MAD, three independent invocations

| phase | run 1 | run 2 | run 3 | share of total |
|---|---|---|---|---|
| `Space::new()` | 0.83 µs | 0.83 | 0.83 | **0.3%** |
| `add_all_sexpr` (parse) | 100.16 | 104.38 | 58.59 | **31%** |
| `metta_calculus(1)` (reduce) | 206.35 | 210.11 | 128.59 | **66%** |
| `dump_all_sexpr` | 3.91 | 3.70 | 3.85 | **1.3%** |
| **total** | **311.25** | **319.01** | **191.88** | |

## 1. Space construction is 0.3% of stage 2, so there is nothing to amortise
`Space::new()` costs **0.83 µs** — flat to two decimals across every run, MAD ±0.05. The thing I said a resident agent would save by keeping the space alive is **1/375th of the cost**. Constructing a MORK space is nearly free; filling it is not.

What *is* amortisable is the **parse**, 31% — a shard host parses its shard once, not per query. But my test program is 13 expressions, so it does not separate shard-parse from query-parse. **The 31% is an upper bound on what residency saves, and the real figure needs a program with a big resident shard and a small per-query term.** Unmeasured.

## 2. The resident-step number I nearly shipped was 199 no-ops
The first version of this spike reported a "resident step" of 0.26 µs and computed **"99.9% amortisable"**. I did not believe it, and probed:

```
step 0: 12 exprs, 291 bytes, changed=true
step 1: 22 exprs, 396 bytes, changed=true
step 2: 22 exprs, 396 bytes, changed=false      <- fixed point
step 3..5: unchanged
```

The space reaches a **fixed point after one step**, so 199 of 200 timed calls did nothing. "99.9% amortisable" was the cost of an empty function. Retracted before publication, which is the only reason it is not in the ledger.

It also confirms the converse, which S55 needed and never checked: `metta_calculus(1)` **does** do real work — 12 expressions to 22.

## 3. S55's "0.310 ms" is one point in a 1.66× band, reported to three digits
Across the runs above, total stage 2 ranged **191.88 to 319.01 µs — 1.66×** — while the *within-run* MAD was ~1%. Same binary, same program, same device, minutes apart. Re-running S55's own binary: best-of-20 gave 0.309 / 0.302 / 0.301 ms (stable), but best-of-200 gave 0.263 and 0.176 ms.

This is DVFS, and it is the **fifth** time this workspace has been caught by it. `LEDGER` standing rule 1 says *report cycles/row, not GB/s, because GB/s is a function of the governor* — and I then reported stage 2 in milliseconds. The rule was written about the prefilter and I did not generalise it: **any absolute time on this device is a governor reading unless it is normalised or bracketed by three invocations.**

The tight within-run MAD is what made it look solid. That is the S53 lesson verbatim: *within-run MAD hides run-to-run instability.*

## Corrected claims

| S55 said | corrected |
|---|---|
| in-process stage 2 = **0.310 ms** | **0.19–0.32 ms**, DVFS-dependent, three invocations |
| speedup vs subprocess = **18.3×** | **18–30×**; "more than an order of magnitude" is the defensible form |
| *"a resident agent would amortise it, could be far lower"* | **false** — space construction is 0.3%; at most the 31% parse is amortisable, and that is unmeasured |
| stage 2 is **65%** of a deployable query | arithmetic unchanged but both terms are DVFS-dependent; **needs re-derivation in cycles, not µs** |

## What survives untouched
**MORK is callable in-process.** That is a yes/no question and the answer is yes — 0.83 µs to build a space, real reduction, real output. `LEDGER` line 41 stays disproven. Only the magnitudes were wrong.

## Method note
Three independent invocations were what exposed this; one invocation with a small within-run MAD looked authoritative and was off by 1.66×. Proportions between phases held to ~1 percentage point across all three runs, so **the decomposition is the durable result and the absolute times are not.**
