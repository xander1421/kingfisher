#!/usr/bin/env python3
"""G71: freeze F002_specv1 iff pin holds and Gemini F002 stays invalid."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
FIX = ROOT / "fixtures" / "F002_specv1"


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def grok(path: Path):
    return run(
        [sys.executable, str(ROOT / "fixtures" / "verifier" / "grok_check.py"), str(path)],
        cwd=ROOT / "fixtures" / "verifier",
    )


def ind(path: Path):
    return run([sys.executable, str(ROOT / "fixtures" / "verifier" / "grok_f002.py"), str(path)])


def main() -> int:
    man = json.loads((FIX / "F002.manifest.json").read_text())
    rc1, out1 = grok(ROOT / "fixtures" / "F001")
    rc2, out2 = grok(FIX)
    ri, outi = ind(FIX)
    rr, outr = run([str(ROOT / "fixtures" / "verifier" / "trace_verifier_web"), str(FIX)])
    rg, outg = ind(ROOT / "fixtures" / "F002")

    muts = []
    any_accept = False
    for d in sorted((FIX / "mutants").iterdir()):
        if not d.is_dir():
            continue
        a, oa = grok(d)
        b, ob = ind(d)
        acc = a == 0 or b == 0
        any_accept = any_accept or acc
        muts.append({"name": d.name, "grok_rc": a, "ind_rc": b, "accept": acc})

    tmp = Path(tempfile.mkdtemp(prefix="g71_gen_"))
    gen = (ROOT / "fixtures" / "verifier" / "generate_f002_specv1.py").read_text()
    gen = gen.replace(
        "sys.path.insert(0, str(Path(__file__).resolve().parent))",
        f"sys.path.insert(0, {str(ROOT / 'fixtures' / 'verifier')!r})",
    )
    gen = gen.replace(
        "HERE = Path(__file__).resolve().parent",
        f"HERE = Path({str(ROOT / 'fixtures' / 'verifier')!r})",
    )
    gen = gen.replace(
        'DST = HERE.parent / "F002_specv1"',
        f'DST = Path({str(tmp / "out")!r})',
    )
    script = tmp / "gen.py"
    script.write_text(gen)
    rcg, out_gen = run([sys.executable, str(script)], cwd=ROOT / "fixtures" / "verifier")
    gen_digest = None
    gp = tmp / "out" / "F002.accepted_digest"
    if gp.is_file():
        gen_digest = gp.read_text().strip()

    rec = {
        "id": "G71",
        "not_operator_2": True,
        "f002_status": man.get("status"),
        "live_digest": (FIX / "F002.accepted_digest").read_text().strip(),
        "controls": {
            "C1_f001": {"ok": rc1 == 0 and PIN_F001 in out1, "out": out1},
            "C2_gemini_invalid": {
                "ok": rg != 0 and "F002_FROZEN_INVALID" in outg,
                "out": outg[:500],
            },
            "C3_generate_tmp": {
                "ok": gen_digest == PIN_F002,
                "rc": rcg,
                "digest": gen_digest,
                "out": out_gen[-400:],
            },
            "C4_rust_wrong_class": {"ok": "WRONG_FIXTURE_CLASS" in outr, "out": outr[:240]},
        },
        "falsifiers": {
            "F1_honest_misses_pin": {
                "fired": not (rc2 == 0 and PIN_F002 in out2 and ri == 0 and PIN_F002 in outi),
                "expect": False,
                "grok": out2,
                "ind": outi,
            },
            "F2_mutant_accepts": {"fired": any_accept, "expect": False, "mutants": muts},
            "F3_status_moved_pin": {
                "fired": rec_pin_moved(out2),
                "expect": False,
                "digest": (FIX / "F002.accepted_digest").read_text().strip(),
            },
            "F4_checker_rejects_honest_frozen": {
                "fired": ri != 0 or "F002_FROZEN_VALID" not in outi,
                "expect": False,
                "ind": outi,
            },
            "F5_f001_moved": {
                "fired": PIN_F001 not in out1
                or (ROOT / "fixtures" / "F001" / "F001.accepted_digest").read_text().strip()
                != PIN_F001,
                "expect": False,
            },
        },
        "gate4": {
            "f002_frozen": man.get("status") == "F002_FROZEN",
            "arm_b_on_pin": True,
            "closed": man.get("status") == "F002_FROZEN",
            "note": "F002_TWO_BOUND frozen; Arm B (G70) already keeps c43b1eab. Rust stays F001-only.",
        },
    }
    outp = Path(__file__).resolve().parent / "result.json"
    outp.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": man.get("status"),
        "F1": rec["falsifiers"]["F1_honest_misses_pin"]["fired"],
        "F2": rec["falsifiers"]["F2_mutant_accepts"]["fired"],
        "F3": rec["falsifiers"]["F3_status_moved_pin"]["fired"],
        "F4": rec["falsifiers"]["F4_checker_rejects_honest_frozen"]["fired"],
        "F5": rec["falsifiers"]["F5_f001_moved"]["fired"],
        "C1": rec["controls"]["C1_f001"]["ok"],
        "C2": rec["controls"]["C2_gemini_invalid"]["ok"],
        "C3": rec["controls"]["C3_generate_tmp"]["ok"],
        "C4": rec["controls"]["C4_rust_wrong_class"]["ok"],
        "ind_verdict": [ln for ln in outi.splitlines() if "VERDICT" in ln],
    }, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)
    ok = all(c["ok"] for c in rec["controls"].values()) and not any(
        f["fired"] for f in rec["falsifiers"].values()
    )
    return 0 if ok else 1


def rec_pin_moved(grok_out: str) -> bool:
    return PIN_F002 not in grok_out


if __name__ == "__main__":
    sys.exit(main())
