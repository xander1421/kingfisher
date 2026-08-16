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
    9b28730ea0c7dfaa  x6
    e3057eb3f939a7f3  x1
    f5436eb5a1086319  x1

distinct concurrent outcomes : 3
trials matching serialised   : 0/8
```

**Concurrent execution never reproduces the serialised result, and does not
reproduce itself.** 2,048 nodes, 6 epochs, `rent_rate = 0.03`.

## Why it matters beyond reproducibility

Importance is not a routing hint. It drives consolidation and forgetting — what
the atomspace retains. An importance value that depends on gRPC thread
scheduling means two brokers fed identical stimulus histories diverge in what
they remember.

## Fix — patch attached (`01-epoch-mutex.patch`)

**Restoring the async enqueue does not fix this**, which we assumed at first and
then checked. Two reasons:

1. The worker casts `request.second` back to a `dasproto::HandleCount*`
   (`WorkerThreads.cc:58`) — a gRPC-owned message freed when the handler
   returns. Enqueueing the pointer and processing it later is a use-after-free,
   which may well be why these lines were commented out in the first place.
2. It would not help anyway: `WORKER_THREADS_COUNT` workers pull from one queue
   and each calls `spread_stimuli` on the same network
   (`WorkerThreads.cc:22-24,58`). The concurrency moves from gRPC threads to
   worker threads and the hazard is identical.

The attached patch adds a **per-network epoch mutex** — `HebbianNetwork::epoch_mutex`
— held for the duration of `spread_stimuli`, `correlation` and
`asymmetric_correlation`, the three inline-dispatched entry points that mutate
importance.

Per network rather than global, so distinct contexts (`select_hebbian_network`)
still proceed in parallel. Neither entry point calls the other and nothing
re-enters, so there is no deadlock path. The epoch is already `O(nodes)`, so the
lock does not change the complexity of anything.

Verified in the model:
```
concurrent, unpatched            3 distinct outcomes, 0/8 match serialised
concurrent, with epoch_mutex     1 distinct outcome,  8/8 match serialised
```

A longer-term alternative is **BSP double-buffering** — read importance at epoch
*t*, write *t+1* — which makes concurrent epochs well-defined rather than merely
excluded, and would let them actually run in parallel. That is a larger change
and we have not attempted it.

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
