# H139 — two-phone F001 scale

Operator waived **unread thermal only** (`QUIET_ALLOW_THERMAL_UNREADABLE=1`).
Charging and cpu_busy still refuse. Default gate still refuses the S24+ without
the override.

**Not a new ISA** (both `arm64-v8a`). **Not a new operator domain.**

## Falsifier
If on-device n=200 parallel wall is within 20% of t_S25+t_S24, no scale-out.

It did not fire: speedup **1.29×** (need ≥1.20). Bound is the slower phone:
seq_sum/max = 6.528/4.869 = **1.34×** ideal for this pair; measured 1.29×.

## Operating point
USB, both charging. S25 Ultra `R5CY93675MK` (Snapdragon, thermal 42400m).
S24+ `R5CX508MPRZ` (Exynos, thermal UNREADABLE overridden, battery 37%).
Job = `trace_verifier_android_f001` on `fixtures/F001`, pin `590d8769…`.

On-device loop (one adb call, N verifies; USB-amortised):

| N each | S25 s | S24 s | parallel s | seq sum | speedup |
|---:|---:|---:|---:|---:|---:|
| 50 | 0.486 | 1.174 | 1.384 | 1.660 | 1.20 |
| 100 | 0.887 | 2.462 | 2.456 | 3.349 | 1.36 |
| 200 | 1.659 | 4.869 | 5.060 | 6.528 | 1.29 |

Per-verify: S25 **8.3 ms**, S24 **24.3 ms** (~3×). Two phones do not make 2×
because they are not equal. Parallel wall ≈ S24 wall.

USB-bound one-verify-per-adb n=8 was 1.40× and is **not** the compute figure.

Evidence: `scale.json`. Check: `python3 kitchen/test_h139.py`
