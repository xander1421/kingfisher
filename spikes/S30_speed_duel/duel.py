#!/usr/bin/env python3
"""S30 — the speed duel, run under Agent 1's rules (chat.log C5).

Rules adopted verbatim from S9/bench.py:
  * never report one number: cold sample separately from the warm median,
    plus spread (rsd);
  * declare contention — this script records load average and any competing
    cargo/python processes at start and end, and prints them with the results.

Rule added for this duel:
  * a speedup only counts if the output digest does not move. Every variant is
    checked against the S15 baseline `raw_hash`; a variant whose hash differs
    is reported as INVALID no matter how fast it is.

Device-side timing uses fuelrun's own `run_ms`, which the program measures
around its own interpreter loop, so adb round-trip is excluded from the
comparison. End-to-end adb wall time is reported separately and never used for
the speedup claim.

usage: duel.py [--reps 9] [--jobs job_terminating,job_kb]
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
ADB = f"{HOME}/Library/Android/sdk/platform-tools/adb"
DEV = "/data/local/tmp/kingfisher"
JOBDIR = f"{HERE}/../S15_android_device"

BASELINE_HASH = {
    "job_terminating": "c2940ab5fcd507681ff8d3c32f607f236819915a38cda9a5f4f863c681261ab3",
    "job_kb":          "4937b20a7490523b5b2254926035f9c6286885d9bc9fb6185b357526206ac258",
}
FUEL = {"job_terminating": 5_000_000, "job_kb": 2_000_000}
VARIANTS = ["v0", "v1", "v2"]


def contention():
    """What else was running. The S9 lesson, made mandatory."""
    load = os.getloadavg()
    ps = subprocess.run(["ps", "-Ao", "comm"], capture_output=True, text=True).stdout
    busy = [n for n in ("cargo", "rustc", "python3", "mork", "ninja", "clang")
            if sum(1 for line in ps.splitlines() if line.rstrip().endswith(n)) > 0]
    return {"loadavg_1m": round(load[0], 2), "loadavg_5m": round(load[1], 2),
            "competing_processes": busy}


def parse(out):
    g = lambda k: (re.search(rf"^{k}\s+(\S+)", out, re.M) or [None, None])[1]
    return {"status": g("status"), "fuel_used": g("fuel_used"),
            "raw_hash": g("raw_hash"), "run_ms": g("run_ms"),
            "boot_ms": g("boot_ms")}


def run_host(variant, job):
    t0 = time.perf_counter()
    p = subprocess.run([f"{HERE}/bin/fuelrun.{variant}.host",
                        f"{JOBDIR}/{job}.metta", str(FUEL[job])],
                       capture_output=True, text=True)
    wall = time.perf_counter() - t0
    return parse(p.stdout), wall


def run_phone(variant, job):
    t0 = time.perf_counter()
    p = subprocess.run(
        [ADB, "shell",
         f"cd {DEV} && ./fuelrun.{variant} {job}.metta {FUEL[job]}"],
        capture_output=True, text=True)
    wall = time.perf_counter() - t0
    return parse(p.stdout), wall


def battery_temp():
    p = subprocess.run([ADB, "shell", "dumpsys battery | grep temperature"],
                       capture_output=True, text=True).stdout
    m = re.search(r"temperature:\s*(\d+)", p)
    return int(m.group(1)) / 10.0 if m else None


def measure_interleaved(runner, job, reps, cooldown, temp_fn):
    """Round-robin the variants instead of running each to completion.

    The first pass of this duel ran v0 fully, then v1, then v2 -- and on the
    long job the phone reported v1/v2 as 24-31% SLOWER with the battery rising
    37.2 -> 38.3 C. That is an order effect, not a code effect: whichever
    variant runs last runs hottest. Interleaving spreads any thermal drift
    across all three equally, and per-sample temperature is recorded so the
    drift is visible rather than inferred.
    """
    acc = {v: {"samples": [], "walls": [], "temps": [], "meta": None}
           for v in VARIANTS}
    for i in range(reps):
        for v in VARIANTS:
            r, wall = runner(v, job)
            if r["run_ms"] is None:
                acc[v]["error"] = "no run_ms"
                continue
            acc[v]["samples"].append(float(r["run_ms"]))
            acc[v]["walls"].append(wall * 1000.0)
            acc[v]["temps"].append(temp_fn())
            acc[v]["meta"] = r
            if cooldown:
                time.sleep(cooldown)
    return {v: _summarise(a, job) for v, a in acc.items()}


def _summarise(a, job):
    if "error" in a or not a["samples"]:
        return {"error": a.get("error", "no samples")}
    samples, meta = a["samples"], a["meta"]
    warm = samples[1:] or samples
    med = statistics.median(warm)
    temps = [t for t in a["temps"] if t is not None]
    return {
        "cold_ms": samples[0],
        "warm_median_ms": med,
        "warm_min_ms": min(warm),
        "warm_rsd_pct": round(100 * statistics.pstdev(warm) / statistics.mean(warm), 2)
        if len(warm) > 1 else 0.0,
        "cold_over_warm": round(samples[0] / med, 2) if med else None,
        "adb_wall_median_ms": round(statistics.median(a["walls"]), 1),
        "temp_first_c": temps[0] if temps else None,
        "temp_last_c": temps[-1] if temps else None,
        "boot_ms": meta["boot_ms"],
        "fuel_used": meta["fuel_used"],
        "status": meta["status"],
        "raw_hash": meta["raw_hash"],
        "hash_ok": meta["raw_hash"] == BASELINE_HASH[job],
        "all_ms": samples,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=9)
    ap.add_argument("--jobs", default="job_terminating,job_kb")
    ap.add_argument("--cooldown", type=float, default=0.0,
                    help="seconds to idle between samples")
    args = ap.parse_args()
    jobs = args.jobs.split(",")

    # push variants + jobs
    for v in VARIANTS:
        subprocess.run([ADB, "push", f"{HERE}/bin/fuelrun.{v}.android",
                        f"{DEV}/fuelrun.{v}"], capture_output=True)
    subprocess.run([ADB, "shell", f"chmod 755 {DEV}/fuelrun.v0 {DEV}/fuelrun.v1 {DEV}/fuelrun.v2"],
                   capture_output=True)
    for j in jobs:
        subprocess.run([ADB, "push", f"{JOBDIR}/{j}.metta", f"{DEV}/"], capture_output=True)

    report = {"contention_start": contention(),
              "battery_temp_c_start": battery_temp(),
              "reps": args.reps, "results": {}}

    print(f"contention at start: {report['contention_start']}")
    print(f"battery {report['battery_temp_c_start']} C\n")
    print(f"{'job':<17}{'where':<8}{'var':<5}{'cold':>9}{'warm_med':>10}"
          f"{'rsd':>7}{'c/w':>6}{'vs v0':>8}  hash")

    for job in jobs:
        for where, runner in (("host", run_host), ("phone", run_phone)):
            tf = battery_temp if where == "phone" else (lambda: None)
            res = measure_interleaved(runner, job, args.reps, args.cooldown, tf)
            base = res["v0"].get("warm_median_ms")
            for v in VARIANTS:
                r = res[v]
                report["results"][f"{job}/{where}/{v}"] = r
                if "error" in r:
                    print(f"{job:<17}{where:<8}{v:<5}  ERROR {r['error']}")
                    continue
                spd = base / r["warm_median_ms"] if base else float("nan")
                flag = "OK " if r["hash_ok"] else "INVALID(hash moved!)"
                t = (f"  {r['temp_first_c']}->{r['temp_last_c']}C"
                     if r.get("temp_first_c") is not None else "")
                print(f"{job:<17}{where:<8}{v:<5}{r['cold_ms']:9.1f}"
                      f"{r['warm_median_ms']:10.1f}{r['warm_rsd_pct']:6.1f}%"
                      f"{r['cold_over_warm']:6.2f}{spd:7.2f}x  {flag}{t}")
        print()

    report["contention_end"] = contention()
    report["battery_temp_c_end"] = battery_temp()
    print(f"contention at end:   {report['contention_end']}")
    print(f"battery {report['battery_temp_c_end']} C")

    with open(f"{HERE}/duel.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nwrote {HERE}/duel.json")


if __name__ == "__main__":
    sys.exit(main())
