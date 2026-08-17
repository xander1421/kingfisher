# N1e — false sharing on the S51 barrier line: UNRESOLVED (design defect)

**Status: not citable. Direction suggestive, magnitude unmeasured, design confounded.**

## The hypothesis
`mc.c:59-60` declares `b_gen,b_left,b_stop,b_dyn,b_empty` (atomic_int) immediately
followed by `b_cursor` (atomic_long). Measured offsets: left=+4, cursor=+24 — one
64-byte line.

The contention is **not** the disjoint-phase story. Disjoint phases would mean no
concurrent access and therefore no false sharing. The real overlap is in
`dispatch()`:

```c
while (atomic_load_explicit(&b_left, memory_order_acquire) > 0) { }   /* mc.c:114 */
```

The coordinator spins on `b_left` for the **entire** work phase while every worker
`fetch_add`s `b_cursor` (`mc.c:93`). Coordinator wants the line shared, each claim
takes it exclusive. Continuous, concurrent, different variables, one line.

Static mode never touches `b_cursor` -> same-binary negative control.
This also predicts something already in S51's own table and never explained:
dynamic was slower than static at low T.

## What was run
`mcx.c`, `PAD` compile-time flag placing `cursor` in a separate 128B-aligned slot.
Layout asserted at runtime, not assumed. 5 paired runs, alternating arms.

| regime | arm | n | mean dyn/static @T3 |
|---|---|---|---|
| fast (T1~570-760us) | PAD=0 | 3 | 1.256 |
| fast | PAD=1 | **1** | 1.113 |
| throttled (T1~940us) | PAD=0 | 2 | 1.069 |
| throttled | PAD=1 | 3 | 1.025 |

## Why it is not citable
The device entered the low DVFS state between run3's two arms and never left
(572 -> 940 us at T=1; the 1.64x band S56 documented). **Thermal regime became
confounded with arm**: the fast regime holds 3 PAD=0 against 1 PAD=1.

The balanced comparison is the throttled regime: **4.4 pp, not the ~20 pp the
unbalanced fast regime suggests.** Direction is consistent across both regimes,
which is why this is logged rather than withdrawn.

Per-point noise is large at T=6 (one PAD=0 run gives 1.37, another 0.80), so
single-point comparisons anywhere in this table are meaningless.

## The defect is a repeat
A15 says a positive control must be able to fire. It does not say the arms must
share a thermal state. **A/B across separate binaries fails when between-run
drift exceeds the effect** — the same shape as N1's inherited DVFS band. The
within-run static control normalises DVFS *inside* a run and does nothing about
which arm ran hot.

## Correct design, for whoever picks this up
One binary, both layouts, alternating **per dispatch** — two `bstate_t` instances,
padded and unpadded, switched by a flag inside `measure()`. Thermal state is then
shared by construction and the paired difference is the estimator. Also gate on
`quiet.sh --device` between arms and abort on a DVFS band change.

Cost estimate to close: ~20 minutes. Not spent: settlement caps throughput at
~17 jobs/s and one device already saturates it, so barrier microarchitecture is
the abundant side of a 4-order-of-magnitude mismatch. Deferred deliberately.
