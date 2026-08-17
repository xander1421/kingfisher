# M1 — the whole chain, one run, with provenance

**66/66 UNANIMOUS with a real phone in the quorum.** First full-system run in
which every link is measured and every gate has a control proving it could have
refused.

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

## Still open
- **Process-per-job.** WorkManager reuses the app process; M1.1c measured that
  job N differs from job 1. Three options recorded, none implemented.
- **Panic has no schema.** Deterministic, envelope-less, neither
  `FUEL_EXHAUSTED` nor `DEADLINE_EXCEEDED`. In `HUMAN_NEEDED`.
- **Device-side cache integrity.** The host re-hashes on `get`; the phone trusts
  its own cache file.
- **Two of three workers are the same binary on one host.** This exercises the
  pipeline, not Sybil resistance. Q1's 72% capture stands, and M1.8c shows
  quorum size is attacker-influenceable on top of it.
- **No network transport.** Filesystem and adb only.
