#!/usr/bin/env python3
# eval_hygiene.py v3 — H110 (v1), H231 (v2, v3). ok-1, 2026-08-19.
# This line duplicates the docstring's version on purpose: versioncheck.py
# reads a `#` comment and cannot see a version declared in a docstring (H193).
"""Autoloop Evaluator: Repository Hygiene & Harness Integrity.

Evaluates journalcheck, refcheck, and githygiene.
Outputs normalized JSON metric:
  {"hygiene_score": 1.0 or 0.0, "details": {...}}

v3 (H231, ok-1) — DEFECT REMOVED (§12.7): A CHECKER THAT REFUSED WITHOUT
PRINTING A PARSEABLE LINE SCORED AS `CLEAN`. Found by attacking v2 before it was
committed; the rationale and the reachable instance are on `record_verdict`.

v2 (H231, ok-1) — DEFECT REMOVED (§12.7): A METRIC THAT SCORES THE COMMITTED
RECORD WAS COMPUTED FROM THE WORKING TREE, SO ANOTHER LANE'S UNCOMMITTED
IN-FLIGHT EDIT WAS SCORED AS THE CANDIDATE'S REGRESSION.

`refcheck.py` and `journalcheck.py` read files with plain `open()`, so their
verdict is a function of the shared tree. `pre-commit.hook` v2 (ATTACKER-1, H35)
MEASURED that scope and documented it for the GATE -- "for refcheck.py and
journalcheck.py this is a gate on the state of the shared documents in the tree,
which any lane can trip and any lane can clear" -- and nobody carried the finding
into the EVALUATOR, where the same two checkers set the autoloop's stated safety
invariant (PROGRAM.md: `hygiene_score == 1.00`) and `scripts/autoloop.py` fails
`--ci` on it.

LIVE INSTANCE, measured before this was written: hygiene_score was 0.0 with
journalcheck rc=0 and githygiene rc=0, on ONE refcheck refusal -- a backticked
path in `spikes/harness/constcheck.py`, an UNCOMMITTED file. `git show
HEAD:spikes/harness/constcheck.py` did not contain that citation and `git log
--all` on the cited directory was empty: the committed record never carried the
defect and a fresh clone was green. The tree it scored held 316 dirty tracked
files and 1163 untracked across five lanes. That 0.0 was reported upward as a
composite regression.

THIS IS AGENT-1'S CLASS FROM THE SAME HOUR AT A FOURTH SITE -- "a measurement
that COULD NOT BE TAKEN, scored as a measurement that FAILED" -- and family C,
the artifact is not what you think.

WHAT CHANGES AND WHAT DELIBERATELY DOES NOT. `hygiene_score` keeps its exact
meaning and its exact value: all three checkers green on the content that was
read. It is NOT rescoped, because `.github/autoloop/MEMORY.md` carries historical
`hygiene_score` rows and moving a published number under an unchanged name is
A18. What is ADDED is the attribution that decides whether a red run is a
regression at all:

  hygiene_record_verdict  CLEAN | VIOLATED | NOT_MEASURED
  hygiene_violations      [{checker, path, in_record}]

VIOLATED means at least one refusal attributes to a file whose working-tree
bytes ARE HEAD's bytes -- the checker read the record and refused it. That is a
real regression and scores 0.0 as before. NOT_MEASURED means every refusal
attributes to uncommitted content: the record's own bytes for those files were
never read, so nothing was learned about it either way.

NOT A LOOSENING, and the selfcheck drives that direction first: a broken
citation planted in a CLEAN file must still come out VIOLATED. An unattributable
refusal line counts as IN THE RECORD -- unknown resolves to the worse verdict,
never the better one.

CEILING, stated rather than fixed: a green tree does not prove a green record
either, because an uncommitted repair can mask a defect in HEAD's blob. Scoring
the record exactly means running the checkers on HEAD's content, and the two
routes to that are both refused here on measured grounds -- `git checkout-index`
is 614 ms / 164 MB / 3482 files per run (H35), and a materialised copy anywhere
under the workspace is what H223 measured poisoning `constcheck`, `leakcheck` and
`recheck` with 40, 8 and 29 phantom output lines. So CLEAN below means "green on
what was read", and `tree_dirty` is published beside it so the reader is never
guessing which object the verdict is about.
# ponytail: attribution, not materialisation. Score HEAD exactly only if a
# cheap read-only route appears (git cat-file into the checkers, not a checkout).

Check that fails when this breaks (§12.3):
  python3 .github/autoloop/evaluators/eval_hygiene.py --selfcheck
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def run_cmd(cmd, cwd=None):
    p = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


# A refusal line from either tree-reading checker names its file first:
#   refcheck      "  UNRESOLVED spikes/harness/constcheck.py: `x` does not exist"
#   journalcheck  "  COLLISION  HANDOFF.ok-1.md: NEXT is headed by H99, which ..."
# Both are `<marker> <repo-relative-path>: <prose>`. Anything else is
# unattributable and is treated as IN THE RECORD.
_REFUSAL = re.compile(r'^\s*(?:UNRESOLVED|COLLISION)\s+(\S+?):')


def changed_vs_head(cwd=None):
    """Paths whose working-tree bytes are NOT HEAD's bytes.

    `git diff HEAD --name-only` covers staged and unstaged alike; untracked
    files are not in HEAD at all. A path in this set was not read as the record.
    """
    _, tracked, _ = run_cmd("git diff HEAD --name-only", cwd=cwd)
    _, untracked, _ = run_cmd(
        "git ls-files --others --exclude-standard", cwd=cwd)
    return {p for p in (tracked + "\n" + untracked).split("\n") if p.strip()}


def attribute(checker, out, dirty):
    """Refusal lines in `out`, each tagged with whether it is in the record."""
    found = []
    for line in (out or "").split("\n"):
        m = _REFUSAL.match(line)
        if not m and not line.strip().startswith(("UNRESOLVED", "COLLISION")):
            continue
        path = m.group(1) if m else None
        # Unattributable: the worse verdict, never the better one.
        found.append({"checker": checker, "path": path,
                      "in_record": path is None or path not in dirty})
    return found


def record_verdict(results, dirty):
    """(verdict, violations) for {checker: (ok, output)} against dirty paths.

    Pure, so the selfcheck can drive every direction without a repository.

    v3, H231, AND IT IS AN ATTACK ON v2 BY ITS OWN AUTHOR BEFORE v2 WAS EVER
    COMMITTED. DEFECT CLASS REMOVED: A CHECKER THAT REFUSED WITHOUT PRINTING A
    PARSEABLE LINE SCORED AS `CLEAN` -- the instrument reporting fiction
    (family B) inside the instrument built to stop a family-C misattribution,
    and the exact loosening v2's docstring said it did not do.

    REACHABLE, NOT HYPOTHETICAL: `journalcheck.py:186` refuses an absent
    WORK_QUEUE.md by writing to STDERR and `sys.exit(2)`. v2 handed `classify`
    stdout only, so that run produced no violation, and a checker that refused
    outright was published as a clean record. v2 escalated exactly one checker
    -- githygiene, at the call site, because it emits no marker of its own --
    which is §12.2's defect verbatim: the class fixed at one site while the
    same class lives elsewhere, in eleven lines of my own new code.

    THE RULE, ONCE, FOR EVERY CHECKER: not ok contributes at least one
    violation. If it printed nothing attributable, that violation is
    unattributable and counts as IN THE RECORD. So the githygiene special case
    is DELETED rather than joined by two more.
    """
    violations = []
    for checker, (ok, out) in results.items():
        found = attribute(checker, out if not ok else "", dirty)
        if not ok and not found:
            found = [{"checker": checker, "path": None, "in_record": True}]
        violations += found
    if not violations:
        return "CLEAN", violations
    if any(v["in_record"] for v in violations):
        return "VIOLATED", violations
    return "NOT_MEASURED", violations


def main():
    rc_ref, out_ref, err_ref = run_cmd("python3 spikes/harness/refcheck.py")
    rc_jnl, out_jnl, err_jnl = run_cmd("python3 spikes/harness/journalcheck.py")
    # H110 (ok-1): this file's own docstring claimed three checkers and ran two.
    # githygiene was named and never invoked, so `hygiene_score` — which is 1.0
    # or 0.0 and is what ACCEPTS a mutation — was blind to §13 entirely: a
    # candidate adding a binary, or a commit with an actionless subject, scored
    # exactly like one that did not. The gap was between the docstring and the
    # code in one file, which is why reading either alone missed it.
    rc_git, out_git, err_git = run_cmd("python3 spikes/harness/githygiene.py")

    ref_ok = (rc_ref == 0)
    jnl_ok = (rc_jnl == 0)

    git_ok = rc_git == 0
    all_ok = ref_ok and jnl_ok and git_ok
    score = 1.0 if all_ok else 0.0

    # v3, H231. githygiene emits no attributable marker of its own -- it reads
    # the INDEX via `git ls-files` and is already scoped to the commit
    # (pre-commit.hook v2) -- so its refusals land unattributable and count in
    # the record. That is now the general rule and not its special case.
    dirty = changed_vs_head()
    verdict, violations = record_verdict(
        {"refcheck": (ref_ok, out_ref),
         "journalcheck": (jnl_ok, out_jnl),
         "githygiene": (git_ok, out_git)}, dirty)

    result = {
        "hygiene_score": score,
        "hygiene_record_verdict": verdict,
        "hygiene_violations": violations,
        "tree_dirty": len(dirty),
        "refcheck_ok": ref_ok,
        "journalcheck_ok": jnl_ok,
        "githygiene_ok": git_ok,
        "checkers_run": ["refcheck", "journalcheck", "githygiene"],
        "refcheck_output": out_ref if ref_ok else (out_ref + " | " + err_ref),
        "journalcheck_output": out_jnl if jnl_ok else (out_jnl + " | " + err_jnl),
    }

    print(json.dumps(result, indent=2))
    return 0 if all_ok else 1


def selfcheck():
    """§12.3. Drives the NOT-A-LOOSENING direction first.

    A checker only ever seen reporting NOT_MEASURED is as uninformative as one
    only ever seen passing, so every case below is driven in both directions.
    """
    bad = []
    ref = "  UNRESOLVED spikes/harness/constcheck.py: `x/` does not exist"
    jnl = "  COLLISION  HANDOFF.ok-1.md: NEXT is headed by H99, which is DONE"

    def check(want, results, dirty, why):
        got, _ = record_verdict(results, dirty)
        if got != want:
            bad.append(f"{why}: want {want}, got {got}")

    check("NOT_MEASURED", {"refcheck": (False, ref)},
          {"spikes/harness/constcheck.py"},
          "a refusal in an UNCOMMITTED file")
    check("VIOLATED", {"refcheck": (False, ref)}, set(),
          "a refusal in a CLEAN file")

    # The mixed case is the one a loosening would get wrong: one dirty, one
    # clean. A record violation is not excused by an unrelated in-flight edit.
    check("VIOLATED", {"refcheck": (False, ref), "journalcheck": (False, jnl)},
          {"spikes/harness/constcheck.py"},
          "one clean-file refusal among dirty ones")

    check("CLEAN", {"refcheck": (True, ""), "journalcheck": (True, "")},
          {"anything"}, "no refusals at all")

    # v3, H231, AND THIS IS THE CASE v2 DID NOT CONSTRUCT. journalcheck.py:186
    # refuses an absent WORK_QUEUE.md on STDERR with `sys.exit(2)`, printing
    # nothing on stdout: v2 saw no line, produced no violation, and published
    # CLEAN for a checker that had refused outright. Two-sided, because
    # "escalate whenever silent" would be the same check with no information
    # in it: a checker that is OK and silent must stay CLEAN.
    check("VIOLATED", {"journalcheck": (False, "")}, {"anything"},
          "a checker that REFUSED and printed nothing parseable")
    check("CLEAN", {"journalcheck": (True, "")}, {"anything"},
          "a checker that PASSED and printed nothing")

    # githygiene emits no UNRESOLVED/COLLISION marker at all, so it is the
    # standing instance of the case above rather than a special case in main().
    check("VIOLATED", {"githygiene": (False, "ADD 3.2 MB spikes/x/model.bin")},
          {"spikes/x/model.bin"}, "a githygiene refusal on a dirty path")

    # H14's failure mode: refcheck prints a KNOWN ROW SHAPE backlog on every
    # GREEN run. Counting those as refusals would make this red forever --
    # and the same text on a RED run is a refusal it declined to attribute.
    known = ("  KNOWN ROW SHAPE WORK_QUEUE.md: `S75` has 8 fields, not 5 -- its "
             "status column is unreadable. Owner fixes it by escaping the pipe "
             "as \\| (H82).")
    check("CLEAN", {"refcheck": (True, known)}, set(),
          "a KNOWN ROW SHAPE report on a green run")
    check("VIOLATED", {"refcheck": (False, known)}, set(),
          "a refusal whose only output is a KNOWN ROW SHAPE backlog")

    # Unattributable must resolve to the WORSE verdict.
    check("VIOLATED", {"refcheck": (False, "UNRESOLVED no path colon here")},
          {"everything"}, "an unattributable refusal")

    # changed_vs_head is git plumbing and gets a throwaway repo, never this one:
    # a test that can stop production is not a test. The scratch root is
    # `.scratch/` and not $TMPDIR -- H89 decided §10 that way, and v2 reached
    # outside the workspace through `tempfile.mkdtemp()`, a route
    # `scratchcheck.py` cannot see because it is a SHELL classifier (H198).
    import shutil
    t = os.path.join(REPO_ROOT, ".scratch", "eval_hygiene_selfcheck")
    shutil.rmtree(t, ignore_errors=True)
    os.makedirs(t)
    try:
        for c in ("git init -q .", "git config user.email a@b",
                  "git config user.name a", "echo one > f.md", "echo two > g.md",
                  "git add f.md g.md", "git commit -q -m base"):
            run_cmd(c, cwd=t)
        if changed_vs_head(cwd=t) != set():
            bad.append("a clean repo must report nothing changed vs HEAD")
        run_cmd("echo edited > f.md", cwd=t)
        run_cmd("echo new > h.md", cwd=t)
        got = changed_vs_head(cwd=t)
        if got != {"f.md", "h.md"}:
            bad.append(f"edited + untracked must both be dirty, got {sorted(got)}")
        run_cmd("git add f.md", cwd=t)
        if "f.md" not in changed_vs_head(cwd=t):
            bad.append("a STAGED edit still differs from HEAD and must be dirty")
    finally:
        shutil.rmtree(t, ignore_errors=True)

    for b in bad:
        print("  FAIL  " + b)
    if not bad:
        print("eval_hygiene selfcheck: VIOLATED reachable, NOT_MEASURED reachable, "
              "mixed resolves to VIOLATED, a silent REFUSAL is VIOLATED and a "
              "silent PASS is CLEAN, backlog reports gate only on a red run, "
              "unattributable counts against, staged edits count as dirty")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else main())
