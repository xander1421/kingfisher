# Q1 — the join: fleet model × canonical envelope × majority-of-quorum

**Verdict: GREEN, and it puts a number on C4 for the first time. Five adversarial devices camped on a rare shard get wrong results accepted 72% of the time against a 3-device honest pool, 0.5% against 100. Both controls fire. Ships code, seed, and a fixed x-axis.**

S61 modelled *where a job lands* (Device with `lru`/`cap`/`jobs`, Zipf demand,
duty, LRU, k-candidate matcher). S49's `verifier2.py` modelled *whether an
envelope is accepted* (`Contract`/`Job`/`Envelope`, `canonicalise`, `CANON`).
**Neither knew the other existed**, so nothing in the tree could answer C4 — the
rare-shard Sybil attack, which went live again when W1 was invalidated.

Artefacts: `quorumsim.py` (stdlib, seed 20260817), `quorumsim.json`.

## Design constraint that made it runnable today
The host gate refuses (11 containers, another project's). So this reports
**counts and outcomes only, never a duration** — the property that let S61 run on
a contended machine. Execution speed is a **parameter**: S71's measured 2.83 /
11.17 jobs/s are inputs, exactly as `S32/tps.py` treats device constants. Nothing
here simulates how fast a device is.

## What a fake device is now
S61's `Device` gains three fields and a behaviour:
```
(idx, lru, cap, jobs)                  ← S61
  + operator_id    # Sybil grouping. DuplicateSourceInMatch is per-SOURCE;
                   #   an operator running many sources defeats it
  + honest: bool
  + execute(job) -> digest             # honest: canonical (S49 length-prefixed)
                                       # dishonest: echo a confederate's digest
```
Adjudication is `GUARDRAILS` C5 verbatim — **majority of a quorum**, from BOINC's
`sample_bitwise_validator.cc:17-18`, not pairwise agreement.

## Measured — one adversarial operator, 5 devices, camped on shard 0

| honest pool | total pool | adversarial | seats captured | **wrong results accepted** |
|---|---|---|---|---|
| 3 | 8 | 5 | 72.0% | **72.0%** |
| 5 | 10 | 5 | 49.9% | **49.9%** |
| 10 | 15 | 5 | 23.9% | 23.9% |
| 25 | 30 | 5 | 6.0% | 6.0% |
| 50 | 55 | 5 | 2.3% | 2.3% |
| 100 | 105 | 5 | 0.5% | **0.5%** |

**Captured seats and accepted-wrong track exactly**, because colluders under one
operator echo a single digest — so capturing the majority *is* getting the wrong
answer accepted. That is the failure `DuplicateSourceInMatch` does not prevent:
it rejects one **source** twice, not one **operator** twice.

## The instrument defect I caught, and how
First run was **non-monotone**: 23.9% at "pool 10" against 18.1% at "pool 5".
The `pool` column showed why — my sizing loop only *added* honest holders, so
random LRU admissions inflated it and the x-axis was not the quantity it named.
Fixed to evict as well as admit, with an assertion. The corrected curve is
monotone and the pool-3 figure moved **33.8% → 72.0%**.

Recording it because the wrong number was the *reassuring* one.

## Controls, each with its failing input (D6)
| control | fails if | result |
|---|---|---|
| all-honest fleet always agrees | any wrong verdict or any failed majority in an honest fleet | **PASS** (0 wrong, 0 no-majority over 500 rounds) |
| one operator captures a rare shard | an operator owning most of a 3-device pool does *not* get wrong results accepted | **PASS** (>50%) |

Both fire, which is the property W1 lacked.

## What this settles and what it does not
**Settles:** C4 is real and quantified. Quorum-3 alone does not resist a
multi-device operator on a small pool. Honest pool size is the whole defence, and
it must exceed ~25 before capture drops below 10% against just five adversarial
devices.

**Does not settle:** pool size is a function of shard demand `Δ`, which D3
declares unmeasured and unmeasurable from inside this workspace. So this gives
the *shape* of the requirement, not a coverage target — deliberately, per D3.

## Caveats
- Synthetic fleet. This workspace has been burned three times by synthetic
  magnitudes: S52 took shaping from 54× to 4–5× on a real KG, and S61 is grade D
  for the same reason. **Q1 answers a combinatorial question, where simulation is
  the right instrument, and cannot say whether two real devices agree.**
- One adversary model (echo-a-confederate). A smarter adversary that sometimes
  reports honestly to build reputation is not modelled.
- No stake. D1+ makes seat draw stake-weighted; this draws uniformly from the
  pool, so it is the *no-stake* case — a lower bound on the defence.
