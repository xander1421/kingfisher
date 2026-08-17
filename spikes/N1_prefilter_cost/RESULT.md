# N1 — the prefilter's per-query cost, measured. The descope's last rung holds, and it is stronger than the figure it replaces.

**Verdict: GREEN. 23.9 µs at the deployable 3-worker shape, against the ~50 µs the workspace had been inheriting from S18's overhead artifact. Lower cost means a tighter Amdahl bound, so the one rung that could carry the NPU descope alone now does — on measured ground.**

The audit found the Amdahl rung compromised: the ~50 µs figure *"inherits S18's
overhead artifact and should be re-derived from a kernel profiled against the
roof."* This re-derives it. Code: `pf.c`, built with the Android NDK; gates
captured before and after.

## Measured — B=64 shard (12,500 bundles = 1.60 MB, per S11), `taskset 33`

| threads | µs/query | cycles/bundle | speedup |
|---|---|---|---|
| 1 | 71.4 | 15.60 | 1.00× |
| 2 | 35.8 | 7.81 | 2.00× |
| **3** | **23.9** | **5.22** | **2.99×** |
| 4 | 8080.1 | 1764.15 | **0.01×** |

Clock measured at 2,729 MHz by inline-asm dependent chain with a plausibility
gate (S53's lesson — sysfs was 27% wrong on this part). Reported in
**cycles/bundle** as well as µs, per standing rule 1.

## 1. T=4 is coordinator starvation — the third occurrence
The coordinator spins on `while(atomic_load(&left)>0){}` and `taskset 33`
confines the whole process to cores 0,1,4,5. At T=4 the workers occupy all four
and the coordinator timeslices against one of them: **337× slower than T=3.**

This is exactly S51's T=8 collapse and S53's T=1 error, and the LEDGER already
carries the rule — *"4 background cores − 1 coordinator = 3 workers, or the
barrier must block."* **The rule was written down and the code still hit it.**
T=4 is discarded as invalid by our own standing rule, not by inspection of the
number.

## 2. The deployable prefilter is 23.9 µs, not ~50
Scaling to T=3 is essentially perfect (2.00×, 2.99×) because each thread owns a
disjoint bundle range and the shard is 1.6 MB — small enough not to be
bandwidth-bound, unlike S72b's 100k-row store which saturated at 2.68×.

**That difference matters and is worth stating:** at the deployable *shard size*
the kernel is compute-bound and scales; at the 12.8 MB store S72b used it is
bandwidth-bound. B=64 bundling is what puts it back in the compute-bound regime.

## 3. Consequence: the Amdahl rung is restored, and strengthened
Lower prefilter cost tightens the bound. Against S56's in-process stage 2
(~250 µs):

```
prefilter  23.9 µs   ->   8.7% of the query
stage 2   ~250   µs   ->  91.3%
```

An NPU that made the prefilter **free** would save at most **8.7%**. The
inherited ~50 µs figure implied ~17%. So re-deriving it did not weaken the
descope — **it doubled the strength of its last remaining rung.**

## Where this leaves the NPU decision
The audit reclassified the descope to *a resource-allocation decision, not a
technical conclusion*, because the licence rung was dead, the SDK rung was paid,
and the Amdahl rung was inherited. **The Amdahl rung is now measured and
stronger.** That does not restore the other two — they are still gone — but it
means the descope has one load-bearing argument again rather than none.

## Controls, with failing inputs (D6)
| control | fails if |
|---|---|
| clock plausibility gate | outside 500–5000 MHz → abort. S53's 769,190,472 MHz artefact would trip it |
| gates captured pre and post | non-quiet either side invalidates the scaling curve |
| perfect scaling at T=2,3 | sub-linear would mean bandwidth-bound, contradicting the compute-bound claim |
| T=4 collapse reproduces the known pathology | if T=4 were merely slow rather than 337× slow, the diagnosis would be wrong |

Thermal drifted 34.3 → 38.6 °C across the run, inside the 45 °C gate.

## Caveats
- Synthetic bundles (`r64()`), not FB15k-237 hypervectors. Cost is a function of
  bundle count and D, not content — but the query's `nnz` affects nothing here
  since the kernel is fixed-width.
- One shard size. The compute-bound/bandwidth-bound crossover between 1.6 MB and
  12.8 MB is inferred from S72b, not measured here.
- Best-of-9 over 200 iterations per sample; a single invocation, so process-scoped
  variance (S55/S56's 2.1× lesson) is not sampled.
