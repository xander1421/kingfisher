#!/usr/bin/env python3
"""Certify H148. Falsifier: fleet and 3:1 still lose to one phone after submit-all."""
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
    d = json.loads((HERE / "fleet.json").read_text())
    if d.get("pin") != PIN:
        raise SystemExit(f"pin moved: {d.get('pin')}")

    c_eval = Control(
        "eval_order_is_sum",
        "host 50ms+50ms: tuple submit().result() wall is ~2x submit-all",
        null_must_contain="two 50ms sleeps whose walls can be a sum or a max",
        can_fail_because="if the tuple already overlapped, bug_s would be within 50% of fix_s",
    )
    demo = d["eval_order_demo"]
    c_eval.observe(
        demo["bug_is_sum"] and demo["fix_is_max"],
        {"bug_s": demo["bug_s"], "fix_s": demo["fix_s"], "ratio": demo["ratio_bug_over_fix"]},
    )

    c_src = Control(
        "no_sequential_submit_result",
        "production H141/H148 source must not call .result() on submit() in one expr",
        null_must_contain="AST of a file that can contain submit().result() or wait_all",
        can_fail_because="AST hits on H141 or H148 (demo_eval_order excluded)",
    )
    hits = d["submit_result_same_expr"]
    c_src.observe(
        not hits.get("H141") and not hits.get("H148"),
        {"H141": hits.get("H141"), "H148": hits.get("H148")},
    )

    c_par = Control(
        "phone_wall_is_max",
        "1:1 and 3:1 walls must be <= 1.20 * max(phone times), not the sum",
        null_must_contain="a wall that can equal max(s25,s24) or s25+s24",
        can_fail_because="wall ≈ s25+s24 as in retracted H141 6.874 / 5.173",
    )
    oo, to = d["one_one"], d["three_one"]
    c_par.observe(
        oo["wall_s"] <= 1.20 * max(oo["s25_s"], oo["s24_s"])
        and to["wall_s"] <= 1.20 * max(to["s25_s"], to["s24_s"]),
        {
            "one_one_wall": oo["wall_s"],
            "one_one_max": max(oo["s25_s"], oo["s24_s"]),
            "three_one_wall": to["wall_s"],
            "three_one_max": max(to["s25_s"], to["s24_s"]),
            "retracted_one_one": d["retracted_h141"]["one_one_wall_s"],
            "retracted_three_one": d["retracted_h141"]["three_one_wall_s"],
        },
    )

    f1 = Falsifier(
        "devices_add_no_capacity",
        "two phones still lose to one Snapdragon after the harness is parallel",
        fires_when="three_one_vs_s25_only >= 0.90 and fleet_vs_s25_k2 >= 0.90",
        null_must_contain="ratios that can sit above or below 0.90",
    )
    f1.observe(
        d["three_one_vs_s25_only"] >= 0.90 and d["fleet_vs_s25_k2"] >= 0.90,
        {
            "three_one_vs_s25_only": d["three_one_vs_s25_only"],
            "fleet_vs_s25_k2": d["fleet_vs_s25_k2"],
            "three_one_wall": to["wall_s"],
            "s25_only": d["s25_only_400_s"],
            "fleet_wall": d["fleet_weighted_k2"]["wall_s"],
            "s25_k2_wall": d["s25_k2"]["wall_s"],
        },
    )

    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "fleet.py"), str(HERE / "fleet.json")],
        controls=[c_eval, c_src, c_par],
        falsifiers=[f1],
        captures=[("fleet", json.dumps(d, sort_keys=True))],
        falsifier=(
            "after submit-all, 3:1 k=1 wall not < 0.90 of S25-only 400 "
            "AND fleet k=2 wall not < 0.90 of S25 k=2 400"
        ),
        allow_dirty=True,
        no_deps_reason="harness evaluation-order defect; no elder",
        note="H148: two-phone scale failed because submit().result() serialized the pair",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
