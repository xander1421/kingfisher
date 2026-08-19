#!/usr/bin/env python3
"""H152: is F001 feasible on devices — 1 phone, then 2.

Falsifier (stated first): S25 does not ACCEPT 590d8769, or a live 2-phone
steal (if S24 is quiet) is not faster than S25-only at the same worker count.
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
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_feas"
N1 = 200
JOBS2 = 400
CHUNK = 50


def wait_all(calls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as ex:
        futs = [ex.submit(*c) for c in calls]
        return [f.result() for f in futs]


def adb(serial, *a, timeout=300):
    p = subprocess.run(
        ["adb", "-s", serial, *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout
    )
    if p.returncode != 0:
        raise SystemExit(f"{serial} {a}: {p.stdout}{p.stderr}")
    return p


def gate(serial, override=False) -> tuple[int, str]:
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = serial
    if override:
        e["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = subprocess.run(
        ["bash", "spikes/quiet.sh", "--device"], cwd=ROOT, capture_output=True, text=True, env=e
    )
    text = (p.stdout + p.stderr).strip()
    print(serial, text)
    return p.returncode, text


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    adb(serial, "push", str(TV), f"{DEST}/tv")
    adb(serial, "push", str(F001), f"{DEST}/F001")
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def verify_once(serial: str) -> dict:
    t0 = time.perf_counter()
    p = adb(serial, "shell", f"{DEST}/tv {DEST}/F001")
    dt = time.perf_counter() - t0
    out = p.stdout + p.stderr
    ok = PIN in out and "ACCEPTED" in out
    if not ok:
        raise SystemExit(f"{serial} pin fail:\n{out}")
    return {"wall_s": dt, "digest": PIN, "verdict": "ACCEPTED", "out_tail": out[-400:]}


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


def steal(k25: int, k24: int) -> dict:
    q = Queue(JOBS2, CHUNK)
    calls = [(worker, S25, q)] * k25 + [(worker, S24, q)] * k24
    t0 = time.perf_counter()
    results = wait_all(calls)
    wall = time.perf_counter() - t0
    return {
        "k25": k25,
        "k24": k24,
        "jobs": JOBS2,
        "chunk": CHUNK,
        "wall_s": wall,
        "taken": dict(q.taken),
        "workers": results,
        "jobs_per_s": JOBS2 / wall if wall else 0,
    }


def main() -> int:
    rc25, g25 = gate(S25)
    if rc25 != 0:
        raise SystemExit("S25 gate refused; 1-device test cannot run")
    push(S25)
    once = verify_once(S25)
    print("S25 once", once["wall_s"], once["verdict"])
    t200 = loop(S25, N1)
    print(f"S25 n={N1} wall={t200:.3f}s jobs/s={N1/t200:.1f}")
    t0 = time.perf_counter()
    k2 = wait_all([(loop, S25, 200), (loop, S25, 200)])
    w_k2 = time.perf_counter() - t0
    print(f"S25 k=2 400 jobs wall={w_k2:.3f}s jobs/s={400/w_k2:.1f}")

    two = None
    rc24, g24 = gate(S24, True)
    if rc24 != 0:
        print("S24_SKIP", g24)
    else:
        push(S24)
        two_once = verify_once(S24)
        print("S24 once", two_once["wall_s"], two_once["verdict"])
        stolen = steal(2, 2)
        print(
            f"steal wall={stolen['wall_s']:.3f}s jobs/s={stolen['jobs_per_s']:.1f} "
            f"taken={stolen['taken']}"
        )
        two = {
            "gate": g24,
            "once": two_once,
            "steal": stolen,
            "steal_vs_s25_k2": stolen["wall_s"] / w_k2 if w_k2 else 0,
        }

    out = {
        "pin": PIN,
        "status": "F001_FROZEN",
        "not_a_new_operator_domain": True,
        "one": {
            "serial": S25,
            "gate": g25,
            "once": once,
            "n200_s": t200,
            "n200_jobs_per_s": N1 / t200,
            "k2_400_s": w_k2,
            "k2_jobs_per_s": 400 / w_k2,
            "k2_times": k2,
        },
        "two": two,
        "s24_gate_rc": rc24,
    }
    HERE.joinpath("feas.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("pin", "s24_gate_rc")}, indent=2))
    if once["digest"] != PIN:
        print("ONE_DEVICE_FAIL")
        return 1
    print("ONE_DEVICE_OK")
    if two is None:
        print("TWO_DEVICE_SKIPPED")
        return 0
    if two["steal"]["taken"][S25] + two["steal"]["taken"][S24] != JOBS2:
        print("TWO_DEVICE_FAIL")
        return 1
    print("TWO_DEVICE_SCALE" if two["steal_vs_s25_k2"] < 0.90 else "TWO_DEVICE_NO_WIN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
