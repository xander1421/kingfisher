#!/usr/bin/env python3
"""Certify H153. Falsifier: 3-way steal not faster than S25 k=2."""
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
    d = json.loads((HERE / "three.json").read_text())
    c = Control(
        "three_serials_same_pin",
        "S25 S24 emu all ACCEPT 590d8769",
        null_must_contain="three digests that can match or miss",
        can_fail_because="any serial REJECT or different digest",
    )
    pins = d["pins"]
    c.observe(
        all(pins[s]["digest"] == PIN for s in pins),
        {s: pins[s]["digest"][:16] for s in pins},
    )
    c2 = Control(
        "emu_not_claimed_phone",
        "record must say emulator is not a phone and not a new operator",
        null_must_contain="flags that can be true or omitted",
        can_fail_because="emulator_is_not_a_phone false",
    )
    c2.observe(
        d["emulator_is_not_a_phone"] and d["not_a_new_operator_domain"],
        {
            "emu_not_phone": d["emulator_is_not_a_phone"],
            "not_op": d["not_a_new_operator_domain"],
        },
    )
    f1 = Falsifier(
        "three_no_faster_than_s25",
        "best 3-way steal wall not < 0.90 of S25 k=2",
        fires_when="three_best_vs_s25_k2 >= 0.90",
        null_must_contain="a ratio that can sit above or below 0.90",
    )
    f1.observe(
        d["three_best_vs_s25_k2"] >= 0.90,
        {"ratio": d["three_best_vs_s25_k2"], "s25": d["s25_k2_s"]},
    )
    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "three.json")],
        controls=[c, c2],
        falsifiers=[f1],
        captures=[("three", json.dumps(d, sort_keys=True))],
        falsifier="3-way steal not faster than S25 k=2, or a serial fails the pin",
        allow_dirty=True,
        no_deps_reason="live 3-serial F001; no elder",
        note="H153: 3 adb serials; emu is not a third phone",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
