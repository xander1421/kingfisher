# G2 — learning the rule instead of encoding it. It didn't learn.

**Verdict: RED, and the RED is the result.** An exhaustive rule search over G1's
graph reaches leave-one-out accuracy **0.760** against a majority baseline of
**0.740** — and a label-shuffle permutation test puts that at **p = 0.129**.
Three of thirty shuffles matched or beat it; one reached **0.800**. The search
fits noise about as well as it fits the truth.

G1 inferred `at-risk` from a rule I wrote. G2 asks whether the rule can be
*found*. It cannot, on this data.

## Setup

```
task        predict DIED (verdict RED|INVALID) vs LIVED (GREEN)
data        50 labelled spikes — 13 died, 37 lived
literals    26   hypothesis space (conjunctions, len<=2)  351
search      exhaustive, not heuristic — so what was searched is auditable
```

`Popper` (MIT, 313 stars) is the grown-up ILP tool and is cloned. It needs
SWI-Prolog, which is not on this machine; at |H| ≈ 10³ an exhaustive search is
sufficient and I can report the whole space rather than a search trace.

## The three controls

| control | result |
|---|---|
| 1. majority baseline | **0.740** |
| 2. leave-one-out CV | **0.760** — beats it by one spike in fifty |
| 3. **label shuffle, n=30** | mean 0.677, **max 0.800**, ≥ real in 3/30, **p = 0.129** |

The rule the search settles on in 48 of 50 folds:

```
died :- not_cites_GREEN AND words>=800
```

Note what that is *not*: it is not about inheritance, conditions, or citing a
dead claim. It is "a long spike that cites nothing green." That is the shape of
an artefact, and the permutation test agrees.

## My own control was underpowered, and it lied in the comfortable direction

The first version used **5 shuffles** and printed **`REAL SIGNAL`**, on a
threshold of `gap > 0.05` against the shuffle *mean*. At n=5 one seed had
already tied the real accuracy at 0.760 and I nearly shipped it.

At n=30 the shuffle distribution is mean 0.677, sd ≈ 0.07, max 0.800 — the real
result sits **inside** it. The correct statistic is the fraction of shuffles at
or above the real value, not the distance from their mean.

`learn.py` now runs n=30 and reports a permutation p. **Fifth instrument defect
this week, same shape: the control agreed with me until I made it harder.**

## Why it failed — and the honest reason is actionable

1. **13 positives.** Too few for a 351-hypothesis search; overfitting is the
   expected outcome, and the permutation test is what measures it.
2. **The features are regex over prose I wrote.** `inherits`, `admits_missing`
   and the rest are my judgement of my own text — weak, and circular.
3. **Feature signal is genuinely thin.** Best separations are `declares_gate`
   (0/13 died vs 6/37 lived) and `declares_null` (0/13 vs 4/37) — suggestive,
   tiny counts, and they fail the permutation test alongside everything else.
4. **The labels are author-assigned.** "Died" partly measures how honest a
   spike was about itself, not a structural property of the graph.

## What would actually make this learnable

**The `conditions` blocks A13 asks for are exactly the missing features.**
`claimcheck.py` collects `platforms`, `concurrency`, `workers`, `cpuset`,
`encoding`, `data` — structured, declared at write time, not regex-guessed
afterwards. The A9 pattern is literally a diff over those fields, and **no spike
has adopted them yet** (`0 opted in, 59 not`).

So the dependency runs the other way from how it was framed: A13 was proposed as
a *checker*. It is also the **feature engineering** this learner is starved of.
Until spikes emit `conditions`, G2 has nothing structural to learn from and is
guessing from prose.

## What this does NOT say

- Not that the graph approach fails. It says **this corpus, these features,
  n=50** yields no learnable rule at p<0.05.
- Not that the A9 pattern is unreal — G1 found four true instances by inference.
  Encoding it works; discovering it from 13 positives does not.
- No comparison against the LLM null was run. It would have been meaningless:
  the graph learner does not beat its own majority baseline, so there is nothing
  to compare.

## Reproduce

```sh
cd spikes/G2_rule_learning && python3 learn.py     # ~90 s, 31 x 50 exhaustive searches
```

Counts and accuracies only — no durations cited. Host `quiet.sh` REFUSED
throughout and it does not matter.
