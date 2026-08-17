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

---

# N1b — two inheritance defects in N1, both confirmed. One conclusion survives as a range; one is false.

## 1. The 8.7% inherited a band S56 explicitly retracted
S56 measured stage 2 at **191.88–319.01 µs — a 1.66× DVFS band** — and recorded
the rule: *"any absolute time on this device is a governor reading unless it is
normalised or bracketed by three invocations."* N1 used 250 µs as a value.

| stage 2 | prefilter share |
|---|---|
| 191.88 µs | **11.1%** |
| 250 µs | 8.7% |
| 319.01 µs | **7.0%** |

**The honest figure is 7.0–11.1%, not 8.7%.** The conclusion survives — every
point in the band is well under the inherited ~17% — but quoting one number
re-asserted a precision S56 withdrew. Fifth DVFS catch here.

And the asymmetry underneath is the sharper point: N1 reports **cycles/bundle**
(normalised, per standing rule 1) and then divides it by a **governor-dependent
millisecond**. Numerator normalised, denominator not.

## 2. "Compute-bound at 1.6 MB, bandwidth-bound at 12.8 MB" is FALSE
The reconciliation was confounded two ways — thread count (3 vs 4) *and*
concurrency model (threads on a spin barrier vs independent processes with no
barrier). Isolated by running **the same code, same barrier, same T=3, varying
only shard size**:

| shard | T=1 | T=2 | T=3 | cycles/bundle @T=3 |
|---|---|---|---|---|
| 1.60 MB | 71.2 µs | 35.6 (2.00×) | 24.0 (**2.96×**) | 5.23 |
| 12.8 MB | 572.9 µs | 290.4 (1.97×) | 196.7 (**2.91×**) | 5.70 |

**Both scale ~2.9×.** Shard size costs ~7% in cycles/bundle (15.48 → 16.61 at
T=1) and **nothing in scaling**. It does not explain S72b's 2.68×.

### The actual explanation
S72b ran **four processes each scanning the full 100k rows** — 4× the total work
and 4× the memory traffic. N1 splits **one query's rows across threads** — the
same traffic divided. Those are different memory behaviours, and the difference
is the **workload shape**, not the shard size and not the barrier.

So S72b's saturation is real *for throughput scaling under 4× working set*, and
N1's near-linear scaling is real *for latency scaling of fixed work*. Both
correct, measuring different things, and my sentence claiming shard size
reconciled them was wrong.

## 3. The T=4 collapse is now refused, not remembered
`pf.c` gains, at the loop head:
```c
if(T>=NCPUS){ printf("... REFUSED: spin barrier needs a free core (T>=%d)\n",NCPUS); continue; }
```
The rule was in the LEDGER for all three occurrences — S51 at T=8, S53 at T=1,
N1 at T=4 — and it never fired. It is now a construction-time refusal in the
harness, the same move A10 made for the quiet gate.

## 4. Conditions block added
`conditions.json` declares `concurrency: threads-spin-barrier`, `workers: 3`,
`cpuset: 0-1,4-5`, and cites `S56_mork_amortise` and `S72_c3_cpuset` — so
`claimcheck.py` reports both findings above as inheritance diffs without anyone
needing to notice them. This is the first spike to opt in.

---

# N1c — cache padding: predicted effect, measured none. And the control came free.

**Verdict: negative result. Padding the barrier atomics to 128 bytes changes nothing measurable at this granularity, so the workspace's multi-threaded figures do NOT carry a hidden false-sharing term. Noise floor is ~6%, established by a control I got for free.**

`pf.c:33` was `static atomic_int gen, left, stop;` — three adjacent atomics,
almost certainly one cacheline, crossed on every barrier. The prediction: pad
them and if the barrier cost drops, every multi-threaded figure here carries an
unaccounted term.

Padded after `crossbeam-utils/src/cache_padded.rs:94` (Apache-2.0, licence read
from `LICENSE-APACHE` on disk), which uses **`repr(align(128))` on aarch64** —
128 not 64, because ARM prefetches pairs of 64-byte lines.

| threads | unpadded µs | padded µs | unpadded cyc/bundle | padded |
|---|---|---|---|---|
| 1 | 71.1 | 71.2 | 15.56 | 16.48 |
| 2 | 35.9 | 35.7 | 7.85 | 8.28 |
| 3 | **23.9** | **23.9** | 5.23 | 5.53 |

**Identical to three significant figures, and scaling is 2.98× both ways.**

## Why there is no effect, and where there would be
Each barrier crossing here covers ~4,167 bundles per thread at ~5 cycles each —
about **20,000 cycles of work per crossing**. A cacheline invalidation costs
tens of cycles. The barrier term is amortised into nothing.

False sharing would matter in the opposite regime: a fine-grained barrier with
little work between crossings. **S51's `mc.c` is the candidate**, not this one,
and it has not been tested.

## The free control
Padding **cannot** affect single-threaded performance — there is no other core
to share with. So the T=1 delta is pure measurement noise: 15.56 vs 16.48
cycles/bundle = **5.9%**.

That is the resolution of this experiment, and it bounds the claim honestly:
**no false-sharing effect larger than ~6% exists here.** A smaller one would be
invisible. I did not design that control; it fell out of measuring T=1 in both
variants, and it is worth keeping as a pattern — *include a configuration the
treatment cannot affect, and its spread is your noise floor.*

## Adopted from crossbeam, and deferred
- **`Backoff` (`crossbeam-utils/src/backoff.rs`)** — `SPIN_LIMIT 6`,
  `YIELD_LIMIT 10`, `spin()` → `snooze()` → park, with `is_completed()` telling
  you when spinning stopped being profitable. **This is the escalation the
  LEDGER's "the barrier must block" describes in prose and the code never
  implemented** — three occurrences: S51 T=8, S53 T=1, N1 T=4 (337×).
  N1's fix was a construction-time refusal (`T>=NCPUS`), which prevents the
  collapse but does not let T=4 *work*. Backoff would.
- **`loom`** — deferred to the tooling list, not the elder list. It is the
  highest-value item here and not a queue: an exhaustive interleaving model
  checker is **a null that fires by construction**, which is precisely the
  property W1's four dead controls, S53's folded clock, B1's flat recall metric
  and Q1's non-monotone curve all lacked. It is the right instrument for the DAS
  concurrency patch, which was validated by a hand-written Python model swept
  over a GAP parameter — sampling where enumeration is available.
  **Limit: Rust-only, so it does not apply to the DAS C++ patch.**
- **Skipped:** `bbqueue`, `ringbuf`. SPSC solutions to a problem not measured
  here — M1.7 transport does not exist and no buffer has been profiled. YAGNI.
