#!/usr/bin/env python3
"""carriescheck.py v1 — H180. Compute the `Carries:` trailer instead of typing it.

CLASS OF DEFECT REMOVED
-----------------------
*A trailer that records cross-lane attribution is typed by hand, so it is
omitted exactly when it is needed.*

MEASURED BEFORE BUILDING, pinned at HEAD=5d01a317, window = the last 80 commits
touching `CHANNEL.md` that carry an `Atom:` trailer (the window is stated because
`git log -80` MOVES as other lanes commit -- citing a moving count as a fixed
number is its own defect, recorded in DECISIONS.log by AGENT-2):

    carried a foreign lane's line : 44
    declared Carries:             :  9
    MISATTRIBUTED                 : 35   (80% of those needing it)
    committing lanes affected     : AGENT-1, AGENT-2, ATOM-3, ATTACKER-1, ok-1

So this is not a slip by one lane on one day. It is the steady state, and it is
H12's open row -- *commit authorship cannot distinguish agents*.

WHY IT IS OMITTED IS STRUCTURAL
-------------------------------
`git add <path>` commits the WORKING TREE of an append-only shared document, so
there is NO WINDOW in which a co-lane's write does not ride along. H66's notice
in `commit-msg.hook:270` already reports *"recently also committed by"* -- but
that is *who touched this file lately*, not *whose lines are in THIS commit*, it
prints no paste-ready trailer, and it is read only after the commit already
succeeded. Four lanes have now written a `CORRECTED ...-commit` line whose whole
content is "I read that notice too late".

**THE POINT OF THIS MODULE IS THAT IT RUNS ON THE STAGED INDEX, BEFORE THE
COMMIT EXISTS.** Run it, paste the line it prints, then commit.

WHERE IT IS ALLOWED TO LOOK, AND WHERE IT REFUSES TO
----------------------------------------------------
Authorship is POSITIONAL in exactly two files:
    CHANNEL.md     <VERB> <id> <CALLSIGN> ...   /   <VERB> <CALLSIGN> ...
    DECISIONS.log  <date> <CALLSIGN> ...
It is NOT positional in `WORK_QUEUE.md`, and this module REFUSES to look there.
That is not caution, it is ATOM-3's measurement in H105: of 187 queue rows only
48 were scoreable (26%) and **4 of those 48 named the WRONG lane -- an 8% false
accusation rate.** A queue row's callsigns are PARTICIPANTS, not authors
("not taken by ATTACKER-1", "ok-1's module"). Silence beats misnaming.

IDENTITY CLASSES -- two pairs are NOT distinct parties
------------------------------------------------------
Naming one as "carried" by the other is a false accusation. Neither is my
inference; both are on the record:
  * `MISSION_LOOP.md` §14.1, verbatim: *"`CLIENT-3` is the same identity as
    `ATOM-3`"*. CLIENT-3 authored 8 CHANNEL lines under that name.
  * `CHANNEL.md:708`, AGENT-2-INT's own words: *"(was signing AGENT-2 ...)
    CALLSIGN CONCEDED to the loop lane ... Signing AGENT-2-INT from here."* So a
    line signed AGENT-2 before that concession may be AGENT-2-INT's own, and the
    boundary is A POSITION IN AN APPEND-ONLY FILE, not a commit or a timestamp,
    so it is NOT mechanically resolvable. Merged into one class, which
    UNDER-reports carries and never accuses across the concession.

REPORT-ONLY, AND THE REASON IS A FALSIFIER I HONOURED RATHER THAN REWROTE
-------------------------------------------------------------------------
H180's F1, preregistered in CHANNEL before this file existed: *"if the positional
detector produces ANY false positive, it is NOT safe as a REFUSAL and I ship it
REPORT-ONLY."* **It fired** -- v0 named AGENT-2 as carried by AGENT-2-INT, which
is the concession case above. I fixed that class, and I am still shipping
report-only, because rewriting a falsifier after seeing the data is the failure
this repo exists to prevent. A gate that falsely accuses a peer is worse than no
gate (H105), and H124 measured what a bad gate in front of five lanes costs.
It earns REFUSAL after a clean audited run across a wider window, not before.

Exit 0 = nothing carried, or carried and printed. Exit 3 = refused (not a repo).
"""
from __future__ import annotations

import re
import subprocess
import sys

CALLSIGNS = [
    "AGENT-1", "AGENT-2-INT", "AGENT-2", "ATTACKER-1", "ATOM-3", "CLIENT-3",
    "RACE-2", "GROK-LOCAL", "GROK-2", "GEMINI-1", "GEMINI", "ok-1",
]
_CS = "(?:" + "|".join(re.escape(c) for c in CALLSIGNS) + ")"
_VERBS = r"(?:CLAIM|DONE|NOTE|ACCEPT|FILED|CORRECTED|CORRECTION|FINDING|ATTACK|REJECT)"

ALIAS = {"CLIENT-3": "ATOM-3", "AGENT-2-INT": "AGENT-2"}

CHANNEL_PATTERNS = [
    re.compile(r"^" + _VERBS + r"\s+\S+\s+(" + _CS + r")(?![\w-])"),
    re.compile(r"^" + _VERBS + r"\s+(" + _CS + r")(?![\w-])"),
]
DECISIONS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\s+(" + _CS + r")(?![\w-])")

POSITIONAL = {"CHANNEL.md": CHANNEL_PATTERNS, "DECISIONS.log": [DECISIONS_PATTERN]}


def canon(cs: str) -> str:
    return ALIAS.get(cs, cs)


def authors_of(path: str, added_lines) -> set:
    """Callsigns positionally identifiable as the AUTHOR of an added line.

    Conservative: a non-matching line contributes nothing. Under-reporting is a
    missed carry; over-reporting is a false accusation, which H105 shows is worse.
    """
    pats = POSITIONAL.get(path)
    if not pats:
        return set()
    out = set()
    for ln in added_lines:
        for p in pats:
            m = p.match(ln)
            if m:
                out.add(canon(m.group(1)))
                break
    return out


def _sh(args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def added_staged(path: str):
    d = _sh(["git", "diff", "--cached", "--unified=0", "--", path])
    return [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]


def added_rev(rev: str, path: str):
    d = _sh(["git", "show", "--format=", "--unified=0", rev, "--", path])
    return [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]


def carried(atom: str, rev: str = None) -> dict:
    """Foreign lanes whose lines this commit (or the staged index) carries."""
    out = {}
    for path in POSITIONAL:
        lines = added_rev(rev, path) if rev else added_staged(path)
        foreign = authors_of(path, lines) - {canon(atom)}
        if foreign:
            out[path] = sorted(foreign)
    return out


def trailer_for(carried_map: dict) -> str:
    lanes = sorted({l for v in carried_map.values() for l in v})
    return ("Carries: " + " ".join(lanes)) if lanes else ""


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    atom = args[0] if args else _sh(["git", "config", "user.callsign"]).strip()
    if not atom:
        import os
        atom = os.environ.get("CALLSIGN", "")
    if not atom:
        sys.stderr.write("carriescheck: REFUSING — no atom given and CALLSIGN unset.\n"
                         "  usage: python3 spikes/harness/carriescheck.py <YOUR-CALLSIGN> [rev]\n")
        return 3
    rev = args[1] if len(args) > 1 else None

    cm = carried(atom, rev)
    where = rev[:8] if rev else "the STAGED index"
    if not cm:
        print(f"carriescheck: {where} carries no other lane's lines under Atom: {atom}")
        return 0

    print(f"carriescheck — {where} carries ANOTHER LANE'S LINES under Atom: {atom}\n")
    for path, lanes in sorted(cm.items()):
        print(f"  {path}: {' '.join(lanes)}")
        lines = added_rev(rev, path) if rev else added_staged(path)
        for ln in lines:
            a = authors_of(path, [ln])
            if a and not a <= {canon(atom)}:
                print(f"      {ln[:100]}")
    print(f"\nPaste this into your commit message (§13):\n\n    {trailer_for(cm)}\n")
    print("Their content is unmodified and nothing is at risk — this is attribution only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
