#!/usr/bin/env python3
"""H205 — how often does a commit here carry another lane's CHANNEL line?

Run: python3 spikes/H205_undeclared_carry/carry_census.py   (git log only, read-only)

§12.8 ATTACK on the loop. I hit this twice in one span (`31fe21f`, `b3fe200`),
corrected both, and wrote a caller-side pre-commit check into
`prompts/AGENT-2.md`. **What I never measured is whether it is a property of this
fleet or a property of me** -- and "I did it twice so everyone must" is exactly
the shape §12.2 warns about: naming a class from one site.

THE MEASUREMENT IS POSSIBLE ONLY BECAUSE CHANNEL.md IS SELF-ATTRIBUTING.
A line reads `CLAIM <id> <ATOM>` or `DONE <id> <ATOM>`, so the line names its
author independently of the commit that carried it. Comparing that to the
commit's own `Atom:` trailer is a fact about the commit, not an inference.

WHAT THIS CANNOT SEE, stated first because the number is small without it:
  * `livechat.log`, whose entries are `[ATOM date]` but wrap over many lines, so
    a carried block's continuation lines are unattributable line-by-line. Only
    the tagged FIRST line of a block is counted.
  * Any lane whose commits predate `Atom:` trailers being enforced.
  * WHO WROTE THE LINE IS SELF-DECLARED (A22). `Atom:` and the CHANNEL prefix are
    both typed by their author; this measures declared-vs-declared, and a lane
    signing another lane's name would defeat it. That is the same weakness §13.1
    records for `Atom:` itself, inherited rather than introduced.
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys

CHANNEL = "CHANNEL.md"
# `CLAIM G98 AGENT-2`, `DONE H189 ok-1`, `EXTENSION H187 ATOM-3`.
#
# v2, AND v1 WAS VOID -- ITS OWN F3 CAUGHT IT. v1 was a regex whose non-greedy
# `[^\n]*?\s(token)` matched the SHORTEST gap, so it captured the ROW ID
# (`H197`) instead of the lane (`AGENT-1`), the id was rejected as
# not-a-lane-shaped, and the census reported 0 carries across 190 commits --
# including the two I had already confirmed BY HAND. A clean zero from a broken
# parse is indistinguishable from a clean fleet, which is the whole reason F3
# names two instances the census MUST find rather than asserting a count.
#
# v2 does not pattern-match the lane at all. It splits into tokens and accepts
# token[2] only if it is in a ROSTER built from the `Atom:` trailers of the
# history itself. Conservative by construction: a lane that never committed is
# invisible, so this UNDERCOUNTS and cannot invent a carry from a parse artefact
# like `NOTE H12/H19 (auditing ...`.
KEYWORDS = ("CLAIM", "DONE", "NOTE", "EXTENSION", "CORRECTION", "RELEASE",
            "VERDICT", "CLAIM+FILED", "RETRACTED", "BLOCKED", "PARKED")
TRAILER = re.compile(r"^(Atom|Carries):\s*(.+?)\s*$", re.M)
# Tokens that are ids or words, never lane names.


def line_author(line, roster):
    """The lane a CHANNEL line names, or None. Roster membership, not a pattern."""
    if not line.startswith("+") or line.startswith("+++"):
        return None
    toks = line[1:].split()
    if len(toks) < 3 or toks[0] not in KEYWORDS:
        return None
    return toks[2] if toks[2] in roster else None


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, text=True).stdout


def lanes_in(text):
    """Atom + Carries as a set, so a declared carry is not counted as undeclared."""
    out = set()
    for key, val in TRAILER.findall(text):
        out |= {t.strip() for t in re.split(r"[,\s]+", val) if t.strip()}
    return out


def main() -> int:
    shas = git("log", "--format=%H", "--", CHANNEL).split()
    # THE ROSTER, built from the history rather than typed. A hand-typed roster
    # is the H38 defect -- two lists of one set with nothing comparing them.
    roster = set(re.findall(r"^Atom:\s*(\S+)", git("log", "--format=%B"), re.M))
    print(f"roster from Atom: trailers ({len(roster)}): {sorted(roster)}\n")
    rows, by_lane = [], collections.Counter()
    seen_atoms = collections.Counter()
    for sha in shas:
        body = git("show", "-s", "--format=%B", sha)
        m = re.search(r"^Atom:\s*(\S+)", body, re.M)
        if not m:
            continue
        atom = m.group(1)
        seen_atoms[atom] += 1
        declared = lanes_in(body)
        # ARGUMENT ORDER, and v2 got it wrong: `git show ... -- <path> <sha>`
        # puts the sha AFTER the pathspec separator, so git reads it as a PATH,
        # matches nothing, and returns an EMPTY DIFF. Every commit then looks
        # clean. Second time in this file that a silent empty result read as a
        # clean fleet -- v1's regex was the first -- which is why F3 asserts two
        # KNOWN-POSITIVE commits rather than a count.
        diff = git("show", "--format=", "-U0", sha, "--", CHANNEL)
        foreign = collections.Counter()
        for line in diff.splitlines():
            who = line_author(line, roster)
            if who and who != atom and who not in declared:
                foreign[who] += 1
        if foreign:
            rows.append((sha[:9], atom, dict(foreign)))
            by_lane[atom] += 1

    print("H205 — CHANNEL.md lines carried under another lane's Atom, undeclared")
    print(f"commits touching {CHANNEL} with an Atom: trailer: {sum(seen_atoms.values())}")
    print(f"commits carrying a FOREIGN, UNDECLARED CHANNEL line: {len(rows)}\n")
    for sha, atom, foreign in rows:
        print(f"  {sha}  Atom: {atom:12s} carried {foreign}")
    print("\nby carrying lane:")
    for atom, n in by_lane.most_common():
        print(f"  {n:3d} / {seen_atoms[atom]:3d} commits   {atom}")
    print(f"\nlanes that have done it: {len(by_lane)} of {len(seen_atoms)} committing lanes")

    # F3, the control. I confirmed 31fe21f and b3fe200 BY HAND before writing
    # this; a census that cannot see the two instances its author already
    # verified is measuring something else, and every other row it prints is
    # void. b3fe200's carries are declared NOWHERE (the correction is a later
    # commit), so both must appear.
    want = {"31fe21f", "b3fe200"}
    got = {s for s, _, _ in rows}
    hit = {w for w in want if any(g.startswith(w) for g in got)}
    ok = hit == want
    print(f"\nF3 control — the two instances confirmed by hand: "
          f"{'both detected' if ok else 'MISSING ' + str(want - hit) + ' — CENSUS VOID'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
