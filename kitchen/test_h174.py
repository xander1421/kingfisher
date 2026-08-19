#!/usr/bin/env python3
"""H174: on the non-leaked partition G89's symbolic rules beat G91's RotatE.

The load-bearing assertions are (a) ARM-FULL reproduces G89's published 0.0355,
without which nothing here is about G89, and (b) the ordering on the clean
partition is the REVERSE of the published "10.0x lift".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "spikes" / "H174_clean_partition_baseline" / "result.json"


def main() -> int:
    bad = []
    if not J.is_file():
        print("SELFCHECK FAILED: result.json missing")
        return 1
    d = json.loads(J.read_text())
    if d.get("spike") != "H174":
        bad.append(d.get("spike"))

    ctrls = d.get("controls") or {}
    for c in ("C1_reproduces_G89", "C2_same_partition_as_H165", "C3_full_split_evaluated"):
        if not (ctrls.get(c) or {}).get("ok"):
            bad.append(f"control {c} not ok")

    full = d.get("arm_full") or {}
    comp = d.get("comparands_read_from_disk") or {}
    if full.get("mrr") != comp.get("g89_published_mrr"):
        bad.append(f"ARM-FULL {full.get('mrr')} != G89 published {comp.get('g89_published_mrr')}")
    if full.get("n_queries") != 6268:
        bad.append(f"ARM-FULL n_queries {full.get('n_queries')} != 6268")

    part = d.get("partition") or {}
    if part.get("clean_triples") != 2048 or part.get("clean_queries") != 4096:
        bad.append(f"partition {part} is not H165's 2,048/4,096")

    v = d.get("verdict_on_clean") or {}
    if v.get("g89_symbolic", 0.0) <= v.get("rotate_g91", 1.0):
        bad.append(f"ordering did NOT invert on clean: G89 {v.get('g89_symbolic')} "
                   f"vs RotatE {v.get('rotate_g91')} — F1 fires, finding withdrawn")

    fz = d.get("falsifiers") or {}
    for f in ("F1_rotate_still_wins_on_clean", "F2_run_is_void", "F3_partition_mismatch"):
        if (fz.get(f) or {}).get("fired"):
            bad.append(f"{f} FIRED")

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1

    print(f"h174: G89 full {full.get('mrr')} (reproduced) · clean {v.get('g89_symbolic')} "
          f"vs RotatE clean {v.get('rotate_g91')} — symbolic is {v.get('g89_over_rotate')}x "
          f"on the 4,096 queries that require generalisation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
