# Attacking the three descopes — C1–C5

All three descopes were proposed and then verified by their proposer. That is the
closed loop that produced the multitrie misdiagnosis and the stale-citation
error. These are the named falsifiers.

## C1 — the self-reported binary hash. **Resolved: it is a matching hint, not a security control.**

The worry: build-enforcement works only if the verifier knows which binary ran,
and the envelope's hash is self-reported — the exact mechanism marked INVALID in
S62 claim D ("`backend_class` is self-reported and reintroduces the trust
assumption").

**It is not the same mechanism, and the difference is quorum.**

Under S62's design the backend label *was* the correctness argument: report your
class, and the verifier trusts the result. Nothing detects a lie.

Under quorum-majority the hash proves nothing and is not asked to. A device that
reports an approved build and runs a different one **produces a different
result** — a banned op returns a value where honest devices deterministically
return "unregistered symbol" — and loses 2-of-3. The lie is caught by
*disagreement*, not by attestation.

So the hash selects replicas likely to agree. Its failure mode is a **failed
match**, not an accepted wrong answer:

| | S62 claim D | build-enforced ban list under quorum |
|---|---|---|
| what the hash asserts | this result is correct | this replica should agree with those replicas |
| a liar produces | an accepted wrong answer | a minority vote |
| detection | none | disagreement |

**The differentiator survives**, and for the reason already stated: attestation
carries *independence*, not correctness. C1 would be fatal to a design where the
hash is the enforcement. It is not fatal to one where the hash is routing.

**Residual, and it is real:** if all three replicas run the same unapproved
build, quorum agrees on a wrong answer. That is C4, not C1.

## C4 — Sybil cost against quorum-3. **Refuted at realistic adversary sizes.**

Minimum adversary share to control 2-of-3 at even odds, random assignment
without replacement:

| fleet N | adversary m | P(≥2 of 3) | share |
|---|---|---|---|
| 100 | 50 | 0.500 | **50%** |
| 1,000 | 500 | 0.500 | **50%** |
| 10,000 | 5,000 | 0.500 | **50%** |

**Independent of N — the classic majority threshold.** Small adversaries win a
negligible slice:

```
N=1,000   m=10   (1%)  -> 0.0269% of jobs
N=1,000   m=50   (5%)  -> 0.7121% of jobs
N=10,000  m=100  (1%)  -> 0.0295% of jobs
```

So quorum-majority is not theatre, and `PORT_PLAN`'s commit/reveal seal stays
superseded.

**But the assumption is load-bearing and our design violates it.** This is
*random* assignment. Wedge #2 is a **locality-aware matcher** that deliberately
biases assignment toward devices already holding the shard. An adversary holding
a **rare shard** faces a far smaller effective N for that shard's quorums and can
dominate them at a fraction of 50% of the fleet.

> **Corrected claim: quorum-3 costs 50% of the *effective candidate pool*, and
> locality shrinks that pool per shard.** The seal is superseded for the uniform
> case and **not** for rare shards. Mitigations — a minimum replication factor
> per shard, or forcing one replica from outside the locality set — are
> unpriced.

That is a sharper result than the one the descope claimed, and it is the first
concrete argument for keeping replication *breadth* rather than just depth.

## C2, C3 — gated, not skipped
Both are throughput measurements. `quiet.sh` refuses: 11 containers up and a
compiler in the top 3. Per A10 they wait for a quiet machine rather than being
taken dirty.

- **C2**: re-derive per-device supply without descending from S32's INVALID
  projection — measured, background cpuset, sustained not burst. `RISKS.md:218`
  currently cites 2.87 jobs/s, which is `28,726 / 10,000`, and 28,726 is marked
  INVALID.
- **C3**: re-run packed popcount pinned to `0,1,4,5`. Prediction on record:
  marginal cost roughly doubles from ~0.05 ms and "1.2× short" becomes ~2.4×
  short — and the descope survives anyway, because the ladder argument (no SDK,
  no delegate, no scale pinning, no QNN licence, no requantisation assumption)
  is independent of throughput.

## C5 — attacking A12 itself. **Partly conceded.**
The charge: A12 compares a *measured* removal cost against an *unmeasured*
measurement cost, so it is structurally biased toward deletion, and three
descopes in one evening is a smell.

Conceded on the bias — the asymmetry is real and A12 should carry it. What it
does not concede: in all three cases the *replacement* was already measured
(CPU `asimddp`+`i8mm`; S57's byte-identical results; unregistered-means-unreachable),
not merely assumed. A12 is safe when the replacement is measured and dangerous
when it is not, and it did not say so.

The named candidate for a wrong removal is the zkVM descope, because it deleted
the only mechanism whose cost is constant in the work proved, on the strength of
C2's number. **C2 is gated, so that charge is currently unanswered** — and it
should be read as open, not as survived.


---

# S69 and S70 broken — 2026-08-17

Both were proposed and self-verified by me. Both are RED.

## 1. "Two independent constraints agreeing" was manufactured
S70 read S61's "plateaus at ~3×" as an operating point. **S61 says the opposite**
(`S61/RESULT.md:84-86`): *"Adding users past coverage ≈ 5 buys almost no locality
and costs hot-spotting."* Re-running S61's own `fleetsim.py`:

| coverage | gain | load imbalance |
|---|---|---|
| 6 | 2.76× | 2.46 |
| 100 | 3.09× | **32.14** |

Coverage 6 → 100 buys **+12% locality for 13× worse hot-spotting**, closing on
the 102× pathology S61 flags as the design's failure mode. **The constraints
point in opposite directions**, and I picked the point that maximises the cost
S61 was warning about.

Worse: **coverage is not a sufficient statistic.** S61's own axes give 5.46× and
3.28× at the *same* coverage 20 — so S61's conclusion 4 is falsified by S61's own
tables.

## 2. The demand proxy measured the wrong axis, and the answer swings 400×
Predicate frequency is not shard demand. Under S52's clustering the hottest
predicate (15,989 triples) becomes **59 shards**, not one hot shard. And
**S52's own query generator samples uniformly over triples** (`realkg.c:170`),
so the only query distribution ever measured here implies **flat** shard demand
(max/median **1.04**).

Coverage needed for min-pool ≥ R=25, by demand model: **2R** (S52 measured) to
**780R** (object-degree weighted). My α=0.8 was a two-point fit on the wrong
quantity.

## 3. `4R` is circular and refuted by its own table
Both "free" rows had coverage 100 and R 25 — and 100 = 4×25 **by construction**.
R was never varied against coverage. My own 236 MB row raises coverage 10 → 28.5
and meets the floor at **1.14R**.

**The real constraint is the feasibility bound `N·C/S ≥ R`** — you cannot place
`R·S` replicas into `N·C` slots. The coverage-10 row is not "expensive", it is
*arithmetically impossible* at C=10; the 236 MB **is** the C increase,
mislabelled as a marginal cost.

And B3 reports a **mean** placement cost while S69's threat model is about the
**minimum**. "0 MB/device" coexists with 4.5–10.8% of shards below the floor,
which is exactly the set an adversary targets.

## 4. "~33% more shard traffic" is wrong by three orders of magnitude
S34's 4,500-query amortisation assumes **residency**. A fleet-drawn replica has
none — it fetches 12.8 MB to serve one job on a shard it will never be drawn for
again.

```
resident replica   12.8 MB / 4,500 =  2.9 KB/job
global replica                       12.8 MB/job     4,500x
quorum: 8.7 KB/job  ->  12.81 MB/job                ~1,500x
```
Fleet-wide at the 17 jobs/s ceiling: **218 MB/s sustained ingress, 18.8 TB/day**,
on a fleet gated to `NetworkType.UNMETERED`. The trade is not "give back part of
the locality win" — it is give back all of it and 500× more.

## 5. The mitigation is backwards, and duty cycle kills it
A globally-drawn device needs **no shard residency**, so a global-only device is
the adversary's *cheapest* device. My mitigation shifts weight onto the cheap
variable.

And `R` is a **residency** floor while the draw is over **online** devices.
Honest duty is 0.05–0.25 (charge-time); an adversary runs at 1.0:

| R | honest duty | adversary devices | P(2-of-3 local) |
|---|---|---|---|
| 25 | 0.25 | 5 | **0.424** |
| 25 | 0.05 | 5 | **1.000** |

**Five always-on devices beat an R=25 shard.** My "~72% of the pool" was computed
against a pool that never exists at run time. And my caveat — *"assumes an
adversary who cannot bias the global draw"* — is exactly the assumption that
fails: **staying online is biasing the global draw.**

## 6. I mis-described my own mechanism in the other direction
Breadth decays as ~`(A/k)²` — **quadratic in the hypergeometric, linear in cost.**
Calling it "weak, linear" was wrong, and it makes finding 5 the dominant term.

## 7. `min pool = 0` is a category error
S8 establishes an authoritative origin: *"the device agent must talk to a desktop
shard host that fronts the bus"* (`S8/RESULT.md:61`), and M1.5 calls the phone
side an **LRU cache**. Zero phone replicas is a 100% miss rate against the shard
host, not a lost object. It remains a real Sybil and shard-host-load concern —
neither of which is what I claimed.

## 8. Process failure: neither spike shipped code
Both are `RESULT.md` only. No simulator, no seed, no artefact, no controls —
against S61, which ships `fleetsim.py`, JSON, a log, five seeds and four controls
"all capable of failing". **LEDGER rules 6 and 7 both unmet.** The reviewer's
reconstructions landed on my numbers, so the arithmetic was real; nothing in the
repo let them know that without rebuilding it.

## What survives
> **`N·C/S ≥ R` is a hard feasibility bound. Any multiplier above 1 is a function
> of shard demand, which is UNMEASURED** — the predicate histogram is the wrong
> quantity, and the only measured query distribution implies a nearly flat one.
> **No coverage target can be set until shard demand under a real query mix is
> measured.** And coverage 100 is unadoptable regardless: S61's simulator puts
> load imbalance at 32× there.
