#!/usr/bin/env python3
"""S32c — what is the world computer's TPS?

An arithmetic projection from measured constants. It is NOT a measurement of a
fleet; there is no fleet. Every input is labelled with where it came from, and
the assumed inputs are the ones to attack.

MEASURED on a Galaxy S25 Ultra (SM8750) and an M4 Pro, this workspace:
  single-thread sustained      383 k steps/s     S30 (job_kb back-to-back)
  single-thread duty-cycled    658 k steps/s     S30 (25 s idle between)
  8-way burst                2,954 k steps/s     S32a (5.87x scaling, hashes identical)
  8-way sustained r1         3,868 k steps/s     S32b (first round)
  8-way sustained r6         1,963 k steps/s     S32b (sixth round, throttled)
  host single-thread         1,440 k steps/s     S30
  a small query job            100,082 steps     S15 job_terminating
  verification                = one re-execution S7 (~85 ms recompute vs 0.7 ms check)

ASSUMED (attack these):
  duty_frac      fraction of a fleet charging+idle+unmetered at any instant
  window_h       hours per device per night in that state
  replication    how many devices run each job before it is accepted
  audit_rate     fraction re-executed by a verifier on top of replication
"""

import json

# ---------------------------------------------------------------- measured
SINGLE_SUSTAINED = 383_000
EIGHT_BURST      = 2_954_450
EIGHT_SUST_HI    = 3_867_536     # round 1
EIGHT_SUST_LO    = 1_963_190     # round 6, thermally settled
EIGHT_SUST       = 2_300_000     # steady-state estimate, rounds 4-6
HOST_SINGLE      = 1_440_000
JOB_STEPS        = 100_082       # S15's job_terminating

def jobs_per_device_second(steps_per_s, job_steps=JOB_STEPS):
    return steps_per_s / job_steps

def fleet_tps(n_devices, steps_per_s, duty_frac, replication, audit_rate):
    """Useful (accepted, not merely executed) jobs per second, fleet-wide."""
    raw = n_devices * duty_frac * jobs_per_device_second(steps_per_s)
    return raw / (replication + audit_rate)

def main():
    out = {"measured": {
        "single_thread_sustained_steps_s": SINGLE_SUSTAINED,
        "eight_way_burst_steps_s": EIGHT_BURST,
        "eight_way_sustained_steps_s_range": [EIGHT_SUST_LO, EIGHT_SUST_HI],
        "eight_way_sustained_steps_s_used": EIGHT_SUST,
        "host_single_thread_steps_s": HOST_SINGLE,
        "job_steps": JOB_STEPS,
    }}

    print("=" * 78)
    print("ONE DEVICE  (job = 100,082 MeTTa steps, the S15 query job)")
    print("=" * 78)
    rows = [
        ("phone, 1 thread, sustained", SINGLE_SUSTAINED),
        ("phone, 1 thread, duty-cycled", 658_000),
        ("phone, 8-way, burst", EIGHT_BURST),
        ("phone, 8-way, sustained (est)", EIGHT_SUST),
        ("phone, 8-way, sustained (worst round)", EIGHT_SUST_LO),
        ("M4 Pro laptop, 1 thread", HOST_SINGLE),
    ]
    for name, sp in rows:
        jps = jobs_per_device_second(sp)
        print(f"  {name:<40} {sp:>9,} steps/s = {jps:6.2f} jobs/s "
              f"= {jps*3600:9,.0f} jobs/hour")
    out["per_device"] = {n: jobs_per_device_second(s) for n, s in rows}

    print()
    print("=" * 78)
    print("FLEET TPS   (useful accepted jobs/s; replication and audit deducted)")
    print("=" * 78)
    scenarios = [
        # label,            duty_frac, replication, audit_rate
        ("optimistic+audit", 0.25, 1, 0.10),   # run once, 10% re-executed
        ("2-of-2 quorum",    0.25, 2, 0.00),   # every job twice
        ("conservative",     0.10, 2, 0.10),   # fewer devices available, both
    ]
    fleets = [1_000, 10_000, 100_000, 1_000_000]
    for label, duty, rep, audit in scenarios:
        print(f"\n  {label}: duty_frac={duty}, replication={rep}, audit={audit}")
        print(f"    {'devices':>10} {'8-way sust':>14} {'1-thread sust':>15}")
        for n in fleets:
            a = fleet_tps(n, EIGHT_SUST, duty, rep, audit)
            b = fleet_tps(n, SINGLE_SUSTAINED, duty, rep, audit)
            print(f"    {n:>10,} {a:>14,.0f} {b:>15,.0f}")
        out.setdefault("fleet", {})[label] = {
            str(n): {"eight_way": fleet_tps(n, EIGHT_SUST, duty, rep, audit),
                     "one_thread": fleet_tps(n, SINGLE_SUSTAINED, duty, rep, audit)}
            for n in fleets}

    print()
    print("=" * 78)
    print("EQUIVALENCE  (how many phones equal one laptop core, sustained)")
    print("=" * 78)
    print(f"  1 phone  8-way sustained = {EIGHT_SUST/HOST_SINGLE:.2f} laptop cores")
    print(f"  1 phone  1-thread sustained = {SINGLE_SUSTAINED/HOST_SINGLE:.2f} laptop cores")
    print(f"  phones per laptop core (1-thread) = {HOST_SINGLE/SINGLE_SUSTAINED:.1f}")

    print()
    print("=" * 78)
    print("THE NUMBER THAT ACTUALLY BINDS")
    print("=" * 78)
    print("""  A 10,000-device fleet under 2-of-2 quorum sustains ~28,700 jobs/s of the
  100k-step size if every device gives all 8 cores, ~4,800 if each gives one
  thread. The 6x between those is a POLICY choice (how much of a user's
  phone we take), not a hardware fact, and it dominates every other term in
  the model. That is the honest headline:
  fleet TPS is set by how many cores users donate and by the replication
  factor, and only then by the engine. The pitch is not throughput per dollar
  against a datacentre; it is VERIFIED throughput on hardware nobody had to
  buy. Note the equivalence below: one phone at 8-way sustained is 1.6 M4 Pro
  cores. The device is not the weak link. The window and the replication
  factor are.""")

    with open(__file__.replace("tps.py", "tps.json"), "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
