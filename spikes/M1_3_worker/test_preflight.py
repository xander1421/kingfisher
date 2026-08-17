#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preflight import parse_probe, decide, Policy, Backoff, THERMAL_MODERATE

# --- the log-dump trap: real state says level 100 / temp 30.5C, the trailing
# log says level 12 / temp 48.9C. A last-match or bare-grep parser reads the log.
REAL = """IsStatusOverride: false
Thermal Status: 0
Current Battery Service state:
  AC powered: true
  status: 5
  level: 100
  scale: 100
  temperature: 305
08-16 18:18:06.811  Sending ACTION_BATTERY_CHANGED: level:12, status:3, temperature:489, scale:100
Filesystem 1K-blocks Used Available Use% Mounted
/dev/block/dm-72 978352128 181846272 796374784 19% /data
"""
s = parse_probe(REAL)
assert s['level'] == 100, s          # not 12
assert s['temperature'] == 305, s    # not 489
assert s['status'] == 5 and s['thermal'] == 0 and s['free_kb'] == 796374784
assert s['powered'] is True, 'AC powered: true must parse as powered'
assert decide(s, Policy())[0] is True

UNPLUGGED = REAL.replace('AC powered: true', 'AC powered: false')
su = parse_probe(UNPLUGGED)
assert su['powered'] is False
assert decide(su, Policy())[0] is False, \
    'a phone at 100% with no power source must be refused (status=5 is FULL, not plugged)'

# a frozen battery service must REFUSE, not silently report pinned values
FROZEN = REAL.replace('Current Battery Service state:',
                      'Current Battery Service state:\n  (UPDATES STOPPED -- use \'reset\' to restart)')
sf = parse_probe(FROZEN)
assert sf['battery_overridden'] is True
assert decide(sf, Policy())[1].startswith('battery_service_overridden'), \
    'a pinned battery service must refuse: every field it reports is stale'
assert parse_probe(REAL)['battery_overridden'] is False

p = Policy()
def st(**kw):
    base = dict(thermal=0, level=100, scale=100, status=5,
                temperature=305, free_kb=796374784, powered=True)
    base.update(kw); return base

# each rule refuses on its own, and names itself
assert decide(st(thermal=THERMAL_MODERATE), p)[1].startswith('thermal')
assert decide(st(status=3), p)[1].startswith('not_charging')   # discharging
assert decide(st(level=89), p)[1].startswith('battery')
assert decide(st(level=90), p)[0] is True                      # floor inclusive
assert decide(st(temperature=401), p)[1].startswith('temp')
assert decide(st(free_kb=100*1024), p)[1].startswith('space')
assert decide(st(status=2), p)[0] is True                      # CHARGING ok
# an UNPLUGGED phone at 100% reports status=5 FULL. Accepting that is what let
# every device run this session pass a gate that should have refused.
assert decide(st(status=5, powered=False), p)[1].startswith('not_charging'), \
    'status=FULL with no power source must be refused'
assert decide(st(scale=0), p)[1] == 'bad_scale'                # no div by zero

# an unreadable sensor must REFUSE, never pass
for k in ('thermal', 'level', 'scale', 'status', 'free_kb', 'powered'):
    d = st(); d[k] = None
    ok, why = decide(d, p)
    assert ok is False and why == f'unreadable:{k}', (k, ok, why)

# a parser that finds nothing must produce refusal, not a pass
assert decide(parse_probe(''), p)[0] is False

# backoff: 5 min, doubling, capped, reset on success
b = Backoff(p)
assert [b.on_refusal() for _ in range(5)] == [300, 600, 1200, 2400, 3600]
assert b.on_refusal() == 3600                  # capped
b.on_success()
assert b.on_refusal() == 300                   # reset
print('preflight: 30 assertions pass')
