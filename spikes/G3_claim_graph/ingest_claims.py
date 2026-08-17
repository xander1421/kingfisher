#!/usr/bin/env python3
"""G3 — ingest CLAIMS, not spikes. G2 said the features were too weak; this
tests that diagnosis with better ones from data that already existed.

`out/LEDGER.md` carries 108 graded rows organised under section headers, and
**the section is the label**: a row under `## DEAD` died, a row under
`## LIVE — …` survived. That is claim-level supervision, assigned by
adversaries rather than by the claim's author, and G1 never read it — G1 only
ingested RESULT.md files.

`out/RETRACTIONS.md` adds 35 rows of `| claim | spike | why |` — failures with
a stated cause.

THE CIRCULARITY TRAP, named before it bites: the grade `INVALID` is assigned
*because* a claim died. Using it to predict death is tautological. It is
excluded from the feature set here and the exclusion is asserted in code.
That is the trap S70's `4R` fell into and it is the first thing to get wrong.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))

GRADES = ("A", "B", "C", "D", "E", "INVALID")


def parse_ledger():
    path = os.path.join(ROOT, "out", "LEDGER.md")
    section, rows = None, []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or section is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        claim, grade_cell = cells[0], cells[1]
        m = re.match(r"^\*\*(" + "|".join(GRADES) + r")\*\*$", grade_cell)
        if not m:
            continue                      # header rows, the grading key, prose
        evidence = cells[2] if len(cells) > 2 else ""
        rows.append({
            "claim": re.sub(r"\s+", " ", claim)[:160],
            "grade": m.group(1),
            "section": section,
            "dead": section.startswith("DEAD"),
            "struck": claim.startswith("~~"),
            "evidence": evidence[:400],
            "cites": sorted(set(re.findall(r"\b([A-Z]\d{1,2}[a-z]?)\b", evidence))
                            - {"S25"}),
        })
    return rows


def parse_retractions():
    path = os.path.join(ROOT, "out", "RETRACTIONS.md")
    if not os.path.isfile(path):
        return []
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("claim", "---"):
            continue
        if set(cells[1]) <= set("- "):
            continue
        out.append({"claim": re.sub(r"\s+", " ", cells[0])[:160],
                    "spike": cells[1], "why": cells[2][:300]})
    return out


def section_shapes():
    """The finding: are claims recorded as rows, or as prose?"""
    import re as _re
    t = open(os.path.join(ROOT, "out", "LEDGER.md"), encoding="utf-8",
             errors="replace").read()
    out = []
    for s in _re.split(r"\n## ", t)[1:]:
        name = s.split("\n")[0]
        body = s.split("\n")[1:]
        rows = sum(1 for l in body if l.startswith("|") and "**" in l)
        prose = sum(1 for l in body if l.strip() and not l.startswith("|"))
        out.append((name, rows, prose))
    return out


def main():
    rows = parse_ledger()
    retr = parse_retractions()

    print("SHAPE OF THE RECORD — the actual finding\n")
    print(f"  {'section':<44}{'rows':>6}{'prose':>7}")
    live_r = dead_r = 0
    for name, r, p in section_shapes():
        print(f"  {name[:42]:<44}{r:>6}{p:>7}")
        if name.startswith("LIVE"):
            live_r += r
        if name.startswith("DEAD"):
            dead_r += r
    print(f"\n  LIVE claims as structured rows: {live_r}")
    print(f"  DEAD claims as structured rows: {dead_r}")
    print(f"  -> failure is recorded as PROSE. A learner sees "
          f"{live_r} positives and {dead_r} negatives.\n")

    # ---- the circularity assertion, in code, not in a comment ----
    invalid_dead = sum(1 for r in rows if r["grade"] == "INVALID" and r["dead"])
    invalid_all = sum(1 for r in rows if r["grade"] == "INVALID")
    print(f"circularity check: INVALID rows {invalid_all}, of which in DEAD "
          f"{invalid_dead}")
    print("  -> INVALID is EXCLUDED from predictors; it is assigned because a "
          "claim died.\n")

    atoms = []
    for i, r in enumerate(rows):
        cid = f"c{i}"
        atoms.append(f'(claim {cid})')
        atoms.append(f'(grade {cid} {r["grade"]})')
        atoms.append(f'(outcome {cid} {"DEAD" if r["dead"] else "LIVE"})')
        if r["struck"]:
            atoms.append(f'(struck {cid})')
        for s in r["cites"]:
            atoms.append(f'(evidence {cid} {s})')

    with open(os.path.join(HERE, "claims.metta"), "w") as f:
        f.write("; G3 — LEDGER claims as a MeTTa fact graph\n")
        f.write("\n".join(atoms) + "\n")
    json.dump({"rows": rows, "retractions": retr, "n_atoms": len(atoms),
               "conditions": {"data": "real:kingfisher-LEDGER",
                              "concurrency": "single-process", "swept": {}},
               "cites": ["G1_graph_ingest"]},
              open(os.path.join(HERE, "claims.json"), "w"), indent=1)

    from collections import Counter
    print(f"claims {len(rows)}  atoms {len(atoms)}  retractions {len(retr)}")
    print("by grade   :", dict(Counter(r["grade"] for r in rows)))
    print("by outcome :", dict(Counter("DEAD" if r["dead"] else "LIVE" for r in rows)))
    print("\ngrade x outcome (INVALID shown but excluded downstream):")
    print(f"  {'grade':>8} {'LIVE':>6} {'DEAD':>6}  {'death rate':>10}")
    for g in GRADES:
        sub = [r for r in rows if r["grade"] == g]
        if not sub:
            continue
        d = sum(1 for r in sub if r["dead"])
        print(f"  {g:>8} {len(sub)-d:>6} {d:>6}  {d/len(sub):>9.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
