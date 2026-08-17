# S69 — pricing the rare-shard attack C4 opened, and its mitigations

**Verdict: GREEN, and it closes the question with a cheap fix. The rare-shard attack is real and cheap; forcing one of the three replicas to be drawn fleet-wide collapses it. Minimum replication breadth alone does not.**

C4 refuted the Sybil attack for *uniform* assignment — 50% of the fleet to
control 2-of-3, independent of N — then noted our own locality-aware matcher
violates that assumption. This prices the violation. Arithmetic only, so it is
valid while `quiet.sh` refuses.

## 1. Pool size is what matters, and a pool can be tiny

| candidate pool *k* | adversarial devices for P≥0.5 | share of pool |
|---|---|---|
| 3 | **2** | 67% |
| 5 | 3 | 60% |
| 10 | 5 | 50% |
| 50 | 25 | 50% |
| 1,000 | 500 | 50% |

The 50% threshold is preserved — but it is 50% **of the pool holding that
shard**, not of the fleet. **A shard held by three devices costs two devices to
control**, at any fleet size. C4's fleet-wide number was never the binding one
for a locality-aware matcher.

## 2. Minimum replication breadth is a weak mitigation
Forcing every shard onto ≥ *R* devices is linear and leaves the structure intact:

```
R=3  -> 2 adversarial devices     R=25 -> 13
R=5  -> 3                         R=50 -> 25
R=10 -> 5
```

It raises the price and does not change the shape. To make the attack expensive
you would need *R* in the hundreds, which is exactly the replication factor
locality exists to avoid.

## 3. One replica drawn fleet-wide collapses it
Draw two replicas from the locality set and **one uniformly from the fleet**. The
adversary can no longer win 2-of-3 from the pool — they must win **both** local
slots, since the global slot is effectively out of reach at any realistic
adversary share:

| pool *k* | adversary share | P(control), local-only | P(control), 2 local + 1 global |
|---|---|---|---|
| 5 | 60% | 0.700 | **0.300** |
| 10 | 50% | 0.500 | **0.222** |
| 50 | 40% | ~0.31 | **0.156** |

The requirement moves from 2-of-3 to **2-of-2**, so P ≈ *f* ² in the adversary's
pool share rather than ≈ *f*.

### Combined with a modest breadth floor

| *R* | adversary share for P=0.5 | for P=0.01 |
|---|---|---|
| 5 | 80% | 40% |
| 10 | 80% | 20% |
| 25 | 72% | 12% |
| 50 | 72% | **12%** |
| 100 | 71% | **11%** |

**R ≥ 25 plus one fleet-wide replica requires an adversary to hold ~72% of a
shard's pool for even odds, and still ~12% for a 1% chance.** Against 50% of a
possibly-3-device pool unmitigated.

## What this costs
One of three replicas does not hold the shard, so it pays a **cold fetch** —
12.8 MB, amortised over ~4,500 queries (S34). At quorum 3 that is one third of
replicas fetching cold, i.e. roughly a **33% increase in shard traffic**, against
S61's locality gain which plateaus at ~3× anyway.

That is the honest trade: **give back part of the locality win to buy Sybil
resistance on rare shards.** S61 already found locality plateaus at ~3× while
imbalance grows without bound, so the marginal locality being surrendered is the
least valuable part of it.

## Disposition
- `PORT_PLAN` M3.4's commit/reveal seal stays **superseded** — including for rare
  shards, once one replica is drawn fleet-wide.
- The matcher gains two constraints: **minimum replication breadth R ≥ 25**, and
  **one replica of every quorum drawn uniformly from the fleet, not the locality
  set.** Neither exists in Acurast's pallet, which has no locality concept at all
  — so this is in the ADAPT half of that row, not the PORT half.

## Caveats
- Arithmetic, not simulation. Assumes uniform random draw within each set and an
  adversary who can seed itself into a target shard's pool but cannot bias the
  global draw.
- "Rare shard" is not quantified against any real distribution. S61's coverage
  model (`N·C/S`) gives the mean pool size; the *tail* is what matters and has
  not been measured.
- Ignores stake. Acurast's model makes each Sybil device carry collateral, which
  multiplies the cost of all of the above by whatever the stake floor is.
