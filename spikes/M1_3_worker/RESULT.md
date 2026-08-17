# M1.3 — charge-time worker: the preflight residue, and why it cannot run per job

**GREEN for the policy half. The WorkManager half is blocked on M1.1.**

S6's `SCHEDULER_SPEC.md` maps BOINC's rules onto Android WorkManager and marks
three as **residue** — constraints the OS cannot express, which must run inside
`doWork()`. This builds that residue as a tested policy object, and measures it.

## CORRECTED — "per-job preflight is not viable" was an artifact

This section first claimed that batched preflight costs 35.1 ms = 0.51x a warm
job, so preflight must be amortised across a work session. **That measured the
harness, not the mechanism**, and A18 — written by this author one spike
earlier, saying exactly this — was not applied to it.

What was actually measured, over adb:

```
dumpsys thermalservice   21.1 ms
dumpsys battery          21.2 ms
df /data                 21.1 ms
naive, 3 separate calls  63.4 ms
batched, 1 call          35.1 ms   = 16.2 adb round trip + 18.9 dumpsys text dump
```

Neither term is the on-device cost. `SCHEDULER_SPEC:19-20` specifies
`BatteryManager.EXTRA_LEVEL/EXTRA_SCALE` and
`PowerManager.getCurrentThermalStatus()` — **in-process binder calls** — plus
`addThermalStatusListener`, which means thermal is *pushed by the OS, not
polled at all*.

Measured floor for a native on-device path (`tprobe.c`, 2,000 iterations,
open+read+close on `/sys/class/thermal/thermal_zone0/temp`):

| path | cost | vs a 68.8 ms job |
|---|---|---|
| adb + dumpsys (measured) | **35,100 µs** | 0.51x |
| native sysfs read (measured) | **8.4 µs** | 0.0001x |
| **`getCurrentThermalStatus()` + battery + StatFs — MEASURED in M1.1** | **98.5 µs** | **0.0014x** |

**Settled by M1.1**: the real spec path is **98.47 µs**, 356x cheaper than the
published 35.1 ms and **0.14% of a job**. Per-job preflight is trivially viable.
Following SCHEDULER_SPEC:19 literally (sticky `ACTION_BATTERY_CHANGED` rather
than `getIntProperty`) gives ~38.9 µs, another 2.5x better.

### What this changes
- **Per-job preflight IS viable, and S6 requires it.** Rows 2 and 3 of the
  rule table are both marked *Residue: yes* — the 90% charge floor and thermal
  status must be re-checked inside `doWork()`, because WorkManager's
  `BatteryNotLow` fires near 15%, nowhere near BOINC's 90%. A result
  contradicting the spec being implemented should have stopped the write-up.
- **Session gating in `q3.py` stays, as a harness accommodation.** Over adb the
  reads genuinely cost half a job, so the host harness batches them. That is a
  property of driving a phone over USB, not a design conclusion.
- **The WorkManager conclusion was right for the wrong reason.** Declarative
  constraints are OS-evaluated per session because that is what they *are*, not
  because polling is expensive. Resting it on 35 ms invited a reversal the
  moment the real number appeared — which took one command.

### Limits of the correction
- 8.4 µs is a **floor**, not the answer. `getCurrentThermalStatus()` is a
  different signal (system-wide, vendor-calibrated, SoC + skin temperature) and
  a binder round trip, not a file read.
- **Battery sysfs could not be measured at all**: `/sys/class/power_supply/
  battery/{capacity,status}` is permission-denied to the shell user.
- ~~The honest number needs a JNI or Kotlin harness on-device, which is M1.1.~~
  **Done — see `spikes/M1_1_android/RESULT.md`.**

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
