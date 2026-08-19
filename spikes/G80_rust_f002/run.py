#!/usr/bin/env python3
"""G80 — rust F002_TWO_BOUND at c43b1eab. Record live checker outputs."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
RUST = ROOT / "fixtures" / "verifier" / "trace_verifier_web"
GROK = ROOT / "fixtures" / "verifier" / "grok_check.py"


def run(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def parse_fuel(out: str):
    m = re.search(r"Derived Fuel:\s+(\d+)", out)
    return int(m.group(1)) if m else None


def main() -> int:
    r1, o1 = run([str(RUST), str(ROOT / "fixtures" / "F001")])
    r2, o2 = run([str(RUST), str(ROOT / "fixtures" / "F002_specv1")])
    rg, og = run([str(RUST), str(ROOT / "fixtures" / "F002")])
    r3, o3 = run([str(RUST), str(ROOT / "fixtures" / "F003_specv1")])
    p1, po1 = run([sys.executable, str(GROK), str(ROOT / "fixtures" / "F001")])
    p2, po2 = run([sys.executable, str(GROK), str(ROOT / "fixtures" / "F002_specv1")])

    muts = []
    any_accept = False
    tokens = {}
    mdir = ROOT / "fixtures" / "F002_specv1" / "mutants"
    for d in sorted(mdir.iterdir()):
        if not d.is_dir():
            continue
        rc, out = run([str(RUST), str(d)])
        acc = rc == 0 or "ACCEPTED" in out
        any_accept = any_accept or acc
        tok = "ACCEPT"
        for line in out.splitlines():
            if "REJECTED:" in line:
                tok = line.split("REJECTED:", 1)[1].strip().split()[0].rstrip(":")
                break
        muts.append({"name": d.name, "rc": rc, "accept": acc, "token": tok})
        tokens[d.name] = tok

    fuel_f001 = parse_fuel(o1)
    fuel_f002 = parse_fuel(o2)
    c3_ok = fuel_f001 == 400 and fuel_f002 == 400

    f1 = PIN_F002 not in o2 or r2 != 0
    f2 = PIN_F001 not in o1 or r1 != 0
    f3 = any_accept
    f4 = rg == 0 or "ACCEPTED" in og
    f5 = "MISSING_FILE" in o3 and "F001.corpus.bin" in o3

    rec = {
        "spike": "G80",
        "not_operator_2": True,
        "gate4_phone_closed": False,
        "rust_f001": {"rc": r1, "digest_ok": PIN_F001 in o1, "fuel": fuel_f001},
        "rust_f002": {"rc": r2, "digest_ok": PIN_F002 in o2, "fuel": fuel_f002},
        "rust_gemini_f002": {"rc": rg, "accept": f4, "out_tail": og[-200:]},
        "rust_f003": {"rc": r3, "wrong_class": "WRONG_FIXTURE_CLASS" in o3, "missing_f001": f5},
        "python_f001": {"rc": p1, "ok": PIN_F001 in po1},
        "python_f002": {"rc": p2, "ok": PIN_F002 in po2},
        "mutants": muts,
        "controls": {
            "C1_python_f001": {"ok": p1 == 0 and PIN_F001 in po1},
            "C2_python_f002": {"ok": p2 == 0 and PIN_F002 in po2},
            "C3_fuel": {"fuel_f001": fuel_f001, "fuel_f002": fuel_f002, "ok": c3_ok},
        },
        "falsifiers": {
            "F1_rust_f002_pin": {"fired": f1, "digest_in_out": PIN_F002 in o2},
            "F2_rust_f001_pin": {"fired": f2, "digest_in_out": PIN_F001 in o1},
            "F3_mutant_accept": {"fired": f3, "any_accept": any_accept, "tokens": tokens},
            "F4_gemini_accept": {"fired": f4},
            "F5_f003_looks_like_broken_f001": {"fired": f5, "wrong_class": "WRONG_FIXTURE_CLASS" in o3},
        },
    }
    outp = HERE / "result.json"
    outp.write_text(json.dumps(rec, indent=2) + "\n")

    controls = [
        Control("C1_python_f001", why="python F001 pin", can_fail_because="checker drift",
                null_must_contain="F001 miss"),
        Control("C2_python_f002", why="python F002 pin", can_fail_because="checker drift",
                null_must_contain="F002 miss"),
        Control("C3_fuel", why="F002 fuel 400", can_fail_because="table hot-patched",
                null_must_contain="fuel!=400"),
    ]
    controls[0].observe(rec["controls"]["C1_python_f001"]["ok"], rec["controls"]["C1_python_f001"])
    controls[1].observe(rec["controls"]["C2_python_f002"]["ok"], rec["controls"]["C2_python_f002"])
    controls[2].observe(c3_ok, rec["controls"]["C3_fuel"])
    falsifiers = [
        Falsifier("F1_rust_f002_pin", refutes="that rust reproduces c43b1eab",
                  fires_when="rust F002_specv1 digest != c43b1eab",
                  null_must_contain="pin miss"),
        Falsifier("F2_rust_f001_pin", refutes="that F001 pin is unmoved",
                  fires_when="rust F001 digest != 590d8769",
                  null_must_contain="F001 moved"),
        Falsifier("F3_mutant_accept", refutes="that rust rejects F002 mutants",
                  fires_when="any of 7 F002 mutants ACCEPT",
                  null_must_contain="mutant ACCEPT"),
        Falsifier("F4_gemini_accept", refutes="that Gemini F002 stays invalid",
                  fires_when="rust fixtures/F002 ACCEPT",
                  null_must_contain="gemini ACCEPT"),
        Falsifier("F5_f003_looks_like_broken_f001",
                  refutes="that unknown class is WRONG_FIXTURE_CLASS not MISSING_FILE F001",
                  fires_when="rust F003_specv1 reports MISSING_FILE F001.corpus.bin",
                  null_must_contain="MISSING_FILE F001"),
    ]
    falsifiers[0].observe(f1, rec["falsifiers"]["F1_rust_f002_pin"])
    falsifiers[1].observe(f2, rec["falsifiers"]["F2_rust_f001_pin"])
    falsifiers[2].observe(f3, rec["falsifiers"]["F3_mutant_accept"])
    falsifiers[3].observe(f4, rec["falsifiers"]["F4_gemini_accept"])
    falsifiers[4].observe(f5, rec["falsifiers"]["F5_f003_looks_like_broken_f001"])

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(ROOT / "fixtures" / "F001"), str(ROOT / "fixtures" / "F002_specv1")],
        artifacts=[str(ROOT / "fixtures" / "verifier" / "trace_verifier.rs"), str(outp)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("g80_json", json.dumps(rec, sort_keys=True))],
        falsifier="rust F002 digest moves, or F001 moves, or a mutant/Gemini ACCEPT, or F003 looks like broken F001",
        allow_dirty=True,
        note="G80: rust F002_TWO_BOUND. Phone F002 not claimed closed.",
    )
    print(json.dumps({
        "F1": f1, "F2": f2, "F3": f3, "F4": f4, "F5": f5,
        "rust_f002": PIN_F002 in o2, "certify": ok,
    }))
    for pr in problems:
        print("PROBLEM", pr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
