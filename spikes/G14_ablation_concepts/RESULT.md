# G14 — exact ablation works; there is nothing to abstract. Hypothesis refuted.

**Verdict: NO CLASSES.** Pre-registered hypothesis (a) — *nodes with identical
non-empty ablation signatures exist above chance* — is **refuted**. Zero classes,
and the observed collision count is **below** the random null.

```
baseline findings, 5 queries      332
empty signatures                  36/60   ablation changes nothing beyond the node's own
non-empty                         24/60
equivalence classes (size>1)      0

CONTROL random signatures, same size distribution, 200 draws
  observed pairs 0    null mean 0.2   max 3   >= observed 200/200   p = 1.000
```

Hypothesis (b) — *merging them preserves findings while shrinking the graph* —
is untested, because there was nothing to merge.

## Why it failed, and it is a property of the substrate not the method

Ablating node *X* removes *X*'s edges, which perturbs exactly the paths running
through *X*. Two nodes share a signature only if they occupy **identical
positions in the 2-hop structure**. In a sparse, irregular citation graph of 60
distinct spikes, that essentially never happens — every node is structurally
unique.

> **Abstraction by equivalence requires redundancy. This graph has none.**

That is worth knowing before anyone builds a categoriser on it, and it is not
something a statistical method would have told you — it would have returned
weak, noisy clusters instead of a clean zero.

## What the sweep produced anyway

The mechanism worked; the target was absent. Two exact results fall out:

**36 of 60 nodes are causally inert.** Ablating them changes nothing about any
other node's conclusions. That is an exact statement — no variance, no
threshold — and it is 60% of the graph.

**Load-bearing hubs, discovered rather than declared:**

```
S34  |sig|=17      S32  |sig|=12      M1  |sig|=8
S45  |sig|= 7      S15  |sig|= 5
```

`S34` is the packed-popcount spike and `S32` is the fleet-capacity projection —
both heavily cited, both already known to be load-bearing from reading. The
ablation recovers that **without being told**, which is a weak validation of the
instrument on a case where the answer is independently known.

## The exact-ablation asset survives the refutation

Byte-exact replay makes ablation an *exact* experiment: perfect attribution,
zero variance, no confound. ML ablation is statistical because a weight's
contribution cannot be isolated. 60 exhaustive ablations × 5 queries ran in
**10.4 s**.

The instrument is sound and cheap. It was pointed at a mechanism this graph
cannot support.

## What this names as the next mechanism

Equivalence asks *do two nodes behave identically*. In a graph of unique nodes
the answer is always no. Human discovery mostly does not work that way either —
the mechanism with the strongest cognitive grounding is **analogy / structure
mapping** (Gentner), where two subgraphs need not be equivalent, only
**relationally isomorphic**.

That is a subgraph-isomorphism question, not a signature-equality one, and it is
a different experiment. It is also the mechanism `hyperon-miner` implements —
frequent and *surprising* subhypergraph mining — which is **AGPL-3.0**, so
readable for ideas and never copyable (§7).

## Pre-registration held

The hypothesis was written into the file's docstring before the run and it
failed. That is the correction for the G2→G3→G6 pattern of each spike blaming
the previous one's cause: a stated prediction cannot be retrofitted.

The trap was also named first and it mattered — 36 of 60 signatures are empty,
so "both change nothing" would have produced 630 spurious pairs if empty
signatures had been allowed to collide.

## Reproduce

```sh
cd spikes/G14_ablation_concepts && python3 ablate.py     # ~10 s
```
