# M1.5b — the 40 ms is not a bandwidth. Transfer still dominates, by 3–14x not 22–120x.

**A reviewer extrapolated M1.5's 173 KiB / 40 ms into 4.21 MB/s and priced
B1's deployable shards at 22–120x the compute. The rate is wrong; the
conclusion survives at a smaller multiplier.**

## Measured — same `device_fetch` path, device gate open

```
   KiB       ms     MB/s        (median of 5, incompressible os.urandom)
    64     54.4      1.1
   173     60.2      2.8   <- M1.5's operating point
   512     69.2      7.2
  2048    110.2     18.1
  6560    230.1     27.8
 13100    401.2     31.9
 32768    908.6     35.2
```

Apparent "MB/s" rises monotonically by **32x** across the sweep. That alone
falsifies the single-rate model: a bandwidth does not depend on transfer size.
Fit on the two largest points: **63.2 ms fixed + 37.9 MB/s marginal.**

| shard | single-rate prediction | measured/fitted | overestimate |
|---|---|---|---|
| B=32, 6.41 MB | 1521 ms | **233 ms** | 6.5x |
| B=16, 12.79 MB | 3035 ms | **401 ms** | 7.6x |
| B=1, 34.83 MB | 8264 ms | **983 ms** | 8.4x |

## Most of the fixed cost is the harness, not the system

```
adb shell true       18.0 ms
adb shell test -f    16.6 ms
adb push 1 byte      12.0 ms
```

`device_fetch` issues **three separate adb invocations** (`test -f`, `mkdir -p`,
`push`), so ~47 of the 63.2 ms is process spawn and USB protocol setup in the
measurement rig. A real transport does one round trip. **Do not inherit 63 ms as
a system constant** — it is a property of this spike.

## Against compute, at ~69 ms warm per job

| | reviewer's ratio | measured (adb/USB) |
|---|---|---|
| B=32 | 22.1x | **3.4x** |
| B=16 | 44.1x | **5.8x** |
| B=1 | 120.1x | **14.2x** |

**The qualitative conclusion holds and is robust.** Transfer exceeds compute at
every deployable shard size, and it does so under transports better *and* worse
than this one:

- **USB (measured here), 37.9 MB/s** — the optimistic bound. Nothing in the
  product uses USB.
- **WiFi, the actual deployment** (the worker gates on UNMETERED, so this is the
  real path). At a conservative 10 MB/s, B=32 is ~640 ms, i.e. **~9x compute**.
  The ratio is transport-dependent and this spike does not measure WiFi.

So the reviewer's scheduler consequence stands: the objective is **never fetch
during a job**, not fewer fetches per job. Pre-stage at charge time and dispatch
only to devices already holding the CID — `prefer_cached_cids` as a hard filter,
not a score. That survives every transport bound above.

## What this does NOT license
- **No WiFi measurement.** The number that matters for the product is unmeasured;
  everything above is USB, standing in for it.
- **The 3.4–14x ratios use a 69 ms warm job** from a 173 KiB program. Compute
  scales with shard size too, so these ratios are not size-invariant either —
  the same error one level up. Pricing a B=32 *job* needs a B=32 job, which does
  not exist yet.
- **S61's operating point is not re-derived here.** This supplies the unit S61
  lacked; re-running the sweep against it is separate work.

---

## Addendum — the two regimes, and a 38x fix in the first one

A reviewer split the finding by regime rather than by magnitude, which is the
better reading and is now measured directly rather than fitted:

| shard | fixed-cost share | what wins |
|---|---|---|
| 173 KiB (M1.5's point) | **93%** | fewer round trips — **batching** |
| B=32, 6.41 MB | 27% | not transferring — **residency** |
| B=16, 12.79 MB | 16% | residency |
| 32 MB | 7% | residency |

**M1.5's corpus is 173.5 KiB across 67 shards — mean 2,652 bytes.** It sits at
the far end of the fixed-cost regime, so `device_fetch`'s per-shard round trips
dominate everything.

Measured, same bytes, cold each time, median of 3:

```
per-shard (3 adb calls x 67)   3680 ms    54.9 ms/shard
batched   (1 adb push)           97 ms     1.4 ms/shard
speedup                          38.0x
```

So M1.5's cold-cache penalty was ~97 ms of actual bytes and ~3.6 s of adb round
trips. **The 40 ms/job it reported is a round-trip count, not a transfer cost.**

Consequences, and the second one is a correction to this document:

1. **`prefer_cached_cids` as a hard filter is right only at large shards.** At
   2.6 KiB it is near-pointless; coalescing fetches beats locality by 38x. The
   scheduler needs both mechanisms, selected by shard size.
2. **"Never fetch during a job" was stated as holding under every transport
   bound.** It does not — it holds in the residency regime. In the fixed-cost
   regime the correct move is to batch the fetches, not to avoid them. This
   document asserted the general form and the regime split refutes it.
3. **A18 applies to this spike's own recommendation**, not just to the rate it
   corrected: a conclusion drawn at one operating point was generalised across
   four orders of magnitude of shard size.
