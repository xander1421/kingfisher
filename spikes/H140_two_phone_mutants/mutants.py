#!/usr/bin/env python3
"""H140: both phones REJECT F001 mutants M01–M07. S24+ uses unread-thermal override."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TV = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
F001 = ROOT / "fixtures" / "F001"
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25 = "R5CY93675MK"
S24 = "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_scale"
WANT = {
    "M01_tampered_step_fuel": "FUEL_DIVERGENCE",
    "M02_illegal_opcode": "ILLEGAL_OPCODE",
    "M03_corrupted_root": "CORPUS_ROOT_MISMATCH",
    "M04_declared_fuel_mismatch": "FUEL_FILE_MISMATCH",
    "M05_inconsistent_unify": "SEMANTIC_UNIFICATION_FAILURE",
    "M06_result_mismatch_rehashed": "RESULT_NOT_DERIVED",
    "M07_skipped_unify_rewritten": "SEMANTIC_UNIFICATION_FAILURE",
}


def run(args, env=None, timeout=120):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=e, timeout=timeout)


def adb(serial, *args, timeout=180):
    p = run(["adb", "-s", serial, *args], timeout=timeout)
    return p


def gate(serial: str) -> None:
    env = {"ANDROID_SERIAL": serial}
    if serial == S24:
        env["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = run(["bash", "spikes/quiet.sh", "--device"], env=env)
    if p.returncode != 0:
        raise SystemExit(f"gate {serial}: {p.stdout}{p.stderr}")


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    p = adb(serial, "push", str(TV), f"{DEST}/tv")
    if p.returncode != 0:
        raise SystemExit(p.stderr)
    p = adb(serial, "push", str(F001), f"{DEST}/F001")
    if p.returncode != 0:
        raise SystemExit(p.stderr)
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def check_phone(serial: str) -> dict:
    rows = {}
    p = adb(serial, "shell", f"{DEST}/tv {DEST}/F001")
    out = p.stdout + p.stderr
    if PIN not in out or "ACCEPTED" not in out:
        raise SystemExit(f"{serial} honest F001 failed:\n{out}")
    rows["honest"] = {"verdict": "ACCEPTED", "pin": PIN}
    for name, token in WANT.items():
        p = adb(serial, "shell", f"{DEST}/tv {DEST}/F001/mutants/{name}")
        out = p.stdout + p.stderr
        ok = "REJECTED" in out and token in out
        rows[name] = {"ok": ok, "want": token, "out": out[-400:]}
        if not ok:
            print(f"FAIL {serial} {name}: {out}")
    return rows


def main() -> int:
    gate(S25)
    gate(S24)
    push(S25)
    push(S24)
    a = check_phone(S25)
    b = check_phone(S24)
    dest = Path(__file__).with_name("mutants.json")
    dest.write_text(json.dumps({S25: a, S24: b, "pin": PIN}, indent=2) + "\n")
    bad = []
    for serial, rows in ((S25, a), (S24, b)):
        for name in WANT:
            if not rows[name]["ok"]:
                bad.append(f"{serial} {name}")
    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print(f"h140: both phones ACCEPT {PIN[:8]} and REJECT 7/7 mutants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
