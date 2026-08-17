# G8 — per-context attention works, and it partitions the zero-sum rather than removing it

**Verdict: DIAGONAL.** Each context-scoped importance field preserves its own
query's answers and discards the other's. That is DAS's
`select_hebbian_network(context)` shape (`AttentionBrokerServer.cc:369-375`)
reproduced, and it is the fix G7's failure named.

```
                          ctxRED    ctxINVALID
prune_by_ctxRED              93%           0%
prune_by_ctxINVALID          42%         100%
keep_low_ctxINVALID          53%           0%
arbitrary                    53%           0%

conservation controls: ['True', 'True']   (one per context, per G5)
stimulus density: ctxRED touched 33/60 nodes, ctxINVALID 7/60
baselines: ctxRED 43 findings, ctxINVALID 6
```

Forgetting 50% of a 60-node graph. `arbitrary` keeps 30 nodes and still loses
**every** INVALID finding, so preserving them is not a free consequence of
keeping half the graph.

## The finding: per-context does not remove the zero-sum, it partitions it

G7 established that conservative attention is zero-sum across tasks. G8 shows
per-context fields do not repeal that law — they give each task its own budget.

The evidence is the cell nobody would look at:

```
arbitrary            preserves 53% of ctxRED findings
prune_by_ctxINVALID  preserves 42% of ctxRED findings     <- WORSE than arbitrary
```

Allocating a field to INVALID makes the graph **actively worse** for RED than
pruning by alphabetical order. Conservation is still conservation inside each
context; contexts merely stop stealing from one another.

## What this costs architecturally

> **You must know your query classes in advance.** A context is created per
> class, stimulated by that class, and serves only that class. An unseen query
> gets whichever context it is handed, and G7 measured what that is worth: 0%.

That is not a limitation of this implementation. It is what a conservative
allocation implies, and it is why DAS's API makes `context` a **caller-supplied
argument** rather than something the broker infers. The caller has to know.

## What G8 does NOT show

- **Not generalisation.** Each diagonal cell is train-on-test: the context was
  stimulated by the query it is then evaluated on. G8 measures **specificity**
  — that a field serves its own task *and not others* — which is a different
  property. G7 measured generalisation and it failed; G8 does not repair that,
  it confirms it in the off-diagonal (0% and 42%).
- **Not that 100% is impressive.** `ctxINVALID` touches 7 of 60 nodes and 30 are
  kept, so its ceiling is easy. The informative number is `arbitrary`'s **0%**
  in the same column — the task is easy for a field that knows about it and
  impossible for one that does not.
- n = 60 nodes, two contexts, one prune fraction. Nothing swept.

## Where the G-series stands

| | |
|---|---|
| **G1** GREEN | self-modifying graph, two devices, identical hash and fuel |
| **G2/G3/G4** RED | rule cannot be *learned* from the corpus, three framings |
| **G5** GREEN | deterministic fixed-point ECAN in MeTTa, both devices — and a deterministic wrong answer is still wrong |
| **G6** INVERTED | in-degree attention drops what an audit needs |
| **G7** NO SIGNAL | conservation makes a global field zero-sum across tasks; DAS partitions by context and I failed without it |
| **G8** DIAGONAL | per-context fields work, and partition the zero-sum rather than removing it |

The substrate composes and is replayable. Attention works **within a declared
context** and cannot serve an undeclared one. Learning a rule from the corpus
does not work at this n.

## Reproduce

```sh
cd spikes/G8_per_context && python3 gen_g8.py     # ~8 s
```

Counts and fractions only. Host gate REFUSED throughout; nothing here is timed.
