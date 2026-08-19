#!/usr/bin/env python3
"""G83 — F003_DRAFT is named, not frozen, not rust.

KERNEL_FRAGMENT now names fixtures/F003_specv1 as F003_DRAFT (modus
ponens, FT_METTA_CORE_V2) and says it is not a legal kernel class.
This row measures that. It does not teach rust F003. It does not
write immortal.json. It does not freeze.

F1: rust ACCEPT on F003_specv1 (must stay WRONG_FIXTURE_CLASS).
F2: F003 appears in kitchen/immortal.json.
F3: F001 or F002 pin moves.

  python3 spikes/G83_f003_draft/draft.py
"""
from __future__ import annotations

import json
import os
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
F003_SIDECAR = "0e1edf5bf87964efe1de8def1bef38ee22cdf86d495d8ac53273d2a6ed8bc8a5"
SPEC = ROOT / "specs" / "KERNEL_FRAGMENT.md"
IMMORTAL = ROOT / "kitchen" / "immortal.json"
RUST = ROOT / "fixtures" / "verifier" / "trace_verifier_web"
if not RUST.is_file():
    RUST = ROOT / "fixtures" / "verifier" / "trace_verifier"
GROK = ROOT / "fixtures" / "verifier" / "grok_check.py"
F003 = ROOT / "fixtures" / "F003_specv1"
F001 = ROOT / "fixtures" / "F001"
F002 = ROOT / "fixtures" / "F002_specv1"


def run(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    spec = SPEC.read_text()
    immortal = json.loads(IMMORTAL.read_text())
    man = json.loads((F003 / "F003.manifest.json").read_text())
    fuel_tbl = json.loads((F003 / "F003.fuel_table.json").read_text())

    r_f003, o_f003 = run([str(RUST), str(F003)])
    r_py, o_py = run([sys.executable, str(GROK), str(F003)])
    r1, o1 = run([sys.executable, str(GROK), str(F001)])
    r2, o2 = run([sys.executable, str(GROK), str(F002)])

    rust_wrong = "WRONG_FIXTURE_CLASS" in o_f003 and r_f003 != 0
    rust_accept = r_f003 == 0 or "ACCEPTED" in o_f003
    f003_immortal = any(
        "F003" in k for k in (immortal.get("fixtures") or {})
    )
    py_ok = r_py == 0 and F003_SIDECAR[:12] in o_py
    f001_ok = r1 == 0 and PIN_F001 in o1
    f002_ok = r2 == 0 and PIN_F002 in o2

    spec_names_draft = "F003_DRAFT" in spec and "FT_METTA_CORE_V2" in spec
    spec_not_legal = "not** a legal class" in spec.replace(" ", "") or (
        "not a legal class" in spec
    )
    spec_gate4_phone = "Phone F002 still open" not in spec
    spec_gate4_s25 = "S25" in spec and "c43b1eab9db84338" in spec
    v1_unpatched = "FT_METTA_CORE_V1" in spec and "Do not hot-patch V1" in spec
    nlines = spec.count("\n")

    f1 = rust_accept
    f2 = f003_immortal
    f3 = (PIN_F001 not in o1) or (PIN_F002 not in o2)

    rec = {
        "spike": "G83",
        "not_operator_2": True,
        "f003_frozen": False,
        "rust_taught_f003": False,
        "spec": {
            "names_f003_draft": spec_names_draft,
            "says_not_legal_class": spec_not_legal,
            "gate4_phone_open_removed": spec_gate4_phone,
            "gate4_names_s25_and_pin": spec_gate4_s25,
            "v1_not_hotpatched": v1_unpatched,
            "nlines": nlines,
        },
        "f003_sidecar": {
            "status": man.get("status"),
            "digest": man.get("accepted_digest"),
            "table_id": fuel_tbl.get("table_id"),
            "has_modus_ponens": "MODUS_PONENS" in (fuel_tbl.get("costs") or {}),
            "in_immortal": f003_immortal,
        },
        "python_f003": {"rc": r_py, "digest_ok": py_ok, "out_tail": o_py[-240:]},
        "rust_f003": {
            "rc": r_f003,
            "wrong_class": rust_wrong,
            "accept": rust_accept,
            "out_tail": o_f003[-240:],
        },
        "pins": {
            "f001": f001_ok,
            "f002": f002_ok,
        },
        "controls": {
            "C1_spec_draft": {"ok": spec_names_draft and spec_not_legal},
            "C2_gate4": {"ok": spec_gate4_phone and spec_gate4_s25},
            "C3_python_f003": {"ok": py_ok, "digest": F003_SIDECAR},
            "C4_rust_wrong_class": {"ok": rust_wrong},
            "C5_pins": {"ok": f001_ok and f002_ok},
            "C6_spec_length": {"nlines": nlines, "ok": nlines <= 120},
        },
        "falsifiers": {
            "F1_rust_accepts_f003": {
                "fired": f1,
                "fires_when": "rust ACCEPT on F003_specv1",
            },
            "F2_f003_immortal": {
                "fired": f2,
                "fires_when": "F003 key in kitchen/immortal.json",
            },
            "F3_pin_moved": {
                "fired": f3,
                "fires_when": "F001 or F002 pin missing from grok_check",
            },
        },
        "literature_compare": "unavailable",
    }

    outp = HERE / "draft.json"
    HERE.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rec, indent=2) + "\n")

    print("=== G83 F003_DRAFT ===")
    print(f"  spec draft={spec_names_draft} not_legal={spec_not_legal} "
          f"gate4_s25={spec_gate4_s25} nlines={nlines}")
    print(f"  python F003 rc={r_py} digest_ok={py_ok}")
    print(f"  rust F003 rc={r_f003} WRONG_FIXTURE_CLASS={rust_wrong}")
    print(f"  immortal F003={f003_immortal} F001={f001_ok} F002={f002_ok}")
    print(f"  F1={f1} F2={f2} F3={f3}")

    controls = [
        Control("C1_spec_draft", why="fragment names F003_DRAFT and not a legal class",
                can_fail_because="spec silent or treats F003 as frozen",
                null_must_contain="F003 missing from spec"),
        Control("C2_gate4", why="Gate 4 line names S25 + real pin; phone-open gone",
                can_fail_because="stale phone-open sentence",
                null_must_contain="Phone F002 still open"),
        Control("C3_python_f003", why="grok_check ACCEPT 0e1edf5b on sidecar",
                can_fail_because="python checker drift",
                null_must_contain="python miss"),
        Control("C4_rust_wrong_class", why="rust stays WRONG_FIXTURE_CLASS",
                can_fail_because="rust taught F003",
                null_must_contain="rust ACCEPT"),
        Control("C5_pins", why="F001 590d8769 F002 c43b1eab9db84338",
                can_fail_because="pin move",
                null_must_contain="pin miss"),
        Control("C6_spec_length", why="KERNEL_FRAGMENT stays 1–2 pages",
                can_fail_because="spec bloated past 120 lines",
                null_must_contain="nlines>120"),
    ]
    for ctl, key in zip(controls, [
        "C1_spec_draft", "C2_gate4", "C3_python_f003",
        "C4_rust_wrong_class", "C5_pins", "C6_spec_length",
    ]):
        ctl.observe(rec["controls"][key]["ok"], rec["controls"][key])

    falsifiers = [
        Falsifier("F1_rust_accepts_f003",
                  refutes="that rust has not been taught F003",
                  fires_when="rust ACCEPT on F003_specv1",
                  null_must_contain="rust ACCEPT"),
        Falsifier("F2_f003_immortal",
                  refutes="that F003 is not frozen",
                  fires_when="F003 key in kitchen/immortal.json",
                  null_must_contain="immortal F003"),
        Falsifier("F3_pin_moved",
                  refutes="that F001/F002 pins are unmoved",
                  fires_when="F001 or F002 pin missing from grok_check",
                  null_must_contain="pin miss"),
    ]
    falsifiers[0].observe(f1, rec["falsifiers"]["F1_rust_accepts_f003"])
    falsifiers[1].observe(f2, rec["falsifiers"]["F2_f003_immortal"])
    falsifiers[2].observe(f3, rec["falsifiers"]["F3_pin_moved"])

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(ROOT / "specs"), str(F003), str(ROOT / "kitchen")],
        artifacts=[str(HERE / "draft.py"), str(outp)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("draft_json", json.dumps(rec, sort_keys=True))],
        falsifier="rust ACCEPT F003, or F003 frozen, or F001/F002 pin moves",
        allow_dirty=True,
        note="G83: F003_DRAFT named in fragment, not frozen, rust WRONG_FIXTURE_CLASS.",
    )
    print(f"D6 certify ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
