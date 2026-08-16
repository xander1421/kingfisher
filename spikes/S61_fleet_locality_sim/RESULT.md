# S61 — fleet scaling / locality simulation *(renumbered from S55; the directory was renamed to resolve a collision with `S55_mork_inproc` and this title lagged behind)*

**Verdict: GREEN for locality-aware matching, and RED for the naive version of it.**
Locality matching is worth **2.8× fewer shard fetches** at the realistic operating
point and up to 10.4× at full duty — but the configuration where it pays most is
also the one where it piles **102× the mean load** onto single devices. Churn turns
out to be the load balancer, which means the charge-time premise is accidentally
protecting a design nobody had checked.

**GRADE D. This is a simulation.** Per `out/LEDGER.md`'s scale, D is the weakest
grade in the workspace and every claim below carries it. It simulates the
*coordination layer* — matcher, caches, churn — which is server software we would
write and which has **never been measured at all** (`GAP_MATRIX` row 18,
`PROPOSAL_DRAFT` wedge #2: *"no elder matches on which data a node already
holds"*). It does not simulate silicon. Every device-side constant is a parameter,
not an output.

Code: `fleetsim.py` (stdlib only, ~230 lines). Output: `fleetsim.json`,
`S55.log`. Contention declared: `load averages: 2.67 2.31 2.29`, WindowServer
12.6%, Chrome 6.6% — irrelevant here because the reported unit is **fetches per
job**, an invariant of the policy, not a wall clock (LEDGER rule 1).

## Why this and not more fleet arithmetic

`spikes/S32_fleet_capacity/tps.py` already closes the **N** axis:
`N × duty × (steps/s ÷ job_steps) ÷ (replication + audit)`. That is arithmetic
from measured constants and it is honest about being so. It has no notion of a
shard, a cache, or locality — so it cannot answer the question the architecture
actually rests on. This spike adds the **size** axis and the policy comparison.

## Method

- `S` shards, Zipf(a) query demand, `N` devices each with an LRU cache of `C`
  shards, a device online with probability `duty` per job.
- Matcher samples **k=8** candidates (power-of-k-choices — a matcher samples
  bids, it does not poll the fleet). Both policies get the same k, so the
  comparison is not confounded by candidate-set size.
- `random` = the null: least-loaded of 8 online draws.
- `locality` = prefer devices advertising the CID (a holder index), fall back to
  the null when no holder is online.
- **The matcher never sees the query distribution or the ground truth** (LEDGER
  rule 5). It reads advertised cached CIDs, which is what a real bid carries.
- First 30% of jobs discarded as warmup; stated, not hidden.

### Controls, and one that fired on me

`demo()` runs four controls, all capable of failing:

1. null fires at the bottom — cache=1, uniform demand: >0.95 fetches/job
2. null fires at the top — cache ≥ graph: <0.001 fetches/job
3. **closed-form plausibility gate** — 1 device, uniform demand, LRU cache C of
   S shards must give hit rate ≈ C/S. Sim lands within 5 points.
4. ordering — locality is never worse than random on hit rate

Control 1 **failed on first run** at 0.62 for the locality policy. The control was
wrong, not the sim: I had set Zipf 1.0, where a 1-slot cache still holds the hot
head, so "everything misses" is false by construction. Fixed to uniform demand.
Noted here because LEDGER rule 7 exists precisely for this and four controls in
this workspace were silently broken before anyone checked one.

## AXIS 1 — graph size (1,000 devices, C=20, duty 0.25, Zipf 1.0)

| shards | coverage `NC/S` | fetch/job random | fetch/job locality | gain |
|---|---|---|---|---|
| 100 | 200.0 | 0.4500 | 0.0833 | **5.40×** |
| 1,000 | 20.0 | 0.6875 | 0.1259 | 5.46× |
| 10,000 | 2.0 | 0.7947 | 0.2864 | **2.78×** |
| 30,000 | 0.667 | 0.8289 | 0.3681 | 2.25× |
| 100,000 | 0.2 | 0.8561 | 0.4407 | 1.94× |

Gain decays smoothly as the graph outgrows total fleet cache. **No cliff** — the
knee people expect at coverage = 1 does not exist, because Zipf demand means the
hot head stays resident however large the tail gets.

## AXIS 2 — fleet size (10,000 shards, C=20, duty 0.25, Zipf 1.0)

| devices | coverage | gain | **load imbalance** |
|---|---|---|---|
| 100 | 0.2 | 1.62× | 1.01 |
| 1,000 | 2.0 | 2.78× | 1.31 |
| 3,000 | 6.0 | 2.99× | 2.14 |
| 10,000 | 20.0 | 3.28× | **5.48** |

**Gain plateaus at ~3× while imbalance grows without bound.** Adding users past
coverage ≈ 5 buys almost no locality and costs hot-spotting. The scaling variable
is `N·C/S`, not `N`.

## AXIS 3 — query skew (1,000 devices, 10,000 shards)

| Zipf a | hit random | hit locality | fetch/job r | fetch/job l | gain |
|---|---|---|---|---|---|
| 0.0 (uniform) | 0.0017 | 0.4003 | 0.9983 | 0.5997 | 1.66× |
| 1.0 | 0.2053 | 0.7136 | 0.7947 | 0.2864 | 2.78× |
| 1.5 | 0.7245 | 0.9007 | 0.2755 | 0.0993 | 2.78× |

Note the trap: at uniform demand locality improves *hit rate* 235× (0.0017 →
0.40) and *fetches per job* only 1.66×. **Hit-rate ratios are the misleading
statistic** — fetch reduction is bounded by `1/(1−hit)`. Report fetches/job.

## AXIS 4 — the finding: churn is a load balancer

1,000 devices, 10,000 shards, Zipf 1.0. **5 seeds**, because one draw is not a
measurement (LEDGER rule 6):

| duty | gain (mean ± sd) | load imbalance (mean, min–max) |
|---|---|---|
| 0.05 | 1.27 ± 0.005 | 1.47 (1.4–1.5) |
| 0.25 | 2.80 ± 0.034 | 1.30 (1.3–1.3) |
| 0.50 | 4.55 ± 0.053 | 6.48 (5.8–7.1) |
| **1.00** | **10.31 ± 0.123** | **102.43 (100.5–103.9)** |

Locality gain and hot-spotting rise together, and neither is subtle. At full duty
one device absorbs **10% of all fleet jobs** — it cached the Zipf head, it is
always online, so it is always the best holder, and least-loaded tie-breaking
inside the holder set cannot escape a holder set of size ~1.

**The charge-time premise is load-bearing in a way nobody claimed.** Devices being
mostly offline (duty 0.05–0.25) is what keeps imbalance at 1.3–1.5. A design that
succeeded at getting devices online more would make its own matcher pathological.

## Consequences

1. **Wedge #2 has its first number.** `PROPOSAL_DRAFT` asserts locality matching
   matters and cites the dead 26→353 GOP/s figure. It can now cite **2.8× fewer
   shard fetches at coverage 2.0, duty 0.25**, five seeds, sd 0.034. That is a
   simulation and must be labelled one, but it is better than a retracted
   measurement.
2. **The matcher needs a load cap, and it is cheap.** Either a per-device
   in-flight ceiling or ε-greedy (ignore locality with probability ε). Unmeasured
   — the obvious next spike, and it is a two-line change to `fleetsim.py`.
3. **`ShardManifest` needs an advertised-CID list to be usable at all.**
   `PORT_PLAN` M3.1 already proposes `prefer_cached_cids`. This is the first
   evidence of what it is worth.
4. **Stop sizing the fleet by N.** The planning variable is `N·C/S`. At C=20 and
   a 100k-shard graph, 1,000 devices and 10,000 devices differ by 18% in fetch
   traffic and 4× in hot-spotting.

## What this does NOT show — stated plainly

- **Synthetic Zipf demand.** S52 is the cautionary precedent in this exact
  workspace: synthetic data gave 54×, FB15k-237 gave 4–5×, and the collapse was
  an artefact. **Treat every magnitude here as untrustworthy and only the
  directions as evidence** until this is re-run against a real query trace.
  Doing so is mechanical — replace `zipf_weights` with the FB15k-237 predicate
  histogram S52 already built.
- **No time.** Fetch cost, compute cost, and queueing are absent; the model
  counts fetches, not seconds. It therefore cannot say whether 2.8× fewer fetches
  is worth anything until someone measures what a fetch costs on a metered phone
  connection. That number does not exist.
- **No replication or audit.** Every job runs once. Real placement must satisfy
  `exclude_device_groups` and a replication factor, both of which fight locality
  — the second replica must *not* be the device that already has the shard, or
  replication proves nothing.
- **LRU is assumed.** No eviction policy was compared. LRU under Zipf is close to
  optimal, so this is likely generous to both arms equally.
- **Cache capacity is uniform** at 20 shards for every device. Real fleets are
  wildly heterogeneous.

## Reproduce

```sh
cd spikes/S55_fleet_locality_sim
python3 -c 'import fleetsim; fleetsim.demo()'    # 4 controls, all can fail
python3 fleetsim.py 60000                        # full sweep, ~7 s, writes fleetsim.json
```
