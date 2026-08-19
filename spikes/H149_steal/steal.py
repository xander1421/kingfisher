#!/usr/bin/env python3
"""H149: pull-based chunks, no a-priori 3:1.

A peer write-up treated retracted H141 sums (6.87s / 5.17s) as
max(fast,slow) and called that a straggler model. 200×24.3 ms = 4.86 s,
not 6.87 s. 5.17 s = 2.50+2.67, not max(2.49, 2.43). Mission is not
achieved (Gate 3 open, §8 UNPROVEN, 0 ACCEPTED).

H148 showed a *known* 3:1 split scales once the harness is actually
parallel. This spike asks whether a pull queue reaches that wall
without being told the ratio.

Falsifier (stated first): steal wall of 400 is not < 0.90 of static 1:1
AND not within 20% of oracle 3:1 k=2 (steal_wall > 1.20 * oracle_wall).
Then pulling does not replace knowing the weights.

Operator unread-thermal on S24 only. Not a new ISA or operator domain.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TV = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
F001 = ROOT / "fixtures" / "F001"
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_scale"
HERE = Path(__file__).resolve().parent
JOBS = 400
CHUNK = 50


def wait_all(calls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as ex:
        futs = [ex.submit(*c) for c in calls]
        return [f.result() for f in futs]


def adb(serial, *a, timeout=300):
    p = subprocess.run(
        ["adb", "-s", serial, *a],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if p.returncode != 0:
        raise SystemExit(f"{serial} {a}: {p.stdout}{p.stderr}")
    return p


def gate(serial, override=False) -> str:
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = serial
    if override:
        e["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = subprocess.run(
        ["bash", "spikes/quiet.sh", "--device"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=e,
    )
    text = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        raise SystemExit(f"gate {serial}: {text}")
    print(serial, text)
    return text


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    adb(serial, "push", str(TV), f"{DEST}/tv")
    adb(serial, "push", str(F001), f"{DEST}/F001")
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def loop(serial, n):
    if n <= 0:
        return 0.0
    script = (
        f"i=0; while [ $i -lt {n} ]; do "
        f"{DEST}/tv {DEST}/F001 | grep -q {PIN[:16]} || exit 2; "
        f"i=$((i+1)); done; echo LOOP_OK n={n}"
    )
    t0 = time.perf_counter()
    p = adb(serial, "shell", script)
    dt = time.perf_counter() - t0
    if "LOOP_OK" not in p.stdout:
        raise SystemExit(p.stdout + p.stderr)
    return dt


class Queue:
    def __init__(self, n: int, chunk: int):
        self.n = n
        self.chunk = chunk
        self.lock = threading.Lock()
        self.taken = {S25: 0, S24: 0}

    def pull(self, serial: str) -> int:
        with self.lock:
            k = min(self.chunk, self.n)
            self.n -= k
            self.taken[serial] += k
            return k


def worker(serial: str, q: Queue) -> dict:
    chunks = []
    t0 = time.perf_counter()
    while True:
        k = q.pull(serial)
        if k == 0:
            break
        dt = loop(serial, k)
        chunks.append({"n": k, "s": dt})
    return {"serial": serial, "wall_s": time.perf_counter() - t0, "chunks": chunks}


def steal(k25: int, k24: int, jobs: int, chunk: int) -> dict:
    q = Queue(jobs, chunk)
    calls = [(worker, S25, q)] * k25 + [(worker, S24, q)] * k24
    t0 = time.perf_counter()
    results = wait_all(calls)
    wall = time.perf_counter() - t0
    return {
        "k25": k25,
        "k24": k24,
        "jobs": jobs,
        "chunk": chunk,
        "wall_s": wall,
        "taken": dict(q.taken),
        "workers": results,
        "jobs_per_s": jobs / wall if wall else 0,
    }


def main() -> int:
    g25 = gate(S25)
    g24 = gate(S24, True)
    push(S25)
    push(S24)

    t0 = time.perf_counter()
    one_one = wait_all([(loop, S25, 200), (loop, S24, 200)])
    w11 = time.perf_counter() - t0

    t0 = time.perf_counter()
    oracle = wait_all(
        [(loop, S25, 150), (loop, S25, 150), (loop, S24, 50), (loop, S24, 50)]
    )
    w_or = time.perf_counter() - t0

    t0 = time.perf_counter()
    s25k2 = wait_all([(loop, S25, 200), (loop, S25, 200)])
    w25 = time.perf_counter() - t0

    stolen = steal(2, 2, JOBS, CHUNK)

    out = {
        "pin": PIN,
        "thermal_override": "QUIET_ALLOW_THERMAL_UNREADABLE=1",
        "not_a_new_isa": True,
        "not_a_new_operator_domain": True,
        "peer_claim_decay": {
            "cited_one_one_as_max": 6.874,
            "arith_200_x_24_3ms": 200 * 0.0243,
            "cited_three_one_as_parallel": 5.173,
            "if_parallel_would_be_max": "max(2.50, 2.67)≈2.67, not 5.17",
            "mission_not_achieved": [
                "Gate 3 open (8c46ea20 unmatched)",
                "F001_DRAFT",
                "section-8 UNPROVEN",
                "0 ACCEPTED",
                "two phones are not operator=2",
            ],
        },
        "gates": {S25: g25, S24: g24},
        "one_one": {
            "s25_s": one_one[0],
            "s24_s": one_one[1],
            "wall_s": w11,
        },
        "oracle_3_1_k2": {
            "times_s": oracle,
            "wall_s": w_or,
            "jobs_per_s": JOBS / w_or if w_or else 0,
        },
        "s25_k2": {"times_s": s25k2, "wall_s": w25, "jobs_per_s": JOBS / w25 if w25 else 0},
        "steal": stolen,
        "steal_vs_one_one": stolen["wall_s"] / w11 if w11 else 0,
        "steal_vs_oracle": stolen["wall_s"] / w_or if w_or else 0,
        "steal_vs_s25_k2": stolen["wall_s"] / w25 if w25 else 0,
    }
    HERE.joinpath("steal.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(
        f"1:1={w11:.3f} oracle3:1k2={w_or:.3f} s25k2={w25:.3f} "
        f"steal={stolen['wall_s']:.3f} taken={stolen['taken']}"
    )
    beats_11 = stolen["wall_s"] < 0.90 * w11
    near_oracle = stolen["wall_s"] <= 1.20 * w_or
    print("STEAL_BEATS_1_1" if beats_11 else "STEAL_LOSES_TO_1_1")
    print("STEAL_NEAR_ORACLE" if near_oracle else "STEAL_FAR_FROM_ORACLE")
    if not beats_11 and not near_oracle:
        print("STEAL_NO_HELP")
        return 0
    print("STEAL_HELPS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
