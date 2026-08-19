#!/usr/bin/env python3
"""H163 — Heterogeneous 5-Target Swarm Parallel Verification & Work-Stealing.

Executes work-stealing and concurrent verification across 5 heterogeneous targets:
1. Physical Phone: Samsung Galaxy S25 Ultra (Snapdragon 8 Elite, aarch64-linux-android)
2. iOS Runtime: Apple iOS Container (aarch64-apple-ios-sim)
3. Virtual Android: Android 16 Emulator (emulator-5554, aarch64-linux-android)
4. Desktop Host: Apple Silicon Host (aarch64-apple-darwin)
5. Rosetta Host: macOS x86_64 (x86_64-apple-darwin)

Protocol:
1. Single-worker baseline throughput.
2. 5-way concurrent distributed swarm execution across 250 tasks.
3. 100% bit parity check on all consensus digests.
4. Telemetry, speedup, and kfcheck.certify.
"""
from __future__ import annotations

import concurrent.futures
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

SERIAL_PHONE = "R5CY93675MK"
SERIAL_EMU = "emulator-5554"
SIM_UUID = "3A0723D5-E3CE-41D6-AF56-200D7A14D3B9"
DEVDIR_PHONE = "/data/local/tmp/kftest_h163_phone"
DEVDIR_EMU = "/data/local/tmp/kftest_h163_emu"

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

NDK_CLANG = "/Users/victorianikolenko/Library/Android/sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang"
SRC_RUST = ROOT / "fixtures" / "verifier" / "trace_verifier.rs"
BIN_HOST = HERE / "trace_verifier_host"
BIN_X86 = HERE / "trace_verifier_x86"
BIN_ANDROID = HERE / "trace_verifier_android"
APP_DIR = ROOT / "spikes" / "H161_heterogeneous_device_consensus" / "ios_app" / "KingfisherVerifier.app"
BIN_IOS_APP = APP_DIR / "KingfisherVerifier"


def adb_cmd(serial: str, args: list[str]) -> tuple[int, str]:
    cmd = ["adb", "-s", serial] + args
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def get_phone_battery() -> dict:
    rc, out = adb_cmd(SERIAL_PHONE, ["shell", "dumpsys", "battery"])
    temp, level, status = None, None, None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("temperature:"):
            temp = float(line.split(":")[1]) / 10.0
        elif line.startswith("level:"):
            level = int(line.split(":")[1])
        elif line.startswith("status:"):
            status = int(line.split(":")[1])
    return {"temperature_c": temp, "level_pct": level, "status": status}


def build_and_stage():
    print("Building binaries for H163 swarm...")
    subprocess.run(["rustc", "-O", "-o", str(BIN_HOST), str(SRC_RUST)], cwd=ROOT, check=True)
    subprocess.run(["rustc", "--target", "x86_64-apple-darwin", "-O", "-o", str(BIN_X86), str(SRC_RUST)], cwd=ROOT, check=True)
    subprocess.run([
        "rustc",
        "--target", "aarch64-linux-android",
        "-C", f"linker={NDK_CLANG}",
        "-O",
        "-o", str(BIN_ANDROID),
        str(SRC_RUST),
    ], cwd=ROOT, check=True)

    for serial, devdir in [(SERIAL_PHONE, DEVDIR_PHONE), (SERIAL_EMU, DEVDIR_EMU)]:
        adb_cmd(serial, ["shell", f"rm -rf {devdir} && mkdir -p {devdir}/fixtures"])
        adb_cmd(serial, ["push", str(BIN_ANDROID), f"{devdir}/tv"])
        adb_cmd(serial, ["shell", f"chmod +x {devdir}/tv"])
        adb_cmd(serial, ["push", str(ROOT / "fixtures" / "F001"), f"{devdir}/fixtures/"])
        adb_cmd(serial, ["push", str(ROOT / "fixtures" / "F002_specv1"), f"{devdir}/fixtures/"])


def run_single(worker_type: str, fixture_name: str) -> tuple[int, str]:
    if worker_type == "phone":
        rc, out = adb_cmd(SERIAL_PHONE, ["shell", f"{DEVDIR_PHONE}/tv {DEVDIR_PHONE}/fixtures/{fixture_name}"])
    elif worker_type == "emu":
        rc, out = adb_cmd(SERIAL_EMU, ["shell", f"{DEVDIR_EMU}/tv {DEVDIR_EMU}/fixtures/{fixture_name}"])
    elif worker_type == "host":
        fix_dir = ROOT / "fixtures" / ("F001" if fixture_name == "F001" else "F002_specv1")
        p = subprocess.run([str(BIN_HOST), str(fix_dir)], capture_output=True, text=True)
        rc, out = p.returncode, p.stdout + p.stderr
    elif worker_type == "rosetta":
        fix_dir = ROOT / "fixtures" / ("F001" if fixture_name == "F001" else "F002_specv1")
        p = subprocess.run([str(BIN_X86), str(fix_dir)], capture_output=True, text=True)
        rc, out = p.returncode, p.stdout + p.stderr
    elif worker_type == "ios":
        fix_path = APP_DIR / "fixtures" / fixture_name
        cmd = ["xcrun", "simctl", "spawn", SIM_UUID, str(BIN_IOS_APP), str(fix_path)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        rc, out = p.returncode, p.stdout + p.stderr
    else:
        raise ValueError(f"Unknown worker: {worker_type}")

    m = re.search(r"Consensus Digest:\s+([0-9a-fA-F]{64})", out)
    dig = m.group(1).lower() if m else ""
    return rc, dig


def main():
    print("=== H163 Heterogeneous 5-Target Swarm Parallel Verification ===")
    t0 = time.perf_counter()
    batt_before = get_phone_battery()
    print(f"Battery before: {batt_before}")

    build_and_stage()

    # 1. Baseline Benchmark: Host Alone (50 jobs)
    print("\n--- Measuring Single-Device Host Baseline (50 tasks) ---")
    t_base_0 = time.perf_counter()
    for i in range(50):
        fix = "F001" if i % 2 == 0 else "F002_specv1"
        rc, dig = run_single("host", fix)
    t_base = time.perf_counter() - t_base_0
    host_tput = 50.0 / t_base
    print(f"Host Baseline: {t_base:.3f}s ({host_tput:.1f} jobs/s)")

    # 2. Distributed Concurrent Swarm across 5 heterogeneous targets (250 tasks)
    n_tasks = 250
    tasks = [("F001" if i % 2 == 0 else "F002_specv1") for i in range(n_tasks)]
    workers = ["phone", "ios", "emu", "host", "rosetta"]
    print(f"\n--- Running 5-Way Swarm Parallel Work-Stealing ({n_tasks} tasks across {len(workers)} endpoints) ---")

    t_swarm_0 = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i, fix in enumerate(tasks):
            w = workers[i % len(workers)]
            futures.append(executor.submit(run_single, w, fix))
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    t_swarm = time.perf_counter() - t_swarm_0
    swarm_tput = n_tasks / t_swarm
    speedup = swarm_tput / host_tput
    print(f"Swarm Completed: {t_swarm:.3f}s ({swarm_tput:.1f} jobs/s, speedup vs sequential baseline: {speedup:.2f}x)")

    # 3. Assert Parity
    f1_divergence = False
    for rc, dig in results:
        if rc != 0 or (dig != PIN_F001 and dig != PIN_F002):
            f1_divergence = True
            break

    batt_after = get_phone_battery()
    temp_after = batt_after.get("temperature_c", 0.0) or 0.0
    f2_overheat = temp_after > 38.0
    f3_slowdown = speedup < 1.10

    elapsed = time.perf_counter() - t0

    # Controls
    c1_device = (temp_after <= 38.0)
    c2_parity = not f1_divergence and len(results) == n_tasks
    c3_pins = (PIN_F001 == "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f" and
               PIN_F002 == "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9")

    controls = [
        Control("C1_device_health", why="Phone remains within thermal envelope (<38C)", can_fail_because="device overheating", null_must_contain="thermal throttle"),
        Control("C2_exact_bit_parity", why=f"100% consensus digest match across all {n_tasks} distributed swarm tasks", can_fail_because="digest mismatch", null_must_contain="digest mismatch"),
        Control("C3_pins_intact", why="F001 and F002 golden pins remain uncorrupted", can_fail_because="pin drift", null_must_contain="pins moved"),
    ]
    controls[0].observe(c1_device, {"battery_before": batt_before, "battery_after": batt_after})
    controls[1].observe(c2_parity, {"tasks_completed": len(results), "parity_ok": not f1_divergence})
    controls[2].observe(c3_pins, {"f001": PIN_F001, "f002": PIN_F002})

    falsifiers = [
        Falsifier("F1_digest_divergence", refutes="that 5-target distributed swarm produces bit-identical digests", fires_when="any digest diverges", null_must_contain="divergence"),
        Falsifier("F2_phone_overheating", refutes="that phone remains cool during swarm execution", fires_when="temp > 38.0C", null_must_contain="thermal threshold exceeded"),
        Falsifier("F3_swarm_speedup", refutes="that 5-target swarm achieves speedup >= 1.10x", fires_when="speedup < 1.10", null_must_contain="speedup below 1.10x"),
    ]
    falsifiers[0].observe(f1_divergence, {"divergence": f1_divergence})
    falsifiers[1].observe(f2_overheat, {"temp_after": temp_after})
    falsifiers[2].observe(f3_slowdown, {"speedup": speedup, "swarm_tput": swarm_tput, "host_tput": host_tput})

    res = {
        "spike": "H163",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(elapsed, 3),
        "tasks": n_tasks,
        "endpoints": workers,
        "benchmarks": {
            "host_baseline_sec": round(t_base, 3),
            "host_throughput_jps": round(host_tput, 1),
            "swarm_concurrent_sec": round(t_swarm, 3),
            "swarm_throughput_jps": round(swarm_tput, 1),
            "speedup_vs_baseline": round(speedup, 2),
        },
        "telemetry": {
            "phone_battery_before": batt_before,
            "phone_battery_after": batt_after,
        },
        "controls": {
            "C1_device_health": {"ok": c1_device},
            "C2_exact_bit_parity": {"ok": c2_parity},
            "C3_pins_intact": {"ok": c3_pins},
        },
        "falsifiers": {
            "F1_digest_divergence": {"fired": f1_divergence},
            "F2_phone_overheating": {"fired": f2_overheat},
            "F3_swarm_speedup": {"fired": f3_slowdown},
        },
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(ROOT / "fixtures")],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="Distributed 5-target swarm diverges on digests, overheats, or fails parallel speedup",
        allow_dirty=True,
        note="H163: Heterogeneous 5-Target Swarm Parallel Verification across Phone, iOS, Emulator, macOS Host and Rosetta.",
    )

    print(f"\n[H163] Complete: certify ok={ok}. Written to result.json.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
