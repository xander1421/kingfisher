# Two gate defects, one of which I misdiagnosed

> **CORRECTION, same day.** This document first claimed *"the phone was not
> charging, all session"*. **That was wrong.** The battery service was pinned in
> a test override — `dumpsys battery` was printing
> `(UPDATES STOPPED -- use 'reset' to restart)` and reporting frozen values.
> After `dumpsys battery reset`: `USB powered: true`,
> `deviceidle get charging: true`. The phone was charging.
>
> I read a frozen instrument, concluded the world was broken, and wrote a report
> about it. The heading below is preserved because the sequence matters more
> than the tidy version.
>
> **What survives**: defect 1 is real and the fix is right — `status in {2,5}`
> genuinely cannot distinguish plugged-and-full from unplugged-and-full, and it
> was never demonstrated by this incident. **What is withdrawn**: every claim
> about the session's device runs being unpowered. They were fine. On-device
> timings are NOT unknown-condition and need no re-measurement.
>
> **The bigger defect is defect 2, which this incident did demonstrate**: no
> gate detected that the battery service was overridden at all.

# Defect 1 — `BATTERY_STATUS_FULL` is not a charging test

**`BATTERY_STATUS_FULL` means the battery is full. It does not mean the device
is plugged in.** An unplugged phone at 100% reports `status: 5`, and both
`quiet.sh --device` and M1.3's preflight accepted it.

## How it surfaced
Porting the WorkManager worker onto the M1.7 transport, the worker never ran.
No `KFWORKER` lines at all, though the activity logged all three enqueues.

```
dumpsys jobscheduler:
  Unsatisfied constraints: CHARGING [0x1]
  Ready: false
```

while our own gate was reporting, in the same minute:

```
device quiet: cpu_busy 0.4% ... battery status=5 level=100
```

**The platform and the gate disagreed, and the platform was right:**

```
AC powered: false   USB powered: false   Wireless powered: false
Max charging current: 0
dumpsys deviceidle get charging -> false
status: 5   level: 100
```

adb works, so the cable is attached — but nothing is drawing power. Data-only
port, or charge management holding it off at full.

## Why the wrong rule was chosen, and why it survived
`quiet.sh` carried an explicit rationale for preferring `status` over the
powered flags:

> *"Android clears the powered flags at 100% because the charger disengages, so
> a plugged phone at full reads AC powered: false. 2=CHARGING and 5=FULL are
> both plugged."*

**The phenomenon is real. The conclusion does not follow.** An unplugged phone
at 100% also reports FULL, so `status` cannot separate the two cases — the rule
is not merely wrong, it is *incapable* of being right in the direction that
matters. It was chosen to avoid a false negative and bought a false positive
that nothing could detect, because a passing gate produces no evidence.

Same family as the dead controls: the failure mode is silence.

## What it invalidates — WITHDRAWN
This section originally said every device run was unpowered and all on-device
timings were unknown-condition. **Both withdrawn.** The phone was charging; the
instrument was frozen. Timings stand, §10 was honoured.

The defect in the rule is still real: `status in {2,5}` cannot separate
plugged-and-full from unplugged-and-full, so it is *incapable* of being right in
the direction that matters. It just had not fired.

# Defect 2 — no gate detected that the battery service was OVERRIDDEN

`dumpsys battery set` / `unplug` pins the service and prints one line:

```
Current Battery Service state:
  (UPDATES STOPPED -- use 'reset' to restart)
  AC powered: false      <- fiction
  USB powered: false     <- fiction
  status: 5              <- fiction
```

Every field after that banner is a stale override, and both `quiet.sh` and
`preflight.py` parsed them as current state. There was no error, no warning, and
no way to tell from the values themselves — a pinned `false` looks exactly like
a measured `false`.

**This is the defect that actually fired**, and it is worse than defect 1
because it makes *every* battery reading untrustworthy rather than one rule
wrong. It also means a device could be put into a pinned state and the gate
would never notice.

Fixed: both gates now grep for `UPDATES STOPPED` and refuse with
`battery-service-OVERRIDDEN(run: adb shell dumpsys battery reset)`.
`test_preflight.py` is at **30 assertions** including a frozen-service fixture.

## The pattern, stated plainly
An instrument in a test-override state reports confident, well-formed, wrong
values. That is the same failure as the dead controls, the self-flattering
domain key and the stale binary — and this time it produced not a bad number but
an entire false narrative, complete with a mechanism, a §10 violation and a
request to the human. **The tell was one line of banner text I was not
parsing.**

## Fix
Ask the platform the question the platform asks. `dumpsys deviceidle get
charging` is authoritative and is what JobScheduler uses; the AC/USB/Wireless/
Dock powered flags are the fallback; `status` alone is never sufficient.

- `quiet.sh` now reports `charging=` and `powered=` and **refuses** — verified,
  exit 1, `not-charging(status=5 deviceidle=false powered=0)`.
- `preflight.py` parses `powered` and refuses without it. Missing field is
  treated as unreadable and refuses, rather than defaulting to false.
- `test_preflight.py`: **27 assertions**, including a fixture that is FULL and
  unplugged — the exact state that was passing.

## The reason WorkManager caught this and we did not
The declarative constraint is stricter than our hand-rolled check, and it is
enforced by code that does not want the answer to be yes. Our gate was written
by the party that benefits from it passing — **A22, applied to ourselves**.
