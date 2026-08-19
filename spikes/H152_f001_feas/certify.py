#!/usr/bin/env python3
"""Certify H152. Falsifier: 1-device pin fail or steal not faster than S25 k=2."""
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
    d = json.loads((HERE / "feas.json").read_text())
    c1 = Control(
        "one_device_accepts",
        "S25 on-device F001 ACCEPT 590d8769 and 200-loop is a rate",
        null_must_contain="a digest and a jobs/s that can be zero or the pin",
        can_fail_because="REJECT or digest mismatch or n200_jobs_per_s < 50",
    )
    c1.observe(
        d["one"]["once"]["digest"] == PIN and d["one"]["n200_jobs_per_s"] >= 50,
        {"digest": d["one"]["once"]["digest"], "jps": d["one"]["n200_jobs_per_s"]},
    )
    two = d["two"]
    c2 = Control(
        "two_device_same_pin",
        "S24 ACCEPT same frozen digest",
        null_must_contain="S24 digest that can match or miss",
        can_fail_because="S24 REJECT or different digest",
    )
    c2.observe(
        two["once"]["digest"] == PIN,
        {"digest": two["once"]["digest"], "taken": two["steal"]["taken"]},
    )
    f1 = Falsifier(
        "second_phone_does_not_add_capacity",
        "live steal wall not < 0.90 of S25 k=2",
        fires_when="steal_vs_s25_k2 >= 0.90",
        null_must_contain="a ratio that can sit above or below 0.90",
    )
    f1.observe(
        two["steal_vs_s25_k2"] >= 0.90,
        {
            "ratio": two["steal_vs_s25_k2"],
            "steal": two["steal"]["wall_s"],
            "s25_k2": d["one"]["k2_400_s"],
        },
    )
    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "feas.json")],
        controls=[c1, c2],
        falsifiers=[f1],
        captures=[("feas", json.dumps(d, sort_keys=True))],
        falsifier="S25 pin fail, or live 2-phone steal not faster than S25 two workers",
        allow_dirty=True,
        no_deps_reason="live F001 on phones; no elder",
        note="H152: F001 feasible on 1 phone; steal adds the second",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
