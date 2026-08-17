# M2.1 — locality routing, measured on a real fleet instead of simulated

**S61, S69 and S70 modelled locality and executed nothing. This runs N real
worker processes, each with its own content-addressed cache, and moves real
bytes. S61's predicted locality/imbalance tension is confirmed, quantified, and
then largely removed by a `maxSkew` cap.**

Not simulated: MeTTa evaluation, the shard store, the CIDs, the byte counts,
the quorum comparison (198/198 unanimous in every arm below).
Simulated: the devices are host processes, which is **one failure domain** —
see `M1_8_quorum3/DETECTION_FLOORS.md`. This measures routing, not trust.

## 1. Under uniform demand, locality has no cost — and that is misleading

fleet 16, 66 programs once each, prefill 25%:

| policy | imbalance | transfer saved |
|---|---|---|
| random | 3.17x | — |
| locality_pure | 2.00x | 88.9% |
| locality_lb | 1.27x | 88.9% |

Locality *improves* imbalance here. I nearly published that as "locality
dominates on both axes, S61's tension is not observed".

**It was an artifact of uniform demand.** Each program was dispatched exactly
once, so no shard was hot, so residency could not concentrate load. S61's
imbalance regime is skewed demand and I had measured a different question.

## 2. Under skewed demand the tension is real and large

fleet 16, 198 jobs drawn Zipf over the same 66 shards:

| zipf | locality_pure imbalance | random |
|---|---|---|
| 0.0 (uniform) | 2.00x | 3.17x |
| 0.7 | 2.95x | 1.79x |
| 1.0 | 4.58x | 1.79x |
| **1.4** | **19.33x** | 1.79x |

Transfer saving is roughly flat at **89–96%** across all skews. So locality buys
~95% of transfer for **10.8x worse imbalance** than random at heavy skew. That
is S61's warning, now with numbers.

A least-loaded tiebreak inside the resident set helps and is not enough:
19.33x -> 8.38x, saving unchanged.

## 3. A `maxSkew` cap removes most of the tension

k8s `podtopologyspread` bounds concentration per domain regardless of pool size.
Ported to load: prefer residency, but a device already more than `maxSkew` jobs
above the fleet mean is ineligible however well it matches.

zipf 1.4, fleet 16, 198 jobs, random baseline imbalance 1.79x:

| maxSkew | imbalance | transfer saved |
|---|---|---|
| 0 | 1.03x | 38.9% |
| **1** | **1.06x** | **78.7%** |
| 2 | 1.12x | 77.5% |
| 4 | 1.30x | 86.7% |
| 8 | 1.43x | 86.0% |
| 16 | 2.79x | 89.4% |
| 64 | 6.73x | 91.5% |

**The knee is at maxSkew = 1.** Going 0 -> 1 buys **40 percentage points of
transfer for 0.03x of imbalance**. Going 1 -> 4 buys 8 points for 0.24x. Going
4 -> 64 buys 5 points for 5.4x.

So the operating point is: **better balance than random routing (1.06x vs
1.79x) while saving 79% of transfer bytes.** The tradeoff S61 identified is real
and is cheap to buy out of.

`maxSkew=2` (77.5%) scoring marginally below `maxSkew=1` (78.7%) is
single-seed noise, not a real inversion. Flagged rather than smoothed.

## 4. The cap must never shrink the quorum
If the cap leaves fewer than `k` eligible devices, `choose()` refills from the
ineligible set rather than returning a short list. M1.8c established that a
short quorum is an availability failure and a craftable one; a *scheduling*
policy must not be able to manufacture it.

## Limits
- **One failure domain.** All devices are host processes on one machine, one
  binary. This is a routing measurement; it says nothing about trust,
  independence, or Sybil resistance.
- **Prefill is a stand-in for history.** Devices start holding a random 25% of
  shards. Real residency comes from what a device has previously run, which is
  itself policy-dependent — a feedback loop this does not model.
- **Single seed per point.** The maxSkew curve's shape is clear; individual
  points are not separated from noise.
- **66 shards, all the same size (~2.6 KiB).** Transfer percentages would change
  with the B1 shard sizes (6.41–34.83 MB), where M1.5b showed transfer is
  `63 ms + 37.9 MB/s` rather than a flat rate.

---

# 5. Residency feedback — locality manufactures the conditions for its own capture

`prefill` was a stand-in for history. Real residency comes only from what a
device has previously run, which makes locality a **feedback loop**: holding a
shard wins you jobs on it, which keeps you holding it.

**This section is SIMULATED**, and that is a change from sections 1–4. Twelve
rounds x 198 jobs is 2,376 job-slots; executing them would take hours and the
question is about the routing dynamic, which sections 1–4 already showed matches
real execution. No prefill: residency starts empty and grows only from dispatch.

zipf 1.4, fleet 16, 198 jobs/round, `maxSkew=1`:

| | fetches rd0 -> rd11 | imbalance | **coverage** (holders per shard) |
|---|---|---|---|
| random | 181 -> 23 | ~1.6x | 2.74 -> **11.20** |
| locality_pure | 96 -> **0** | **10–19x, no decay** | 1.45 -> **2.91** |
| locality_capped | 127 -> 3 | **1.06–1.15x** | 1.92 -> **3.98** |

## The imbalance locks in
Pure locality reaches **zero transfer by round 7** — perfect locality — and its
imbalance never decays, because nothing ever makes a non-holder resident. This
is S61's warning as a dynamic rather than a snapshot: the policy is a
ratchet, and one round of skewed demand fixes the assignment permanently.

## The finding I did not expect: coverage is an OUTPUT, not an input
Pure locality drives coverage to **2.91 holders per shard and stalls there**,
while random reaches 11.20. Locality does not merely *perform badly at* low
coverage — **it creates low coverage**.

That closes a loop with Q1. Q1 measured **72% quorum capture at an honest pool
of 3**, and treated pool size as a property of the fleet. It is not: it is a
consequence of the routing policy. **Pure locality routing drives the honest
pool for each shard to ~3, which is precisely Q1's worst measured case.**

So the S69/S70 root cause — verification eligibility coupled to shard residency
— is not just a coupling to be broken. Under locality routing the coupling
*tightens over time on its own*.

## The cap fixes the dynamic, not just the snapshot
`maxSkew=1` holds imbalance at 1.06–1.15x across all twelve rounds **and** keeps
coverage climbing (3.98 and rising), while still converging to near-zero
transfer (3 fetches in round 11 against random's 23). It buys out of the ratchet
as well as the imbalance.

**Design consequence:** a locality policy needs a spread floor as a
*safety* property, not a performance tuning knob. Uncapped locality is not a
scheduler that occasionally imbalances — it is a scheduler that walks itself
into the fleet configuration its own verification model is weakest against.

## What would falsify this
Coverage stalling at ~3 is `k=3` plus a ratchet: exactly the quorum size, which
is suspicious in a way worth stating. If coverage stalls at `k` for k=5 and k=7
too, the mechanism is "locality pins holders at exactly quorum size" and the
Q1 connection is a coincidence of both being 3. **Not yet run.**
