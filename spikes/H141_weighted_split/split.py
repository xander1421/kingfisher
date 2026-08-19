#!/usr/bin/env python3
"""H141: 400 F001 verifies, 1:1 vs 3:1 split. Needs both phones."""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_scale"


def adb(s, *a, timeout=300):
    p = subprocess.run(["adb", "-s", s, *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"{s} {a}: {p.stdout}{p.stderr}")
    return p


def gate(s, override=False):
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = s
    if override:
        e["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = subprocess.run(["bash", "spikes/quiet.sh", "--device"], cwd=ROOT, capture_output=True, text=True, env=e)
    if p.returncode != 0:
        raise SystemExit(p.stdout + p.stderr)
    print(s, (p.stdout + p.stderr).strip())


def loop(serial, n):
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


def wait_all(calls):
    """Submit every call, then wait. A tuple of submit().result() is sequential."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as ex:
        futs = [ex.submit(*c) for c in calls]
        return [f.result() for f in futs]


def main() -> int:
    gate(S25)
    gate(S24, True)
    t0 = time.perf_counter()
    t25_11, t24_11 = wait_all([(loop, S25, 200), (loop, S24, 200)])
    w11 = time.perf_counter() - t0
    t0 = time.perf_counter()
    t25_31, t24_31 = wait_all([(loop, S25, 300), (loop, S24, 100)])
    w31 = time.perf_counter() - t0
    t25_only = loop(S25, 400)
    out = {
        "pin": PIN,
        "one_one": {"s25_n": 200, "s24_n": 200, "s25_s": t25_11, "s24_s": t24_11, "wall_s": w11},
        "three_one": {"s25_n": 300, "s24_n": 100, "s25_s": t25_31, "s24_s": t24_31, "wall_s": w31},
        "s25_only_400_s": t25_only,
        "weighted_vs_one_one": w31 / w11,
    }
    Path(__file__).with_name("split.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(f"1:1={w11:.3f} 3:1={w31:.3f} ratio={w31/w11:.3f} s25only={t25_only:.3f}")
    print("WEIGHTING_HELPS" if w31 < 0.85 * w11 else "WEIGHTING_NO_HELP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
