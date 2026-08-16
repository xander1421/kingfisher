#!/usr/bin/env python3
"""Timing harness shared by S9..S13.

Exists because of a defect found while re-reading S5: a warm single run
(352.9 GOP/s, run2.json) and a cold single run (25.9 GOP/s, run1.json) of the
byte-identical workload were reported in the same document as if comparable.
A single `time.perf_counter()` delta around one call is not a measurement.

Two rules enforced here:

1. Never report one number.  Report the first (cold) sample separately from
   the median of the rest, plus the spread.  If cold/warm disagree by more
   than a few percent, say so instead of picking the flattering one.
2. Never time something near the clock's resolution.  `autoscale` grows an
   inner repeat count until each timed sample is >= `min_time`, so a 2 us
   kernel is measured as N x 2 us, not as one noisy tick.
"""

import statistics
import time

# perf_counter on darwin is ~40ns, but syscall + loop overhead dominates well
# above that.  50 ms per sample keeps overhead under ~0.001%.
MIN_SAMPLE_S = 0.05


def autoscale(fn, min_time=MIN_SAMPLE_S, cap=1 << 22):
    """Return the inner repeat count that makes one sample last >= min_time."""
    n = 1
    while n < cap:
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        if time.perf_counter() - t0 >= min_time:
            return n
        n *= 4
    return n


def run(fn, reps=7, min_time=MIN_SAMPLE_S, scale=True):
    """Time `fn` and report cold, warm and spread. Never a single number."""
    inner = autoscale(fn, min_time) if scale else 1
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        for _ in range(inner):
            fn()
        samples.append((time.perf_counter() - t0) / inner)

    warm = samples[1:] or samples
    med = statistics.median(warm)
    return {
        "reps": reps,
        "inner_reps": inner,
        "cold_s": samples[0],
        "warm_median_s": med,
        "warm_min_s": min(warm),
        "warm_max_s": max(warm),
        # relative spread of the warm samples; > ~10% means the number is soft
        "warm_rsd_pct": (100 * statistics.pstdev(warm) / statistics.mean(warm)
                         if len(warm) > 1 else 0.0),
        # the S5 defect, quantified: how much does cold differ from warm
        "cold_over_warm": samples[0] / med if med else float("inf"),
        "all_s": samples,
    }


def gops(flops, seconds):
    return flops / seconds / 1e9


def fmt(name, r, flops=None):
    """One honest line per measurement."""
    s = (f"{name:<28} cold {r['cold_s']*1e3:9.3f} ms | "
         f"warm_med {r['warm_median_s']*1e3:9.3f} ms | "
         f"rsd {r['warm_rsd_pct']:4.1f}% | "
         f"cold/warm {r['cold_over_warm']:6.2f}x | "
         f"inner {r['inner_reps']}")
    if flops:
        s += (f" | cold {gops(flops, r['cold_s']):7.1f} GOP/s"
              f" warm {gops(flops, r['warm_median_s']):7.1f} GOP/s")
    return s
