#!/usr/bin/env python3
"""G70: Gate 4 Arm B against F002_specv1 (the fragment), not Gemini F002.

DEV (KF_DEV_SINGLE_OPERATOR) is rehearsal. This row does not mint operator=2
and does not freeze F002. Kitchen shortlist may change fallback rate; the
accepted digest must stay the grok_check pin.

Falsifiers stated first:
F1: homemade fixtures/battery_arm_b.make_digest of the correct F002_specv1
    result equals c43b1eab → old 8/8 Gate 4 is the fragment (expect FIRE).
F2: a no-fallback forged/partial result hashes to Arm A → battery cannot
    see interference (expect FIRE on the forged arm).
F3: fallback-to-grok_check on kitchen mutations leaves digest != c43b1eab
    → noninterference fails (signed; expect quiet).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "fixtures" / "verifier"))
sys.path.insert(0, str(ROOT / "fixtures"))

from grok_f002 import derive_hits, parse_corpus, spec_v1_digest  # noqa: E402
from battery_arm_b import make_digest  # noqa: E402

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
FIX = ROOT / "fixtures" / "F002_specv1"


def grok_check(path: Path) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(ROOT / "fixtures" / "verifier" / "grok_check.py"), str(path)],
        cwd=ROOT / "fixtures" / "verifier",
        capture_output=True,
        text=True,
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def rust_check(path: Path) -> tuple[int, str]:
    tv = ROOT / "fixtures" / "verifier" / "trace_verifier_web"
    if not tv.is_file():
        return 127, "MISSING_VERIFIER"
    p = subprocess.run([str(tv), str(path)], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def load_fix():
    corpus = (FIX / "F002.corpus.bin").read_bytes()
    cites, verdicts = parse_corpus(corpus)
    hits = derive_hits(cites, verdicts)
    man = json.loads((FIX / "F002.manifest.json").read_text())
    witness = (FIX / "F002.witness.json").read_bytes()
    result = json.loads(witness)["result"]
    return {
        "corpus_root": (FIX / "F002.corpus_root").read_text().strip(),
        "manifest_id": man["manifest_id"],
        "query": (FIX / "F002.query").read_text().strip(),
        "result": result,
        "fuel": int((FIX / "F002.fuel").read_text().strip()),
        "witness": witness,
        "hits": hits,
        "status": man.get("status"),
    }


def kitchen_shortlist(hits, mutation: str | None):
    true = [f"(hit {x} {y})" for x, y in sorted(hits)]
    extra = ["(hit FORGED S9)"]
    cands = [{"cand": h, "score": 1.0 - i * 0.001, "hdc": True} for i, h in enumerate(true)]
    cands.extend({"cand": e, "score": 0.01, "hdc": False} for e in extra)
    if mutation == "MUT1_REVERSE_SCORES":
        cands.sort(key=lambda c: c["score"])
    elif mutation == "MUT2_EXTREME_BETA":
        for c in cands:
            c["score"] = -100.0 * c["score"]
    elif mutation == "MUT3_DROP_GROUND_TRUTH":
        cands = [c for c in cands if c["cand"] != true[0]]
    elif mutation == "MUT4_INJECT_POISON":
        cands.insert(0, {"cand": extra[0], "score": 999.0, "hdc": True})
    elif mutation == "MUT5_CORRUPT_HDC":
        for c in cands:
            c["hdc"] = False
    elif mutation == "MUT6_FLAT_NOISE":
        for c in cands:
            c["score"] = 0.001
    elif mutation == "MUT7_NEAR_TIE":
        if len(cands) > 1:
            cands[0], cands[1] = cands[1], cands[0]
    short = [c["cand"] for c in cands if c.get("hdc", True)]
    return short


def arm_b(fix, mutation: str | None, *, fallback: bool):
    short = kitchen_shortlist(fix["hits"], mutation)
    claimed = set()
    for cand in short:
        if cand.startswith("(hit ") and cand.endswith(")"):
            a, b = cand[5:-1].split()
            claimed.add((a, b))
    complete = claimed == fix["hits"]
    if complete:
        digest = spec_v1_digest(
            corpus_root=fix["corpus_root"],
            manifest_id=fix["manifest_id"],
            query=fix["query"],
            result=fix["result"],
            fuel=fix["fuel"],
            witness_bytes=fix["witness"],
        )
        return {"digest": digest, "mode": "fast-path", "complete": True, "n": len(short)}
    if fallback:
        rc, out = grok_check(FIX)
        token = "ACCEPT" if rc == 0 and PIN_F002 in out else out
        return {
            "digest": PIN_F002 if PIN_F002 in out else token,
            "mode": "fallback-grok_check",
            "complete": False,
            "n": len(short),
            "rc": rc,
        }
    # no-fallback: hash whatever the kitchen published (forged/partial)
    fake_result = "(" + " ".join(f"(hit {x} {y})" for x, y in sorted(claimed)) + ")"
    digest = spec_v1_digest(
        corpus_root=fix["corpus_root"],
        manifest_id=fix["manifest_id"],
        query=fix["query"],
        result=fake_result,
        fuel=fix["fuel"],
        witness_bytes=fix["witness"],
    )
    return {"digest": digest, "mode": "no-fallback-forged", "complete": False, "n": len(short)}


def main() -> int:
    fix = load_fix()
    rc1, out1 = grok_check(ROOT / "fixtures" / "F001")
    rc2, out2 = grok_check(FIX)
    rcr, outr = rust_check(FIX)

    homemade = make_digest(
        fix["corpus_root"],
        fix["manifest_id"],
        fix["query"],
        fix["result"],
        fix["fuel"],
        __import__("hashlib").sha256(fix["witness"]).hexdigest(),
    )
    f1_fired = homemade != PIN_F002

    forged = arm_b(fix, "MUT3_DROP_GROUND_TRUTH", fallback=False)
    f2_fired = forged["digest"] != PIN_F002

    muts = [
        None,
        "MUT1_REVERSE_SCORES",
        "MUT2_EXTREME_BETA",
        "MUT3_DROP_GROUND_TRUTH",
        "MUT4_INJECT_POISON",
        "MUT5_CORRUPT_HDC",
        "MUT6_FLAT_NOISE",
        "MUT7_NEAR_TIE",
    ]
    rows = []
    all_pin = True
    for m in muts:
        row = arm_b(fix, m, fallback=True)
        row["mutation"] = m or "MUT0_BASELINE"
        rows.append(row)
        if row["digest"] != PIN_F002:
            all_pin = False
    f3_fired = not all_pin

    rec = {
        "id": "G70",
        "class": "Gate 4 Arm B retarget to F002_specv1",
        "not_operator_2": True,
        "not_f002_freeze": True,
        "f002_status": fix["status"],
        "fuel": fix["fuel"],
        "n_hits": len(fix["hits"]),
        "controls": {
            "C1_f001": {"rc": rc1, "out": out1, "ok": rc1 == 0 and PIN_F001 in out1},
            "C2_f002": {"rc": rc2, "out": out2, "ok": rc2 == 0 and PIN_F002 in out2},
            "C3_rust_wrong_class": {
                "rc": rcr,
                "out": outr,
                "ok": "WRONG_FIXTURE_CLASS" in outr,
            },
            "C4_still_draft": {"status": fix["status"], "ok": fix["status"] == "F002_DRAFT"},
        },
        "falsifiers": {
            "F1_old_battery_is_fragment": {
                "homemade": homemade,
                "pin": PIN_F002,
                "fired": f1_fired,
                "expect": True,
            },
            "F2_no_fallback_invisible": {
                "forged_digest": forged["digest"],
                "fired": f2_fired,
                "expect": True,
            },
            "F3_fallback_leaves_pin": {
                "all_mutations_keep_pin": all_pin,
                "fired": f3_fired,
                "expect": False,
            },
        },
        "arm_b": rows,
        "gate4_closed": False,
        "reason_not_closed": "F002_specv1 is F002_DRAFT; rust stays F001-only; Arm B is now on the fragment digest",
    }
    outp = Path(__file__).resolve().parent / "result.json"
    outp.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "F1_fired": f1_fired,
        "F2_fired": f2_fired,
        "F3_fired": f3_fired,
        "C1": rec["controls"]["C1_f001"]["ok"],
        "C2": rec["controls"]["C2_f002"]["ok"],
        "C3": rec["controls"]["C3_rust_wrong_class"]["ok"],
        "C4": rec["controls"]["C4_still_draft"]["ok"],
        "homemade_prefix": homemade[:16],
        "n_hits": len(fix["hits"]),
        "fuel": fix["fuel"],
        "status": fix["status"],
        "gate4_closed": False,
    }, indent=2))
    ok = (
        rec["controls"]["C1_f001"]["ok"]
        and rec["controls"]["C2_f002"]["ok"]
        and rec["controls"]["C3_rust_wrong_class"]["ok"]
        and rec["controls"]["C4_still_draft"]["ok"]
        and f1_fired
        and f2_fired
        and not f3_fired
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
