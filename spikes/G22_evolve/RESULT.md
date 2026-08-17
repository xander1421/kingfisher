# G22 — the graph rewrites itself and gets no smarter. Controlled negative.

**Verdict: NO DISCOVERY.** Materialising mined composition rules back into the
graph does expose rules that were not minable before — 18 to 1,577 of them
depending on how much is written — but they predict held-out edges **worse than
the same edges randomly rewired**. At every rewrite size. The new rules appear
because edges were added, not because structure was.

```
  written   new     conf  ctrl new  ctrl conf    A15
     2688    18   0.0093        24     0.0274    yes
     7528   206   0.1001       231     0.1074    yes
    60000  1577   0.0956      1477     0.1222    yes
```

`conf` is mean held-out confidence over the top 12 rules that were **not**
minable in round 0. `ctrl` is the identical pipeline on the identical derived
edges with objects permuted within predicate — same count, same predicate
marginals, same subject out-degrees, composition alignment destroyed.

Treatment does not merely fail to beat the control. It **loses to it every
time.**

## Why this is a result and not a broken run

**The positive control fires at all three sizes.** A synthetic second-order
chain is planted whose body has support *only* through materialised edges, and
the pipeline recovers it:

```
A15  RECOVERED (15,238)=>239   n=248   conf 0.165   -- machinery is not blind
```

0.165 is above both the treatment (0.0956) and the control (0.1222) at the
largest rewrite. So a genuine second-order rule, if one existed, would rank into
the top 12 and lift the treatment number. **The instrument can register
discovery. There was none to register.**

**The first version of A15 failed**, and the reason was structural rather than a
slip: `mine()` builds `head` from the mining graph, so a rule whose conclusions
live entirely in the scored set is never a *candidate* — not scored badly, never
considered. Planting 100% of the conclusions into the held-out set guaranteed
`NOT RECOVERED` for a rule present by construction. Had I shipped that, this
spike would have read **"NO DISCOVERY, control beats treatment"** — the correct
verdict reached through a blind instrument, which is worth nothing and is
indistinguishable from the real thing in the output. Same failure mode as G17's
A20, twice, in one week.

## Leakage: why the split is three-way

Materialised edges are predictions, and some are correct. Choosing which rules
to materialise using the set the new rules are later scored on writes correct
answers into the training graph.

```
train 70%   bodies mined here; derived = f(train, rules) and carries no
            information from anywhere else
dev   15%   ranks round-0 rules, picks what to materialise. Nothing else.
test  15%   untouched until round-1 rules are scored
```

Because `derived = f(train, rules(dev))`, test is causally upstream of nothing.

**Round-0 top-12 on test is 0.2922 here, not G17's 0.4405.** Not a discrepancy —
a 15% held-out set has fewer chances to confirm a prediction than a 20% one. The
numbers are not comparable across splits and are not compared.

## The reading

The best current explanation is that **a materialised deduction carries no
information.** `derived` is a deterministic function of `train`. Any 2-hop rule
minable on `train + derived` is, in principle, a longer-path rule on `train`
alone. Materialisation cannot create information; it can only change what a
fixed-depth miner can *reach* — and it does so by spending graph density on
conclusions the graph already entailed.

That would also explain why it loses to the shuffle. Derived edges land exactly
on the pairs the rule already explains, so rules built on them re-predict
already-known facts and get excluded by the candidate filter, leaving a residue
of hard cases. The shuffled edges land on unrelated pairs and behave like a
generic degree-driven predictor, whose confidence is the marginal rate — low,
but higher than a residue.

**This is an explanation fitted to a result, and it is written down as such.**
G18's withdrawn "exact bound 1021, head plus wrapper" was exactly this shape and
was wrong. It is tested directly in G23, not believed here.

## What this means for the evolving-graph thesis

The thesis was that a graph rewriting itself with its own conclusions
bootstraps discovery. **On FB15k-237, with composition rules and a controlled
comparison, it does not.** Believing your own conclusions and re-reading them is
not discovery; it is re-reading.

That does not sink self-modification. It relocates where its value would have to
come from: not making entailments explicit, but **selection** — attention,
forgetting, error-correction. Nothing here tests those. What is now excluded is
the cheapest version of the claim, the one that would have been easiest to
believe.

## What this does NOT show

- **Not that self-modification is useless.** One rewrite rule (composition), one
  dataset, one round. No attention gating, no pruning, no iteration to fixpoint.
- **Not that no second-order structure exists in FB15k-237.** It shows this
  miner does not reach it this way. G23 tests whether direct 3-hop mining does.
- **Not a statement about the derived edges' accuracy.** They are ~30-37%
  correct by round-0 confidence; the question here was never whether the
  predictions are good, but whether writing them down exposes new structure.
- One machine, single process. No cross-device check — this is arithmetic over
  integers with no engine involved.
- Caps were hit at the largest size: 62,663 edges eligible, 60,000 written,
  **2,663 dropped**. Reported because a silent cap reads as coverage.

## Reproduce

```sh
cd spikes/G22_evolve && python3 evolve.py     # ~3m17s
```
