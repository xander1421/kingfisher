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

`spread_stimuli` runs **inline inside the gRPC handler**. The service is a plain
synchronous `AttentionBroker::Service` registered with a bare
`RegisterService()` — no `SetSyncServerOption`, `ResourceQuota` or `num_cqs` — so
gRPC's default pool dispatches handlers concurrently.

**The hazard is between phases, not inside one.** Each `visit_nodes` pass *is*
atomic: `HandleTrie::traverse` is called with `keep_root_locked=true`, and
`HandleTrie.cc:227-233` skips unlocking root inside the walk, releasing it only
after the pass completes. Since `insert()` and `fetch()` both lock root first,
one traversal excludes every other traversal, insert and lookup. There is no
torn read inside `collect_rent`.

But `spread_stimuli` performs **several root-locked passes and releases root
between them** — `collect_rent` (:177), then `alienate_tokens` (:181),
`distribute_wages` (:185), then `consolidate` (:192). Two epochs can interleave
at those boundaries:

```
A: collect_rent            (rent_A computed from state S0)
B: collect_rent            (rent_B also from S0)
B: consolidate             (state now S1)
A: consolidate             (applies rent_A, computed from S0, to S1)
```

A applies rent derived from a state B has already superseded. Each traversal is
atomic; **the epoch is not.**

## Reproduction

`epochs2.rs` models the real synchronisation — root lock per pass, released
between passes — with `RENT_RATE = 0.75` (`AttentionBrokerServer.cc:8`). `GAP`
widens the inter-phase window, which in DAS contains `alienate_tokens` and
`distribute_wages`. 2,048 nodes, 6 epochs, 50 trials:

| inter-phase window | unpatched `match_serialised` | with the patch |
|---|---|---|
| GAP = 0 (tightest possible) | 47/50 | **50/50** |
| GAP = 100 | 20/50 | **50/50** |
| GAP = 2000 | **0/50** | **50/50** |

**Frequency scales with the width of the window between passes**, which is why a
short synthetic model understates it and the real four-pass epoch will not.

We report `match_serialised` rather than a count of distinct outcomes: the
distinct count varies with core count, allocator timing and N, and is not a
stable statistic. Below roughly N≈2048 the epoch completes before the next
thread starts and nothing overlaps at all.

**Two controls.** A global lock around the epoch restores 50/50 — and since all
epochs here are identical, ordering cannot matter, which isolates the cause as
*interleaving* rather than order. And an integer (Q32.32) version of the same
model also diverges, confirming this is not a rounding-order artefact.

## Why it matters beyond reproducibility

Importance is not a routing hint. It drives consolidation and forgetting — what
the atomspace retains. An importance value that depends on gRPC thread
scheduling means two brokers fed identical stimulus histories diverge in what
they remember.

## Fix — patch attached (`01-epoch-mutex.patch`)

**Restoring the async enqueue does not fix this.** We assumed it would, then
checked:

1. `SharedQueue` stores a bare `void*` (`SharedQueue.cc:33-41`) and the worker
   casts it back to `dasproto::HandleCount*` (`WorkerThreads.cc:59`) — a
   gRPC-owned message freed when the handler returns. **Use-after-free**, which
   is very likely why these three lines were commented out.
2. It would not help regardless. `WORKER_THREADS_COUNT = 10`
   (`AttentionBrokerServer.h:58`), and `RequestSelector` gives the five
   even-numbered threads the stimulus queue (`RequestSelector.cc:24,46-48`), each
   calling `spread_stimuli` on the shared network. **The async path is more
   concurrent, not less.**

The patch adds a **per-network `HebbianNetwork::epoch_mutex`**, held across
`spread_stimuli`, `correlation` and `asymmetric_correlation` — the three
inline-dispatched entry points that mutate importance. Per network rather than
global, so distinct contexts (`select_hebbian_network`) still run in parallel.
No entry point calls another and nothing re-enters, so there is no deadlock path,
and the epoch is already `O(nodes)` so complexity is unchanged.

## A more severe bug in the same file, which we did not patch

`AttentionBrokerServer.h:213` is `unordered_map<string, HebbianNetwork*> hebbian_network;`
with **no mutex anywhere in the class**, and `select_hebbian_network`
(`:377-380`) does `this->hebbian_network[context] = network;` from every
concurrent handler. Concurrent `operator[]` insertion is a rehash race — a crash
or a silently lost network, not merely a wrong number. This is strictly worse
than the issue above and wants its own fix.

Also unsynchronised: `network->largest_arity` is read at `StimulusSpreader.cc:167`
while `add_asymmetric_edge` writes it under `largest_arity_mutex`
(`HebbianNetwork.cc:57-61`), and the static `RENT_RATE` / `SPREADING_RATE_*` are
written by `set_parameters` while epochs read them.

## Your own test suite asserts the property this breaks

`src/tests/cpp/stimulus_spreader_test.cc:150-236` reimplements the algorithm
arithmetically and asserts each node's importance against a closed-form
expectation to within `1e-3`. **DAS's test suite already treats importance as
exactly determined by the stimulus sequence** — which is the property concurrent
epochs violate.

## Optional hardening, not required for the above
A fixed-point (Q32.32) importance type makes the broker immune to compiler
flags, which matters if the network is ever replicated across heterogeneous
hardware. **This is not needed to fix the bug above** and we flag it only
because we built it: `ecan.rs` here is a reference implementation.

We initially claimed the `double` arithmetic could not diverge across platforms
via FMA contraction. **That was wrong**, and wrong because our line list omitted
the one contractable expression. `StimulusSpreader.cc:74-75` is:

```cpp
ImportanceType spreading_rate = data->spreading_rate_lowerbound +
                                (data->spreading_rate_range_size * arity_ratio);
```

an `a + b*c`. Bazel's `compilation_mode=opt` is `-O2` and `src/.bazelrc` sets no
FP flags, so clang's default `-ffp-contract=on` applies: aarch64 emits `fmadd`,
baseline x86-64 emits `mulsd` + `addsd`. An ARM node and an x86-64 node compute
different `spreading_rate`.

It is numerically inert **only while** `SPREADING_RATE_LOWERBOUND == UPPERBOUND`
(both default to 0.10, so `range_size == 0.0`). A client calling `set_parameters`
with different bounds makes it live. Note your own test computes
`lb + (arity_ratio * (ub - lb))` with a `1e-3` tolerance, so it would not catch
this either.
