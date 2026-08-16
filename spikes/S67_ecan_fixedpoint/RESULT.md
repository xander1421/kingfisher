# S67 — deterministic fixed-point ECAN: the failing test and the passing one

**Verdict: GREEN. A11's prediction is confirmed by construction — DAS's `double` attention broker fails the N-thread==1-thread oracle, and a fixed-point implementation to the A11 spec passes it. Reference implementation and oracle are in this directory.**

`analysis/THE_BRAIN.md` names attention as the missing organ, and the only one
outside the verified perimeter. This is the surgery, demonstrated rather than
argued.

## DAS's semantics, read from source
`elders/das/src/attention_broker/StimulusSpreader.cc`:

```
rent_i        = rent_rate * importance_i           :51
total_rent    = sum of rent_i                      :52   <- threaded trie walk
to_spread     = alienated_tokens + total_rent      :183
wages_i       = stim_i * to_spread / total_wages   :147
importance_i' = importance_i - rent_i + wages_i    :67-68
```
with `typedef double ImportanceType` (`HebbianNetwork.h:17`).

## The oracle — 4,096 nodes, 12 epochs, reproduced 3×

| implementation | T=1 | T=2 | T=4 | T=8 | verdict |
|---|---|---|---|---|---|
| **`double`** — as DAS ships | `108bf89a…` | `53fe11df…` | `dfd0b79c…` | `43a502ad…` | **FAIL** |
| **`fixed`** — A11 spec | `8a463a9f…` | `8a463a9f…` | `8a463a9f…` | `8a463a9f…` | **PASS** |

**Four thread counts, four different answers.** Attention state — which
determines consolidation and forgetting, i.e. *what the graph becomes* — depends
on how many threads happened to run.

## Why, precisely — and why "just use integers" is the wrong summary
Integer addition is associative, so thread order is harmless for the *sum*. That
was never the problem. The problem is that **`rent_rate * importance` rounds**,
and float addition is **not** associative, so partial sums combined in
completion order give different totals.

The fix is not "use integers". It is the three-part law:

| A11 requirement | as implemented here |
|---|---|
| **accumulate wide** | rent summed in `u128`. Integer addition is exact, so **no rounding happens in the sum at all** — thread order becomes irrelevant by construction, not by luck |
| **round canonically** | exactly two rounding sites per epoch: the Q32.32 rate multiply (truncating) and the wage division. Not one per edge |
| **update synchronously** | BSP double-buffered — read epoch *t*, write *t+1*. No read-modify-write interleaving |
| canonical fold order | partial sums folded by chunk index, never by completion order |

Importance is Q32.32 (`u64`, scale 2⁻³²); rates are Q32 fixed.

## Anti-degeneracy guard
An oracle that passes because the computation does nothing proves nothing — the
S58 `b4` lesson. `cargo test --release` asserts, on one epoch, that rent is
collected, that **more than half the nodes actually move**, that there are more
than 100 distinct resulting values, and that nothing saturates to zero. Passes.

## What this is worth beyond the fix
Per `THE_BRAIN`, a deterministic fixed-point ECAN contributed upstream to
DAS/Hyperon is three things in one artifact: the organ this architecture is
missing, a legible Deep Funding deliverable, and the first credible buyer
hypothesis this workspace has produced. **This directory is the demonstration
half of that contribution** — a reproducible failing test for the current design
and a passing implementation of the replacement.

## Caveats, stated precisely
- **What failed is thread-count sensitivity, not run-to-run jitter.** The
  `double` hashes are stable per T across runs in this harness, because chunk
  submission order is fixed. Real DAS, under contention, would additionally vary
  run to run at fixed T. Both are disqualifying; only the first is demonstrated
  here, and it is the stronger evidence for a maintainer because it reproduces.
- This is a **reference implementation of the semantics**, not a patch to DAS's
  C++. Porting means editing `StimulusSpreader.cc`, `HebbianNetwork.h` and the
  `HandleTrie` fold, and building DAS (bazel + gRPC) — not attempted.
- Synthetic stimulus and a synthetic network. The arithmetic law does not depend
  on the topology, but the magnitude of divergence would.
- `HandleTrie`'s own fold order is **unaudited** (S66 note). The spec requires
  content-hash ordering by construction, which sidesteps needing to audit it.
- Precision loss from Q32.32 versus `double` is not characterised. For an
  attention value in [0, ~100] with 2⁻³² resolution it is far below anything
  that could change a ranking, but that is an argument, not a measurement.
