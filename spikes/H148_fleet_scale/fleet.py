#!/usr/bin/env python3
"""H148: two-device scale failed because the harness serialized the phones.

CLASS: H141 labelled sequential walls as parallel. Python evaluates
`ex.submit(a).result(), ex.submit(b).result()` left-to-right, so the second
phone is not submitted until the first finishes. The published 1:1=6.874s and
3:1=5.173s equal s25+s24. That is why "the pair loses to one Snapdragon".

Falsifier (stated first): after submit-all, if a 3:1 k=1 split of 400 does
not beat S25-only 400, AND a weighted fleet (S25 k=2 × 300 + S24 k=2 × 100)
does not beat S25 k=2 × 400, then devices still add no capacity.

Operator unread-thermal override on S24 only. Charging and cpu_busy still
refuse. Same-source aarch64 Android is not a new ISA or operator domain.
"""
from __future__ import annotations

import ast
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TV = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
F001 = ROOT / "fixtures" / "F001"
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_scale"
HERE = Path(__file__).resolve().parent


def wait_all(calls):
    """Submit every call, then wait. A tuple of submit().result() is sequential."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as ex:
        futs = [ex.submit(*c) for c in calls]
        return [f.result() for f in futs]


def sequential_submit_calls(src: str) -> list[int]:
    """Line numbers where `.result()` is called on a `submit(...)` in the same expr."""
    tree = ast.parse(src)
    hits = []

    def is_submit(n: ast.AST) -> bool:
        return (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "submit"
        )

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node.name == "demo_eval_order":
                return
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "result"
                and is_submit(node.func.value)
            ):
                hits.append(getattr(node, "lineno", 0))
            self.generic_visit(node)

    V().visit(tree)
    return hits


def demo_eval_order() -> dict:
    """Host-only: the H141 tuple form is a sum; submit-all is a max."""

    def nap(s: float) -> float:
        time.sleep(s)
        return s

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(2) as ex:
        a, b = ex.submit(nap, 0.05).result(), ex.submit(nap, 0.05).result()
    bug = time.perf_counter() - t0
    t0 = time.perf_counter()
    aa, bb = wait_all([(nap, 0.05), (nap, 0.05)])
    fix = time.perf_counter() - t0
    return {
        "bug_s": bug,
        "fix_s": fix,
        "bug_is_sum": bug > 1.5 * fix,
        "fix_is_max": fix < 0.10,
        "ratio_bug_over_fix": bug / fix if fix else 0,
        "slept": [a, b, aa, bb],
    }


def adb(serial, *a, timeout=300):
    p = subprocess.run(
        ["adb", "-s", serial, *a],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if p.returncode != 0:
        raise SystemExit(f"{serial} {a}: {p.stdout}{p.stderr}")
    return p


def gate(serial, override=False) -> str:
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = serial
    if override:
        e["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = subprocess.run(
        ["bash", "spikes/quiet.sh", "--device"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=e,
    )
    text = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        raise SystemExit(f"gate {serial}: {text}")
    print(serial, text)
    return text


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    adb(serial, "push", str(TV), f"{DEST}/tv")
    adb(serial, "push", str(F001), f"{DEST}/F001")
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def loop(serial, n):
    script = (
        f"i=0; while [ $i -lt {n} ]; do "
        f"{DEST}/tv {DEST}/F001 | grep -q {PIN[:16]} || exit 2; "
        f"i=$((i+1)); done; echo LOOP_OK n={n}"
    )
    t0 = time.perf_counter()
    p = adb(serial, "shell", script)
    dt = time.perf_counter() - t0
    if "LOOP_OK" not in p.stdout:
        raise SystemExit(p.stdout + p.stderr)
    return dt


def k_loops(serial, k, n_each):
    t0 = time.perf_counter()
    times = wait_all([(loop, serial, n_each)] * k)
    wall = time.perf_counter() - t0
    jobs = k * n_each
    return {
        "serial": serial,
        "k": k,
        "n_each": n_each,
        "jobs": jobs,
        "times_s": times,
        "wall_s": wall,
        "jobs_per_s": jobs / wall if wall else 0,
    }


def main() -> int:
    demo = demo_eval_order()
    print(
        f"eval-order demo bug={demo['bug_s']:.3f}s fix={demo['fix_s']:.3f}s "
        f"bug_is_sum={demo['bug_is_sum']} fix_is_max={demo['fix_is_max']}"
    )
    hits_h141 = sequential_submit_calls(
        (ROOT / "spikes" / "H141_weighted_split" / "split.py").read_text()
    )
    hits_h148 = sequential_submit_calls(Path(__file__).read_text())
    print(f"submit().result() same-expr H141={hits_h141} H148={hits_h148}")

    g25 = gate(S25)
    g24 = gate(S24, True)
    push(S25)
    push(S24)

    t0 = time.perf_counter()
    t25_11, t24_11 = wait_all([(loop, S25, 200), (loop, S24, 200)])
    w11 = time.perf_counter() - t0

    t0 = time.perf_counter()
    t25_31, t24_31 = wait_all([(loop, S25, 300), (loop, S24, 100)])
    w31 = time.perf_counter() - t0

    s25_only = loop(S25, 400)
    s25_k2 = k_loops(S25, 2, 200)
    s24_k2 = k_loops(S24, 2, 100)

    t0 = time.perf_counter()
    fleet_times = wait_all(
        [
            (loop, S25, 150),
            (loop, S25, 150),
            (loop, S24, 50),
            (loop, S24, 50),
        ]
    )
    fleet_wall = time.perf_counter() - t0
    fleet = {
        "s25_n": 300,
        "s24_n": 100,
        "jobs": 400,
        "times_s": fleet_times,
        "wall_s": fleet_wall,
        "jobs_per_s": 400 / fleet_wall if fleet_wall else 0,
    }

    out = {
        "pin": PIN,
        "thermal_override": "QUIET_ALLOW_THERMAL_UNREADABLE=1",
        "operator_waived_unread_thermal": True,
        "not_a_new_isa": True,
        "not_a_new_operator_domain": True,
        "retracted_h141": {
            "one_one_wall_s": 6.8744451660022605,
            "three_one_wall_s": 5.173469625005964,
            "why": "tuple of submit().result() evaluated left-to-right; walls were sums",
        },
        "eval_order_demo": demo,
        "submit_result_same_expr": {"H141": hits_h141, "H148": hits_h148},
        "gates": {S25: g25, S24: g24},
        "one_one": {
            "s25_n": 200,
            "s24_n": 200,
            "s25_s": t25_11,
            "s24_s": t24_11,
            "wall_s": w11,
        },
        "three_one": {
            "s25_n": 300,
            "s24_n": 100,
            "s25_s": t25_31,
            "s24_s": t24_31,
            "wall_s": w31,
        },
        "s25_only_400_s": s25_only,
        "s25_k2": s25_k2,
        "s24_k2": s24_k2,
        "fleet_weighted_k2": fleet,
        "weighted_vs_one_one": w31 / w11 if w11 else 0,
        "three_one_vs_s25_only": w31 / s25_only if s25_only else 0,
        "fleet_vs_s25_k2": fleet_wall / s25_k2["wall_s"] if s25_k2["wall_s"] else 0,
    }
    HERE.joinpath("fleet.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))

    def serialized(wall, a, b) -> bool:
        return wall > 1.20 * max(a, b)

    print(
        f"1:1={w11:.3f} (max={max(t25_11, t24_11):.3f}) "
        f"3:1={w31:.3f} (max={max(t25_31, t24_31):.3f}) "
        f"s25only={s25_only:.3f} s25k2={s25_k2['wall_s']:.3f} "
        f"fleet={fleet_wall:.3f}"
    )
    if serialized(w11, t25_11, t24_11) or serialized(w31, t25_31, t24_31):
        print("STILL_SERIALIZED")
        return 1
    k1_wins = w31 < 0.90 * s25_only
    k2_wins = fleet_wall < 0.90 * s25_k2["wall_s"]
    print("K1_PAIR_WINS" if k1_wins else "K1_PAIR_LOSES")
    print("FLEET_WINS" if k2_wins else "FLEET_LOSES")
    if not k1_wins and not k2_wins:
        print("NO_DEVICE_SCALE")
        return 0
    print("DEVICE_SCALE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
