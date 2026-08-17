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
