# S70 — the shard-pool tail, and the coverage floor it forces

**Verdict: GREEN, and it converts S69's `R ≥ 25` from an assumption into a condition on one parameter. Demand-driven caching leaves most shards with tiny pools; enforcing a replication floor is free above a coverage threshold and unaffordable below it. The threshold is `N·C/S ≳ 4R`.**

S69 proposed `R ≥ 25` plus one fleet-wide replica, and flagged its own soft spot:
*"'rare shard' is not quantified against any real distribution… the tail is what
matters and has not been measured."* This measures it. Simulation and arithmetic
only, valid while `quiet.sh` refuses.

## Demand skew, fitted to measured data
S52 measured FB15k-237: 237 predicates, **max 15,989 against median 373**, top 1%
of objects holding 28% of triples. Fitting Zipf to the rank-1/rank-118 ratio
(42.9 measured) gives **α = 0.8** (45.4 predicted). Devices cache *C* shards each,
drawn by demand.

## The tail is far worse than `R ≥ 25` assumed

| N | S | C | coverage `N·C/S` | min | p1 | median | max | **% shards below 25** |
|---|---|---|---|---|---|---|---|---|
| 1,000 | 1,000 | 10 | 10 | **0** | 0 | 5 | 507 | **94%** |
| 1,000 | 1,000 | 50 | 50 | 5 | 9 | 27 | 985 | 45% |
| 10,000 | 1,000 | 10 | 100 | 16 | 20 | 48 | 4,899 | **5%** |
| 10,000 | 10,000 | 10 | 10 | **0** | 0 | 4 | 3,151 | **94%** |
| 10,000 | 10,000 | 50 | 50 | 3 | 7 | 22 | 8,477 | 56% |
| 100,000 | 10,000 | 10 | 100 | 10 | 17 | 42 | 31,526 | **11%** |

**A minimum of 0 appears twice.** Some shards are cached by nobody — an
*availability* failure before it is a security one, and neither S61 nor S69
surfaced it.

## Enforcing the floor is free above a coverage threshold, ruinous below

Forced placements needed to bring every shard to *R*, and the storage that costs
each device (a device already caches C=10 shards = 128 MB):

| N | S | C | coverage | R=3 | R=10 | **R=25** |
|---|---|---|---|---|---|---|
| 10,000 | 1,000 | 10 | 100 | 0 MB | 0 MB | **0 MB** |
| 10,000 | 10,000 | 10 | 10 | 5 MB | 63 MB | **236 MB** |
| 100,000 | 10,000 | 10 | 100 | 0 MB | 0 MB | **1 MB** |

At coverage 10, enforcing `R = 25` costs **18.5 extra shards per device — 236 MB,
nearly 3× what the device already holds.** At coverage 100 it costs nothing,
because demand-driven caching has already satisfied the floor for all but the
deepest tail.

## The design constraint

> **`N·C/S ≳ 4R`.** Mean coverage must exceed the replication floor by roughly
> 4×, or the floor has to be bought with forced replication of shards nobody
> wants.

For `R = 25` that is **coverage ≈ 100**.

### And it reconciles with S61 rather than fighting it
S61 measured locality gain tracking `coverage = N·C/S`, plateauing at ~3× while
imbalance grows without bound. So there is an **upper** bound on useful coverage
from diminishing locality returns and a **lower** bound from Sybil resistance —
and they are compatible. **Coverage ≈ 100 sits at the locality plateau *and*
satisfies the Sybil floor for free.** That is the operating point, and it is the
first parameter in this project derived from two independent constraints
agreeing.

## What this changes in S69
`R ≥ 25` is not a free parameter to assert. It is affordable **only at coverage
≳ 100**, and the matcher must either hold coverage there or pay explicitly. The
mitigation stands; its precondition is now named.

## Caveats
- Zipf α = 0.8 is fitted to **one** knowledge graph's predicate distribution and
  used as a proxy for *shard* demand, which is a different quantity. Shard demand
  under a real query mix is unmeasured.
- Uniform independent caching per device. Real caches correlate — devices in one
  region see similar queries — which would make the tail **worse**, not better.
- Ignores eviction, churn, and the LRU behaviour a real cache would have.
- Availability (`min = 0`) is flagged, not addressed. A shard nobody holds is a
  separate problem from a shard too few hold.
