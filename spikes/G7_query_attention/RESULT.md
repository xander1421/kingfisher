# G7 — conservative attention is zero-sum across tasks, and DAS already knew

**Verdict: NO SIGNAL for the treatment, and the failure independently
rediscovers a design decision in production DAS code.**

G6 inverted using in-degree as stimulus. The named fix was to stimulate what a
*query* touched, as `stimulate(HandleCount)` does. G7 does that, tested for
**generalisation** rather than memory — train attention on one audit query,
evaluate on a different one — because the naive version is circular.

```
TRAIN  (, (cites $x $y) (verdict $y RED))       33 of 60 nodes touched
TEST   (, (cites $x $y) (verdict $y INVALID))   G1's independently verified finding

forgetting 30 of 60 nodes (50%)

  arm                found  preserved
  query_attention        0        0%     <- the treatment
  indegree               1       17%     <- G6's arm, which it was meant to beat
  keep_low               3       50%     <- prune HIGHEST importance
  arbitrary              0        0%     <- the null
```

Query-driven attention is **worse than in-degree** and no better than pruning by
alphabetical order. Pruning by *lowest* importance preserves the most.

## The mechanism, and it follows from G5's own correctness proof

ECAN is **conservative**: rent is redistributed as wages, so total importance is
preserved. G5 verified exactly that — 59,907 against a seed of 60,000, the 93
lost being floor-division only, and the conservation check is emitted into the
program.

That property is what makes the implementation correct. It is also what makes
attention **zero-sum across tasks**:

> Stimulating the region a TRAIN query touches necessarily **demotes** every
> region it does not. Training on query A does not merely fail to help query B —
> it actively harms it.

Which is why `keep_low` wins. The nodes TRAIN did *not* stimulate are precisely
the ones TEST needs. Attention did work; it allocated away from the test.

## DAS solves this, and the code says so

`elders/das/src/attention_broker/AttentionBrokerServer.cc`:

```cpp
:62,:69,:94,:116   HebbianNetwork* network = select_hebbian_network(request->context());
:369-375           if ((context != "") && (this->hebbian_network.find(context) != end()))
                       network = this->hebbian_network[context];
                   if (context == "")
                       network = this->hebbian_network[this->global_context];
```

**DAS keeps a map of Hebbian networks keyed by context**, with a global fallback,
and every entry point selects by context. Attention is partitioned per context
by construction.

I built one global importance field and reproduced, from first principles, the
exact failure that design exists to prevent. That is a stronger endorsement of
their architecture than reading it would have been — and it is the first time
this workspace has confirmed an elder's design by independently failing without
it.

## What this establishes

1. **A single global importance field cannot serve multiple query classes.**
   Not a tuning problem, not a stimulus-function problem — a consequence of
   conservation. Any conservative attention mechanism has it.
2. **G6's diagnosis was incomplete.** I blamed the stimulus function
   (in-degree vs query-driven). Swapping it made things *worse*. The stimulus
   was the wrong variable; the **scope** was.
3. **The next form is per-context importance**, i.e. `(imp <context> <epoch>
   <node> <v>)`, with each audit query carrying its own field. That is DAS's
   shape and it is a small change to G5's generator.

## What this is NOT

- Not evidence that attention-driven forgetting cannot work. It shows one global
  field cannot serve two queries, which is what a conservative allocation
  predicts. Per-context has not been tried.
- **Not a comparison anyone should cite as "attention is useless."** `keep_low`
  winning at 50% is not a strategy — it is the complement of a field allocated
  elsewhere, and it would invert again under a different TRAIN query.
- n = 60 nodes, one train/test pair, 50% prune. Nothing swept.

## The control that earned its place, again

With only `query_attention` vs `arbitrary` the report would have been "0% vs 0%,
inconclusive." The `keep_low` arm at 50% is what turns a null result into a
mechanism — it shows the field was allocated, just to the wrong place. That is
the third time a two-sided control has changed a conclusion in this workspace
(N1c, G6, G7).

## Reproduce

```sh
cd spikes/G7_query_attention && python3 gen_g7.py
```
