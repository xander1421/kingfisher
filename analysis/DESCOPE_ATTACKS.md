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
