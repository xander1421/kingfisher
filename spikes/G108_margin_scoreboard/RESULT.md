# G108 — 82% of this lane's scored arms cannot be put on a scoreboard at all

**AGENT-2, cycle 19 (BUILD), 2026-08-19.** `certify ok=true`, **6 controls**,
F2/F3 preregistered in `CHANNEL.md`. **F2 fired.**

## The row started as a wrong answer of mine

Sweeping `spikes/G*/*.json` for the largest leak-free MRR returned
`G75/arms/F_dir_select = 0.3034`, and I read it as *"a certified spike already
beats the 0.2313 the evaluator scores."* **It does not.** G75's `split` field is
`official FB15k-237 train/valid/test`; my sweep had matched the string
`pair_disjoint` in a note. Two correct numbers, different denominators —
CLAUDE.md's second untoolable failure, caught only by opening the artifact.

## What is actually comparable

`config.json`'s `bar_rule`: *a bar is a number minus its own split's null.* That
is necessary and it is not sufficient — an MRR is comparable to another only
when **both the split and the candidate set** match. Ranking against all 14,541
entities and ranking against a predicate's train support are different tasks,
and subtracting a null does not make them one.

**official FB15k-237** · candidates `all 14541 entities` · null **0.2334** (G59)

| margin | MRR | arm |
|---|---|---|
| **+0.0700** | 0.3034 | `G75_complex_gate F_dir_select` |
| +0.0695 | 0.3029 | `G75_complex_gate E_pred_select` |
| +0.0518 | 0.2852 | `G76_distmult_min10 C_distmult_min10` |
| +0.0421 | 0.2755 | `G72_complex_all_entity C_complex_all_entity` |
| +0.0345 | 0.2679 | `G75_complex_gate D_g59_pred_gate` |

**pair-disjoint** · candidates `train_support_of_p (same as G51)` · null
**0.1732** (G49)

| margin | MRR | arm |
|---|---|---|
| +0.0000 | 0.1732 | `G58_transe_latent A_prior_support` |
| −0.0198 | 0.1534 | `G58_transe_latent B_transe_on_prior_support` |

**Two groups, and they do not rank against each other.** F2 fired: two candidate
sets survive among the ranked arms, so the single cross-series ranking this row
set out to build does not exist.

## The finding: 106 of 129 arms are unplaceable

| | count |
|---|---|
| ranked | **23** |
| refused — declares no `candidate_set` | **89** |
| refused — declares no resolvable `split` | **17** |

**89 arms state a number and never state the protocol it was measured under.**
Not a wrong number in any of them — an unplaceable one.

## The sharpest form of it (C6)

**`G54 C_dev_gated`, the arm `--eval` publishes as `filtered_mrr`, is one of the
89.** `spikes/G54_slice_gated_lift/slice_gated.json` declares no
`candidate_set`. So **the number the loop maximises cannot be compared with
anything, including its own successors** — and the comparison I tried to make in
the first paragraph is one instance of the general problem.

## A defect in this scoreboard, corrected mid-cycle

v1 substituted `"train_support_of_p (undeclared; G51 family default)"` for any
artifact declaring no candidate set, **and then grouped by that substitution.**
Two consequences, both the same mistake — **I supplied an input to my own
comparison (A22)**:

1. it invented a protocol for spikes that never stated one, and
2. it placed G54 (undeclared) in a **different** group from G58 (which declares
   `train_support_of_p (same as G51)`) — a split manufactured entirely by my own
   label.

v2 treats an undeclared candidate set as **unknown and refuses the arm.** That
is what moved the refusal count from 17 to 106, and it is why C6 exists at all:
under v1 the loop's own arm was quietly ranked against a guess.

## Also found, and it is not mine to fix

`spikes/G94_ensemble_pairdisjoint/distmult.json` declares
`split: official FB15k-237 train/valid/test` and carries **`n_test 46518`**,
which matches neither the official split's 20,466 nor pair-disjoint's 40,817 —
and the directory is named `..._pairdisjoint`. G94's headline is already
withdrawn (`WORK_QUEUE.md`, under G98), so this is a label to correct rather
than a live claim to retract.

## Reproduce

```sh
python3 spikes/G108_margin_scoreboard/probe.py
```
