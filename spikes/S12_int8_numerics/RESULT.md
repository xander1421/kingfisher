# S12 — the INT8 exactness claim, tested as far as it can be without silicon

**Verdict: GREEN, and it substantially de-risks M2.1.** The two failure modes the
plan worried about — narrow accumulation and saturation — are **not** hazards at
any dimension we would ship. The one that is real, output requantisation, is
survivable with a one-line change to how the cutoff is computed; getting that
wrong silently loses 46% of answers.

Code: `numerics.py`. Output: `numerics.json`, `numerics.log`. 20k triples, 32
queries (small enough to hold an exact int32 reference matmul).

## Why this had to be run

S7 states the open risk plainly and leaves it open:

> "the exactness claim assumes the phone NPU performs true INT8×INT8→INT32 with
> no internal saturation, requantisation, or reduced-width accumulation. Some
> NNAPI/Core ML paths do not."

`out/PORT_PLAN.md` M2.1 makes this the gate on the entire rung-2 design. No phone
is attached, so the on-device half stays open — but everything *upstream* of the
device could have been settled and was not.

## 1. Was S5's float32 path actually integer-exact?

S5 asserted it from the 2²⁴ argument and never checked. Checked here against a
true `int32 @ int32` reference at every dimension:

| D | float32 == int32 reference | peak \|score\| 2-bound | peak \|score\| 3-bound | worst partial (tile=64) | int16 used |
|---|---|---|---|---|---|
| 256 | **true** | 294 | 426 | 294 | 1.3% |
| 512 | **true** | 550 | 800 | 550 | 2.4% |
| 1024 | **true** | 1,094 | 1,596 | 1,094 | 4.9% |
| 2048 | **true** | 2,136 | 3,152 | 2,136 | 9.6% |
| 4096 | **true** | 4,190 | 6,242 | 4,190 | 19.0% |
| 10000 | **true** | 10,226 | 15,228 | 10,226 | 46.5% |

S5's assertion holds. It is now verified rather than argued.

## 2. Real headroom — int16 is safe everywhere we would ship

Scores are bounded by 3·D by construction, so the worst case at D=10000 is
15,228 against an int16 ceiling of 32,767 — **46.5% utilisation**, and the worst
*intermediate* partial sum under tiled accumulation never exceeds the final
value. The crossover where 3-bound queries would overflow int16 is D ≈ 10,922,
well above the D=1024 operating point.

**Consequence: an NPU that accumulates in int16 is fine.** That removes one of
the three named M2.1 risks outright, and it means the design does not need to
demand int32 accumulate from a backend.

## 3. What actually breaks — the three deviations, simulated at D=1024

| deviation | differs from ideal | exact rule holds | recall@threshold | false pos |
|---|---|---|---|---|
| ideal int32 | — | true | 1.0000 | 0 |
| int16 **wrapping** accumulation | **no** | true | 1.0000 | 0 |
| int16 **saturating** accumulation | **no** | true | 1.0000 | 0 |
| int8 **output requantisation** | **yes** | true | **0.5395** | 0 |

Wrapping and saturating int16 accumulation produce results **byte-identical** to
int32 — there is no headroom to exceed, so neither behaviour is ever triggered.

Output requantisation is the real one. Per-tensor rescaling to int8 collapses 397
distinct score values to 107. The threshold rule itself survives — every match
still lands on the same quantised value, and **zero** non-matches collide with it
— but the analytic cutoff `2·nnz(Q)` is stated in raw score units. Compared
against the quantised grid without rounding, matches that round *down* fall below
it and **46% of answers vanish silently**.

Snap the cutoff to the same grid and it is fully recovered:

```
recall_at_rounded_cutoff            : 1.0
false_positives_at_rounded_cutoff   : 0
```

## Design consequences

1. **The result envelope must carry the quantisation scale**, exactly as S7
   concluded the modulus must be transmitted rather than assumed. Add `scale` (or
   a `quantisation: {scheme, scale, zero_point}` block) to `lsh_commitment` in
   `spikes/S4_hyperjob_schema/hyperjob_v0.proto`. Without it a verifier cannot
   reconstruct the cutoff and cannot reproduce the shortlist.
2. **The cutoff must be computed as `rint(2·nnz(Q)/scale)`, never `2·nnz(Q)/scale`.**
   This is the entire difference between recall 1.0 and recall 0.54, and it is the
   kind of defect that passes every unit test written against exact arithmetic.
3. **Devices with different quantisation scales produce different score arrays**
   for the same job. Byte-comparison across heterogeneous devices therefore needs
   the scale pinned in the job, not chosen by the backend — otherwise honest
   replicas disagree and the dispute mechanism fires on nothing.
4. **M2.1 shrinks.** It is no longer "is INT8 exact on device"; it is specifically
   "does this backend requantise the output, and can the scale be pinned". That is
   a much smaller question to answer on real silicon.

## What is still not measured
Real NPU behaviour. Core ML and LiteRT may requantise, may fuse, may reorder, and
may not honour a pinned scale. This spike narrows the question and supplies the
test to run; it does not answer it. A device is still required.
