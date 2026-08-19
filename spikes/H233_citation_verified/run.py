#!/usr/bin/env python3
"""H233 — split `NO_OPENING` into "nowhere" and "somewhere else, unsaid".

Run: python3 spikes/H233_citation_verified/run.py   (seconds, reads only)

WHAT WAS WRONG WITH THE NUMBER I PUBLISHED ONE CYCLE AGO
  `opencheck` v2 reported 22 NO_OPENING. G100 v2, written days earlier for a
  different question, independently calls 11 of those `OPENS_ELSEWHERE`: the
  object exists in a sibling spike and the citing site simply does not say
  where. **One verdict was carrying a real defect and a bookkeeping gap, and a
  number that merges those will be quoted as the defect.** It is the same
  collapse that made G100's own "one gate, eight citers, ONE PUBLISHER" wrong --
  a sentence that could not tell a CITATION from a PUBLICATION -- arriving one
  level up, in the detector written to catch it.

WHAT THIS MEASURES
  The split, using G100's verdicts as the INDEPENDENT source rather than a
  second pass of my own detector. A site this run calls NO_OPENING and G100
  calls OPENS_ELSEWHERE needs one `opens_at` line from its owner; a site both
  call NO_OPENING needs its producing spike re-run. Those are different asks
  addressed to different people and the row exists to tell them apart.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
sys.path.insert(0, os.path.join(SPIKES, "harness"))

import kfcheck                                            # noqa: E402
import opencheck as oc                                    # noqa: E402
from provenance import Control, Falsifier                 # noqa: E402

AUDIT = os.path.join(SPIKES, "G100_digest_openings", "AUDIT.txt")
F1_MIN_ELSEWHERE = 3


def g100_verdicts():
    out = {}
    pat = re.compile(r"\s+(NO_OPENING|OPENS_ELSEWHERE|OPENABLE_VERIFIED|"
                     r"OPENABLE_STRUCTURE_PRESENT)\s+(\S+)\s+([0-9a-f]{12})")
    for line in open(AUDIT):
        m = pat.match(line)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def main() -> int:
    rows = [r for r in oc.census()
            if oc.is_structural(r[1], r[1].rsplit("/", 1)[-1])]
    key = lambda r: os.path.relpath(r[0], ROOT) + r[1]
    verd = g100_verdicts()
    shut = [r for r in rows if r[3] == "NO_OPENING"]
    cited = [r for r in rows if r[3] == "CITED_VERIFIED"]
    broken = [r for r in rows if r[3] == "CITATION_BROKEN"]
    elsewhere = [r for r in shut if verd.get(key(r)) == "OPENS_ELSEWHERE"]
    nowhere = [r for r in shut if verd.get(key(r)) != "OPENS_ELSEWHERE"]

    sc = subprocess.run([sys.executable,
                         os.path.join(SPIKES, "harness", "opencheck.py"),
                         "--selfcheck"], capture_output=True, text=True)
    arms = [l.strip() for l in sc.stdout.splitlines()
            if l.strip().startswith(("ok", "FAIL"))]

    controls = [
        Control("C1_selfcheck_covers_both_sides_of_the_declaration",
                why="a pointer a checker cannot refuse is a field that turns a "
                    "red row green by being typed",
                can_fail_because="any of the 13 arms fails, including the four "
                                 "constructed ways a pointer can lie",
                null_must_contain="the arm list and the exit code"),
        Control("C2_the_two_repaired_sites_verify",
                why="the repair must be checked by the same instrument that "
                    "reported the defect, on the live artifacts",
                can_fail_because="G95 or G96 stops resolving to G88's object",
                null_must_contain="the verdict for each"),
        Control("C3_split_is_exhaustive",
                why="every NO_OPENING must land in exactly one bucket or the "
                    "split is hiding a third case",
                can_fail_because="elsewhere + nowhere != the NO_OPENING count",
                null_must_contain="all three counts"),
    ]
    controls[0].observe(sc.returncode == 0,
                        {"returncode": sc.returncode, "arms": arms})
    controls[1].observe(len(cited) == 2 and not broken,
                        {"cited": [key(r) for r in cited],
                         "broken": [key(r) for r in broken]})
    controls[2].observe(len(elsewhere) + len(nowhere) == len(shut),
                        {"elsewhere": len(elsewhere), "nowhere": len(nowhere),
                         "no_opening": len(shut)})

    falsifiers = [
        Falsifier("F1_the_collapse_is_not_real",
                  refutes="that NO_OPENING was carrying two different things",
                  fires_when=f"fewer than {F1_MIN_ELSEWHERE} sites resolve to an "
                             f"object published elsewhere",
                  null_must_contain="the elsewhere count and the threshold"),
        Falsifier("F4_the_count_did_not_move",
                  refutes="that the vocabulary change bought anything measurable",
                  fires_when="NO_OPENING is still 22 after v3 and the two re-runs",
                  null_must_contain="the before and after counts"),
    ]
    n_elsewhere_total = len(elsewhere) + len(cited)
    falsifiers[0].observe(n_elsewhere_total < F1_MIN_ELSEWHERE,
                          {"elsewhere_now": len(elsewhere),
                           "repaired_by_this_row": len(cited),
                           "elsewhere_before_repair": n_elsewhere_total,
                           "threshold": F1_MIN_ELSEWHERE})
    falsifiers[1].observe(len(shut) == 22, {"before": 22, "after": len(shut)})

    res = {"spike": "H233",
           "no_opening": len(shut),
           "no_opening_before": 22,
           "cited_verified": [key(r) for r in cited],
           "citation_broken": [key(r) for r in broken],
           "needs_a_pointer_from_its_owner": sorted(key(r) for r in elsewhere),
           "needs_its_spike_re_run": sorted(key(r) for r in nowhere),
           "selfcheck": {"returncode": sc.returncode, "arms": arms}}
    json.dump(res, open(os.path.join(HERE, "split.json"), "w"),
              indent=1, sort_keys=True)

    print(f"CITED_VERIFIED  {len(cited)}   CITATION_BROKEN {len(broken)}")
    print(f"NO_OPENING      {len(shut)}  = {len(elsewhere)} need a pointer "
          f"+ {len(nowhere)} need a re-run")
    print(f"F1 {'FIRED' if n_elsewhere_total < F1_MIN_ELSEWHERE else 'did not fire'}"
          f"   F4 {'FIRED' if len(shut) == 22 else 'did not fire'}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=["spikes/harness"],
        # THE MODULE IS THE INSTRUMENT, NOT THE ARTIFACT, and listing it as
        # one was wrong: `opencheck.py` then has to be NEWER than every file
        # under its own dep directory, so a co-lane edit to an unrelated
        # harness module (`constcheck.py`, 0.1h) made this run read STALE.
        # A staleness floor is for "could this artifact have been built from
        # this tree"; the tool is covered by `deps`, which is where it belongs.
        artifacts=[os.path.join(HERE, "split.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="every NO_OPENING turns out to be a genuine missing object, OR "
                  "the declaration cannot be refused by the checker, OR the two "
                  "re-runs move a published digest",
        note="H233: opencheck v3 -- CITED_VERIFIED / CITATION_BROKEN, and the "
             "split of NO_OPENING into nowhere vs elsewhere-and-unsaid.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
