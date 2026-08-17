# G9 — contexts cannot be discovered here, but they barely need to be

**Verdict: NOT DISCOVERY — and the negative result comes with a design rule
worth more than the positive one would have been.**

G8 established that per-context attention works and named the cost: *you must
know your query classes in advance*. G9 asks whether they can instead be
**discovered** from what queries touch — because a system that cannot form its
own contexts cannot restructure its own attention, and that is what "self-
evolving" would have to mean.

```
scheme           contexts  mean preserved
global_1                1            48%
random_k                3            77%
discovered_k            3            79%
declared_N              5            86%
```

## The two-point gap was noise, and the exhaustive control proves it

79% against 77% is a tenth of one query across five. With 5 queries into 3
groups there are only **S(5,3) = 25** partitions, so the honest control
enumerates every one rather than sampling a single arbitrary arm:

```
best     83.6%   [[q_green], [q_2hop_red, q_red], [q_invalid, q_yellow]]
median   72.8%
worst    58.2%   [[q_2hop_red], [q_invalid], [q_green, q_red, q_yellow]]

discovered ranks 4/25    exact p = 0.160
```

Jaccard clustering finds a *good* partition — above median, 4th of 25 — and not
a distinguishable one. **Clustering by touch-set overlap is no better than an
arbitrary 3-way split at this scale.**

My verdict logic said `DISCOVERY WORKS` on the single-arm comparison. That is
the second time a lenient threshold has fired on noise here (G2's 5-shuffle
`REAL SIGNAL` was the first), and both were caught the same way — by making the
control exhaustive instead of sampled. `gen_g9.py`'s verdict now states the
exhaustive result.

## The rule the negative result produces

Preservation is **monotone in the number of contexts and nearly indifferent to
their membership**:

```
1 context    48%
3 contexts   72.8% median over ALL partitions   (58.2% worst, 83.6% best)
5 contexts   86%
```

Going 1 → 3 buys **+25 points regardless of how you split.** Choosing the *best*
3-way split over the worst buys 25 points too — but you cannot identify it, and
the median is what an arbitrary choice gets you.

> **Allocate as many contexts as you can afford. Partition quality is
> second-order and, at this scale, undetectable.**

That materially weakens G8's constraint. You do **not** need to know your query
classes — you need enough separate budgets. Which is a far cheaper thing to
build than context discovery, and it is consistent with DAS letting the caller
pass any string as `context`.

## Two things fixed mid-experiment

- **`q_amber` returns 0 findings** and was dropped as degenerate: a query with
  no answers can be neither preserved nor lost, and including it dilutes every
  arm identically while inflating all of them.
- **ECAN results were parsed by line order**, which broke the moment a context
  had no stimulus. Output is now tagged `(IMPOF <ctx> <node> <v>)` so parsing
  cannot depend on ordering — the same defect class as G3's schema-fitted parser.

## What this does NOT show

- Not that context discovery is impossible. It shows **Jaccard on touch sets,
  single-linkage at 0.55** does not beat chance on **5 queries over 60 nodes**.
  Richer clustering, more queries, or a graph where query classes genuinely
  separate might all change it. The n here is tiny.
- Not that the discovered partition is bad — it ranked 4/25. It is just not
  distinguishable from luck, which is a different claim and the one the data
  supports.
- The monotone-in-k rule is measured over exactly three values of k
  (1, 3, 5) on one graph. It is a rule of thumb, not a curve.

## Reproduce

```sh
cd spikes/G9_context_discovery
python3 gen_g9.py       # the four schemes, ~50 s
python3 exhaustive.py   # all 25 partitions, the real control
```
