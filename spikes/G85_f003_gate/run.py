#!/usr/bin/env python3
"""G85 — Python-only F003 Modus Ponens Verification Gate (GROK-LOCAL claim fulfill)."""
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
    print("=== Spike G85: Python-only F003 Gate ===")

    rc3, out3 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F003_specv1")])
    d3 = parse_digest(out3)
    p3_ok = rc3 == 0 and d3 == PIN_F003

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

    rc_rust, out_rust = run_cmd([str(RUST), str(ROOT / "fixtures" / "F003_specv1")])
    rust_wrong_class = rc_rust != 0 and "WRONG_FIXTURE_CLASS" in out_rust

    rc1, out1 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F001")])
    d1 = parse_digest(out1)
    rc2, out2 = run_cmd([sys.executable, str(GROK), str(ROOT / "fixtures" / "F002_specv1")])
    d2 = parse_digest(out2)
    pins_unmoved = d1 == PIN_F001 and d2 == PIN_F002

    spec_text = SPEC.read_text(encoding="utf-8")
    spec_lines = len(spec_text.splitlines())
    spec_has_draft = "F003_DRAFT" in spec_text and "F003_MODUS_PONENS" in spec_text
    
    immortal_data = json.loads(IMMORTAL.read_text(encoding="utf-8")) if IMMORTAL.is_file() else []
    f003_not_immortal = "F003" not in immortal_data and "F003_specv1" not in immortal_data

    manifest_f003 = json.loads((ROOT / "fixtures" / "F003_specv1" / "F003.manifest.json").read_text())
    status_is_draft = manifest_f003.get("status") == "F003_DRAFT"

    res = {
        "spike": "G85",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "f003_digest": d3,
        "mutants": muts,
        "rust_wrong_class": rust_wrong_class,
        "pins_unmoved": pins_unmoved,
        "spec_ok": spec_has_draft and spec_lines <= 120,
        "not_immortal": f003_not_immortal,
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    controls = [
        Control("C1_spec_draft", why="Spec names F003_MODUS_PONENS and F003_DRAFT", can_fail_because="spec drift", null_must_contain="spec missing draft"),
        Control("C2_mutants_reject", why="All 7 mutants REJECT", can_fail_because="mutant ACCEPT", null_must_contain="mutant pass"),
        Control("C3_python_f003", why="Python accepts 0e1edf5b", can_fail_because="digest mismatch", null_must_contain="digest miss"),
        Control("C4_rust_wrong_class", why="Rust returns WRONG_FIXTURE_CLASS", can_fail_because="wrong rust error", null_must_contain="wrong error"),
        Control("C5_nlines_120", why="Spec <= 120 lines", can_fail_because="spec too long", null_must_contain="lines > 120"),
    ]
    controls[0].observe(spec_has_draft, {"spec_has_draft": spec_has_draft})
    controls[1].observe(len(muts) == 7 and not any_accept, {"mutants_count": len(muts), "any_accept": any_accept})
    controls[2].observe(p3_ok, {"d3": d3})
    controls[3].observe(rust_wrong_class, {"rust_wrong_class": rust_wrong_class})
    controls[4].observe(spec_lines <= 120, {"spec_lines": spec_lines})

    falsifiers = [
        Falsifier("F1_mutant_accept", refutes="that Python checker rejects F003 mutants", fires_when="any mutant ACCEPT", null_must_contain="mutant pass"),
        Falsifier("F2_rust_accept", refutes="that Rust checker does not accept F003", fires_when="rust accepts F003", null_must_contain="rust accept"),
        Falsifier("F3_in_immortal", refutes="that F003 is not in immortal.json", fires_when="F003 in immortal.json", null_must_contain="in immortal"),
        Falsifier("F4_pin_moved", refutes="that F001 and F002 pins remain invariant", fires_when="F001 or F002 pin moves", null_must_contain="pin moved"),
    ]
    falsifiers[0].observe(any_accept, {"any_accept": any_accept})
    falsifiers[1].observe(rc_rust == 0, {"rc": rc_rust})
    falsifiers[2].observe(not f003_not_immortal, {"in_immortal": not f003_not_immortal})
    falsifiers[3].observe(not pins_unmoved, {"pins_unmoved": pins_unmoved})

    ok, problems = kfcheck.certify(
        str(HERE),
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="Python-only F003 gate check failure",
        allow_dirty=True,
        no_deps_reason="kernel specification gate; no external elder",
        note="G85: Python-only F003 modus ponens gate.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike G85 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
