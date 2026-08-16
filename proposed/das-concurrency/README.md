# Attention broker: concurrent `stimulate()` calls interleave whole epochs on one shared network

**Question first, since this may be intentional:** three async enqueues are
commented out and replaced by inline calls —
`AttentionBrokerServer.cc:64` (stimulus), `:96` and `:118` (correlation). They
look like a deliberate temporary change. **Was the async path intended to be
restored?** If so the rest of this is moot and worth only a note in the code.

If not, the consequence below is a correctness bug in the shipping
configuration.

## What happens

```cpp
// AttentionBrokerServer.cc:64-65
// this->stimulus_requests->enqueue((void *) request);
this->stimulus_spreader->spread_stimuli(request);
```

`spread_stimuli` now runs **inline inside the gRPC handler**, so gRPC's worker
threads execute *entire epochs* concurrently against one shared
`HebbianNetwork`. The only synchronisation is `trie_node_mutex`, taken per node
inside `HandleTrie::traverse`.

Per-node locking makes each individual read and write atomic. It guarantees
nothing about the **aggregate**:

```cpp
// StimulusSpreader.cc:51-52   — collect_rent, across a full traversal
ImportanceType rent = data->rent_rate * node->value->importance;
data->total_rent += rent;

// StimulusSpreader.cc:67-68   — consolidate, a read-modify-write
value->importance -= changes->rent;
value->importance += changes->wages;
```

While epoch A traverses to collect rent, epoch B is writing importance behind
it. `total_rent` therefore sums a **torn state that never existed as a
consistent snapshot**, and A's per-node `rent` values are computed from stale
reads that B has already superseded.

**This is not a floating-point rounding-order issue.** We checked that first and
it does not apply: `HandleTrie::traverse` is serial, the trie is a fixed 16-way
alphabet keyed by handle content (`HandleTrie.h:9,177`), and the broker uses
only `+ - * /`, which IEEE-754 requires to be correctly rounded. Intra-epoch
order is fully determined. The defect is cross-epoch interleaving.

## Reproduction

`epochs.rs` in this directory models `spread_stimuli` faithfully — serial
content-ordered traversal, per-node mutexes, the same rent/wages/consolidate
arithmetic — and runs 6 epochs two ways.

```
serialised (async enqueue path)   62f3d55a454977bd
concurrent (inline dispatch), 8 trials:
    9b28730ea0c7dfaa  x7
    db10f65e6bc28f50  x1

distinct concurrent outcomes : 2
trials matching serialised   : 0/8
```

**Concurrent execution never reproduces the serialised result, and does not
reproduce itself.** 2,048 nodes, 6 epochs, `rent_rate = 0.03`.

## Why it matters beyond reproducibility

Importance is not a routing hint. It drives consolidation and forgetting — what
the atomspace retains. An importance value that depends on gRPC thread
scheduling means two brokers fed identical stimulus histories diverge in what
they remember.

## Suggested fixes, in increasing order of change

1. **Restore the async enqueue.** If the worker-thread path serialises requests,
   the defect disappears with no algorithmic change. This is presumably why the
   code is written that way.
2. **An epoch-level lock** around `spread_stimuli`, if inline dispatch is wanted.
   Coarse, but correct, and the epoch is already O(nodes).
3. **BSP double-buffering** — read importance at epoch *t*, write *t+1* — which
   also makes concurrent epochs well-defined rather than merely excluded.

## Optional hardening, not required for the above
A fixed-point (Q32.32) importance type makes the broker immune to compiler
flags, which matters if the network is ever replicated across heterogeneous
hardware. **This is not needed to fix the bug above** and we flag it only
because we built it: `ecan.rs` here is a reference implementation.

We checked whether current `double` arithmetic could diverge across platforms
via FMA contraction and concluded it cannot as written — every float operation
in the hot path is a bare multiply or a bare add in its own statement
(`StimulusSpreader.cc:51,67,68,76,77`), so there is no `a*b+c` for clang's
default `-ffp-contract=on` to contract, and `src/.bazelrc` sets no FP flags.
