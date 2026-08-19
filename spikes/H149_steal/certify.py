#!/usr/bin/env python3
"""Certify H149. Falsifier: steal neither beats 1:1 nor matches oracle 3:1."""
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
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"


def main() -> int:
    d = json.loads((HERE / "steal.json").read_text())
    if d.get("pin") != PIN:
        raise SystemExit(f"pin moved: {d.get('pin')}")

    c_ratio = Control(
        "steal_discovers_three_one",
        "untold pull queue should land on 300/100 for this pair",
        null_must_contain="taken counts that can be 200/200 or 300/100",
        can_fail_because="queue still splits 1:1 or starves one phone",
    )
    taken = d["steal"]["taken"]
    c_ratio.observe(
        taken.get(S25) == 300 and taken.get(S24) == 100,
        {"s25": taken.get(S25), "s24": taken.get(S24)},
    )

    c_wall = Control(
        "steal_near_oracle_and_beats_one_phone",
        "steal wall within 20% of 3:1 k=2 and < 0.90 of S25 k=2",
        null_must_contain="three walls that can be ordered steal/oracle/s25k2",
        can_fail_because="USB-per-chunk makes steal slower than one Snapdragon",
    )
    c_wall.observe(
        d["steal_vs_oracle"] <= 1.20 and d["steal_vs_s25_k2"] < 0.90,
        {
            "steal": d["steal"]["wall_s"],
            "oracle": d["oracle_3_1_k2"]["wall_s"],
            "s25_k2": d["s25_k2"]["wall_s"],
            "vs_oracle": d["steal_vs_oracle"],
            "vs_s25_k2": d["steal_vs_s25_k2"],
        },
    )

    f1 = Falsifier(
        "steal_no_help",
        "pulling neither beats static 1:1 nor matches known 3:1",
        fires_when="steal_vs_one_one >= 0.90 and steal_vs_oracle > 1.20",
        null_must_contain="ratios that can sit on either side of 0.90 / 1.20",
    )
    f1.observe(
        d["steal_vs_one_one"] >= 0.90 and d["steal_vs_oracle"] > 1.20,
        {
            "steal_vs_one_one": d["steal_vs_one_one"],
            "steal_vs_oracle": d["steal_vs_oracle"],
        },
    )

    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "steal.json")],
        controls=[c_ratio, c_wall],
        falsifiers=[f1],
        captures=[("steal", json.dumps(d, sort_keys=True))],
        falsifier=(
            "steal wall of 400 not < 0.90 of static 1:1 "
            "AND not within 20% of oracle 3:1 k=2"
        ),
        allow_dirty=True,
        no_deps_reason="on-device pull queue; no elder",
        note="H149: pull chunks find 3:1 without a baked ratio",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
