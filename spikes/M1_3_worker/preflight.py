#!/usr/bin/env python3
"""M1.3 — in-worker preflight gate, per job.

S6's SCHEDULER_SPEC maps BOINC's rules onto WorkManager and marks three as
RESIDUE -- constraints the OS cannot express, which must run inside doWork():

  rule 2  battery floor, default 90%   (BatteryNotLow fires at ~15%, far below)
  rule 3  thermal >= MODERATE          (PowerManager.getCurrentThermalStatus)
  rule 4  backoff 5 min, exponential   (BOINC's own comment: "crude hysteresis")

plus a cache-space check. This is that residue as a testable policy object,
portable to Kotlin later. It is NOT the WorkManager half -- that needs M1.1.

M1.8's RESULT flagged that the device gate ran once in the coordinator, not
per job. This is the fix.

All signals are read in ONE round trip. M1.5b measured an adb round trip at
~17 ms against a ~69 ms job, so three separate reads would put preflight at
~25% of a warm job's cost.
"""
import re, subprocess, time

# PowerManager.THERMAL_STATUS_*
THERMAL_NONE, THERMAL_LIGHT, THERMAL_MODERATE = 0, 1, 2
# BatteryManager.BATTERY_STATUS_*
STATUS_CHARGING, STATUS_FULL = 2, 5

PROBE = ('dumpsys thermalservice; echo ---; dumpsys battery; echo ---; df /data')


class Policy:
    def __init__(self, battery_floor_pct=90, thermal_max=THERMAL_LIGHT,
                 temp_max_c=40.0, min_free_mb=512,
                 backoff_base_s=300, backoff_cap_s=3600):
        self.battery_floor_pct = battery_floor_pct
        self.thermal_max = thermal_max      # inclusive: stop ABOVE this
        self.temp_max_c = temp_max_c
        self.min_free_mb = min_free_mb
        self.backoff_base_s = backoff_base_s
        self.backoff_cap_s = backoff_cap_s


def parse_probe(text: str) -> dict:
    """First occurrence of each key wins.

    `dumpsys battery` is followed by a log dump whose lines also contain
    `temperature:` and `level:`. Taking the last match -- or a bare grep --
    reads a historical log line as current state. That is the S57/S62
    empty-capture failure in a new place, so it is guarded here by construction.
    """
    out = {}
    m = re.search(r'^\s*Thermal Status:\s*(\d+)', text, re.M)
    out['thermal'] = int(m.group(1)) if m else None
    for key in ('level', 'scale', 'status', 'temperature'):
        m = re.search(rf'^\s{{2}}{key}:\s*(-?\d+)\s*$', text, re.M)  # 2-space indent only
        out[key] = int(m.group(1)) if m else None
    m = re.search(r'^/dev/\S+\s+\d+\s+\d+\s+(\d+)', text, re.M)
    out['free_kb'] = int(m.group(1)) if m else None
    return out


def decide(s: dict, p: Policy):
    """Return (ok, reason). Missing signals REFUSE -- an unreadable sensor is
    not a passing sensor (A15: a control that cannot fail proves nothing)."""
    for k in ('thermal', 'level', 'scale', 'status', 'free_kb'):
        if s.get(k) is None:
            return False, f'unreadable:{k}'
    if s['thermal'] > p.thermal_max:
        return False, f"thermal:{s['thermal']}>{p.thermal_max}"
    if s['status'] not in (STATUS_CHARGING, STATUS_FULL):
        return False, f"not_charging:status={s['status']}"
    if s['scale'] <= 0:
        return False, 'bad_scale'
    pct = 100.0 * s['level'] / s['scale']
    if pct < p.battery_floor_pct:
        return False, f'battery:{pct:.0f}%<{p.battery_floor_pct}%'
    if s['temperature'] is not None and s['temperature'] / 10.0 > p.temp_max_c:
        return False, f"temp:{s['temperature']/10.0:.1f}C>{p.temp_max_c}C"
    if s['free_kb'] / 1024.0 < p.min_free_mb:
        return False, f"space:{s['free_kb']/1024:.0f}MB<{p.min_free_mb}MB"
    return True, 'ok'


def probe(serial=None) -> dict:
    cmd = ['adb'] + (['-s', serial] if serial else []) + ['shell', PROBE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return parse_probe(r.stdout)


class Backoff:
    """Rule 4: exponential from 5 min. WorkManager owns this on-device; the
    state machine is here so the policy is testable without an app."""
    def __init__(self, p: Policy):
        self.p = p
        self.attempt = 0

    def on_refusal(self) -> int:
        d = min(self.p.backoff_base_s * (2 ** self.attempt), self.p.backoff_cap_s)
        self.attempt += 1
        return d

    def on_success(self):
        self.attempt = 0
