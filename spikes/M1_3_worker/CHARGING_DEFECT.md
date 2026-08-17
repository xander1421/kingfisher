# The charging gate accepted an unplugged phone, all session

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

## What it invalidates, stated precisely
Every device run this session passed a gate that should have refused. What that
does and does not touch:

- **Not invalidated: the determinism results.** Byte-identity across host, phone
  and x86-64 does not depend on the power source. 66/66 agreement stands.
- **Weakened: every timing number taken on device.** A phone on battery runs a
  different DVFS policy than one on external power. M1.5b's transfer curve,
  M1.1's 98.5 µs preflight and the phone job medians were all measured
  unplugged and are now *unknown-condition*, not wrong.
- **Falsified: the claim that device work honoured the charging constraint.**
  MISSION_LOOP §10 requires device jobs to honour charging+idle+UNMETERED. They
  did not honour charging, and the gate that existed to enforce it reported
  success.

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
