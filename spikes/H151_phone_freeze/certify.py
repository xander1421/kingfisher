#!/usr/bin/env python3
"""Certify H151. Falsifier: S25 post-freeze digest moved."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
from kfcheck import Control, certify  # noqa: E402
from provenance import Falsifier  # noqa: E402

PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"


def main() -> int:
    d = json.loads((HERE / "phone.json").read_text())
    c25 = Control(
        "s25_holds_pin",
        "on-device F001 after freeze must ACCEPT 590d8769",
        null_must_contain="a digest that can match or miss the pin",
        can_fail_because="S25 printed a different digest or REJECTED honest F001",
    )
    c25.observe(
        d["s25"]["digest"] == PIN and d["s25"]["verdict"] == "ACCEPTED",
        {"digest": d["s25"]["digest"], "verdict": d["s25"]["verdict"], "m06_rc": d["s25"]["m06_rc"]},
    )
    c24 = Control(
        "s24_gate_held",
        "attached+charging S24 must not run a job while cpu_busy",
        null_must_contain="job_ran true or false",
        can_fail_because="job_ran true, or limit raised, or app killed",
    )
    c24.observe(
        (not d["s24"]["job_ran"]) and d["s24"]["refused"] == "cpu_busy",
        {
            "job_ran": d["s24"]["job_ran"],
            "refused": d["s24"]["refused"],
            "samples": d["s24"]["cpu_busy_pct_samples"],
        },
    )
    f1 = Falsifier(
        "freeze_moved_phone_pin",
        "F001_FROZEN status flip changed the on-device digest",
        fires_when="S25 digest != 590d8769",
        null_must_contain="a digest field that can equal or differ from the pin",
    )
    f1.observe(d["s25"]["digest"] != PIN, {"digest": d["s25"]["digest"]})
    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "phone.json")],
        controls=[c25, c24],
        falsifiers=[f1],
        captures=[("phone", json.dumps(d, sort_keys=True))],
        falsifier="S25 on-device digest after freeze is not 590d8769",
        allow_dirty=True,
        no_deps_reason="on-device pin check; no elder",
        note="H151: S25 holds frozen pin; S24 refused cpu_busy (game)",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
