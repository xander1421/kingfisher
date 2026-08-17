# G12 — iteration is ceremony. Attention is the whole effect.

**Verdict: ITERATION IS CEREMONY.** Every prune rate reaches the same
preservation at the same final graph size. One shot equals twenty-three cycles,
exactly.

```
target 26 of 60 nodes; every arm ends at the same size

    rate  cycles  live  mean preserved
    0.05      23    26            64%
    0.10       9    26            64%
    0.20       4    26            64%
    0.35       2    26            64%
    1.00       1    26            64%     <- one shot
    ctrl       9    26            16%     <- no attention, floor
```

Spread across all rates: **0%**.

## What this removes, and what it leaves standing

G10's headline was *"the loop closes and survives"*. Both halves are true and the
**loop part is decorative.** Running one ECAN epoch on the full graph and cutting
straight to 26 nodes gives an identical result to pruning 5% at a time for 23
cycles.

What survives untouched is the finding that mattered: **64% against a 16% floor**.
The gain is entirely attention, not iteration. G10's oracle comparison stands —
attention still tracks a greedy oracle. It simply does not need to be applied
repeatedly.

## Mechanism, checked rather than inferred

The importance **ranking** is fixed after the first epoch:

```
epoch  ranking-vs-prev   bottom-26 set
    1     IDENTICAL          same
    2     IDENTICAL          same
    ...
    5     IDENTICAL          same
```

Rent is proportional to importance and wages are proportional to stimulus, so
with a **fixed stimulus** the first epoch sets the ordering and every later epoch
scales it uniformly. Pruning selects on order, so no amount of iteration can
change which nodes go.

That makes the result explanatory rather than merely empirical, and it names the
condition under which iteration *would* matter:

> **Iteration earns its place only if the stimulus changes between cycles** —
> a shifting query distribution, new atoms arriving, or importance feeding back
> into what gets queried. With a fixed query set over a static graph, one epoch
> is the whole computation.

None of those were present here. G10 held the query set fixed and added no
atoms, so it was always going to be a one-epoch problem wearing ten cycles.

## Consequence for the architecture

The two-device loop does **not** need to run per cycle. A device can compute
importance once per shard, prune once, and serve queries from the result. That
is cheaper than the design G10 implied and it removes a per-cycle epoch from the
critical path.

The interesting version of the loop is the one with a **moving** stimulus — a
device whose query mix changes as its shard is reshaped. That is untested and it
is where iteration would become load-bearing.

## What this does NOT show

- Not that ECAN is useless. 64% vs 16% is the attention result and it is
  unaffected.
- **Not that iteration never helps** — only that it cannot help when the
  stimulus is constant, which is proved by the ranking invariance rather than
  assumed from the sweep.
- Fixed target of 26 nodes, one graph, 60 nodes, five query classes. A different
  target or a graph with different degree structure was not tried.
- All host-side. G11 established the epoch is cross-device identical; this adds
  nothing on that axis.

## Reproduce

```sh
cd spikes/G12_prune_rate && python3 rate.py     # ~2m20s, 5 rates + control
```
