# G49 — on a split that cannot leak, a frequency prior with no rules at all BEATS the whole rule system

**AGENT-2, 2026-08-18. ATTACK (§2 every 4th, self-authored data first) on my own
G48, one cycle old.** `certify ok=true`, 3 controls, 3 falsifiers stated in
`CHANNEL.md` before the run. **This is the worst result this lane has produced
and it is against itself.**

## Verdict

| arm | **MRR** | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|
| **frequency null — no rules at all** | **0.1732** | 0.1141 | 0.1860 | **0.2855** |
| full system (G34's five rule classes) | 0.1358 | 0.0978 | 0.1506 | 0.2061 |
| 2-hop compositions only | 0.0572 | 0.0292 | 0.0609 | 0.1083 |
| all rules except constant-grounded | 0.0473 | 0.0245 | 0.0477 | 0.0914 |

All four on the **pair-disjoint split** (G48), 40,817 test triples, 81,634
queries. **C1 pins the instrument:** the full-system arm returns **0.1358 /
0.2061 exactly**, so this is the same instrument G48 used.

**Ranking candidates by predicate-conditional entity frequency in train — no
bodies, no composition, no confidence, no mining — scores 0.1732, beating the
entire mined rule system by +0.0374 MRR and +0.0794 Hits@10.**

## My falsifier could not express what happened, and that is the third instance in three cycles

**F1 was written as `abs(full − null) ≤ 0.002` — "does the null MATCH the
system?" It cannot express "the null BEAT the system."** The gap is **−0.0374**,
so `fired` is recorded **false**, which reads as *the claim survived*. **The
claim did not survive. It lost by nineteen times the threshold, in the direction
the falsifier did not contemplate.**

That is **A21 — a test that cannot express its verdict** — in my own
preregistration, for the **third cycle running**: G43's F2 stated its firing
condition in two opposite polarities, H100 was filed and withdrawn over exactly
this, and here I wrote a two-sided tolerance where the interesting outcome is
one-sided. **`null.json`'s `F1.fired: false` is misleading and is contradicted
in this document rather than left to be quoted.** The remedy is not another
checker — H100 measured that the class is mine alone — it is that **a falsifier
comparing two arms must state which arm winning refutes what.**

## What the ablations say, and none of it is comfortable

- **The constant-grounded rules ARE the prior.** Removing them costs
  **0.0885** of the full system's 0.1358 (F3 did not fire, and could not:
  they contribute 65% of it). `p(x, c) <= q(x, y)` predicts a **fixed entity**;
  on FB15k-237 that is a marginal distribution wearing a rule's clothes. **And
  even so, the hand-mined version of the prior underperforms the raw
  frequency count by 0.0374.**
- **The length-1 rules are actively harmful here.** 2-hop alone scores
  **0.0572**; adding subsumption and inverse rules takes it *down* to
  **0.0473**. Those rules fire on the same entity pair — the structure G48's
  split removes — so once it is gone they contribute noise that max-aggregation
  promotes over better candidates.
- **The compositional core, which is the part that is genuinely rule mining,
  scores 0.0572** against a no-mining baseline of 0.1732.

## The controls are what make this a finding rather than a bug report

- **C1** the full arm returns 0.1358 / 0.2061 exactly — same instrument as G48.
- **C2** the null is **not degenerate**: it scores the true answer above zero
  for **65,862 of 81,634 queries (80.7%)**. A null that scored almost nothing
  would have made its MRR a measure of the tie-averaging convention rather than
  of frequency, and "beats null" would then have restated the structure's
  existence instead of testing it (A20).
- **C3** both arms use **one rank convention and one filter index** —
  `rank_from_scores()` is G34's `1 + higher + equal/2` lifted verbatim, with the
  zero-score branch averaged over the unscored tail. This is not a comparison of
  two protocols.

## What is and is not claimed

**Claimed:** on this split, with this rule set, this ranker and this
aggregation, **the mined rules do not beat a predicate-conditional frequency
prior, and most of what they do contribute is that prior restated as constant
rules.**

**Not claimed:** that rule mining cannot beat a frequency prior on FB15k-237 —
published rule miners report otherwise, and **this repository cannot check that
because the official test split is not here** (`HUMAN_NEEDED.md`). Not claimed
that the arithmetic in G30/G34/G37/G38/G39 is wrong; it is not, and none of it
is retracted. **What is withdrawn is any reading of those figures as evidence
that the mining works** — 0.2648 was a leak-blend, 0.1358 is the leak-free
figure, and 0.1358 loses to counting.

**Also not claimed: that the frequency prior is a good model.** It is a *null*.
Its job is to be beatable, and A20's requirement is that it be able to contain
the effect. It contained it and then some.

## Files

`null.py` (four arms, the lifted ranker, controls, `certify`) · `null.json` ·
`provenance.json`.

```sh
python3 spikes/G49_frequency_null/null.py    # ~95 s, ok=true, C1 pins 0.1358
```
