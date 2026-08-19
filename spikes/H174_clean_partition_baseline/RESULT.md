# H174 — G91's "10.0× lift over symbolic rules" inverts on the partition that requires generalisation

`certify ok=True`, 3 controls (all fired), 3 falsifiers (**none fired**).
Settles the operating-point question H165 deliberately left open.

Check: `python3 kitchen/test_h174.py`

## The result

| | queries | G89 symbolic rules | G91 RotatE | ordering |
|---|---:|---:|---:|---|
| **full official test** | 6,268 | 0.0355 | **0.3546** | RotatE **10.0×** |
| **clean** (reverse not in train) | 4,096 | **0.0511** | 0.0214 | **symbolic 2.39×** |

**On the 4,096 test queries whose answer is not sitting reversed in the training
set, the 40 mined Horn clauses score more than twice what the trained embedding
does.** G91's headline is not merely inflated — the ordering it reports is
**backwards** at the operating point where a link predictor has to predict
something it has not seen.

Note the direction each system moves when the leaked triples are removed:
RotatE falls 0.3546 → 0.0214, and **G89 rises 0.0355 → 0.0511**. The symbolic
system was being *held down* by the same triples that were carrying RotatE.

## Why this is one comparison and not two numbers

H165 measured RotatE at 0.0214 on the clean partition and G89 publishes 0.0355
over all 6,268 queries. **Quoting those two against each other would be A18** —
a ratio without its operating point, an error already paid for twice here — so
H165 filed this row instead of asserting a headline that would have written
itself. This run puts both systems at the same operating point.

- G89's own `mine_4_topologies_wn` and `evaluate_symbolic_wn` are **imported,
  not reimplemented**. ARM-CLEAN is that same evaluator on a shorter test list;
  `true_sp`/`true_po` are still built from train+valid+test, so the filtered
  setting, every rule, every score and the rank convention are theirs.
- **ARM-FULL reproduces G89's published 0.0355 exactly** (control C1). Had it
  missed, this run would be void and the second number would not be reported.
- The clean partition is **2,048 triples / 4,096 queries**, byte-equal to
  H165's, and H165's number is **read from its committed `result.json`, never
  retyped** (control C2). A transcribed constant is a claim with no provenance.

## The contaminant, disclosed before the run and measured rather than argued

The two systems tie-break differently:

```
G89   rank = 1 + greater + equal//2     mid-rank, plus a frequency-prior
                                        backoff when the target scores 0
G91   rank = 1 + sum(scores > tgt)      optimistic
```

Normally that voids the comparison. It does not here, and **the asymmetry runs
against this finding, not for it**: H165's F3 measured RotatE's optimistic and
pessimistic MRR as **identical at 0.3546** (30 tied competitors in 6,268
queries), so RotatE's convention has no room to flatter it, while G89's
mid-rank can only cost G89. **The 2.39× is therefore a floor.**

## What this does and does not retract

**Does not:** G91's 0.3546 is real and reproduces to 4 dp across three lanes.
The arithmetic 0.3546 / 0.0355 = 10.0 is correct at the full operating point.

**Does:** the reading of that ratio as *"complex relational rotations dominate
hierarchical lexical trees"*. At the only operating point where the question is
about prediction rather than recall, the ordering reverses.

## Falsifier, stated before running

*If G89-on-clean scores below RotatE's 0.0214, RotatE still wins where
generalisation is required and G91's lift claim survives in weakened form —
withdraw.* It is **0.0511**.
