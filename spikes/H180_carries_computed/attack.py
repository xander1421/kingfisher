#!/usr/bin/env python3
"""H180 — 44 of 80 CHANNEL commits carried a foreign lane's line; 9 declared it.

§12.8 cycle: targets the loop, not a spike.

CLASS: a trailer that records cross-lane attribution is TYPED BY HAND, so it is
omitted exactly when it is needed.

This file measures; `spikes/harness/carriescheck.py` is the shipped tool and the
ONLY implementation. It is imported, never copied -- a second copy of the
detector would be MISSION_LOOP 12.2's own defect class inside the row about it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
HARNESS = os.path.join(SPIKES, "harness")
sys.path.insert(0, HARNESS)

import kfcheck                                    # noqa: E402
from provenance import Control, Falsifier         # noqa: E402
import carriescheck as cc                         # noqa: E402  -- the shipped tool

# The window is PINNED. `git log -80` MOVES as other lanes commit, so a bare
# count is stale by construction -- AGENT-2 recorded that exact defect in
# DECISIONS.log ("cite the artifact, not its size").
PIN_HEAD = "5d01a31707c2771b103ba67f22259fede1a72ce7"
WINDOW = 80

# Hand-verified case, checked by reading the commit before the tool existed:
# 2892b41 has `Atom: ok-1`, no `Carries:`, and two ATOM-3 lines.
HAND_VERIFIED = ("2892b41", "ok-1", ["ATOM-3"])


def sh(a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def survey(head, n):
    revs = sh(["git", "log", "--format=%H", f"-{n}", head, "--", "CHANNEL.md"]).split()
    need = have = miss = 0
    lanes = set()
    rows = []
    for r in revs:
        body = sh(["git", "log", "-1", "--format=%B", r])
        m = re.search(r"^Atom:\s*(\S+)", body, re.M)
        if not m:
            continue
        atom = m.group(1)
        cm = cc.carried(atom, r)
        if not cm:
            continue
        need += 1
        if re.search(r"^Carries:\s*(.+)$", body, re.M):
            have += 1
        else:
            miss += 1
            lanes.add(cc.canon(atom))
            rows.append({"rev": r[:8], "atom": atom, "trailer": cc.trailer_for(cm)})
    return need, have, miss, sorted(lanes), rows


def main() -> int:
    t0 = time.perf_counter()
    print("=== H180: the Carries: trailer is typed by hand, so it is omitted ===\n")

    head_exists = sh(["git", "cat-file", "-t", PIN_HEAD]).strip() == "commit"
    print(f"C1 pinned window -- HEAD {PIN_HEAD[:8]} resolves: {head_exists}")
    if not head_exists:
        print("  REFUSING: the pinned window is gone; the number would not be the one published.")
        return 2

    need, have, miss, lanes, rows = survey(PIN_HEAD, WINDOW)
    print(f"\nlast {WINDOW} commits touching CHANNEL.md with an Atom trailer, at {PIN_HEAD[:8]}:")
    print(f"  carried a foreign lane's line : {need}")
    print(f"  declared Carries:             : {have}")
    print(f"  MISATTRIBUTED                 : {miss}  ({100.0*miss/need:.0f}% of those needing it)")
    print(f"  committing lanes affected     : {', '.join(lanes)}")

    # C2 -- the tool must reproduce the case verified by hand BEFORE it existed.
    rev, atom, expect = HAND_VERIFIED
    got = sorted({l for v in cc.carried(atom, rev).values() for l in v})
    c2_ok = got == expect
    print(f"\nC2 hand-verified {rev} (Atom: {atom}) -> {got}, expected {expect}: {c2_ok}")

    # C3 -- WORK_QUEUE.md must be invisible to the detector (H105: 8% wrong).
    c3_ok = "WORK_QUEUE.md" not in cc.POSITIONAL
    print(f"C3 WORK_QUEUE.md excluded from authorship detection: {c3_ok}")

    # F1 -- THE FALSIFIER THAT DECIDED WHAT SHIPPED. It fired on v0.
    # Both identity classes must be silent, or the tool falsely accuses a peer.
    fp_client3 = cc.authors_of("CHANNEL.md", ["DONE H2 CLIENT-3 x"]) - {"ATOM-3"}
    fp_agent2 = cc.authors_of("CHANNEL.md", ["NOTE AGENT-2 x"]) - {"AGENT-2"}
    fp_prose = cc.authors_of("CHANNEL.md", ["DONE H4 ATTACKER-1 and ATOM-3 should read this"]) - {"ATTACKER-1"}
    f1 = bool(fp_client3 or fp_agent2 or fp_prose)

    # F2 -- is Carries: already computed anywhere in the hook chain?
    hook = Path(HARNESS, "commit-msg.hook").read_text(encoding="utf-8")
    already = bool(re.search(r"Carries:.*\$\(|compute.*Carries", hook))
    f2 = already

    # F3 -- POSITIVE CONTROL: own-lines-only must be silent, or the tool is noise.
    own_only = cc.authors_of("CHANNEL.md", ["DONE H3 ATTACKER-1 my own line"]) - {"ATTACKER-1"}
    foreign_seen = cc.authors_of("CHANNEL.md", ["CLAIM H1 ATOM-3 theirs"]) - {"ATTACKER-1"}
    f3 = bool(own_only) or not foreign_seen

    print(f"\nF1 detector produces a false positive (fired on v0, class fixed): {f1}")
    print(f"F2 Carries: already computed in commit-msg.hook: {f2}")
    print(f"F3 my detector is inert (own-only noisy, or foreign missed): {f3}")

    controls = [
        Control("C1_window_pinned",
                why="the published count is over a FIXED window; `git log -80` moves as other lanes commit",
                can_fail_because="the pinned HEAD could be gone from this clone",
                null_must_contain="pinned window missing"),
        Control("C2_reproduces_hand_verified",
                why="the tool must reproduce 2892b41, which I checked by reading the commit BEFORE the tool existed",
                can_fail_because="my positional detector is wrong, which would make this row the error it reports",
                null_must_contain="hand-verified case mismatch"),
        Control("C3_workqueue_excluded",
                why="H105 measured 8% of queue-row callsigns naming the WRONG lane; a false accusation is worse than silence",
                can_fail_because="a later edit could add WORK_QUEUE.md to POSITIONAL",
                null_must_contain="WORK_QUEUE scanned"),
    ]
    controls[0].observe(head_exists, {"head": PIN_HEAD, "window": WINDOW})
    controls[1].observe(c2_ok, {"rev": rev, "expected": expect, "got": got})
    controls[2].observe(c3_ok, {"positional_files": sorted(cc.POSITIONAL)})

    falsifiers = [
        Falsifier("F1_detector_false_positives",
                  refutes="that the positional detector is safe to REFUSE on",
                  fires_when="either identity class, or a mid-line mention, is read as authorship",
                  null_must_contain="false positive"),
        Falsifier("F2_already_computed",
                  refutes="my claim that the trailer is typed rather than computed",
                  fires_when="commit-msg.hook already computes Carries:",
                  null_must_contain="already computed"),
        Falsifier("F3_detector_inert",
                  refutes="that a silent run means anything",
                  fires_when="own-lines-only is noisy OR a foreign line is missed",
                  null_must_contain="detector inert"),
    ]
    falsifiers[0].observe(f1, {"client3": sorted(fp_client3), "agent2": sorted(fp_agent2),
                               "prose": sorted(fp_prose),
                               "note": "F1 FIRED on v0 (AGENT-2 named as carried by AGENT-2-INT). "
                                       "Class fixed; shipping REPORT-ONLY anyway, because rewriting a "
                                       "falsifier after seeing the data is the failure this repo prevents."})
    falsifiers[1].observe(f2, {"searched": "commit-msg.hook"})
    falsifiers[2].observe(f3, {"own_only_extra": sorted(own_only), "foreign_seen": sorted(foreign_seen)})

    res = {
        "spike": "H180",
        "targets": "the loop (MISSION_LOOP 12.8), not a spike",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.perf_counter() - t0, 3),
        "pinned_head": PIN_HEAD,
        "window_commits": WINDOW,
        "survey": {"carried_foreign_line": need, "declared_carries": have,
                   "misattributed": miss,
                   "misattributed_pct_of_needed": round(100.0 * miss / need, 1),
                   "committing_lanes_affected": lanes},
        "misattributed_commits": rows,
        "identity_classes": {
            "CLIENT-3": "ATOM-3 (MISSION_LOOP 14.1, verbatim)",
            "AGENT-2-INT": "AGENT-2 (CHANNEL.md:708, its own concession; boundary is a file "
                           "position, not a commit, so NOT mechanically resolvable)",
        },
        "excluded_from_detection": {
            "WORK_QUEUE.md": "H105 measured 48/187 rows scoreable and 4/48 naming the WRONG "
                             "lane (8% false accusation); callsigns there are PARTICIPANTS, not authors",
        },
        "shipped_as": "REPORT-ONLY, not a refusal — F1 fired on v0 and the preregistered "
                      "consequence was honoured rather than rewritten",
        "controls": {"C1_window_pinned": {"ok": head_exists},
                     "C2_reproduces_hand_verified": {"ok": c2_ok},
                     "C3_workqueue_excluded": {"ok": c3_ok}},
        "falsifiers": {"F1_detector_false_positives": {"fired": f1},
                       "F2_already_computed": {"fired": f2},
                       "F3_detector_inert": {"fired": f3}},
    }
    out = Path(HERE) / "result.json"
    out.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE), deps=[HARNESS], artifacts=[str(out)],
        controls=controls, falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="the Carries: trailer is already computed, or the positional detector "
                  "cannot name a carried lane without false positives",
        allow_dirty=True,
        note="H180: compute the Carries: trailer instead of typing it.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
