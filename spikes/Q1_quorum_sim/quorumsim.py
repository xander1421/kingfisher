#!/usr/bin/env python3
"""Q1 — the join: S61's fleet model + S49's canonical envelope, adjudicated by
majority-of-quorum. Answers C4 (rare-shard Sybil), which went live again when
W1 was invalidated.

Reports COUNTS AND OUTCOMES ONLY — never a duration. That is deliberate: it is
why this runs through a refused host gate, and it is the property that let S61
survive on a contended machine.

Execution speed is a PARAMETER, not a simulation: S71 measured 2.83 jobs/s
(1 worker) and 11.17 (4 workers) and those are inputs here, exactly as
S32/tps.py treats device constants.

  python3 quorumsim.py            # scenarios + controls
  python3 quorumsim.py --json
"""
import hashlib, random, sys, json
from collections import OrderedDict, Counter

SEED = 20260817
QUORUM = 3
# S71 measured; parameters, not simulated
JOBS_PER_DEV_1W, JOBS_PER_DEV_4W = 2.83, 11.17

def canon_digest(payload, form="SORTED_SET"):
    """S49's canonicalise, reduced to the two forms a job class actually uses."""
    items = sorted(set(payload)) if form == "SORTED_SET" else \
            sorted(payload) if form == "SORTED_BAG" else list(payload)
    h = hashlib.sha256()
    for it in items:                      # length-prefixed: S49 rule 3
        b = str(it).encode()
        h.update(len(b).to_bytes(4, "little")); h.update(b)
    return h.hexdigest()[:16]

class Device:
    """S61's Device (idx, lru, cap, jobs) + the three fields the join needs."""
    __slots__ = ("idx", "cap", "lru", "jobs", "operator_id", "honest", "policy")
    def __init__(self, idx, cap, operator_id, honest=True, policy="echo"):
        self.idx, self.cap = idx, cap
        self.lru = OrderedDict(); self.jobs = 0
        self.operator_id, self.honest, self.policy = operator_id, honest, policy
    def holds(self, shard): return shard in self.lru
    def admit(self, shard, holders):
        if shard in self.lru: self.lru.move_to_end(shard); return
        self.lru[shard] = None; holders.setdefault(shard, set()).add(self.idx)
        while len(self.lru) > self.cap:
            old, _ = self.lru.popitem(last=False)
            holders.get(old, set()).discard(self.idx)
    def execute(self, job_id, truth, peer_digest=None):
        """Honest → canonical digest of truth. Dishonest → corrupt, or echo a peer."""
        self.jobs += 1
        if self.honest:
            return canon_digest(truth)
        if self.policy == "echo" and peer_digest is not None:
            return peer_digest                      # collusion: agree with a confederate
        return canon_digest(list(truth) + ["FORGED"])

def adjudicate(envelopes):
    """Majority of a quorum — GUARDRAILS C5, from BOINC sample_bitwise_validator."""
    c = Counter(envelopes)
    top, n = c.most_common(1)[0]
    return (top, True) if n * 2 > len(envelopes) else (None, False)

def run(N, S, cap, adv_operators, devices_per_adv, target_shard_pool,
        rounds=2000, rnd=None):
    rnd = rnd or random.Random(SEED)
    devs, holders = [], {}
    idx = 0
    # honest fleet
    for _ in range(N):
        devs.append(Device(idx, cap, operator_id=f"h{idx}", honest=True)); idx += 1
    # adversary: few operators, many devices each, all seeded onto the target shard
    adv_ids = []
    for op in range(adv_operators):
        for _ in range(devices_per_adv):
            d = Device(idx, cap, operator_id=f"adv{op}", honest=False, policy="echo")
            devs.append(d); adv_ids.append(idx); idx += 1
    # populate: honest devices hold a random spread; adversary camps the target shard
    for d in devs:
        if not d.honest:
            d.admit(0, holders)                      # shard 0 is the "rare" target
        else:
            for _ in range(cap):
                d.admit(rnd.randrange(S), holders)
    # Force the honest pool of shard 0 to EXACTLY the requested size.
    # The first version only added, so random honest holders inflated the pool
    # and the x-axis was not the quantity it claimed -- capture rate came out
    # non-monotone (23.9% at "pool 10" vs 18.1% at "pool 5") because "pool 10"
    # actually had a SMALLER real pool. Evict as well as admit.
    honest_pool = [d for d in devs if d.honest and d.holds(0)]
    while len(honest_pool) > target_shard_pool:
        d = honest_pool.pop()
        d.lru.pop(0, None); holders.get(0, set()).discard(d.idx)
    while len(honest_pool) < target_shard_pool:
        cand = rnd.choice([d for d in devs if d.honest and not d.holds(0)])
        cand.admit(0, holders); honest_pool.append(cand)
    assert len([d for d in devs if d.honest and d.holds(0)]) == target_shard_pool

    pool = [d for d in devs if d.holds(0)]
    captured = wrong_accepted = no_majority = 0
    for r in range(rounds):
        seats = rnd.sample(pool, min(QUORUM, len(pool)))
        truth = [f"atom{r}", f"atom{r}b"]
        # colluders echo the first adversarial seat's digest
        first_adv = next((s for s in seats if not s.honest), None)
        shared = canon_digest(list(truth) + ["FORGED"]) if first_adv else None
        envs = [s.execute(r, truth, peer_digest=shared) for s in seats]
        verdict, ok = adjudicate(envs)
        if not ok: no_majority += 1
        elif verdict != canon_digest(truth): wrong_accepted += 1
        adv_seats = sum(1 for s in seats if not s.honest)
        if adv_seats * 2 > len(seats): captured += 1
    return {"pool": len(pool), "adv_in_pool": sum(1 for d in pool if not d.honest),
            "rounds": rounds, "captured": captured/rounds,
            "wrong_accepted": wrong_accepted/rounds, "no_majority": no_majority/rounds}

def main():
    out = {"seed": SEED, "quorum": QUORUM,
           "supply_param_jobs_s": {"1w": JOBS_PER_DEV_1W, "4w": JOBS_PER_DEV_4W},
           "scenarios": {}, "controls": {}}
    rnd = random.Random(SEED)

    # ---- controls first, each with a stated failing input (D6) ----
    # C1 null: an all-honest fleet must reach majority every round and accept truth.
    c1 = run(200, 500, 8, adv_operators=0, devices_per_adv=0,
             target_shard_pool=25, rounds=500, rnd=random.Random(1))
    out["controls"]["all_honest_always_agrees"] = {
        "wrong_accepted": c1["wrong_accepted"], "no_majority": c1["no_majority"],
        "pass": c1["wrong_accepted"] == 0 and c1["no_majority"] == 0,
        "fails_if": "any wrong verdict or any failed majority in an honest fleet"}
    # C2 positive: one operator holding 2/3 of a rare shard's pool must capture it.
    c2 = run(200, 500, 8, adv_operators=1, devices_per_adv=6,
             target_shard_pool=3, rounds=500, rnd=random.Random(2))
    out["controls"]["one_operator_captures_rare_shard"] = {
        "adv_in_pool": c2["adv_in_pool"], "pool": c2["pool"],
        "wrong_accepted": c2["wrong_accepted"],
        "pass": c2["wrong_accepted"] > 0.5,
        "fails_if": "an operator owning most of a 3-device pool does NOT get wrong results accepted"}

    # ---- the C4 question: capture rate vs honest pool size ----
    for hp in (3, 5, 10, 25, 50, 100):
        r = run(400, 500, 8, adv_operators=1, devices_per_adv=5,
                target_shard_pool=hp, rounds=1500, rnd=random.Random(hp))
        out["scenarios"][f"honest_pool_{hp}"] = r

    if "--json" in sys.argv: print(json.dumps(out, indent=2)); return
    print(f"Q1 quorum simulation — seed {SEED}, quorum {QUORUM}, counts only (no timings)\n")
    print("  controls:")
    for k, v in out["controls"].items():
        print(f"    {'PASS' if v['pass'] else '*** FAIL ***':<14} {k}")
        print(f"                   fails if: {v['fails_if']}")
    print(f"\n  C4 — one adversarial operator with 5 devices camped on a rare shard:")
    print(f"  {'honest pool':>12} {'pool':>6} {'adv':>5} {'seats captured':>15} {'wrong accepted':>15}")
    for k, v in out["scenarios"].items():
        print(f"  {k.split('_')[-1]:>12} {v['pool']:>6} {v['adv_in_pool']:>5} "
              f"{v['captured']:>14.1%} {v['wrong_accepted']:>15.1%}")
    assert all(v["pass"] for v in out["controls"].values()), "a control failed"

main()
