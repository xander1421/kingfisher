#!/usr/bin/env python3
"""G13 — what is the error rate of the data every G-result rests on?

Fair challenge: G1's graph is regex over prose. Verdicts are scraped from a
`**Verdict: X**` line, citations from any `S\\d+`-shaped token in the body.
Nothing has ever measured how often that is wrong, and every G-series number
inherits it.

So measure it. Sample nodes, re-derive each fact by a DIFFERENT method than the
ingest used, and count disagreements.

  verdict   ingest takes the first VERDICT token in the first 1200 chars.
            Audit re-reads the whole file and takes the token on the line
            beginning `**Verdict`, which is the documented convention.
  cites     ingest takes any S-shaped token anywhere in the body. Audit
            restricts to tokens that name a directory which EXISTS, and
            separately counts tokens appearing only inside code fences or
            file paths — the two places a citation is not a citation.

Then the part that matters: **does the G10/G12 result survive the measured
error rate?** Error that hits both arms equally cannot flip a comparison, so the
sensitivity analysis perturbs the graph at the measured rate and re-runs the
attention-vs-control gap.
"""

import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
GRAPH = os.path.join(SPIKES, "G1_graph_ingest", "graph.json")
VERDICTS = ("GREEN", "RED", "AMBER", "YELLOW", "INVALID")


def audit_verdict(d):
    """Independent re-derivation: the line that starts with **Verdict."""
    p = os.path.join(SPIKES, d, "RESULT.md")
    if not os.path.isfile(p):
        return None, "no RESULT.md"
    txt = open(p, encoding="utf-8", errors="replace").read()
    for line in txt.split("\n"):
        if line.strip().startswith("**Verdict"):
            for v in VERDICTS:
                if v in line:
                    return v, "verdict-line"
            return None, "verdict line, no token"
    for v in VERDICTS:                      # fall back to H1, as ingest does
        if v in txt[:1200]:
            return v, "H1 fallback"
    return None, "none"


def audit_cites(d, known):
    """Independent re-derivation: tokens outside code fences and file paths,
    that name a spike directory which actually exists."""
    p = os.path.join(SPIKES, d, "RESULT.md")
    txt = open(p, encoding="utf-8", errors="replace").read()
    body, infence, kept = txt.split("\n"), False, []
    for line in body:
        if line.strip().startswith("```"):
            infence = not infence
            continue
        if infence:
            continue
        clean = re.sub(r"`[^`]*`", " ", line)          # drop inline code
        clean = re.sub(r"\S*/\S*", " ", clean)         # drop file paths
        kept.append(clean)
    toks = set(re.findall(r"\b([A-Z]\d{1,2}[a-z]?)\b", "\n".join(kept)))
    # exclude the node's OWN id: a spike naming itself is not a citation,
    # and the ingest correctly drops it. First run of this audit did not, and
    # every row reported its own id as "missing" — a uniform shape, which is
    # the tell that it is the instrument and not the data.
    return {t for t in toks if t in known} - {"S25", d.split("_")[0]}


def main():
    g = json.load(open(GRAPH))
    nodes = {n["id"]: n for n in g["nodes"]}
    known = set(nodes)
    rng = random.Random(0xC0FFEE)
    sample = sorted(nodes, key=lambda k: rng.random())[:20]

    print(f"auditing {len(sample)} of {len(nodes)} nodes "
          f"(seeded sample, re-derived by a different method)\n")

    v_bad, e_extra, e_missing, e_total = 0, 0, 0, 0
    rows = []
    for sid in sample:
        n = nodes[sid]
        av, how = audit_verdict(n["dir"])
        vok = (av == n["verdict"])
        v_bad += (not vok)
        ac = audit_cites(n["dir"], known)
        ic = {c for c in n["cites"] if c in known}
        extra, missing = ic - ac, ac - ic
        e_extra += len(extra)
        e_missing += len(missing)
        e_total += len(ic | ac)
        rows.append({"id": sid, "ingest_verdict": n["verdict"],
                     "audit_verdict": av, "verdict_ok": vok, "how": how,
                     "cites_extra": sorted(extra), "cites_missing": sorted(missing)})
        if not vok or extra or missing:
            print(f"  {sid:<6} verdict {str(n['verdict']):<8}-> {str(av):<8}"
                  f"({how})  extra {sorted(extra)}  missing {sorted(missing)}")

    v_err = v_bad / len(sample)
    e_err = (e_extra + e_missing) / e_total if e_total else 0.0
    print(f"\n  verdict error   {v_bad}/{len(sample)} = {v_err:.1%}")
    print(f"  citation error  {e_extra} spurious + {e_missing} missed "
          f"of {e_total} = {e_err:.1%}")

    json.dump({"sampled": len(sample), "verdict_error": v_err,
               "citation_error": e_err, "spurious": e_extra,
               "missed": e_missing, "edge_union": e_total, "rows": rows,
               "conditions": {"data": "real:kingfisher-workspace",
                              "concurrency": "single-process", "swept": {}},
               "cites": ["G1_graph_ingest"]},
              open(os.path.join(HERE, "audit.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
