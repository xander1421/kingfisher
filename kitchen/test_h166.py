#!/usr/bin/env python3
"""H166: H164's shuffle arm collapses a rotation-free model too (A3 0.0038), so
its 99.4% collapse cannot attribute the score to rotation. Involution keeps 0.3513."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "spikes" / "H166_rotation_ablation_discriminates" / "result.json"


def main() -> int:
    bad = []
    if not J.is_file():
        print("SELFCHECK FAILED: result.json missing")
        return 1
    d = json.loads(J.read_text())
    if d.get("spike") != "H166":
        bad.append(d.get("spike"))

    arms = d.get("arms") or {}

    def mrr(name):
        return (arms.get(name) or {}).get("mrr")

    # C1: without reproducing G91 nothing downstream is about G91.
    if mrr("A0_honest") != 0.3546:
        bad.append(f"A0 {mrr('A0_honest')} != G91's 0.3546")
    # H164's own arm must still reproduce, or the comparison is not with H164.
    if mrr("A2_shuffled_h164") != 0.0020:
        bad.append(f"A2 {mrr('A2_shuffled_h164')} != H164's published 0.0020")

    # THE CLAIM, both halves.
    a0, a1, a3 = mrr("A0_honest"), mrr("A1_involution"), mrr("A3_shuffled_involution")
    if None in (a0, a1, a3):
        bad.append("an arm is missing")
    else:
        if a0 - a1 >= 0.05:
            bad.append(f"involution lost {a0 - a1:.4f} >= 0.05 — F1 would have fired")
        if a3 >= 0.05:
            bad.append(f"rotation-free model survived shuffling at {a3} — F2 would have fired")

    inv = d.get("involution_check") or {}
    tol = inv.get("tol", 1e-6)
    if not (inv.get("modulus_err", 1) < tol and inv.get("square_err", 1) < tol):
        bad.append(f"arm is not an involution: {inv}")

    drf = d.get("derivationally_related_form") or {}
    if drf.get("involution_mrr", 0) < 0.50:
        bad.append(f"drf under involution {drf.get('involution_mrr')} < 0.50 — F3 would have fired")

    for c in ("C1_reproduces_G91", "C2_arm_is_an_involution", "C3_scope_and_pins"):
        if not ((d.get("controls") or {}).get(c) or {}).get("ok"):
            bad.append(f"control {c} not ok")
    for f in ("F1_involution_loses", "F2_shuffle_discriminates", "F3_involution_loses_drf"):
        if ((d.get("falsifiers") or {}).get(f) or {}).get("fired"):
            bad.append(f"falsifier {f} fired — the row's claim does not stand")

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print(f"h166: involution keeps {a1} of {a0}; shuffling a rotation-free model "
          f"still collapses to {a3}, so collapse does not attribute rotation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
