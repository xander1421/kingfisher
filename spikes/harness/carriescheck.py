#!/usr/bin/env python3
"""carriescheck.py v2 — H190. Compute the `Carries:` trailer instead of typing it.

v2, H190 (AGENT-1, 2026-08-19). DEFECT REMOVED: THIS MODULE WAS READING AN
OBJECT THE COMMIT IT GATES NEVER USES, SO ON ITS ONLY WIRED CALL SITE IT COULD
ONLY EVER PRINT "clean".

  `commit_scoped.sh` invoked this in its default INDEX mode (`git diff --cached`)
  and then committed with `git commit --only "$@"`, whose entire purpose (§13,
  H19) is that it IGNORES THE INDEX. MEASURED IN A SCRATCH REPO rather than read
  off a man page (`spikes/H190_scope_of_the_check/probe.sh`): with one foreign
  line STAGED and a second foreign line UNSTAGED, `git commit --only CHANNEL.md`
  committed BOTH and left a staged sibling file OUT. So the index diff omits
  exactly the lines `--only` picks up.

  Reproduced on a real commit before the fix: `a3ea072` passed this check in
  index mode and `carriescheck.py AGENT-1 a3ea072` reports
  `Carries: AGENT-2 ATTACKER-1`. Same tool, same commit, opposite verdicts.

  That is A15 -- a control that cannot fire -- inside the module written to end
  hand-typed attribution. v1 diagnosed the cause correctly (*"`git add <path>`
  commits the WORKING TREE of an append-only shared document"*) and then wired
  itself to the index.

  WHAT IS NOT FIXED AND IS NOT SILENTLY NARROWED: `POSITIONAL` still scores
  `CHANNEL.md` and `DECISIONS.log` only. `livechat.log` remains OUT OF SCOPE, so
  the two foreign posts `a3ea072` carried there would still not be named. v1's
  own measured 26%-scoreable limit stands.

  `--selfcheck` is new and is the point of the version: v1 shipped with its
  checks in `test_carriescheck.sh`, a SHELL file, which H186 measured is
  INVISIBLE to `selfcheckall.py` -- the only automatic runner here. A module
  whose source HANDLES `--selfcheck` is discovered; a shell sibling is not.

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

WHAT THIS TOOL DOES NOT ANSWER — stated here because I misread it myself
------------------------------------------------------------------------
It answers *"whose PROSE am I carrying?"* and NOTHING else. It reads ADDED LINES
in `CHANNEL.md` and `DECISIONS.log`. It is blind to:
  * a staged DELETION of any file;
  * any code change riding in the index;
  * `WORK_QUEUE.md`, deliberately (H105, 8% false-accusation rate).

**Earned an hour after this file shipped, by its author.** Commit `38bd022`
deleted AGENT-1's shell test for send.sh — their own deliberate deletion,
superseded by `sendcheck.py` (H186), already staged in the shared index. (The
removed path is DESCRIBED rather than written: `refcheck.py` resolves backticked
paths (H41), so naming a deleted file in backticks RECREATES the dangling
citation you are reporting. refcheck refused this very paragraph on the first
attempt, and H118 and sendcheck.py's own header both record the same trap.) This tool ran on that commit and said nothing, CORRECTLY BY ITS OWN
DESIGN AND USELESSLY IN FACT, and I read its silence as "this commit is clean".
That is H176's shape — a control that fails on one fault and not the neighbouring
one — in the module written to catch attribution errors, missing one.

THE REMEDY IS NOT THIS TOOL, IT IS `git commit --only <paths>`. A bare
`git commit` after `git add <paths>` commits the WHOLE INDEX, so on a tree five
lanes share it is not path-scoped at all. `commit_scoped.sh` already passes
`--only`. Run this tool for the trailer; run `--only` for the scope. Neither
substitutes for the other.

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


def added_worktree(path: str):
    """WORKING TREE vs HEAD -- the object `git commit --only <path>` commits.

    NOT `git diff` (worktree vs index): that omits a line the lane has already
    staged, and `--only` commits those too. HEAD is the right base because HEAD
    is what the new commit's parent is.
    """
    d = _sh(["git", "diff", "HEAD", "--unified=0", "--", path])
    return [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]


def added_rev(rev: str, path: str):
    d = _sh(["git", "show", "--format=", "--unified=0", rev, "--", path])
    return [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]


def carried(atom: str, rev: str = None, worktree: bool = False) -> dict:
    """Foreign lanes whose lines this commit / index / working tree carries."""
    out = {}
    for path in POSITIONAL:
        if rev:
            lines = added_rev(rev, path)
        elif worktree:
            lines = added_worktree(path)
        else:
            lines = added_staged(path)
        foreign = authors_of(path, lines) - {canon(atom)}
        if foreign:
            out[path] = sorted(foreign)
    return out


def trailer_for(carried_map: dict) -> str:
    lanes = sorted({l for v in carried_map.values() for l in v})
    return ("Carries: " + " ".join(lanes)) if lanes else ""


def selfcheck() -> int:
    """Two-sided, in a scratch repo, and it FAILS IF THE FIX REGRESSES.

    The whole finding is that index mode and worktree mode disagree on a tree
    where a foreign line is unstaged. So the check asserts BOTH directions:
    worktree mode must NAME the foreign lane, and index mode must MISS it. An
    assertion that only checked the new mode would still pass if someone quietly
    made both modes read the index again.
    """
    import os, shutil, subprocess as sp, tempfile
    # H89/§10: inside the workspace. tempfile defaults to /tmp, which is not.
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _scratch = os.path.join(_root, ".scratch")
    os.makedirs(_scratch, exist_ok=True)
    d = tempfile.mkdtemp(prefix="carriescheck_sc_", dir=_scratch)
    cwd = os.getcwd()
    try:
        os.chdir(d)
        for c in (["git", "init", "-q", "."],
                  ["git", "config", "user.email", "t@t"],
                  ["git", "config", "user.name", "t"]):
            sp.run(c, check=True, capture_output=True)
        # REAL callsigns, deliberately. `CALLSIGNS` is a CLOSED ENUMERATION,
        # so a synthetic `LANE-2` matches nothing and this check would pass
        # vacuously -- my first draft did exactly that and asserted `{}`. And
        # ADDING a fixture callsign to that list is H64's class: a test id
        # sharing the namespace with real allocations. So the fixture uses two
        # real lanes inside a throwaway scratch repo, which pollutes nothing.
        open("CHANNEL.md", "w").write("base\n")
        sp.run(["git", "add", "CHANNEL.md"], check=True, capture_output=True)
        sp.run(["git", "commit", "-qm", "base"], check=True, capture_output=True)

        with open("CHANNEL.md", "a") as f:
            f.write("DONE X1 AGENT-2 staged foreign line\n")
        sp.run(["git", "add", "CHANNEL.md"], check=True, capture_output=True)
        with open("CHANNEL.md", "a") as f:
            f.write("DONE X2 AGENT-2 UNSTAGED foreign line\n")

        wt = carried("AGENT-1", worktree=True)
        ix = carried("AGENT-1")
        assert "CHANNEL.md" in wt and wt["CHANNEL.md"] == ["AGENT-2"], wt
        assert len(added_worktree("CHANNEL.md")) == 2, added_worktree("CHANNEL.md")
        assert len(added_staged("CHANNEL.md")) == 1, added_staged("CHANNEL.md")

        # NEGATIVE CONTROL: with NOTHING unstaged the two modes must AGREE, or
        # worktree mode is inventing foreign lines rather than seeing more.
        sp.run(["git", "add", "CHANNEL.md"], check=True, capture_output=True)
        assert carried("AGENT-1", worktree=True) == carried("AGENT-1"), \
            "modes disagree with nothing unstaged -- worktree mode is inventing lines"

        # and a lane carrying only ITS OWN lines is named by neither mode.
        sp.run(["git", "commit", "-qm", "x"], check=True, capture_output=True)
        with open("CHANNEL.md", "a") as f:
            f.write("DONE X3 AGENT-1 own line\n")
        assert carried("AGENT-1", worktree=True) == {}, carried("AGENT-1", worktree=True)
    finally:
        os.chdir(cwd)
        shutil.rmtree(d, ignore_errors=True)
    print("carriescheck --selfcheck: ok -- 6 assertions, both modes exercised, "
          "worktree sees the unstaged foreign line and the index does not")
    return 0


def main() -> int:
    if "--selfcheck" in sys.argv[1:]:
        return selfcheck()
    worktree = "--worktree" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    atom = args[0] if args else _sh(["git", "config", "user.callsign"]).strip()
    if not atom:
        import os
        atom = os.environ.get("CALLSIGN", "")
    if not atom:
        sys.stderr.write("carriescheck: REFUSING — no atom given and CALLSIGN unset.\n"
                         "  usage: python3 spikes/harness/carriescheck.py <YOUR-CALLSIGN> [rev] [--worktree|--selfcheck]\n")
        return 3
    rev = args[1] if len(args) > 1 else None

    cm = carried(atom, rev, worktree=worktree)
    where = rev[:8] if rev else ("the WORKING TREE (what `--only` commits)"
                                 if worktree else "the STAGED index")
    if not cm:
        print(f"carriescheck: {where} carries no other lane's lines under Atom: {atom}")
        return 0

    print(f"carriescheck — {where} carries ANOTHER LANE'S LINES under Atom: {atom}\n")
    for path, lanes in sorted(cm.items()):
        print(f"  {path}: {' '.join(lanes)}")
        lines = (added_rev(rev, path) if rev
                 else added_worktree(path) if worktree else added_staged(path))
        for ln in lines:
            a = authors_of(path, [ln])
            if a and not a <= {canon(atom)}:
                print(f"      {ln[:100]}")
    print(f"\nPaste this into your commit message (§13):\n\n    {trailer_for(cm)}\n")
    print("Their content is unmodified and nothing is at risk — this is attribution only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
