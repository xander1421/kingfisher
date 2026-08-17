#!/usr/bin/env python3
"""S55 - does locality-aware matching buy anything, and where is the knee?

GRADE D BY CONSTRUCTION. This is a simulation. It measures the coordination
layer (matcher + cache + churn), which is server software we would write, and
it takes every device-side constant as a PARAMETER from spikes that ran on
real hardware. It does not simulate silicon and must never be cited as if it
had.

What is simulated (unmeasured anywhere in this workspace):
  - cache hit rate across a fleet as the graph grows past total fleet cache
  - whether locality-aware matching beats random placement -- GAP row 18 /
    PROPOSAL_DRAFT wedge #2, which has zero measurements behind it
  - the load imbalance locality matching causes by piling popular shards on
    whichever devices already hold them

What is NOT simulated: throughput, energy, thermals, WorkManager windows.
Those are device facts. See S30/S32/S54.

Reported unit is FETCHES PER JOB, not seconds. Per LEDGER rule 1: a
machine-independent invariant, not a wall-clock that moves with whatever
else the laptop is doing.

The null (LEDGER rule 4) is `random` placement, and §demo proves it fires.
The matcher never sees the query distribution or ground truth (rule 5) --
it decides from advertised cached CIDs only, which is what a real bid
carries.
"""

import json
import random
import sys
from collections import OrderedDict

# ---- device-side constants, MEASURED elsewhere, used only as parameters ----
# S54: a background worker reaches 4 cores (cpuset 0-1,4-5), not 8.
# S30: 383k steps/s sustained single-thread. S15: job = 100,082 steps.
# Fetch cost is expressed in job-equivalents so the sim stays unit-free.
JOB_STEPS = 100_082


class Device:
    __slots__ = ("idx", "lru", "cap", "jobs")

    def __init__(self, idx, cap):
        self.idx = idx
        self.cap = cap
        self.lru = OrderedDict()   # shard_id -> None, oldest first
        self.jobs = 0

    def has(self, shard):
        return shard in self.lru

    def touch(self, shard, holders):
        """Record a use, maintaining the global holder index.

        Returns True if it was a miss (i.e. a fetch was required).
        """
        if shard in self.lru:
            self.lru.move_to_end(shard)
            return False
        self.lru[shard] = None
        holders.setdefault(shard, set()).add(self.idx)
        while len(self.lru) > self.cap:
            evicted, _ = self.lru.popitem(last=False)
            h = holders.get(evicted)
            if h is not None:
                h.discard(self.idx)
                if not h:
                    del holders[evicted]
        return True


def zipf_weights(n, a):
    w = [1.0 / (i + 1) ** a for i in range(n)]
    t = sum(w)
    return [x / t for x in w]


def cumulative(w):
    c, acc = [], 0.0
    for x in w:
        acc += x
        c.append(acc)
    return c


def pick(cum, r):
    """Inverse-CDF sample. Linear scan is fine at these sizes and is obvious."""
    lo, hi = 0, len(cum) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if r <= cum[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


K_CANDIDATES = 8   # power-of-k-choices; a matcher samples bids, it does not
                   # poll the fleet. Both policies get the same k, so the
                   # comparison is not confounded by candidate-set size.


def run(n_devices, n_shards, cache_cap, n_jobs, policy, zipf_a,
        duty, seed, warmup_frac=0.3, k=K_CANDIDATES, prefill=False):
    """One configuration. Returns dict of invariants.

    policy: 'random' (the null) or 'locality'.
    duty:   probability a given device is online for a given job -- the
            charge-time premise, applied independently per job.
    warmup_frac: leading jobs excluded from the statistics so we measure the
                 steady state, not the cold fleet. Reported, never hidden.
    """
    rng = random.Random(seed)
    devices = [Device(i, cache_cap) for i in range(n_devices)]
    holders = {}                       # shard -> set of device idx holding it
    cum = cumulative(zipf_weights(n_shards, zipf_a))

    if prefill:
        # Force universal replication. NOT reachable by running the policy:
        # locality is self-reinforcing, so non-holders never acquire and
        # holders never approaches N. The inert-control state has to be
        # constructed, not warmed into.
        assert cache_cap >= n_shards, 'prefill needs cap >= shards'
        for d in devices:
            for sh in range(n_shards):
                d.touch(sh, holders)

    warmup = int(n_jobs * warmup_frac)
    fetches = hits = counted = 0
    counted_loads = [0] * n_devices
    randrange, rnd = rng.randrange, rng.random
    # Damping draws from its OWN stream. Sharing `rnd` makes `damped`
    # consume a different number of draws than `locality`, so the two
    # runs diverge and are not paired even at an identical seed — the
    # control caught exactly that.
    dcoin = random.Random(seed ^ 0x5EED).random

    def sample_online(k_):
        """k_ uniformly-drawn devices that are online right now. Never empty:
        a fleet with nobody online cannot be scheduled at all, and modelling
        that as a stall would confound the cache measurement with a queueing
        one. Falls back to one forced draw."""
        out = []
        for _ in range(k_):
            d = devices[randrange(n_devices)]
            if rnd() < duty:
                out.append(d)
        return out or [devices[randrange(n_devices)]]

    for j in range(n_jobs):
        shard = pick(cum, rnd())
        fallback = sample_online(k)

        if policy in ("locality", "damped", "damped_c"):
            h = holders.get(shard)
            cands = []
            # k8s `scaledImageScore`: locality preference is scaled by how widely
            # the artefact is ALREADY replicated (`holders/N`), to fight what they
            # name the "node heating problem" — S61's own 102x imbalance.
            # A shard held by one device exerts near-zero pull, so following
            # locality cannot concentrate load on it.
            #
            # `damped`   = the literal k8s port, holders/N.
            # `damped_c` = the same principle renormalised to THIS fleet's
            #   achievable replication. k8s images sit on an O(1) fraction of
            #   nodes; our shards sit on ~coverage = N*C/S devices out of N,
            #   which is O(1/N). The literal port therefore disables locality
            #   almost always. Renormalising against coverage keeps the intent
            #   — do not chase a singleton — without switching the mechanism off.
            use_locality = True
            if h is not None:
                if policy == "damped":
                    use_locality = dcoin() < (len(h) / n_devices)
                elif policy == "damped_c":
                    cov = max(1.0, n_devices * cache_cap / n_shards)
                    use_locality = dcoin() < min(1.0, len(h) / cov)
            if h and use_locality:
                # A bid is only usable if that device is online right now.
                for idx in (h if len(h) <= k else rng.sample(sorted(h), k)):
                    if rnd() < duty:
                        cands.append(devices[idx])
            dev = min(cands or fallback, key=lambda d: d.jobs)
        elif policy == "random":
            dev = min(fallback, key=lambda d: d.jobs)
        else:
            raise ValueError(policy)

        miss = dev.touch(shard, holders)
        dev.jobs += 1
        if j >= warmup:
            counted += 1
            counted_loads[dev.idx] += 1
            if miss:
                fetches += 1
            else:
                hits += 1

    mean_load = counted / n_devices
    max_load = max(counted_loads)
    return {
        "policy": policy,
        "n_devices": n_devices,
        "n_shards": n_shards,
        "cache_cap": cache_cap,
        "fleet_cache": n_devices * cache_cap,
        "coverage": n_devices * cache_cap / n_shards,
        "zipf_a": zipf_a,
        "duty": duty,
        "jobs_counted": counted,
        "warmup_frac": warmup_frac,
        "hit_rate": hits / counted,
        "fetches_per_job": fetches / counted,
        "load_imbalance": max_load / mean_load if mean_load else float("nan"),
    }


# ------------------------------------------------------------------ controls
def demo():
    """LEDGER rule 4 + 7: prove the null fires, and gate on a closed form.

    Every assert here is a control that has to be capable of failing.
    """
    # 1. The null MUST fire: cache of 1, many shards, and UNIFORM demand, so
    #    there is no popular working set for a cache to hold. Essentially
    #    every job is a fetch under either policy. If this passes trivially
    #    the harness is not measuring anything.
    #    (Written first with zipf_a=1.0 and it failed at 0.62 for locality --
    #     correctly: under skew a 1-slot cache still holds the hot head. The
    #     control was wrong, not the sim. Kept as a note per LEDGER rule 7.)
    for pol in ("random", "locality"):
        r = run(50, 5_000, 1, 20_000, pol, zipf_a=0.0, duty=1.0, seed=1)
        assert r["fetches_per_job"] > 0.95, (pol, r["fetches_per_job"])

    # 2. The opposite end MUST also fire: cache big enough to hold the whole
    #    graph means zero fetches in the steady state.
    r = run(20, 40, 40, 20_000, "locality", 1.0, 1.0, seed=2)
    assert r["fetches_per_job"] < 0.001, r["fetches_per_job"]

    # 3. Plausibility gate on the RANDOM null against a closed form.
    #    Uniform queries (a=0), one device (no matching possible), cache C of
    #    S shards: steady-state hit rate under LRU with uniform demand is
    #    ~C/S. If the sim disagrees with that by more than a few points the
    #    instrument is broken, not the finding.
    S_, C_ = 200, 50
    r = run(1, S_, C_, 60_000, "random", 0.0, 1.0, seed=3)
    expected = C_ / S_
    assert abs(r["hit_rate"] - expected) < 0.05, (r["hit_rate"], expected)

    # 4. Locality must never be WORSE than random on hit rate at equal config.
    #    (It may be worse on load imbalance -- that is a real finding, not a bug.)
    a = run(200, 2_000, 20, 40_000, "random", 1.0, 0.25, seed=4)
    b = run(200, 2_000, 20, 40_000, "locality", 1.0, 0.25, seed=4)
    assert b["hit_rate"] >= a["hit_rate"], (a["hit_rate"], b["hit_rate"])

    print("demo: 4/4 controls pass (null fires at both ends, closed-form gate, ordering)")


# -------------------------------------------------------------------- sweeps
def sweep(n_jobs, seed):
    out = []
    # Axis 1: graph size, fleet held constant. This is where the knee is.
    for n_shards in (100, 300, 1_000, 3_000, 10_000, 30_000, 100_000):
        for pol in ("random", "locality"):
            out.append(run(1_000, n_shards, 20, n_jobs, pol, 1.0, 0.25, seed))
    # Axis 2: fleet size, graph held constant at 10k shards.
    for n_dev in (100, 300, 1_000, 3_000, 10_000):
        for pol in ("random", "locality"):
            out.append(run(n_dev, 10_000, 20, n_jobs, pol, 1.0, 0.25, seed))
    # Axis 3: query skew, at the operating point. Uniform is the hard case.
    for a in (0.0, 0.5, 1.0, 1.5):
        for pol in ("random", "locality"):
            out.append(run(1_000, 10_000, 20, n_jobs, pol, a, 0.25, seed))
    # Axis 4: duty cycle -- how much locality survives the fleet being mostly
    # offline, which is the charge-time premise.
    for duty in (0.05, 0.10, 0.25, 0.50, 1.00):
        for pol in ("random", "locality"):
            out.append(run(1_000, 10_000, 20, n_jobs, pol, 1.0, duty, seed))
    return out


def table(rows, key, title, fmt="{}"):
    print(f"\n{title}")
    print(f"{key:>10} | {'coverage':>8} | {'hit random':>10} | {'hit local':>9} | "
          f"{'fetch/job r':>11} | {'fetch/job l':>11} | {'gain':>5} | {'imbal l':>7}")
    print("-" * 96)
    seen = []
    for r in rows:
        v = r[key]
        if v in seen:
            continue
        seen.append(v)
        a = next(x for x in rows if x[key] == v and x["policy"] == "random")
        b = next(x for x in rows if x[key] == v and x["policy"] == "locality")
        gain = a["fetches_per_job"] / b["fetches_per_job"] if b["fetches_per_job"] else float("inf")
        print(f"{fmt.format(v):>10} | {a['coverage']:8.3f} | {a['hit_rate']:10.4f} | "
              f"{b['hit_rate']:9.4f} | {a['fetches_per_job']:11.4f} | "
              f"{b['fetches_per_job']:11.4f} | {gain:5.2f}x | {b['load_imbalance']:7.2f}")


def main():
    n_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0xC0FFEE

    demo()
    rows = sweep(n_jobs, seed)

    n = len(rows) // 4
    print(f"\njobs per cell {n_jobs:,} (first 30% discarded as warmup) · seed {seed:#x}"
          f" · cache 20 shards/device · GRADE D (simulation)")

    table(rows[:14], "n_shards", "AXIS 1 - graph size, 1,000 devices, duty 0.25, zipf 1.0", "{}")
    table(rows[14:24], "n_devices", "AXIS 2 - fleet size, 10,000 shards, duty 0.25, zipf 1.0", "{}")
    table(rows[24:32], "zipf_a", "AXIS 3 - query skew, 1,000 devices, 10,000 shards", "{:.1f}")
    table(rows[32:], "duty", "AXIS 4 - fraction of fleet online, 1,000 dev, 10,000 shards", "{:.2f}")

    with open("fleetsim.json", "w") as f:
        json.dump({"n_jobs": n_jobs, "seed": seed, "grade": "D (simulation)",
                   "rows": rows}, f, indent=1)
    print("\nwrote fleetsim.json")


if __name__ == "__main__":
    main()
