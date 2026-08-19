#!/usr/bin/env python3
"""H226 — how many published digests open from the artifacts that publish them?

Run: python3 spikes/H226_digest_self_containment/run.py   (a few seconds, reads only)

WHAT THIS DECIDES, AND WHY THE DECISION WAS WRITTEN BEFORE THE RUN
  `spikes/harness/opencheck.py` v1 mechanises G99's class -- A DIGEST PUBLISHED
  WITHOUT THE OBJECT IT PINS (family C) -- which §12.10 has required since the
  class was named three cycles ago. The open question was never whether to build
  the detector; it was whether to wire it into `kfcheck.certify` as a REFUSAL.

  Wiring a refusal on a five-lane tree is a fleet-stop risk (H106: `commit-msg`
  refused every lane for 2m16s), and the recorded failure mode of a gate nobody
  can pass is `allow_dirty=True`, which voids it (H216). So both branches were
  preregistered in `CHANNEL.md` before this file existed:

    F1  blast radius <= 3 spikes  -> wire the refusal into certify this cycle
    F2  blast radius is large     -> do NOT wire; ship report-only + the number,
                                     and move the remedy to the WRITE site

  Predicted at claim time: F1 does not fire, F2 fires. The number is the
  deliverable either way (ok-1's H23 precedent: three detectors at 41/93/0%,
  none shipped, and the rate was the result).

TWO POPULATIONS ARE REPORTED AND NEITHER IS "THE" ANSWER
  BROAD  every published hex64 that is not control evidence and not a file hash.
  NARROW those whose name says they pin an IN-RUN SELECTION STRUCTURE.
  Reporting only BROAD would be alarmism; only NARROW would be flattery. The
  boundary is a judgement and both sides of it are printed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
sys.path.insert(0, os.path.join(SPIKES, "harness"))

import kfcheck                                            # noqa: E402
import opencheck as oc                                    # noqa: E402
from provenance import Control, Falsifier                 # noqa: E402

# Preregistered in CHANNEL.md before this file existed.
F1_MAX_SPIKES = 3


def main() -> int:
    rows = oc.census()
    narrow = [r for r in rows if oc.is_structural(r[1], r[1].rsplit("/", 1)[-1])]

    def split(rs):
        # PER VERDICT, not openable-vs-rest. The first version folded
        # CITED_VERIFIED into "openable" by computing it as len(rs) - shut,
        # which is the exact merge-two-verdicts-into-one-number defect H233
        # filed against this module's headline -- reappearing in the artifact
        # that reports it, one cycle later.
        shut = [r for r in rs if r[3] == "NO_OPENING"]
        tally = {}
        for r in rs:
            tally[r[3]] = tally.get(r[3], 0) + 1
        return {"n": len(rs),
                "by_verdict": tally,
                "openable": tally.get("OPENABLE", 0),
                "no_opening": len(shut),
                "spikes": sorted({os.path.basename(os.path.dirname(r[0]))
                                  for r in shut})}

    broad_s, narrow_s = split(rows), split(narrow)

    # The selfcheck is run as a SUBPROCESS so its verdict is the same artifact a
    # reader gets, not an in-process re-implementation of it.
    sc = subprocess.run([sys.executable,
                         os.path.join(SPIKES, "harness", "opencheck.py"),
                         "--selfcheck"], capture_output=True, text=True)
    sc_ok = sc.returncode == 0
    sc_arms = [l.strip() for l in sc.stdout.splitlines() if l.strip().startswith(("ok", "FAIL"))]

    g101 = [r[3] for r in oc.check_spike(os.path.join(SPIKES, "G101_gate_opening"))]
    g59 = [r[3] for r in oc.check_spike(os.path.join(SPIKES, "G59_official_split"))]

    controls = [
        Control("C1_selfcheck_is_two_sided",
                why="a detector that only ever agrees is one nobody can trust; "
                    "every arm must run and pass in a subprocess",
                can_fail_because="any arm of opencheck --selfcheck fails",
                null_must_contain="the arm list and the exit code"),
        Control("C2_known_positions_hold",
                why="the detector is checked against two spikes whose answer was "
                    "known before it was written",
                can_fail_because="G101 stops opening from its own artifacts, or "
                                 "G59 starts",
                null_must_contain="both verdict lists"),
        Control("C3_narrow_is_a_subset_of_broad",
                why="two lenses that are not nested are two different questions "
                    "wearing one name",
                can_fail_because="a row is narrow but not broad",
                null_must_contain="both counts"),
    ]
    controls[0].observe(sc_ok, {"returncode": sc.returncode, "arms": sc_arms})
    controls[1].observe(bool(g101) and set(g101) == {"OPENABLE"}
                        and "NO_OPENING" in g59,
                        {"G101": g101, "G59": g59})
    controls[2].observe(all(r in rows for r in narrow),
                        {"broad": broad_s["n"], "narrow": narrow_s["n"]})

    f1_fires = len(narrow_s["spikes"]) <= F1_MAX_SPIKES
    falsifiers = [
        Falsifier("F1_blast_radius_is_small_so_wire_the_gate",
                  refutes="that a certify refusal cannot ship this cycle",
                  fires_when=f"<= {F1_MAX_SPIKES} spikes carry an unopenable "
                             f"published digest",
                  null_must_contain="the spike count and the threshold, so a "
                                    "reader can see which side of it the tree "
                                    "landed on"),
        Falsifier("F2_blast_radius_is_large_so_do_not_wire",
                  refutes="that the remedy is a gate",
                  fires_when=f"> {F1_MAX_SPIKES} spikes carry one",
                  null_must_contain="both the narrow and broad spike counts"),
    ]
    falsifiers[0].observe(f1_fires, {"n_spikes_narrow": len(narrow_s["spikes"]),
                                     "threshold": F1_MAX_SPIKES})
    falsifiers[1].observe(not f1_fires, {"n_spikes_narrow": len(narrow_s["spikes"]),
                                         "n_spikes_broad": len(broad_s["spikes"])})

    # THE REFUSAL IS PART OF THE RECORD, SO WHAT CAUSED IT IS TOO. certify
    # refuses on a dirty `spikes/harness`, and on a five-lane tree that dep is
    # almost never quiet. Listing the dirty paths lets a reader check the one
    # thing that matters -- whether any of them is mine -- instead of taking
    # "co-lane dirt" on trust. `deps` must be a DIRECTORY (provenance.py:256),
    # so narrowing this to the single module actually imported is not available.
    dirt = subprocess.run(["git", "status", "--porcelain", "spikes/harness"],
                          capture_output=True, text=True, cwd=ROOT).stdout
    dirt = [d for d in dirt.split("\n") if d.strip()]

    res = {"spike": "H226",
           "dep_dirt_at_run_time": dirt,
           "rule": "a digest you publish must open from the artifacts you publish",
           "broad": broad_s, "narrow": narrow_s,
           "selfcheck": {"returncode": sc.returncode, "arms": sc_arms},
           "known_positions": {"G101": g101, "G59": g59},
           "gate_wired_into_certify": bool(f1_fires),
           "narrow_rows": [[os.path.relpath(p, ROOT), dp, dg, v, rs]
                           for p, dp, dg, v, rs in narrow]}
    json.dump(res, open(os.path.join(HERE, "census.json"), "w"),
              indent=1, sort_keys=True)

    print(f"NARROW  {narrow_s['openable']} openable / {narrow_s['no_opening']} "
          f"no_opening in {len(narrow_s['spikes'])} spikes")
    print(f"BROAD   {broad_s['openable']} openable / {broad_s['no_opening']} "
          f"no_opening in {len(broad_s['spikes'])} spikes")
    print(f"F1 {'FIRED' if f1_fires else 'did not fire'} -> gate "
          f"{'IS' if f1_fires else 'is NOT'} wired into certify")

    ok, problems = kfcheck.certify(
        HERE,
        deps=["spikes/harness"],
        # THE MODULE IS THE INSTRUMENT, NOT THE ARTIFACT, and listing it as
        # one was wrong: `opencheck.py` then has to be NEWER than every file
        # under its own dep directory, so a co-lane edit to an unrelated
        # harness module (`constcheck.py`, 0.1h) made this run read STALE.
        # A staleness floor is for "could this artifact have been built from
        # this tree"; the tool is covered by `deps`, which is where it belongs.
        artifacts=[os.path.join(HERE, "census.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the detector reports a clean tree, OR it flags a digest that "
                  "does open, OR the blast radius is small enough that a certify "
                  "refusal ships without a fleet-stop risk",
        note="H226: opencheck v1 -- self-containment census over every spike.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
