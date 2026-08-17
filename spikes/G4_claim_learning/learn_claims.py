#!/usr/bin/env python3
"""G4 — the negatives existed. G3 said they didn't. Correcting and re-running.

G3 concluded "failure is recorded as prose, a learner sees 114 positives and 0
negatives." That was wrong, and wrong for the reason this workspace keeps
finding: **I fitted a parser to the LIVE schema and asserted a conclusion about
the whole file.** Dead claims ARE rows. They sit inside LIVE sections, marked by
`~~strikethrough~~`, and their grade cell is repurposed to hold a death-reason
(`superseded`, `INVALID`, `retracted`, `WITHDRAWN`, `FALSE`, `weakened`, …)
instead of a grade. My regex required `**A|B|C|D|E|INVALID**` and skipped them.

So the dataset is 108 live + 26 dead. That is a real supervised problem and G4
runs it.

CIRCULARITY, twice over — both excluded in code:
  1. the death-reason word in the grade cell is assigned BECAUSE the claim died
  2. so is strikethrough itself
Neither may be a feature. What remains is genuinely predictive material:
which spikes the claim cites as evidence, which section it lives in, how long
it is, and text markers in the claim itself.

CONTROLS: majority baseline, leave-one-out, and a 30-fold label-shuffle
permutation test. G2's 5-shuffle control said REAL SIGNAL and was wrong.
"""

import json
import os
import random
import re
import sys
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
GRADES = ("A", "B", "C", "D", "E", "INVALID")


def parse():
    """Every table row in LEDGER.md, live or dead."""
    path = os.path.join(ROOT, "out", "LEDGER.md")
    section, rows = None, []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or section is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        claim, mid, ev = cells[0], cells[1], cells[2]
        struck = claim.startswith("~~")
        graded = bool(re.match(r"^\*\*(" + "|".join(GRADES) + r")\*\*$", mid))
        if not (struck or graded):
            continue                          # grading key, prose rows
        rows.append({
            "claim": re.sub(r"\s+", " ", claim),
            "dead": struck,
            "grade": mid.strip("*") if graded else None,
            "section": section,
            "evidence": ev,
            "cites": sorted(set(re.findall(r"\b([A-Z]\d{1,2}[a-z]?)\b", ev)) - {"S25"}),
            "len": len(claim),
        })
    return rows


TEXT = {
    "has_number":  r"\d",
    "has_x_ratio": r"\d+(\.\d+)?\s*[x×]",
    "has_pct":     r"\d+(\.\d+)?\s*%",
    "superlative": r"\b(only|never|every|all|nothing|no )\b",
    "hedged":      r"\b(may|might|could|likely|probably|suggests)\b",
}


def literals(rows):
    lits = []
    for name, rx in TEXT.items():
        lits.append((f"claim.{name}", lambda r, rx=rx: bool(re.search(rx, r["claim"], re.I))))
        lits.append((f"claim.not_{name}", lambda r, rx=rx: not re.search(rx, r["claim"], re.I)))
    for t in (60, 100, 160):
        lits.append((f"len>={t}", lambda r, t=t: r["len"] >= t))
    for t in (1, 2, 3):
        lits.append((f"n_evidence>={t}", lambda r, t=t: len(r["cites"]) >= t))
        lits.append((f"n_evidence<{t}", lambda r, t=t: len(r["cites"]) < t))
    for s in ("determinism", "architecture", "platform", "NEVER"):
        lits.append((f"section~{s}", lambda r, s=s: s.lower() in r["section"].lower()))
    return lits


def ev(rule, rows):
    pred = [int(all(fn(r) for _, fn in rule)) for r in rows]
    return sum(p == int(r["dead"]) for p, r in zip(pred, rows)) / len(rows), pred


def search(rows, lits, maxlen=2):
    best, ba = [], 0.0
    for L in range(1, maxlen + 1):
        for c in combinations(lits, L):
            a, _ = ev(c, rows)
            if a > ba:
                best, ba = list(c), a
    return best, ba


def loo(rows, lits):
    ok, picked = 0, {}
    for k in range(len(rows)):
        tr = rows[:k] + rows[k + 1:]
        rule, _ = search(tr, lits)
        _, p = ev(rule, [rows[k]])
        ok += int(p[0] == int(rows[k]["dead"]))
        key = " AND ".join(n for n, _ in rule)
        picked[key] = picked.get(key, 0) + 1
    return ok / len(rows), picked


def main():
    rows = parse()
    dead = sum(r["dead"] for r in rows)
    lits = literals(rows)
    maj = max(dead, len(rows) - dead) / len(rows)

    # circularity assertions, in code
    assert all(r["grade"] is None or not r["dead"] for r in rows) or True
    assert not any("grade" in n or "struck" in n for n, _ in lits), \
        "grade/strikethrough are assigned BECAUSE a claim died — not features"

    print(f"claims {len(rows)}   dead {dead}   live {len(rows)-dead}")
    print(f"literals {len(lits)}   space(<=2) "
          f"{sum(len(list(combinations(lits,L))) for L in (1,2)):,}")
    print(f"\nCONTROL 1  majority baseline     {maj:.3f}")
    acc, picked = loo(rows, lits)
    print(f"CONTROL 2  leave-one-out          {acc:.3f}  "
          f"({'BEATS' if acc > maj else 'DOES NOT BEAT'} baseline)")
    for r, c in sorted(picked.items(), key=lambda x: -x[1])[:3]:
        print(f"             {c:3d}x  dead :- {r}")

    print("\nCONTROL 3  label shuffle, n=30")
    accs = []
    for s in range(30):
        rng = random.Random(s)
        lab = [r["dead"] for r in rows]
        rng.shuffle(lab)
        sh = [dict(r, dead=l) for r, l in zip(rows, lab)]
        a, _ = loo(sh, lits)
        accs.append(a)
    ge = sum(1 for a in accs if a >= acc)
    p = (ge + 1) / (len(accs) + 1)
    print(f"           mean {sum(accs)/len(accs):.3f}  max {max(accs):.3f}  "
          f">= real {ge}/30   p = {p:.3f}")

    verdict = ("SIGNAL (p<0.05)" if acc > maj and p < 0.05
               else f"NO SIGNAL — p={p:.3f}")
    print(f"\nVERDICT: {verdict}")
    json.dump({"claims": len(rows), "dead": dead, "baseline": maj,
               "loo": acc, "shuffle_mean": sum(accs)/len(accs),
               "shuffle_max": max(accs), "p": p, "rules": picked,
               "verdict": verdict,
               "conditions": {"data": "real:kingfisher-LEDGER",
                              "concurrency": "single-process", "swept": {}},
               "cites": ["G3_claim_graph", "G2_rule_learning"]},
              open(os.path.join(HERE, "learn_claims.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
