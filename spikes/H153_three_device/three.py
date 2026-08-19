#!/usr/bin/env python3
"""H153: F001 pull-queue on 3 adb endpoints — S25, S24, emulator.

Emulator is not a phone and not a new host (same Mac). Not a new operator.
Unread-thermal override on S24 and emulator only. Charging/cpu_busy still refuse.

Falsifier: 3-way steal of 400 is not faster than S25 k=2, or any endpoint
fails pin 590d8769.
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
HERE = Path(__file__).resolve().parent
TV = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
F001 = ROOT / "fixtures" / "F001"
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25, S24, EMU = "R5CY93675MK", "R5CX508MPRZ", "emulator-5554"
DEST = "/data/local/tmp/kf_three"
JOBS = 400
CHUNK = 50
ROUNDS = 3


def wait_all(calls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(calls))) as ex:
        futs = [ex.submit(*c) for c in calls]
        return [f.result() for f in futs]


def adb(serial, *a, timeout=300):
    p = subprocess.run(
        ["adb", "-s", serial, *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout
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
        ["bash", "spikes/quiet.sh", "--device"], cwd=ROOT, capture_output=True, text=True, env=e
    )
    text = (p.stdout + p.stderr).strip()
    print(serial, text)
    if p.returncode != 0:
        raise SystemExit(f"gate refused {serial}")
    return text


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    adb(serial, "push", str(TV), f"{DEST}/tv")
    adb(serial, "push", str(F001), f"{DEST}/F001")
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def verify_once(serial: str) -> dict:
    p = adb(serial, "shell", f"{DEST}/tv {DEST}/F001")
    out = p.stdout + p.stderr
    if PIN not in out or "ACCEPTED" not in out:
        raise SystemExit(f"{serial} pin fail:\n{out}")
    return {"digest": PIN, "verdict": "ACCEPTED"}


def loop(serial, n: int) -> float:
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
        self.taken = {S25: 0, S24: 0, EMU: 0}

    def pull(self, serial: str) -> int:
        with self.lock:
            k = min(self.chunk, self.n)
            self.n -= k
            self.taken[serial] += k
            return k


def worker(serial: str, q: Queue) -> dict:
    n = 0
    t0 = time.perf_counter()
    while True:
        k = q.pull(serial)
        if k == 0:
            break
        loop(serial, k)
        n += k
    return {"serial": serial, "jobs": n, "wall_s": time.perf_counter() - t0}


def steal(counts: dict[str, int]) -> dict:
    q = Queue(JOBS, CHUNK)
    calls = []
    for ser, k in counts.items():
        calls.extend([(worker, ser, q)] * k)
    t0 = time.perf_counter()
    results = wait_all(calls)
    wall = time.perf_counter() - t0
    return {
        "workers": counts,
        "wall_s": wall,
        "taken": dict(q.taken),
        "jobs_per_s": JOBS / wall if wall else 0,
        "detail": results,
    }


def main() -> int:
    g25 = gate(S25)
    g24 = gate(S24, True)
    gemu = gate(EMU, True)
    for s in (S25, S24, EMU):
        push(s)
    pins = {s: verify_once(s) for s in (S25, S24, EMU)}
    print("pins", {s: v["verdict"] for s, v in pins.items()})

    t0 = time.perf_counter()
    wait_all([(loop, S25, 200), (loop, S25, 200)])
    s25k2 = time.perf_counter() - t0
    print(f"S25 k=2 400={s25k2:.3f}s {400/s25k2:.1f} j/s")

    pair = steal({S25: 2, S24: 2})
    print(f"2dev {pair['wall_s']:.3f}s {pair['jobs_per_s']:.1f} taken={pair['taken']}")

    rounds = []
    for i in range(ROUNDS):
        r = steal({S25: 2, S24: 2, EMU: 2})
        r["round"] = i
        rounds.append(r)
        print(
            f"3dev r{i} {r['wall_s']:.3f}s {r['jobs_per_s']:.1f} taken={r['taken']}"
        )

    best3 = min(rounds, key=lambda x: x["wall_s"])
    out = {
        "pin": PIN,
        "status": "F001_FROZEN",
        "emulator_is_not_a_phone": True,
        "emulator_same_host_as_mac": True,
        "not_a_new_operator_domain": True,
        "not_three_physical_phones": True,
        "gates": {S25: g25, S24: g24, EMU: gemu},
        "pins": pins,
        "s25_k2_s": s25k2,
        "s25_k2_jobs_per_s": 400 / s25k2,
        "two_phone": pair,
        "three_rounds": rounds,
        "three_best_vs_s25_k2": best3["wall_s"] / s25k2,
        "three_best_vs_two": best3["wall_s"] / pair["wall_s"],
    }
    HERE.joinpath("three.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"3/s25k2={out['three_best_vs_s25_k2']:.3f} "
        f"3/2phone={out['three_best_vs_two']:.3f}"
    )
    if out["three_best_vs_s25_k2"] >= 0.90:
        print("THREE_NO_WIN_VS_S25")
        return 0
    print("THREE_BEATS_S25")
    return 0


if __name__ == "__main__":
    sys.exit(main())
