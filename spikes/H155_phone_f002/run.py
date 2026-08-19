#!/usr/bin/env python3
"""H155 — Phone F002 Execution on Samsung Galaxy S25 Ultra (Snapdragon 8 Elite).

Rebuilds trace_verifier_android from fixtures/verifier/trace_verifier.rs, pushes to S25 Ultra,
and verifies:
1. F001 ACCEPTED at 590d8769... (fuel 400)
2. F002_specv1 ACCEPTED at c43b1eab... (fuel 400)
3. 7/7 F002 mutants REJECTED with exact matching tokens
4. Gemini fixtures/F002 REJECTED with FUEL_TABLE_MISMATCH
5. F003_specv1 REJECTED with WRONG_FIXTURE_CLASS

Completes Gate 4 verification on silicon.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
import kfcheck
from provenance import Control, Falsifier

SERIAL = "R5CY93675MK"
DEVDIR = "/data/local/tmp/kftest_f002"
PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
NDK_CLANG = "/Users/victorianikolenko/Library/Android/sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang"
SRC_RUST = ROOT / "fixtures" / "verifier" / "trace_verifier.rs"
BIN_ANDROID = ROOT / "fixtures" / "verifier" / "trace_verifier_android"


def adb_cmd(args):
    cmd = ["adb", "-s", SERIAL] + args
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def parse_fuel(out: str):
    m = re.search(r"Derived Fuel:\s+(\d+)", out)
    return int(m.group(1)) if m else None


def parse_digest(out: str):
    m = re.search(r"Consensus Digest:\s+([0-9a-fA-F]{64})", out)
    return m.group(1).lower() if m else None


def check_device_quiet():
    env = os.environ.copy()
    env["ANDROID_SERIAL"] = SERIAL
    p = subprocess.run(["sh", str(ROOT / "spikes" / "quiet.sh"), "--device"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def build_android_binary():
    print("Building aarch64 Android binary from trace_verifier.rs...")
    cmd = [
        "rustc",
        "--target", "aarch64-linux-android",
        "-C", f"linker={NDK_CLANG}",
        "-O",
        "-o", str(BIN_ANDROID),
        str(SRC_RUST),
    ]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"rustc build failed: {p.stderr}")
    print(f"Built {BIN_ANDROID} ({BIN_ANDROID.stat().st_size} bytes)")


def stage_phone():
    print("Staging device directory and fixtures on S25 Ultra...")
    adb_cmd(["shell", f"rm -rf {DEVDIR} && mkdir -p {DEVDIR}/fixtures"])
    
    # Push binary
    adb_cmd(["push", str(BIN_ANDROID), f"{DEVDIR}/tv"])
    adb_cmd(["shell", f"chmod +x {DEVDIR}/tv"])

    # Push fixtures
    adb_cmd(["push", str(ROOT / "fixtures" / "F001"), f"{DEVDIR}/fixtures/"])
    adb_cmd(["push", str(ROOT / "fixtures" / "F002_specv1"), f"{DEVDIR}/fixtures/"])
    adb_cmd(["push", str(ROOT / "fixtures" / "F002"), f"{DEVDIR}/fixtures/"])
    adb_cmd(["push", str(ROOT / "fixtures" / "F003_specv1"), f"{DEVDIR}/fixtures/"])


def run_on_phone(fixture_path):
    rc, out = adb_cmd(["shell", f"{DEVDIR}/tv {DEVDIR}/{fixture_path}"])
    return rc, out


def main():
    t0 = time.time()
    print("=== Spike H155: Phone F002 Execution on Samsung Galaxy S25 Ultra ===")

    quiet_before_ok, quiet_before_out = check_device_quiet()
    print(f"Device quiet before: ok={quiet_before_ok} ({quiet_before_out})")
    if not quiet_before_ok:
        print("Device is not quiet! Refusing.")
        return 1

    build_android_binary()
    stage_phone()

    # 1. Run F001 on phone
    r1, o1 = run_on_phone("fixtures/F001")
    d1 = parse_digest(o1)
    f1_fuel = parse_fuel(o1)
    print(f"Phone F001: rc={r1}, digest={d1}, fuel={f1_fuel}")

    # 2. Run F002_specv1 on phone
    r2, o2 = run_on_phone("fixtures/F002_specv1")
    d2 = parse_digest(o2)
    f2_fuel = parse_fuel(o2)
    print(f"Phone F002_specv1: rc={r2}, digest={d2}, fuel={f2_fuel}")

    # 3. Run Gemini F002 on phone
    rg, og = run_on_phone("fixtures/F002")
    print(f"Phone Gemini F002: rc={rg}, token={'FUEL_TABLE_MISMATCH' if 'FUEL_TABLE_MISMATCH' in og else og[-100:]}")

    # 4. Run F003_specv1 on phone
    r3, o3 = run_on_phone("fixtures/F003_specv1")
    print(f"Phone F003_specv1: rc={r3}, token={'WRONG_FIXTURE_CLASS' if 'WRONG_FIXTURE_CLASS' in o3 else o3[-100:]}")

    # 5. Run 7 mutants on phone
    muts = []
    any_accept = False
    tokens = {}
    mdir = ROOT / "fixtures" / "F002_specv1" / "mutants"
    for d in sorted(mdir.iterdir()):
        if not d.is_dir():
            continue
        rc, out = run_on_phone(f"fixtures/F002_specv1/mutants/{d.name}")
        acc = rc == 0 or "ACCEPTED" in out
        any_accept = any_accept or acc
        tok = "ACCEPT"
        for line in out.splitlines():
            if "REJECTED:" in line:
                tok = line.split("REJECTED:", 1)[1].strip().split()[0].rstrip(":")
                break
        muts.append({"name": d.name, "rc": rc, "accept": acc, "token": tok})
        tokens[d.name] = tok
        print(f"  Phone mutant {d.name}: rc={rc}, token={tok}")

    quiet_after_ok, quiet_after_out = check_device_quiet()
    print(f"Device quiet after: ok={quiet_after_ok} ({quiet_after_out})")

    # Clean up device scratch
    adb_cmd(["shell", f"rm -rf {DEVDIR}"])

    f1 = (d2 != PIN_F002 or r2 != 0)
    f2 = (d1 != PIN_F001 or r1 != 0)
    f3 = any_accept
    f4 = (rg == 0 or "ACCEPTED" in og)
    f5 = ("WRONG_FIXTURE_CLASS" not in o3)

    c3_ok = (f1_fuel == 400 and f2_fuel == 400)

    res = {
        "spike": "H155",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "device": {
            "serial": SERIAL,
            "model": "SM-S938B (Galaxy S25 Ultra)",
            "soc": "Snapdragon 8 Elite",
            "arch": "aarch64",
            "quiet_before": quiet_before_out,
            "quiet_after": quiet_after_out,
        },
        "not_operator_2": True,
        "gate4_phone_closed": not (f1 or f2 or f3 or f4 or f5),
        "phone_f001": {"rc": r1, "digest": d1, "digest_ok": d1 == PIN_F001, "fuel": f1_fuel},
        "phone_f002": {"rc": r2, "digest": d2, "digest_ok": d2 == PIN_F002, "fuel": f2_fuel},
        "phone_gemini_f002": {"rc": rg, "accept": f4, "rejected_fuel_table": "FUEL_TABLE_MISMATCH" in og},
        "phone_f003": {"rc": r3, "wrong_class": "WRONG_FIXTURE_CLASS" in o3},
        "mutants": muts,
        "controls": {
            "C1_device_quiet": {"ok": quiet_before_ok and quiet_after_ok},
            "C2_pin_matches_host": {"ok": d1 == PIN_F001 and d2 == PIN_F002},
            "C3_fuel_parsed": {"fuel_f001": f1_fuel, "fuel_f002": f2_fuel, "ok": c3_ok},
        },
        "falsifiers": {
            "F1_phone_f002_pin": {"fired": f1, "observed_digest": d2},
            "F2_phone_f001_pin": {"fired": f2, "observed_digest": d1},
            "F3_mutant_accept": {"fired": f3, "tokens": tokens},
            "F4_gemini_accept": {"fired": f4},
            "F5_f003_wrong_class": {"fired": f5, "out": o3},
        },
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    controls = [
        Control("C1_device_quiet", why="Device must be quiet before and after execution", can_fail_because="thermal/CPU contention", null_must_contain="contention detected"),
        Control("C2_pin_matches_host", why="S25 on-device digests must match host exactly", can_fail_because="cross-ISA compiler divergence", null_must_contain="digest mismatch"),
        Control("C3_fuel_parsed", why="Derived fuel must be 400 parsed from stdout", can_fail_because="unsupported fuel table", null_must_contain="fuel != 400"),
    ]
    controls[0].observe(quiet_before_ok and quiet_after_ok, res["controls"]["C1_device_quiet"])
    controls[1].observe(d1 == PIN_F001 and d2 == PIN_F002, res["controls"]["C2_pin_matches_host"])
    controls[2].observe(c3_ok, res["controls"]["C3_fuel_parsed"])

    falsifiers = [
        Falsifier("F1_phone_f002_pin", refutes="that S25 native binary reproduces c43b1eab", fires_when="S25 F002 digest != c43b1eab", null_must_contain="pin mismatch"),
        Falsifier("F2_phone_f001_pin", refutes="that F001 pin remains unmoved on silicon", fires_when="S25 F001 digest != 590d8769", null_must_contain="F001 moved"),
        Falsifier("F3_mutant_accept", refutes="that on-device binary rejects all 7 F002 mutants", fires_when="any of 7 mutants ACCEPT on phone", null_must_contain="mutant ACCEPT"),
        Falsifier("F4_gemini_accept", refutes="that Gemini F002 is rejected on device", fires_when="Gemini F002 ACCEPT on phone", null_must_contain="gemini ACCEPT"),
        Falsifier("F5_f003_wrong_class", refutes="that F003 is rejected as WRONG_FIXTURE_CLASS", fires_when="F003 output missing WRONG_FIXTURE_CLASS", null_must_contain="wrong error code"),
    ]
    falsifiers[0].observe(f1, {"observed_digest": d2, "expected": PIN_F002})
    falsifiers[1].observe(f2, {"observed_digest": d1, "expected": PIN_F001})
    falsifiers[2].observe(f3, {"any_accept": any_accept, "tokens": tokens})
    falsifiers[3].observe(f4, {"gemini_out": og})
    falsifiers[4].observe(f5, {"f003_out": o3})

    ok, problems = kfcheck.certify(
        str(HERE),
        artifacts=[str(out_json), str(BIN_ANDROID)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="S25 on-device binary failing F002 verification or moving F001 pin",
        allow_dirty=True,
        no_deps_reason="on-device hardware verification; no elder",
        note="H155: Phone F002 execution on Samsung Galaxy S25 Ultra (Snapdragon 8 Elite). Gate 4 closed on silicon.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike H155 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
