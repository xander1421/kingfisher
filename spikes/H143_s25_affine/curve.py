#!/usr/bin/env python3
"""H142: S25 F001 verify wall vs N. Rate only if fit_or_refuse + check_affine pass."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
from units import ModelRefused, check_affine, fit_or_refuse  # noqa: E402

PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25 = "R5CY93675MK"
DEST = "/data/local/tmp/kf_scale"
NS = (50, 100, 200, 400, 800)


def adb(*a, timeout=300):
    import subprocess
    p = subprocess.run(["adb", "-s", S25, *a], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(p.stdout + p.stderr)
    return p


def gate():
    import subprocess
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = S25
    p = subprocess.run(["bash", "spikes/quiet.sh", "--device"], cwd=ROOT, capture_output=True, text=True, env=e)
    if p.returncode != 0:
        raise SystemExit(p.stdout + p.stderr)
    print(p.stdout + p.stderr)


def loop(n: int) -> float:
    script = (
        f"i=0; while [ $i -lt {n} ]; do "
        f"{DEST}/tv {DEST}/F001 | grep -q {PIN[:16]} || exit 2; "
        f"i=$((i+1)); done; echo LOOP_OK n={n}"
    )
    t0 = time.perf_counter()
    p = adb("shell", script, timeout=600)
    dt = time.perf_counter() - t0
    if "LOOP_OK" not in p.stdout:
        raise SystemExit(p.stdout + p.stderr)
    return dt


def main() -> int:
    gate()
    adb("shell", f"test -x {DEST}/tv && test -d {DEST}/F001")
    points = []
    for n in NS:
        dt = loop(n)
        points.append((n, dt))
        print(f"n={n} wall={dt:.3f}s ms/v={1000*dt/n:.2f}")
    try:
        a, b = fit_or_refuse(points, min_decade_span=1.0)
        fit = {"ok": True, "intercept_s": a, "slope_s_per_n": b, "ms_per_verify": 1000 * b}
        print(f"fit intercept={a:.4f}s slope={b*1000:.3f} ms/verify")
    except ModelRefused as e:
        fit = {"ok": False, "reason": str(e)}
        print("FIT_REFUSED", e)
    ok_aff, detail = check_affine(points, tol=0.25)
    print("affine", ok_aff, detail)
    out = {"pin": PIN, "serial": S25, "points": points, "fit": fit, "affine": {"ok": ok_aff, "detail": detail}}
    Path(__file__).with_name("curve.json").write_text(json.dumps(out, indent=2) + "\n")
    if not fit["ok"] or not ok_aff:
        print("NOT_A_RATE")
        return 0
    print("IS_A_RATE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
