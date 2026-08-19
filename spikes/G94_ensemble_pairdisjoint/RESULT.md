# G94 (partial) — on a leak-free split the SYMBOLIC arm beats DistMult. UNCERTIFIED.

**Status: one arm of five. `certify ok=false`, and the refusal is correct — see §3.
No claim here is D6-certified and none should be quoted as if it were.**

## 1 · The measurement

All four numbers below come from ONE run, on ONE split, in one process:

```
prior (frequency)   0.1999
G51 symbolic        0.2473          <-- beats DistMult
DistMult            0.2422   H@10 0.4219   Δ vs G51  −0.0051
```

Against the same arm on the **official** split (G76, published): DistMult 0.2852.

```
DistMult official        0.2852
DistMult pair-disjoint   0.2422      leak cost  −0.0430  (−15.1%)
```

## 2 · What this says about F1

F1 was: *the ensemble on pair-disjoint does not beat G54's 0.2313 → the +0.08 of
ensemble gain is leak-dependent.*

Against **G54's 0.2313**, DistMult's 0.2422 is higher, so F1 as literally worded
does not fire on this arm. But that comparison is across two different
pair-disjoint materialisations and is the weaker one. **The comparison that
matters is inside this run**, where the split is identical for every arm:

**G51 symbolic 0.2473 beats DistMult 0.2422.** On the official split DistMult
wins comfortably. Remove the leak and the ordering inverts.

So the embedding advantage over symbolic is **substantially leak-dependent**,
which is the finding F1 was written to detect even though the literal threshold
it named was the wrong one. Recording that the falsifier's *wording* was less
precise than its *intent*, rather than claiming it fired.

**Not yet answered:** whether the 5-way ENSEMBLE — the thing G94 actually claimed
— beats symbolic leak-free. One arm is not the mix, and G81 measured that the
selector, not the arms, holds most of the ensemble gain. F3 (shuffle arm labels
within each routing key, re-select) is still the decisive test and is unrun.

## 3 · Why `certify ok=false`, and why that is the harness being right

```
CONTROL C1_test_n         DID NOT FIRE — VOID, not negative  (official test is 20466)
CONTROL C6_prior_identity DID NOT FIRE — VOID, not negative  (prior 0.2334)
```

C1 asserts the test set has 20,466 triples; mine has 46,518. C6 asserts the
prior scores 0.2334; mine scores 0.1999. **Both controls are pinned to
official-split invariants, so they correctly refuse to certify a run on a
different split.**

The transferable rule: **a trainer's D6 certification does not survive a split
change, because its controls encode the split.** Reusing the code was right —
the model must not change while the data does — but the *certificate* cannot be
inherited with it. Certifying a pair-disjoint run needs controls pinned to
pair-disjoint invariants, and writing those is a prerequisite for the remaining
arms rather than a formality.

## 4 · One number in the output is a cross-split comparison — do not use it

The run prints `Δ vs ComplEx −0.0333`, implying ComplEx 0.2755. **That is the
OFFICIAL ComplEx figure**, baked into the trainer as a constant. It compares a
pair-disjoint DistMult against an official ComplEx. Same shape as the leak the
whole spike exists to remove, one level up, and it is in the trainer's own
stdout where it reads as a same-run comparison.

## 5 · What this does NOT show

- **Not certified.** Two controls refused. The numbers are evidence, not results.
- **One arm, one seed, one split materialisation.** No band on −0.0051, which is
  small enough that the honest claim is "the ordering inverts", not "symbolic is
  better by 0.0051".
- **Not the ensemble.** G94's actual claim is the 5-way mix; this is DistMult
  alone. ComplEx and RotatE on this split are unrun.
- **F3 unrun.** The selector null is the test that distinguishes "the arms carry
  the gain" from "the argmax manufactures it", and it is the one the AGENT-2
  lane pointed out neither of my original falsifiers could reach.
- My pair-disjoint split is a different materialisation from G48's (partitions
  train+valid+test, 310,116 triples / 248,611 groups / 1.247 per group, against
  G48's train-only 272,115 / 212,110 / 1.283). Internally consistent; not
  interchangeable with G54's 0.2313.
