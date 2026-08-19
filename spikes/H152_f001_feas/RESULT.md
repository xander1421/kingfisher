# H152 — F001 on 1 device, then 2

Is the frozen fragment even runnable on a phone, and does a second
phone add capacity? Live adb, not kitchen JSON.

Falsifier (stated first): S25 does not ACCEPT `590d8769…`, or a live
steal of 400 is not faster than S25 two workers.

It did not fire.

## 1 device — S25 Ultra `R5CY93675MK`

Gate green (cpu 0.7%, thermal 37400m, charging 100%).

| step | result |
|---|---|
| one verify | **ACCEPTED** fuel 400 witness `112f7e8c` digest `590d8769…` |
| 200 on-device loop | **1.582s** (126.5 jobs/s) |
| 2 workers × 200 | **1.861s** (214.9 jobs/s) |

USB-bound n=1 (~24 ms) is not the compute figure.

## 2 devices — S25 + S24+ (unread-thermal override only)

S24 charging 38%, cpu 3.5%. Default unread still refuses. One verify:
**ACCEPTED** same digest.

Pull chunks of 50, 2 workers per phone, 400 jobs:

| | wall | jobs/s | split |
|---|---:|---:|---|
| S25 k=2 | 1.861s | 215 | 400/0 |
| steal | **1.402s** | **285** | **300/100** |

steal / S25 k=2 = **0.753**. Second phone added **+33%** throughput.
Same-source Android is not a new operator domain. §8 still 0 ACCEPTED.

Evidence: `feas.json`. Check: `python3 kitchen/test_h152.py`.
