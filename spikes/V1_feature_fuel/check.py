#!/usr/bin/env python3
"""Does the `das` Cargo feature change fuel_used for programs that never use it?

Agent-1 found that a Cargo FEATURE changes `fuel_used` -- same source, same
commit, same machine:

    features = ["pkg_mgmt"]           fuel 107   hash 49ba5618
    features = ["pkg_mgmt","das"]     fuel 580   hash 2a2b9159

and concluded the equivalence class must include the feature set, because fuel
is both the unit of payment and part of the quorum agreement key.

WHY THIS MATTERS TO MY OWN RESULTS. I reported that G1/G5/G8/G11 reproduce
identical hash AND fuel across a stale and a patched `fuelrun` build, and
attributed the agreement to every fold being over 62-600 atoms. That
attribution was made without knowing the feature set was ALSO varying:

    fuelrun.v2.host      2026-08-16 16:16   default-features = false,
                                            features = ["pkg_mgmt"]
    known/fuelrun.host   2026-08-17 09:18   features = ["pkg_mgmt", "das"]

(commit 545deb3, "matched cargo features"). So the comparison spanned a
feature-set change and I recorded only the binary digest. Agent-1's phrasing is
exact: a digest pins WHICH artifact, a manifest hash pins the feature set behind
it. I had the first and not the second.

Rather than argue from the source about whether that could matter, run both
binaries on the same programs.

WHAT A NULL RESULT HERE WOULD AND WOULD NOT MEAN. Identical fuel does not show
the feature is irrelevant in general -- agent-1 has a counter-example. It shows
the feature does not perturb fuel for programs that never exercise it, which
NARROWS the equivalence class rather than removing the axis.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
OLD = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")
NEW = os.path.join(SPIKES, "S30_speed_duel", "bin", "known", "fuelrun.host")

PROGRAMS = [
    ("G1_graph_ingest/q2_selfmod.metta", "self-modifying graph, small"),
    ("G1_graph_ingest/q1_atrisk.metta", "derived-atom reasoning"),
    ("G5_ecan_metta/ecan.metta", "ECAN fixed point, ~2.9M fuel"),
]
FUEL = 400_000_000


def run(binary, prog):
    r = subprocess.run([binary, prog, str(FUEL)], capture_output=True,
                       text=True)
    out = r.stdout + r.stderr
    g = lambda p: (re.search(p, out, re.M).group(1)
                   if re.search(p, out, re.M) else None)
    return {"status": g(r"^status\s+(\S+)"), "fuel": g(r"^fuel_used\s+(\d+)"),
            "hash": g(r"^raw_hash\s+(\S+)")}


def main():
    for b in (OLD, NEW):
        if not os.path.exists(b):
            print(f"MISSING {b} — cannot run, reporting nothing")
            return 2
    print(f"old  {OLD}\n     features = [\"pkg_mgmt\"]        (pre-545deb3)")
    print(f"new  {NEW}\n     features = [\"pkg_mgmt\",\"das\"]  (545deb3)\n")

    rows, agree = [], 0
    for prog, desc in PROGRAMS:
        p = os.path.join(SPIKES, prog)
        if not os.path.exists(p):
            print(f"  SKIP {prog} — not present")
            continue
        a, b = run(OLD, p), run(NEW, p)
        same = a == b
        agree += same
        rows.append((prog, a, b, same))
        print(f"  {prog}\n    {desc}")
        print(f"      pkg_mgmt      status {a['status']}  fuel {a['fuel']}  "
              f"hash {(a['hash'] or '')[:16]}")
        print(f"      pkg_mgmt+das  status {b['status']}  fuel {b['fuel']}  "
              f"hash {(b['hash'] or '')[:16]}")
        print(f"      -> {'IDENTICAL' if same else 'DIFFERS'}\n")

    print(f"{agree}/{len(rows)} programs identical across the feature change.")
    if agree == len(rows) and rows:
        print(
            "\nThe `das` feature does not perturb fuel for programs that never\n"
            "exercise it, at fuel from 3.7e3 to 2.9e6. Agent-1's counter-example\n"
            "(107 vs 580) stands and is not contradicted: it NARROWS the axis\n"
            "rather than removing it. The feature set still belongs in the\n"
            "equivalence class, because a program that DOES touch the feature\n"
            "diverges and nothing here can tell in advance which programs those\n"
            "are.\n\n"
            "What this does NOT show: that the two binaries are otherwise\n"
            "equivalent. They also differ by the trie precedence patch. This\n"
            "run holds neither variable fixed, so it establishes the JOINT\n"
            "agreement of both changes, not the effect of either alone."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
