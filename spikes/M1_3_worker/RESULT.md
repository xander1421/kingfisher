# M1.3 — charge-time worker: the preflight residue, and why it cannot run per job

**GREEN for the policy half. The WorkManager half is blocked on M1.1.**

S6's `SCHEDULER_SPEC.md` maps BOINC's rules onto Android WorkManager and marks
three as **residue** — constraints the OS cannot express, which must run inside
`doWork()`. This builds that residue as a tested policy object, and measures it.

## The measurement that changed the design

Preflight reads thermal status, battery state and free space. All three are
`dumpsys`/`df` calls over adb:

```
dumpsys thermalservice   21.1 ms
dumpsys battery          21.2 ms
df /data                 21.1 ms
naive, 3 separate calls  63.4 ms   = 0.92x a warm job
batched, 1 call          35.1 ms   = 0.51x a warm job
pure adb round trip      16.2 ms   -> dumpsys itself costs 18.9 ms
```

Batching (M1.5b's lesson, applied) saves **45%**. It is still not enough:
**even batched, preflight costs half a job.** Per-job preflight is not viable.

So preflight gates a **work session**, not a job — which is what WorkManager
does anyway, and is an argument *for* the platform model rather than against it.
Overhead amortises as `35.1/N` ms per job:

| jobs per session | preflight overhead |
|---|---|
| 1 | 51% |
| 16 (default) | 3.2% |
| 67 | 0.76% |

## Runs — 67 programs, 3 workers, warm cache

```
dispatched 67 jobs in 5 work sessions, 0 refusals
66 UNANIMOUS / 1 NO_QUORUM, 0.0 KiB crossed the wire
```

The 1 NO_QUORUM is `test_gnd_conv.metta` calling `(flip)` — same program S57
identified, identical fuel 1012 with three different hashes. Known and explained.

## The gate is proven able to refuse — twice, two different ways

Zero refusals in a clean run means the gate never fired, which is exactly the
N1c defect: **a control that cannot fail proves nothing.** Two injected controls:

| control | result |
|---|---|
| unsatisfiable floor (101%) at session 0 | `REFUSED after 0 jobs: battery:100%<101%`, backoff 300 s, 0 dispatched |
| thermal refusal injected at session 3 | `REFUSED after 32 jobs: thermal:2>1`, **32 dispatched, 32 completed, none lost** |

The second is the one that matters: a mid-run refusal must stop dispatch without
stranding work already in flight. Verified — `all dispatched jobs completed: True`.

## Parsing hazard, guarded by construction
`dumpsys battery` is followed by a log dump whose lines also contain `level:`
and `temperature:`. A bare grep or a last-match parser reads **historical log
state as current battery state** — a phone at 100% would parse as 12%. The
parser anchors on the two-space indent and takes the first match; the test feeds
it a real log tail and asserts `level == 100, temperature == 305`.

This is the S57/S62 empty-capture failure in a new place, which is why it is
tested rather than trusted.

## `test_preflight.py` — 24 assertions
Each rule refuses on its own and names itself; the 90% floor is inclusive;
`scale=0` cannot divide by zero; backoff is 300/600/1200/2400/3600 capped and
resets on success; and **every unreadable signal REFUSES** — an unreadable
sensor is not a passing sensor.

## Not done
- **No WorkManager, no Kotlin, no app.** The five declarative constraints
  (`setRequiresCharging`, `setRequiresDeviceIdle`, `NetworkType.UNMETERED`,
  `setRequiresBatteryNotLow`, `setRequiresStorageNotLow`) need M1.1's Gradle
  project. This is the in-worker residue only.
- **`onStopped()` -> checkpoint at a fuel boundary is NOT implemented.** S6 calls
  interruptibility "the single biggest design constraint on `fuel_limit`". It
  needs the state commitment S68 found does not exist, and that item is being
  re-opened separately on the strength of the Golem audit finding.
- **Backoff is a tested state machine, never exercised against a real refusal
  over time.** WorkManager owns retry scheduling on-device; nothing here sleeps.
- **`setRequiresDeviceIdle` is unmeasured.** S6 warns it can starve on a phone
  that is never idle-while-charging. No data either way.
