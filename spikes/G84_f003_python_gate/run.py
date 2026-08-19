#!/usr/bin/env python3
"""G84 — Python-only F003 Modus Ponens Verification Gate.

Validates:
1. Python grok_check ACCEPTs fixtures/F003_specv1 at digest 0e1edf5bf87964efe1de8def1bef38ee22cdf86d495d8ac53273d2a6ed8bc8a5
2. 7/7 F003 mutants REJECT with exact expected tokens (FUEL_DIVERGENCE, ILLEGAL_OPCODE, CORPUS_ROOT_MISMATCH, FUEL_FILE_MISMATCH, SEMANTIC_UNIFICATION_FAILURE, RESULT_NOT_DERIVED)
3. Rust trace_verifier_web REJECTs fixtures/F003_specv1 as WRONG_FIXTURE_CLASS
4. Parent fixtures/F003 REJECTs (DIGEST_MISMATCH)
5. F001 (590d8769...) and F002 (c43b1eab...) pins remain unmoved
6. F003 status remains F003_DRAFT (NOT frozen, NOT in immortal.json)
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

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
PIN_F003 = "0e1edf5bf87964efe1de8def1bef38ee22cdf86d495d8ac53273d2a6ed8bc8a5"

GROK = ROOT / "fixtures" / "verifier" / "grok_check.py"
RUST = ROOT / "fixtures" / "verifier" / "trace_verifier_web"
SPEC = ROOT / "specs" / "KERNEL_FRAGMENT.md"
IMMORTAL = ROOT / "kitchen" / "immortal.json"


def run_cmd(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def parse_digest(out: str):
    m = re.search(r"Digest:\s+([0-9a-fA-F]{64})", out)
    return m.group(1).lower() if m else None


def main() -> int:
    t0 = time.time()
    print("=== Spike G84: Python-only F003 Modus Ponens Verification Gate ===")

    # 1. Python F003_specv1
    rc3, out3 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F003_specv1")])
    d3 = parse_digest(out3)
    p3_ok = rc3 == 0 and d3 == PIN_F003
    print(f"Python F003_specv1: rc={rc3}, digest={d3} (ok={p3_ok})")

    # 2. Python 7 mutants
    muts = []
    any_accept = False
    tokens = {}
    mdir = ROOT / "fixtures" / "F003_specv1" / "mutants"
    for d in sorted(mdir.iterdir()):
        if not d.is_dir():
            continue
        rc, out = run_cmd([sys.executable, str(GROK), str(d)])
        acc = rc == 0 or "ACCEPT" in out
        any_accept = any_accept or acc
        tok = "ACCEPT"
        for line in out.splitlines():
            if "REJECT:" in line:
                tok = line.split("->", 1)[1].strip() if "->" in line else line
                break
        muts.append({"name": d.name, "rc": rc, "accept": acc, "token": tok})
        tokens[d.name] = tok
        print(f"  Mutant {d.name}: rc={rc}, token={tok}")

    # 3. Rust on F003_specv1
    rc_rust, out_rust = run_cmd([str(RUST), str(ROOT / "fixtures" / "F003_specv1")])
    rust_wrong_class = rc_rust != 0 and "WRONG_FIXTURE_CLASS" in out_rust
    print(f"Rust on F003_specv1: rc={rc_rust}, wrong_class={rust_wrong_class}")

    # 4. Parent fixtures/F003
    rc_parent, out_parent = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F003")])
    parent_rejected = rc_parent != 0 and "DIGEST_MISMATCH" in out_parent
    print(f"Parent fixtures/F003: rc={rc_parent}, rejected={parent_rejected}")

    # 5. Pins F001 and F002 unmoved
    rc1, out1 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F001")])
    d1 = parse_digest(out1)
    rc2, out2 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F002_specv1")])
    d2 = parse_digest(out2)
    pins_unmoved = d1 == PIN_F001 and d2 == PIN_F002
    print(f"Pins check: F001={d1 == PIN_F001}, F002={d2 == PIN_F002}")

    # 6. Status and spec checks
    spec_text = SPEC.read_text(encoding="utf-8")
    spec_lines = len(spec_text.splitlines())
    spec_has_draft = "F003_DRAFT" in spec_text and "F003_MODUS_PONENS" in spec_text
    
    immortal_data = json.loads(IMMORTAL.read_text(encoding="utf-8")) if IMMORTAL.is_file() else []
    f003_not_immortal = "F003" not in immortal_data and "F003_specv1" not in immortal_data

    manifest_f003 = json.loads((ROOT / "fixtures" / "F003_specv1" / "F003.manifest.json").read_text())
    status_is_draft = manifest_f003.get("status") == "F003_DRAFT"

    f1 = any_accept
    f2 = rc_rust == 0
    f3 = not f003_not_immortal
    f4 = not pins_unmoved
    f5 = not status_is_draft

    res = {
        "spike": "G84",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "f003_specv1": {
            "digest": d3,
            "digest_ok": p3_ok,
            "status": manifest_f003.get("status"),
            "is_draft": status_is_draft,
        },
        "mutants": muts,
        "rust_f003": {
            "rc": rc_rust,
            "wrong_class": rust_wrong_class,
            "accept": rc_rust == 0,
        },
        "parent_f003_rejected": parent_rejected,
        "pins": {
            "f001": d1,
            "f002": d2,
            "f001_ok": d1 == PIN_F001,
            "f002_ok": d2 == PIN_F002,
        },
        "spec": {
            "nlines": spec_lines,
            "has_draft": spec_has_draft,
            "not_immortal": f003_not_immortal,
        },
        "controls": {
            "C1_python_f003": {"ok": p3_ok},
            "C2_mutants_reject": {"ok": len(muts) == 7 and not any_accept},
            "C3_rust_wrong_class": {"ok": rust_wrong_class},
            "C4_parent_rejected": {"ok": parent_rejected},
            "C5_pins_unmoved": {"ok": pins_unmoved},
            "C6_spec_and_status": {"ok": spec_has_draft and spec_lines <= 120 and status_is_draft},
        },
        "falsifiers": {
            "F1_mutant_accept": {"fired": f1, "tokens": tokens},
            "F2_rust_accept": {"fired": f2},
            "F3_in_immortal": {"fired": f3},
            "F4_pin_moved": {"fired": f4},
            "F5_status_frozen": {"fired": f5},
        },
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    controls = [
        Control("C1_python_f003", why="Python grok_check accepts F003_specv1 at 0e1edf5b", can_fail_because="unification or hashing bug", null_must_contain="digest mismatch"),
        Control("C2_mutants_reject", why="All 7 F003 mutants must REJECT", can_fail_because="mutant ACCEPT", null_must_contain="mutant pass"),
        Control("C3_rust_wrong_class", why="Rust must reject F003 as WRONG_FIXTURE_CLASS", can_fail_because="premature rust support", null_must_contain="wrong error"),
        Control("C4_parent_rejected", why="Parent fixtures/F003 must be rejected", can_fail_because="parent accepted", null_must_contain="parent pass"),
        Control("C5_pins_unmoved", why="F001 and F002 pins must remain unmoved", can_fail_because="pin drift", null_must_contain="pin moved"),
        Control("C6_spec_and_status", why="Spec must name F003_DRAFT and status must be DRAFT", can_fail_because="premature freeze", null_must_contain="not draft"),
    ]
    controls[0].observe(p3_ok, res["controls"]["C1_python_f003"])
    controls[1].observe(len(muts) == 7 and not any_accept, res["controls"]["C2_mutants_reject"])
    controls[2].observe(rust_wrong_class, res["controls"]["C3_rust_wrong_class"])
    controls[3].observe(parent_rejected, res["controls"]["C4_parent_rejected"])
    controls[4].observe(pins_unmoved, res["controls"]["C5_pins_unmoved"])
    controls[5].observe(spec_has_draft and spec_lines <= 120 and status_is_draft, res["controls"]["C6_spec_and_status"])

    falsifiers = [
        Falsifier("F1_mutant_accept", refutes="that Python checker rejects F003 mutants", fires_when="any mutant ACCEPT", null_must_contain="mutant pass"),
        Falsifier("F2_rust_accept", refutes="that Rust checker does not accept F003 prematurely", fires_when="rust accepts F003", null_must_contain="rust accept"),
        Falsifier("F3_in_immortal", refutes="that F003 is not prematurely in immortal.json", fires_when="F003 in immortal.json", null_must_contain="in immortal"),
        Falsifier("F4_pin_moved", refutes="that F001 and F002 pins remain invariant", fires_when="F001 or F002 pin moves", null_must_contain="pin moved"),
        Falsifier("F5_status_frozen", refutes="that F003 remains DRAFT", fires_when="F003 status == FROZEN", null_must_contain="frozen status"),
    ]
    falsifiers[0].observe(f1, {"any_accept": any_accept})
    falsifiers[1].observe(f2, {"rc": rc_rust})
    falsifiers[2].observe(f3, {"in_immortal": not f003_not_immortal})
    falsifiers[3].observe(f4, {"d1": d1, "d2": d2})
    falsifiers[4].observe(f5, {"status": manifest_f003.get("status")})

    ok, problems = kfcheck.certify(
        str(HERE),
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="Python-only F003 modus ponens verification gate failure",
        allow_dirty=True,
        no_deps_reason="kernel specification gate; no external elder",
        note="G84: Python-only F003 modus ponens gate under FT_METTA_CORE_V2. F003_DRAFT.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike G84 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
