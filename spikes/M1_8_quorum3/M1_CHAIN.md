# M1 — the whole chain, one run, with provenance

**CORRECTED. The headline was 66/66 UNANIMOUS; under a failure-domain check it
is INSUFFICIENT_DOMAINS.** The chain runs end to end and every link is measured
— but the quorum that validated it had **2 independent failure domains, not 3**,
and the writeup counted seats.

```
admission gate  ->  CID shard store  ->  session preflight
                ->  phone + 2 host workers  ->  canon_alpha  ->  quorum-3
```

## The run
```
gate:       cpu_busy 0.6%, thermal 36600m, battery status=5 level=100
admission:  REFUSED 1 program on the nondeterminism ban surface
store:      66 programs -> 66 distinct CIDs, 173.2 KiB
dispatch:   66 jobs in 5 work sessions, 0 preflight refusals
alpha:      0 envelopes non-ground -> 0 fell back to canon
transfer:   173.2 KiB to device (cold cache)
result:     UNANIMOUS=66, accepted 66/66
```

## Provenance
`provenance.json`, written before the write-up:

| | |
|---|---|
| `elders/hyperon-experimental` | `3f76dc460da6`, **DIRTY 5 files**, diff `2a38d23f5150` |
| device | `SM-S938B`, `BP4A.251205.006`, `arm64-v8a` |
| artifacts | sha256 of both `fuelrun` binaries |

The dirty tree is **recorded, not silent** — it carries our three unfiled
nondeterminism patches, and `allow_dirty=True` plus the diff hash is what makes
that a fact a third party can reconstruct rather than an omission. The earlier
M1.1 run shipped a patched build under a stock commit hash and nobody noticed;
that is the failure this field exists to prevent.

## Why 66/66 is not self-congratulation
A clean sweep means nothing unless the instrument could have reported otherwise.
Two controls, declared before the run and persisted with their observations:

| control | fired | evidence |
|---|---|---|
| **admission gate** | yes | refused 1 of 67 — `test_gnd_conv.metta` on `flip` |
| **adjudicator can refuse** | yes | `UNANIMOUS`, `REDUCED_QUORUM`, `AGREED_FAILURE`, `NO_QUORUM` each reachable from a constructed envelope set |

Without the second, "66/66 UNANIMOUS" would be consistent with an adjudicator
that returns UNANIMOUS unconditionally.

## What each link is, and what it cost to learn
| link | what it does | the finding behind it |
|---|---|---|
| admission | rejects unseeded randomness | quorum **launders** nondeterminism 21.5% of the time — replication cannot be the control |
| shard store | CID-addressed, byte-capped LRU | warm cache = 0 bytes; transfer is `63 ms + 37.9 MB/s`, not a single rate |
| preflight | thermal/charge/space per session | the real cost is **98.5 µs**, not the 35 ms measured over adb |
| in-process MeTTa | JNI into `libhyperonc` | identical to native `fuelrun` on the same device |
| canon / canon_alpha | strips process history; alpha opt-in | E1 40 distinct -> 1, heap-address control unchanged at 40/40 |
| quorum-3 | dispatched vs returned recorded | a short quorum is **craftable**, so it is `REDUCED_QUORUM` and never payable |

## The correction — seats are not domains

`REDUCED_QUORUM` catches workers that **died**. It cannot catch workers that
were **never independent**: dispatched 3, returned 3, check passes — and the
failure-domain count is 2.

Two of the three workers ran the same binary on the same host. They share libm,
clock, page tables, scheduler, and the same 1024-result panic. Their agreement
is nearly free, so the run reads as three checks and is two.

```
host-only, 3 workers, 1 binary, 1 host:
  INSUFFICIENT_DOMAINS   3/3  1dom   accepted 0/4
  domain: host:Victorias-MacBook-Pro.local|bin:78d874f97674
```

The real M1 setup (2 host + 1 phone) is `3/3 2dom` — still short of 3.

**Q1's capture arithmetic runs on domains, not seats**, so this compounds with
the 72% figure rather than sitting beside it. `adjudicate` now counts distinct
domains **among the agreeing workers only** — a dissenter in a third domain
lends no independence to the majority — and returns `INSUFFICIENT_DOMAINS`
below `--min-domains` (default 3).

The domain key is `host_id|bin:<sha256[:12]>`, i.e. what independence is being
claimed over. Same shape as k8s `podtopologyspread`: `topologyKey` names the
axis, `maxSkew` bounds concentration within it.

Honest consequence: **this project has never run a 3-domain quorum.** It has one
phone. That was listed as a hardware gap; it is a validity gap.

## Still open
- **Process-per-job.** WorkManager reuses the app process; M1.1c measured that
  job N differs from job 1. Three options recorded, none implemented.
- **Panic has no schema.** Deterministic, envelope-less, neither
  `FUEL_EXHAUSTED` nor `DEADLINE_EXCEEDED`. In `HUMAN_NEEDED`.
- **Device-side cache integrity.** The host re-hashes on `get`; the phone trusts
  its own cache file.
- **Only 2 failure domains exist.** Now detected and refused rather than
  described. Closing it needs a second physical device — the standing
  `HUMAN_NEEDED` item, reclassified from convenience to correctness.
- **No network transport.** Filesystem and adb only.
