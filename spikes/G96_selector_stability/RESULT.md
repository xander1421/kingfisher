# G96 — the ensemble's MRR is robust; its published per-key table is not

**AGENT-2, 2026-08-19. `certify ok=True`, 3 controls (all fired), 3 falsifiers
stated in `CHANNEL.md` before this directory existed, none fired.**
Check: `python3 spikes/G96_selector_stability/stability.py` (143 s)

**ATTACK on my own G95, one cycle old** (§2: self-authored data first).

## What G95 did and did not establish

G95 showed G88's valid-select argmax beats a multiset-preserving permutation
null **0/1000**, +0.0212 above the null max. **That is an aggregate result and it
licenses no per-key claim.** A selector whose individual choices are validation
noise can still beat that null, because the null destroys the key-to-arm match
*globally* while a weakly-informative selector retains a little of it everywhere.

The distinction is not academic: **G88 publishes its selector as a frozen
per-key table with a `choice_sha256`**, and a digest over a table reads as a
claim about the table.

## Method

Shuffle the 35,070 validation rows under a pinned seed, split into two disjoint
halves, fit **G88's own `freeze_dir_select`** independently on each, compare.

**A27 is this lane's own guardrail and it applied to me here** — *a hold-out
drawn from one end of the key order is not a sample.* Splitting `valid_rows`
as-laid-out would have put low predicate ids in A and high in B, and every key
would be absent from one side.

**The chance rate is computed, never assumed.** The choice distribution is
heavily skewed — 279 of 446 keys are `distmult` — so two *independent* selectors
drawing from that marginal agree far more often than 1/5. The baseline is
`sum(p_i²)` over the observed marginals.

## Result

| | |
|---|---|
| full-valid selector | **0.3143** (reproduces G88, sha `f2e8f705f91de769…`) |
| half-A selector | **0.3110** |
| half-B selector | **0.3105** |
| distmult everywhere | 0.2852 |

**The aggregate is robust.** Half the validation data reaches ~99% of the full
selector's gain and both halves beat DistMult comfortably. **F2 did not fire.**

**Agreement between the two halves, over the 424 keys both scored:**

| slice | agree | chance | above chance |
|---|---|---|---|
| all 424 shared keys | 338 = **0.7972** | 0.5700 | **+0.2271** |
| the **139** keys where either half left the default | 53 = **0.3813** | 0.2445 | **+0.1368** |

**F1 did not fire.** Agreement exceeds chance on both slices, so the per-key
choice is *not* pure noise — the selector carries key-level information as well
as aggregate information.

## The finding, which is a qualification and not a refutation

> **62% of the non-default entries in G88's frozen selector table would change on
> a resample of the same validation set.**

Overall agreement of 0.7972 looks stable and is not: it is carried by keys where
**both** halves fell back to `distmult` because `MIN_N=20` was not met. On the
139 keys where the selector actually makes a non-default claim — the only keys it
is asserting anything about — two disjoint halves of the same validation set
agree **38%** of the time.

**So `choice_sha256` is reproducible by SEED, not by RESAMPLE.** Byte-identical
re-execution will reproduce it, which is what this repo's reproducibility asset
tests; drawing different validation rows from the same distribution will not.

**What may be quoted from G77/G87/G88, unchanged:** the MRR figures, the gain
over single arms, and G95's verdict that the selector is a mechanism.
**What may not:** any reading of the frozen table as *which model suits which
predicate*. That is a 38%-stable assignment.

Note the direction of the halving artefact: both half-fits choose `distmult` for
**325** keys against the full fit's **279**, because halving pushes more keys
below `MIN_N`. So the half-fits are *more* default-heavy and still score 0.3105–
0.3110 — further evidence the aggregate gain does not depend on the unstable
entries.

## Falsifiers — stated in `CHANNEL.md` before the directory, none fired

| | claim | verdict |
|---|---|---|
| **F1** | the halves agree at or below the marginal chance rate, so the per-key table is noise | **quiet** — 0.7972 vs 0.5700, and 0.3813 vs 0.2445 on the non-default slice |
| **F2** | a half-fit selector cannot beat DistMult, so the gain is a data-budget effect | **quiet** — 0.3110 and 0.3105 vs 0.2852 |
| **F3** | G88 does not reproduce | **quiet** — 0.3143, selector digest identical |

**Stated plainly because this repo has been burned by the opposite: the 38%
figure was NOT pre-registered with a threshold and F1 was stated on the overall
rate, which did not fire.** The non-default slice is therefore an **observation**,
not a tested hypothesis, and it is not promoted into a falsifier chosen after
seeing the numbers. Its chance rate is reported so it is interpretable, and a
row that wants to *test* it must pre-register one.

## Controls — 3, all fired

| control | observation | how it could have failed |
|---|---|---|
| `reproduces_g88` | 0.3143 + selector sha | any drift in arms, corpus or miner |
| `halves_disjoint_and_shuffled` | 17,535 / 17,535, disjoint, seed pinned | index sets intersecting, or an identity permutation — reachable by deleting one line (A27) |
| `chance_computed_from_marginals` | 0.5700 vs naive 0.2000 | flat marginals, which would make the naive baseline correct after all |

## Against me

- **I nearly recorded another spike's `certify ok=True` as this one's.**
  `null.py` calls `os.execv(…, null.py)` at **module level** when numpy is
  missing, so `import null` from a numpy-less interpreter **replaced this
  process with G95's entire run** — G95's banner, G95's null, and a trailing
  `certify ok=True` that is indistinguishable at a glance from this file having
  worked. **A module whose import can `execv` is not importable.** The re-exec
  now happens in this file *before* the import, so numpy exists by the time
  `null.py` is read and its own bootstrap returns immediately.
- **The 38% figure was uninterpretable when first computed.** Quoting it against
  the 0.5700 baseline computed over *all* keys would have been the naive-1/5
  mistake at one remove — the subset excludes default-default agreements, so its
  marginals differ and its chance rate is necessarily lower. It now carries its
  own baseline (0.2445). **E-family: the number was real and the model behind it
  would have been wrong.**

## Scope

Official FB15k-237 split. Says nothing about a leak-free split (`G94`, another
lane). `MIN_N=20` is G88's constant, not measured here — **a different `MIN_N`
moves both the default-fallback count and the stability figure**, and that is
A26 territory this row does not enter.
