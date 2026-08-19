#!/usr/bin/env python3
"""H165: RotatE's WN18RR score is a reversed-triple leak, not geometry.

Fails if the finding stops holding. The load-bearing assertion is the WITHIN-
RELATION split: _derivationally_related_form's 0.9412 MRR survives only on the
test triples whose reverse (o,p,s) is in train.txt, and collapses on the rest.
That is the comparison G91's C2_zero_leak cannot make, because it intersects
exact (p,s,o) tuples and a reversed triple is never in that intersection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "spikes" / "H165_rotate_symmetry_leak" / "result.json"

SYMMETRIC = {"_derivationally_related_form", "_verb_group", "_also_see", "_similar_to"}


def main() -> int:
    bad = []
    if not J.is_file():
        print("SELFCHECK FAILED: result.json missing")
        return 1
    d = json.loads(J.read_text())
    if d.get("spike") != "H165":
        bad.append(d.get("spike"))

    # C1 is the one that voids everything downstream: if the re-run does not
    # land on G91's published number, nothing here is about G91.
    rep = d.get("reproduction") or {}
    if not rep.get("reproduced"):
        bad.append(f"did NOT reproduce G91: {rep.get('my_mrr_optimistic')} vs {rep.get('g91_published_mrr')}")

    ctrls = d.get("controls") or {}
    for c in ("C1_reproduces_G91", "C2_partition_is_exhaustive", "C3_pins_intact"):
        if not (ctrls.get(c) or {}).get("ok"):
            bad.append(f"control {c} not ok")

    part = d.get("leak_partition") or {}
    if part.get("leaked_queries", 0) + part.get("clean_queries", 0) != 6268:
        bad.append("partition does not cover 6,268 queries")
    if part.get("gap", 0.0) < 0.10:
        bad.append(f"leaked-vs-clean MRR gap {part.get('gap')} < 0.10 — F2 would fire")

    drf = d.get("derivationally_related_form") or {}
    if drf.get("mrr_clean", 1.0) >= 0.50:
        bad.append(f"clean _drf MRR {drf.get('mrr_clean')} >= 0.50 — F1 fires, finding withdrawn")
    if drf.get("mrr_leaked", 0.0) <= drf.get("mrr_clean", 1.0):
        bad.append("leaked _drf does not outscore clean _drf — the split explains nothing")

    fz = d.get("falsifiers") or {}
    for f in ("F1_clean_drf_still_strong", "F2_partition_explains_nothing"):
        if (fz.get(f) or {}).get("fired"):
            bad.append(f"{f} FIRED — this finding is withdrawn, not merely failing")

    # F3 is recorded NOT fired: the tie rule is immaterial. If it ever fires,
    # the headline has a SECOND defect and this test must stop passing silently.
    tb = d.get("tie_breaking") or {}
    if tb.get("swing", 0.0) >= 0.01:
        bad.append(f"tie-rule swing {tb.get('swing')} >= 0.01 — separate defect, F3 fires")

    # the shape of the whole finding: every relation that scores lives in the
    # symmetric set, and every relation with a 0% leak rate does not.
    for name, r in (d.get("per_relation") or {}).items():
        if r.get("leak_rate") == 0.0 and (r.get("mrr") or 0.0) >= 0.20:
            bad.append(f"{name}: 0% leak but MRR {r.get('mrr')} >= 0.20 — geometry after all")
        if (r.get("mrr") or 0.0) >= 0.20 and name not in SYMMETRIC:
            bad.append(f"{name}: MRR {r.get('mrr')} >= 0.20 outside the symmetric set")

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1

    print(f"h165: G91 reproduced at {rep.get('my_mrr_optimistic')}; "
          f"MRR|leaked={part.get('mrr_leaked')} vs MRR|clean={part.get('mrr_clean')}; "
          f"_drf leaked={drf.get('mrr_leaked')} clean={drf.get('mrr_clean')} "
          f"({drf.get('queries_clean')} clean queries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
