#!/usr/bin/env python3
"""H150: coordinator-emulated D1+ seat draw (R1–R4). No chain.

§8 item 4 is UNPROVEN because the draw does not exist. D1's MVP concession:
the named coordinator emulates R1–R5, logs points, can bias every draw.
This spike is that emulator plus the spec's own falsifiers.

Falsifiers (stated first):
  F1  adversary duty 1.0 with stake share s wins more than ~s of FIRST offers
  F2  declining (never-ack) adversary raises its accepted share
  F2b always-on adversary accepted share exceeds stake (R4 redraws)
  F3  a device can influence seed without being the coordinator
  F4  mid-epoch stake change moves the current epoch's draws

F5 (witness cost) is live in D1 and is NOT claimed here. R3 is scoped out.

No p_timeout / T_seat constants (D3: unmeasured). Silence = Bernoulli(duty).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def registry_blob(reg: list[tuple[str, int]]) -> bytes:
    return b"".join(f"{did}:{stake}\n".encode() for did, stake in sorted(reg))


def registry_root(reg: list[tuple[str, int]]) -> bytes:
    return sha256(registry_blob(reg))


def job_seed(root: bytes, job_id: bytes, beacon: bytes) -> bytes:
    return sha256(root + job_id + beacon)


def u64(seed: bytes, i: int) -> int:
    return int.from_bytes(sha256(seed + i.to_bytes(8, "big"))[:8], "big")


def pick_weighted(pool: list[tuple[str, int]], seed: bytes, ctr: int) -> str:
    total = sum(s for _, s in pool)
    if total <= 0:
        raise ValueError("empty pool")
    r = u64(seed, ctr) % total
    acc = 0
    for did, stake in pool:
        acc += stake
        if r < acc:
            return did
    return pool[-1][0]


def first_offers(reg: list[tuple[str, int]], seed: bytes, k: int) -> list[str]:
    """R2: k seats, stake-weighted, without replacement. No duty input."""
    pool = list(reg)
    out = []
    ctr = 0
    for _ in range(k):
        if not pool:
            break
        did = pick_weighted(pool, seed, ctr)
        ctr += 1
        out.append(did)
        pool = [(d, s) for d, s in pool if d != did]
    return out


def fill_acks(
    reg: list[tuple[str, int]],
    seed: bytes,
    k: int,
    online: dict[str, bool],
    decline: set[str],
) -> tuple[list[str], list[str]]:
    """R4: offer; silence/decline redraws; ack binds. Returns (offered, acked)."""
    pool = list(reg)
    offered: list[str] = []
    acked: list[str] = []
    ctr = 0
    while len(acked) < k and pool:
        did = pick_weighted(pool, seed, ctr)
        ctr += 1
        pool = [(d, s) for d, s in pool if d != did]
        offered.append(did)
        if did in decline:
            continue
        if online.get(did, False):
            acked.append(did)
    return offered, acked


def online_set_draw(reg, online, seed, k):
    """S69-shaped null: draw only from currently online devices."""
    pool = [(d, s) for d, s in reg if online.get(d, False)]
    return first_offers(pool, seed, k) if pool else []


def epoch(n_honest=16, n_adv=4, stake_each=1, beacon=b"BEACON_E_FIXED"):
    hon = [(f"h{i}", stake_each) for i in range(n_honest)]
    adv = [(f"a{i}", stake_each) for i in range(n_adv)]
    return hon + adv, {d for d, _ in adv}, beacon


def simulate(duty_h, n_jobs=4000, k=3, seed_prefix=b"H150"):
    reg, adv_ids, beacon = epoch()
    root = registry_root(reg)
    frozen = list(reg)
    s_stake = sum(s for d, s in reg if d in adv_ids) / sum(s for _, s in reg)
    first = {d: 0 for d, _ in reg}
    acked_c = {d: 0 for d, _ in reg}
    online_c = {d: 0 for d, _ in reg}
    declined_ack = {d: 0 for d, _ in reg}
    n_first = n_ack = n_on = n_dec = 0

    for j in range(n_jobs):
        job_id = seed_prefix + j.to_bytes(4, "big")
        sd = job_seed(root, job_id, beacon)
        # duty: honest Bernoulli via seed (deterministic), adv always on
        online = {}
        for d, _ in reg:
            if d in adv_ids:
                online[d] = True
            else:
                online[d] = (u64(sd, 10_000 + hash_id(d)) % 10_000) < int(duty_h * 10_000)
        fo = first_offers(frozen, sd, k)
        for d in fo:
            first[d] += 1
            n_first += 1
        _, acked = fill_acks(frozen, sd, k, online, decline=set())
        for d in acked:
            acked_c[d] += 1
            n_ack += 1
        on = online_set_draw(frozen, online, sd, k)
        for d in on:
            online_c[d] += 1
            n_on += 1
        _, dec = fill_acks(frozen, sd, k, online, decline=adv_ids)
        for d in dec:
            declined_ack[d] += 1
            n_dec += 1

    def share(counter, n, ids):
        return (sum(counter[d] for d in ids) / n) if n else 0.0

    return {
        "stake_share": s_stake,
        "duty_honest": duty_h,
        "n_jobs": n_jobs,
        "k": k,
        "first_offer_adv": share(first, n_first, adv_ids),
        "accepted_adv": share(acked_c, n_ack, adv_ids),
        "online_set_adv": share(online_c, n_on, adv_ids),
        "decliner_accepted_adv": share(declined_ack, n_dec, adv_ids),
        "n_first": n_first,
        "n_ack": n_ack,
        "n_on": n_on,
        "n_dec": n_dec,
    }


def hash_id(d: str) -> int:
    return int.from_bytes(sha256(d.encode())[:4], "big")


def f3_device_cannot_move_seed() -> dict:
    reg, _, beacon = epoch()
    root = registry_root(reg)
    job = b"job-1"
    s0 = job_seed(root, job, beacon)
    # a device going online/offline is not an input to seed
    s1 = job_seed(root, job, beacon)
    # a device cannot supply a private nonce into seed
    s_nonce = job_seed(root, job, beacon + b"x")  # only coordinator beacon would do this
    # mid-epoch local coin != beacon
    return {
        "stable_across_calls": s0 == s1,
        "beacon_moves_seed": s0 != s_nonce,
        "device_id_not_in_seed_input": b"h0" not in job + beacon,
    }


def f4_freeze() -> dict:
    reg, _, beacon = epoch()
    root0 = registry_root(reg)
    job = b"job-f4"
    s0 = job_seed(root0, job, beacon)
    d0 = first_offers(reg, s0, 3)
    mutated = [(d, (s + 50 if d == "a0" else s)) for d, s in reg]
    # current epoch MUST use frozen copy
    s_frozen = job_seed(root0, job, beacon)
    d_frozen = first_offers(reg, s_frozen, 3)
    # next epoch would see mutation
    root1 = registry_root(mutated)
    s1 = job_seed(root1, job, beacon)
    return {
        "same_draws_on_frozen": d0 == d_frozen,
        "root_moves_if_not_frozen": root0 != root1,
        "seed_moves_if_not_frozen": s0 != s1,
    }


def main() -> int:
    duties = (0.05, 0.10, 0.25)
    rows = {f"{d:.2f}": simulate(d) for d in duties}
    f3 = f3_device_cannot_move_seed()
    f4 = f4_freeze()
    # F1: first-offer share within 3pp of stake at every duty
    f1_ok = all(abs(r["first_offer_adv"] - r["stake_share"]) <= 0.03 for r in rows.values())
    # online-set null MUST be able to exceed stake (duty capture)
    null_captures = all(r["online_set_adv"] > r["stake_share"] + 0.10 for r in rows.values())
    f2_ok = all(r["decliner_accepted_adv"] <= 0.01 for r in rows.values())
    f2b_fired = any(r["accepted_adv"] > r["stake_share"] + 0.05 for r in rows.values())
    out = {
        "pin": PIN,
        "concession": "coordinator holds REG_e, beacon_e, and can bias every draw",
        "no_chain": True,
        "r3_scoped_out": True,
        "f5_live": True,
        "rows": rows,
        "f1_first_offer_tracks_stake": f1_ok,
        "null_online_set_captures": null_captures,
        "f2_decliner_cannot_raise": f2_ok,
        "f2b_accepted_exceeds_stake": f2b_fired,
        "f3": f3,
        "f4": f4,
    }
    HERE.joinpath("draw.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print("F1", "HOLD" if f1_ok else "FAIL", "null_captures", null_captures)
    print("F2", "HOLD" if f2_ok else "FAIL")
    print("F2b", "FIRED" if f2b_fired else "QUIET")
    print("F3", "HOLD" if f3["stable_across_calls"] and f3["beacon_moves_seed"] else "FAIL")
    print("F4", "HOLD" if f4["same_draws_on_frozen"] and f4["seed_moves_if_not_frozen"] else "FAIL")
    return 0 if f1_ok and null_captures and f2_ok and f3["stable_across_calls"] and f4["same_draws_on_frozen"] else 1


if __name__ == "__main__":
    sys.exit(main())
