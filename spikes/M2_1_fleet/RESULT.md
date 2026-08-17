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

## CORRECTED — the falsifier fired, and the corrected law is worse

I claimed pure locality "drives coverage to ~2.91, which is precisely Q1's worst
measured case (72% capture at honest pool 3)". I stated the falsifier — stalling
at ~3 could be `k=3` in disguise — and then marked it *not yet run*. It takes
thirty seconds. Run, fleet 24, k in {3,5,7}:

| k | policy | coverage | hot-shard coverage | imbalance |
|---|---|---|---|---|
| 3 | locality_pure | 3.00 | **3.00** | 27.3x |
| 5 | locality_pure | 4.77 | **5.00** | 20.2x |
| 7 | locality_pure | 7.00 | **7.00** | 22.9x |
| 3 | locality_capped | 4.35 | **7.38** | 1.13x |
| 5 | locality_capped | 6.74 | **10.38** | 1.13x |
| 7 | locality_capped | 9.11 | **13.50** | 1.07x |

**Coverage stalls at exactly `k`.** The Q1 link at 3 was a coincidence of both
numbers being 3, and my claim as written is refuted.

The law it refutes into is sharper and the consequence is worse:

> **Pure locality pins holders-per-shard to exactly the quorum size.**
> There is no redundancy beyond the quorum itself — every job on a hot shard
> goes to the same `k` devices, forever.

Q1's capture arithmetic assumes an honest pool *larger* than the quorum, and
computes the chance an attacker wins enough seats. Under pure locality **the
pool IS the quorum**. An operator holding those `k` devices does not capture
72% of that shard's jobs; it captures **all of them**, and no amount of fleet
growth changes it, because a non-holder never becomes resident.

The cap restores a pool larger than the quorum, and does so most where it
matters: hot-shard coverage **7.38 at k=3**, against 3.00 uncapped — 2.5x the
redundancy exactly on the shards an attacker would target.

**The mechanism is the ratchet, not the number.** That is what survives, and
stating the falsifier is what got it.

## The cap fixes the dynamic, not just the snapshot
`maxSkew=1` holds imbalance at 1.06–1.15x across all twelve rounds **and** keeps
coverage climbing (3.98 and rising), while still converging to near-zero
transfer (3 fetches in round 11 against random's 23). It buys out of the ratchet
as well as the imbalance.

**Design consequence:** a locality policy needs a spread floor as a
*safety* property, not a performance tuning knob. Uncapped locality is not a
scheduler that occasionally imbalances — it is a scheduler that walks itself
into the fleet configuration its own verification model is weakest against.

## Both remaining falsifiers run — and they separate two phenomena I had fused

### A. Does the ratchet need skewed demand? **No.**

| zipf | locality_pure coverage | hot cov | imbalance |
|---|---|---|---|
| 0.0 (uniform) | **3.00** | 3.00 | 3.35x |
| 0.4 | **3.00** | 3.00 | 6.30x |
| 0.7 | **3.00** | 3.00 | 5.00x |
| 1.0 | **3.00** | 3.00 | 6.91x |
| 1.4 | 2.91 | 3.00 | 10.30x |

Coverage pins to exactly `k` at **every** skew including uniform. Only the
**imbalance** is skew-dependent.

**This corrects §1 of this document.** §1 concluded "under uniform demand
locality has no cost" — that was true of *imbalance* and I generalised it to
locality. The coverage ratchet was present at zipf 0 the whole time; §1 did not
measure coverage, so it could not see it.

So `pool == quorum` is **not a skewed-demand pathology. It is inherent to pure
locality routing**, and the most benign workload does not avoid it.

### B. Does it need dense per-device load? **No — and it gets far worse.**

| fleet | jobs/device/round | coverage | hot cov | imbalance |
|---|---|---|---|---|
| 8 | 74.2 | 3.00 | 3.00 | 11.5x |
| 16 | 37.1 | 2.91 | 3.00 | 10.3x |
| 64 | 9.3 | 2.86 | 3.00 | **89.0x** |
| 198 | 3.0 | 3.00 | 3.00 | **79.0x** |

Coverage pins at `k` across a 25x range of load density. Imbalance **explodes**
at large fleets — 89x at fleet 64 — because most devices never become resident
at all and the few that do absorb everything.

**Fleet 16 was the flattering case.** A real fleet is thousands of devices with
a handful of jobs each, which is the right-hand end of this table.

The cap holds up but degrades: at fleet 198 it gives coverage 6.86, hot-shard
coverage **23.88**, imbalance 6.0x. Better redundancy than uncapped by 8x, and
6x imbalance is no longer negligible — `maxSkew=1` is tuned for fleet 16 and
needs re-tuning per fleet size.

### What this leaves standing
- **`pool == quorum` under pure locality**: confirmed at 5 skews and 4 fleet
  sizes. Skew-independent, density-independent.
- **imbalance**: skew-dependent AND fleet-size-dependent, up to 89x.
- **the cap**: fixes both at small fleets, fixes redundancy and only partly
  fixes imbalance at large ones.

### Still not falsified
Every run above is 12 rounds. Nothing shows the ratchet is stable at 100+
rounds, or what happens when devices join and leave — churn is the obvious
escape hatch from a ratchet and it is entirely unmodelled.
