#!/usr/bin/env python3
"""G1 — turn this workspace into a fact graph, so a self-modifying graph has
something with GROUND TRUTH to learn on.

Why this corpus and not a bigger one: 59 spikes carry 88 human-assigned
verdicts (GREEN/RED/AMBER/YELLOW/INVALID) and RETRACTIONS.md records 35
failures WITH stated causes. Almost no knowledge graph has supervision in it.
This one does, and it was labelled by adversaries rather than by the author.

Emits atoms in MeTTa s-expression form (for hyperon/MORK) and a JSON mirror
(for the learner). Nothing here is a model — this is the substrate.

Load-insensitive: reads files, counts things, emits text. Runs through a
refused host gate.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPIKES = os.path.join(ROOT, "spikes")

VERDICTS = ("GREEN", "RED", "AMBER", "YELLOW", "INVALID")

# Text markers for properties an adversary would care about. Each is a claim
# the spike makes ABOUT ITSELF, which is why they are usable as features:
# they are written by the author before the outcome is known to a reviewer.
MARKERS = {
    "self_correction": r"my (own )?(prediction|claim|number|figure|result)s? (was|were|is|are) wrong"
                       r"|I was wrong|wrong by|corrects? my own|my own \w+ was",
    "attacks_own":     r"attack(ing|ed)? my own|破|I set out to break my own|my own strongest",
    "declares_null":   r"\bnull\b.*fire|control.*fire|fires? .*control",
    "declares_gate":   r"quiet\.sh|gate (open|refused)|device gate",
    "admits_missing":  r"missing measurement|not (yet )?measured|unmeasured|is the missing",
    "n_equals_one":    r"\bn=1\b|one draw|single (run|draw|point)",
    "inherits":        r"inherit|premise|fitted (to|on)|carried forward|stale",
}


def spike_dirs():
    for d in sorted(os.listdir(SPIKES)):
        p = os.path.join(SPIKES, d, "RESULT.md")
        if re.match(r"^[A-Z]+\d+[_-]", d) and os.path.isfile(p):
            yield d, p


def parse(d, path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    sid = re.match(r"^([A-Z]+\d+)", d).group(1)
    head = txt[:1200]

    verdict = None
    m = re.search(r"\*\*Verdict[^*]*?\b(" + "|".join(VERDICTS) + r")\b", head)
    if m:
        verdict = m.group(1)
    else:                                     # some spikes state it in the H1
        for v in VERDICTS:
            if v in head:
                verdict = v
                break

    # citation edges: any other spike id mentioned in the body
    cited = set(re.findall(r"\b([A-Z]\d{1,2}[a-z]?)\b", txt)) - {sid}
    cited = {c for c in cited if not c.startswith(("S25",))}   # S25 Ultra = the phone

    feats = {k: bool(re.search(rx, txt, re.I)) for k, rx in MARKERS.items()}
    return {
        "id": sid, "dir": d, "verdict": verdict, "cites": sorted(cited),
        "words": len(txt.split()), "features": feats,
    }


def metta_atoms(nodes):
    """MeTTa s-expressions. This is the form hyperon/MORK actually ingest."""
    out = []
    ids = {n["id"] for n in nodes}
    for n in nodes:
        out.append(f'(spike {n["id"]})')
        if n["verdict"]:
            out.append(f'(verdict {n["id"]} {n["verdict"]})')
        out.append(f'(words {n["id"]} {n["words"]})')
        for c in n["cites"]:
            if c in ids:                      # only edges to spikes we have
                out.append(f'(cites {n["id"]} {c})')
        for k, v in n["features"].items():
            if v:
                out.append(f'(has {n["id"]} {k})')
    return out


def main():
    nodes = [parse(d, p) for d, p in spike_dirs()]
    ids = {n["id"] for n in nodes}
    atoms = metta_atoms(nodes)

    # resolve edges to the subgraph we actually have
    for n in nodes:
        n["cites_resolved"] = [c for c in n["cites"] if c in ids]

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "graph.metta"), "w") as f:
        f.write("; G1 — kingfisher workspace as a MeTTa fact graph\n")
        f.write("\n".join(atoms) + "\n")
    with open(os.path.join(here, "graph.json"), "w") as f:
        json.dump({"nodes": nodes, "n_atoms": len(atoms),
                   "conditions": {"data": "real:kingfisher-workspace",
                                  "concurrency": "single-process",
                                  "swept": {}},
                   "cites": []}, f, indent=1)

    vc = {}
    for n in nodes:
        vc[n["verdict"]] = vc.get(n["verdict"], 0) + 1
    edges = sum(len(n["cites_resolved"]) for n in nodes)
    print(f"nodes {len(nodes)}  atoms {len(atoms)}  edges {edges}")
    print("verdicts:", dict(sorted(vc.items(), key=lambda x: -x[1])))
    fc = {k: sum(n["features"][k] for n in nodes) for k in MARKERS}
    print("features:", dict(sorted(fc.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
