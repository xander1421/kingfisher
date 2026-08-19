# H148 — two phones lose when the harness serializes them

Operator: if we cannot scale on devices, the code is bad. The previous
two-phone numbers were the code.

## Retracted (H141)

Published 1:1 wall **6.874s** and 3:1 wall **5.173s**. Those equal
`s25_s + s24_s`. Python evaluates `ex.submit(a).result(), ex.submit(b).result()`
left-to-right, so the second phone is submitted only after the first
finishes. The ThreadPoolExecutor never held two jobs.

Host-only control (50 ms + 50 ms sleep): bug **0.106s** (~sum),
submit-all **0.055s** (~max), ratio **1.93**.

## Falsifier (stated first)

After submit-all: if 3:1 k=1 of 400 is not faster than S25-only 400,
**and** weighted fleet (S25 k=2 × 300 + S24 k=2 × 100) is not faster
than S25 k=2 × 400, devices still add no capacity.

It did not fire.

## Operating point

USB, both charging. S25 Ultra `R5CY93675MK` (thermal 36600m).
S24+ `R5CX508MPRZ` (thermal UNREADABLE overridden, battery 39%).
Job = on-device loop of `trace_verifier_android_f001` on `fixtures/F001`,
pin `590d8769…`. Not a new ISA. Not a new operator domain.

| split | S25 | S24 | wall | vs max | vs S25 |
|---|---:|---:|---:|---:|---:|
| 1:1 k=1 200+200 | 1.556s | 5.380s | **5.382s** | 1.00× | loses (S24 bound) |
| 3:1 k=1 300+100 | 2.326s | 2.554s | **2.556s** | 1.00× | **0.846×** S25-only 3.024s |
| S25 k=2 200+200 | 1.763 / 1.777s | — | **1.779s** | — | 224.8 jobs/s |
| S24 k=2 100+100 | — | 2.520 / 2.525s | 2.527s | — | 79.1 jobs/s |
| fleet 3:1 k=2 150+150+50+50 | 1.292 / 1.294s | 1.334 / 1.246s | **1.337s** | 1.00× | **0.752×** S25 k=2 |

400 F001 verifies: two phones at 3:1 finish in 2.556s vs one S25 in
3.024s. Same 400 with two workers on the S25 plus two on the S24:
**1.337s vs 1.779s** (299 vs 225 jobs/s).

1:1 still loses to one S25 because the S24 is ~3× slower — that is the
split, not the devices. Weight the work and add workers and the second
phone shortens the wall.

Evidence: `fleet.json`. Check: `python3 kitchen/test_h148.py`.
H141 `split.json` replaced with this run; prior walls kept under
`retracted_prior`.
