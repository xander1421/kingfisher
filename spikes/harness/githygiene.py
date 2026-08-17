#!/usr/bin/env python3
"""Git hygiene checker. The history is training data, so it is a deliverable.

Measured on this repo 2026-08-17, before this checker existed:

    uncompressed blob total   183.7 MB, of which 158.1 MB (86%) is files >1 MB
    packed on disk            104.63 MiB   (`git count-objects -vH`)

BOTH numbers are true and they are different measurements; agent-1 flagged that
quoting only the first invites the next reader to run the obvious command and
conclude the figure is wrong. 86% is the share of UNCOMPRESSED blob bytes in
files over 1 MB, while every RESULT in the workspace is plain text.

Size is the weaker argument anyway. The stronger one is BLAST RADIUS: a
repo-wide `git add` sweeps other lanes' in-progress files into a commit titled
for unrelated work, and can commit a SHARED file mid-edit. That happened here --
four commits absorbed another agent's uncommitted spikes -- and had one landed
between two edits of a shared harness file, the committed harness would have
been broken for every lane.

WHAT THIS ENFORCES
  * no binary / model / archive extensions added
  * no build trees or __pycache__
  * no oversized additions (default 1 MB)
  * commit subjects that state a finding rather than an action

WHAT THIS DELIBERATELY DOES NOT DO
  It never rewrites history and never deletes anything. Other agents hold
  clones whose provenance chains reference existing blobs by hash; removing a
  blob changes every downstream hash. `git rm --cached` going forward is
  reversible and safe. `filter-repo` is a human decision, and this tool only
  reports the candidates for it.

Exit 0 clean, 1 violations, 2 could not run.

VERSION HISTORY (§12.7: a harness change carries a version bump and a rationale
block naming the defect it removes). Numbered from here; earlier states are
described by the H14 and H35 comments in the body, which predate the convention
reaching this file.

  v3 · 2026-08-17, AGENT-1, H71. DEFECT REMOVED: **§13's only stated commit form
       cannot express the operation every cycle performs, and nothing in the
       tree said so.** §13 gives one form -- `git commit --only <paths>`, not
       `git add` then `git commit` -- and `--only` REFUSES an untracked path:

           error: pathspec 'spikes/S36_witnessed_job/RESULT.md' did not match
           any file(s) known to git

       Every cycle in this repo creates a new spike directory, so the rule was
       unfollowable for the commonest operation here, and no `DECISIONS.log`,
       `BLOCKED.log` or `HANDOFF.*` entry records anyone hitting it -- meaning
       every new spike was committed by a route the contract does not name.

       The guardrail H71 adds is a RECIPE in a document, and §12.10 says a
       guardrail that is written but not mechanised is violated again by its own
       author. So the recipe is EXECUTED here rather than asserted: `selfcheck`
       gains three cases proving (a) `--only` refuses an untracked path, (b)
       `git add -N` then `--only` commits it, and (c) **a co-lane's fully staged
       file stays out of that commit** -- which is the property that makes the
       workaround safe rather than a quiet return to the H19 shared-index bug.
       If a future git accepts untracked paths under `--only`, case (a) goes red
       and §13's workaround paragraph can be deleted rather than left as
       folklore.
"""

import os
import re          # H14: absent when CALLSIGN_RE shipped. The module died at
import subprocess  # IMPORT TIME with `NameError: name 're' is not defined`, so
import sys         # `python3 githygiene.py` -- which §13 puts in every lane's
                   # pre-commit path -- was a hard crash for every lane for at
                   # least 20 minutes, committed to HEAD, while the checker whose
                   # job is catching bad commits could not run to catch its own.
                   # H14 predicted exactly this: the one harness module with no
                   # runnable check. See selfcheck() at the bottom.

MAX_ADD = 1_048_576          # 1 MB

BAD_EXT = {
    # compiled
    ".so", ".dylib", ".dll", ".a", ".o", ".exe", ".apk", ".aar", ".jar",
    ".class", ".pyc", ".wasm",
    # model weights — also a §7 licence question, not only a size one
    ".gguf", ".safetensors", ".pt", ".pth", ".onnx", ".ckpt", ".h5", ".npz",
    # archives and images that are usually generated
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".iso", ".dmg",
}
# `.bin` is deliberately NOT in BAD_EXT: spikes/S52_realkg/triples.bin is 3 MB
# of real evidence that several spikes read. Size alone flags it for review.

# Explicit, justified exceptions. A checker that fires on known-accepted items
# every run is a checker everyone learns to ignore, and an ignored check is
# worth less than no check because it looks like coverage. Each entry states
# WHY, so the list can be argued with rather than merely trusted.
ALLOW = {
    "spikes/S52_realkg/triples.bin":
        "FB15k-237 as packed u32 triples — the evidence G17/G21/G22/G23/G24/"
        "G25 all read. Regenerating it needs the original corpus; 3 MB is the "
        "compact form, not a build artefact.",
}

BAD_PATH = ("/target/", "/__pycache__/", "/node_modules/", "/.gradle/",
            "/build/outputs/", "/.venv/", "/jniLibs/")

# H12: in a repo where every commit carries ONE human's git identity, commit
# authorship cannot distinguish agents AT ALL. Two lanes independently mis-
# attributed a 300-file sweep (e990f11) to the wrong atom from the same evidence,
# and the existing `Co-Authored-By: Claude Opus 5` trailer is identical on every
# commit from every session, so it distinguishes nothing either.
#
# `Atom:` is the callsign (§14.1 vocabulary). It is SELF-DECLARED, so it has the
# same A22 weakness as CALLSIGN in CHANNEL.md: a party supplying the input to a
# check applied to itself. It fixes "no attribution exists", not "attribution
# can be false".
#
# `Claude-Session:` is the harder half. It is assigned, not typed, and differs
# per session, so two lanes cannot collide on it even when both sign the same
# callsign — which is exactly what happened today with two AGENT-2s.
# `Reviewed-By:` records WHO ATTACKED IT, which is the thing this workspace's
# credibility actually rests on — a claim here is worth what the review of it was
# worth, and until now the history recorded neither.
#
# Two rules, both mechanical:
#   * Reviewed-By MUST NOT equal Atom. Self-review is the A22 defect exactly: a
#     party supplying the input to a check applied to itself. Every real finding
#     today came from another lane; not one atom's own suite caught its own bug.
#   * `Reviewed-By: unreviewed` is LEGAL and explicit. Unreviewed work is normal
#     and must be committable — but it gets RECORDED as unreviewed rather than
#     left silent, so `git log --grep` can enumerate exactly what nobody checked.
#     Silence reading identical to success is the failure that ran through this
#     whole day.
REQUIRED_TRAILERS = ("Atom", "Claude-Session", "Reviewed-By")

# PRESENCE IS NOT VALIDATION. The first version of this rule checked only that
# the trailer key existed, and the history shows exactly what that buys:
#
#   Atom:        AGENT-1 x8, agent-1 x4, mutation-detection x5,
#                harness-hardening x3, corpus-composition x3, AGENT-2 x2
#   Reviewed-By: unreviewed x14, self x11, ATOM-3 x1
#
#   * 11 of 26 `Atom:` values are TOPIC LABELS, not callsigns. The field that
#     exists to name an atom was being used to name a subject.
#   * AGENT-1 and agent-1 are one atom counted as two, so every tally splits.
#   * `Reviewed-By: self` DEFEATED the A22 rejection 11 times, because the guard
#     compared `rev.lower() == atom.lower()` and "self" is not "agent-1". A
#     guard against self-review, defeated by typing the word self.
#
# Exactly one genuine peer attestation exists in the entire history. So the
# check now validates VALUES: a callsign must look like a callsign, and a
# reviewer must be a different callsign or the literal `unreviewed`.
CALLSIGN_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")
NOT_A_REVIEWER = {"SELF", "ME", "NONE", "N/A", "NA", "UNKNOWN", "NOBODY",
                  "MYSELF", "OWN", "-", ""}


def check_callsign(v):
    """A callsign is upper-case, hyphenated, and contains a digit: AGENT-2,
    ATOM-3, ATTACKER-1, AGENT-2-LANE. Case-folded, so agent-1 == AGENT-1."""
    u = v.strip().upper()
    if not CALLSIGN_RE.match(u) or not any(c.isdigit() for c in u):
        return None
    return u

WEAK_SUBJECTS = ("wip", "update", "updates", "fix", "fixes", "misc", "stuff",
                 "changes", "cleanup", "temp", "test", "asdf", "more work",
                 "address feedback", "minor", "tweak", "tweaks")


def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout.strip()


def classify(path, size):
    if path in ALLOW:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext in BAD_EXT:
        return f"binary/model extension {ext}"
    if any(b in "/" + path for b in BAD_PATH):
        return "build tree or cache"
    if size is not None and size > MAX_ADD:
        return f"{size / 1048576:.1f} MB exceeds {MAX_ADD / 1048576:.0f} MB"
    return None


def check_paths(paths, label, sizes=None):
    bad = []
    for p in paths:
        if not p:
            continue
        size = sizes.get(p) if sizes else (
            os.path.getsize(p) if os.path.exists(p) else None)
        why = classify(p, size)
        if why:
            bad.append((p, why))
    if bad:
        print(f"\n{label}: {len(bad)} violation(s)")
        for p, why in sorted(bad, key=lambda x: x[0]):
            print(f"   {p}\n      -> {why}")
    return bad


def check_subject(subject):
    s = subject.strip().lower()
    if not s:
        return "empty subject"
    head = s.split(":")[0].strip()
    if head in WEAK_SUBJECTS or s in WEAK_SUBJECTS:
        return f"actionless subject '{subject.strip()}' — state the finding"
    # Length is a NOTE, not a violation, above 72. This repo's strongest
    # commit subjects run long precisely because they carry the finding and
    # its number -- "A18 audit: the 29x in-process advantage is 1.09x at real
    # job sizes" is 99 chars and is exactly what the history should look like.
    # Writing a rule the best existing practice violates would train agents to
    # shorten good subjects into weak ones. Only runaway length fails.
    if len(subject) > 120:
        return f"subject is {len(subject)} chars, over 120 — split it"
    return None


def subject_note(subject):
    if 72 < len(subject) <= 120:
        return f"{len(subject)} chars — long, but fine if it carries a finding"
    return None


def main():
    if sh("git", "rev-parse", "--is-inside-work-tree") != "true":
        print("not a git work tree")
        return 2
    do_all = "--all" in sys.argv
    violations = []

    # --diff-filter=ACMR excludes DELETIONS. Without it, `git rm --cached` on
    # an oversized file -- the exact remedy this tool recommends -- is itself
    # reported as a violation, because the deleted path still appears in the
    # staged name list. A check that fails the fix it prescribes is worse than
    # no check: it teaches people to ignore it. Same shape as the G25 finding,
    # where a control penalised the arm that succeeded.
    staged = sh("git", "diff", "--cached", "--name-only",
                "--diff-filter=ACMR").splitlines()
    # H35, ATTACKER-1: THE SIZES COME FROM THE INDEX, NOT FROM THE TREE.
    # `check_paths` defaults to `os.path.getsize`, so the PATHS were the
    # commit's and the BYTES were the working tree's. MEASURED, not argued:
    # stage a 3 MB file, shrink the tree copy to 6 bytes, and this module
    # printed "clean -- nothing you are about to commit violates §13" at exit 0
    # while the commit carried 3,000,000 bytes. Same class as pre-commit.hook
    # v2's F1 -- a checker reading the tree while its verdict is attributed to
    # the commit -- landing in the one checker whose comment above advertises
    # index-awareness: `git ls-files`/`git diff --cached` gave it the right
    # paths and nothing gave it the right bytes.
    staged_sizes, fellback = {}, []
    for p in staged:
        s = sh("git", "cat-file", "-s", f":{p}")
        if s.isdigit():
            staged_sizes[p] = int(s)
        else:
            # Loud, not silent: a size this tool could not read from the index
            # is exactly the case the paragraph above is about.
            fellback.append(p)
            staged_sizes[p] = (os.path.getsize(p)
                               if os.path.exists(p) else None)
    if fellback:
        print(f"\nNOTE: index size unreadable for {fellback} — "
              f"fell back to the working-tree size, which may not be what "
              f"you are committing")
    if staged:
        violations += check_paths(staged, "STAGED", sizes=staged_sizes)
    else:
        print("nothing staged")

    # H14: TRACKED violations are REPORTED, never part of the verdict.
    #
    # This module's own ALLOW comment names the failure mode -- "a checker that
    # fires on known-accepted items every run is a checker everyone learns to
    # ignore" -- and then the verdict did exactly that: exit 1 was PERMANENT on
    # 16 already-committed binaries that §13 forbids REMOVING (other lanes'
    # provenance chains reference those blobs by hash). So the exit code carried
    # no information: it was 1 before you staged anything and 1 after, whatever
    # you did. A gate whose output does not depend on your input is not a gate,
    # which is family A -- the instrument cannot produce the answer.
    #
    # Reported, and loudly, because they are real; just not conflated with
    # "something you did just now is wrong". This is NOT weakening a gate to
    # pass it (§10): the staged path, which is the one a commit can still fix,
    # got STRICTER in the same edit -- it now also fails on a weak subject.
    # `git ls-files` reads the INDEX, so it includes what you just staged: a
    # brand-new violation was printed twice, once as STAGED and again under
    # "already committed", which is the label that means "not your fault and not
    # yours to fix". It still gated correctly via the STAGED list, so this was a
    # mislabel and not a hole -- but the tracked list is the one a reader is
    # invited to ignore, and putting new violations in it teaches exactly the
    # wrong reflex. `git ls-tree -r HEAD` is what "already committed" means.
    committed = (sh("git", "ls-tree", "-r", "--name-only", "HEAD").splitlines()
                 if sh("git", "rev-parse", "--verify", "-q", "HEAD") else [])
    tracked_bad = check_paths(committed,
                              "TRACKED (already committed, reported not gated)")

    if do_all:
        out = sh("bash", "-c",
                 "git rev-list --objects --all | "
                 "git cat-file --batch-check="
                 "'%(objecttype) %(objectsize) %(rest)' | "
                 "awk '$1==\"blob\" && $2>1048576 {print $2, $3}' | sort -rn")
        rows = [l.split(None, 1) for l in out.splitlines() if l]
        if rows:
            tot = sum(int(r[0]) for r in rows)
            print(f"\nHISTORY: {len(rows)} blobs over 1 MB, "
                  f"{tot / 1048576:.1f} MB total")
            seen = set()
            for size, path in rows[:15]:
                if path in seen:
                    continue
                seen.add(path)
                print(f"   {int(size) / 1048576:7.1f} MB  {path}")
            print("   (history is NOT rewritten by this tool — see CLAUDE.md 3)")

    # H14, 2026-08-17. EVERYTHING BELOW REPORTS ON **HEAD**, WHICH IS ALREADY
    # COMMITTED, so it goes in `head_bad` and NOT in `violations`. Two defects,
    # both surfaced by the selfcheck at the bottom the first time it ran:
    #
    #  * with NO COMMITS AT ALL, `git log -1` returns empty, every required
    #    trailer read as "missing", and the tool reported a violation about a
    #    commit that does not exist -- family B, the instrument reporting
    #    fiction, printed under the heading "in what you are about to commit";
    #  * HEAD in a THREE-LANE SHARED TREE is usually somebody else's commit. So
    #    another lane's bad message failed YOUR pre-commit check, and you could
    #    not fix it: the only repair is rewriting history, which §13 forbids
    #    without qualification. Harness state that is not per-lane, again.
    #
    # This is NOT weakening a gate to pass it. The PROSPECTIVE gate on trailers
    # is `.git/hooks/commit-msg`, which refuses the commit being written and got
    # stricter today. This is the RETROSPECTIVE report, and a retrospective
    # report on an unfixable artifact must not gate.
    head_bad = []
    if not sh("git", "rev-parse", "--verify", "-q", "HEAD"):
        print("\nHEAD: no commits yet — nothing to report")
        trailers, missing = "", []
    else:
        trailers = sh("git", "log", "-1", "--pretty=%(trailers:unfold=true)")
        missing = [t for t in REQUIRED_TRAILERS if f"{t}:" not in trailers]
    if not sh("git", "rev-parse", "--verify", "-q", "HEAD"):
        pass
    elif missing:
        print(f"\nHEAD TRAILERS: missing {missing}")
        print("   Every commit must name the atom that made it and the session "
              "it came from:")
        print("     Atom: AGENT-2")
        print("     Claude-Session: <assigned session url>")
        head_bad.append(("HEAD", f"missing trailers {missing}"))
    else:
        def val(key):
            for ln in trailers.splitlines():
                if ln.strip().startswith(key + ":"):
                    return ln.split(":", 1)[1].strip()
            return ""
        atom, rev = val("Atom"), val("Reviewed-By")
        ca = check_callsign(atom)
        if ca is None:
            print(f"\nHEAD TRAILERS: Atom {atom!r} is not a callsign — that "
                  f"field names WHO, not what.")
            head_bad.append(("HEAD", f"Atom {atom!r} not a callsign"))
        elif rev.strip().upper() in NOT_A_REVIEWER:
            print(f"\nHEAD TRAILERS: Reviewed-By {rev!r} is self-review in "
                  f"plain language. A22 — use another atom or 'unreviewed'.")
            head_bad.append(("HEAD", f"Reviewed-By {rev!r} is not a reviewer"))
        elif rev.lower() == "unreviewed":
            print(f"\nHEAD TRAILERS: ok — Atom {atom}, explicitly UNREVIEWED")
        elif check_callsign(rev) is None:
            print(f"\nHEAD TRAILERS: Reviewed-By {rev!r} is neither a callsign "
                  f"nor 'unreviewed'.")
            head_bad.append(("HEAD", f"Reviewed-By {rev!r} malformed"))
        elif check_callsign(rev) == ca:
            print(f"\nHEAD TRAILERS: SELF-REVIEW — Atom {atom} reviewed by "
                  f"{rev}. A22: the reviewed party supplied the review.")
            head_bad.append(("HEAD", f"self-review by {atom}"))
        else:
            print(f"\nHEAD TRAILERS: ok — Atom {atom}, reviewed by {rev}")

    last = sh("git", "log", "-1", "--pretty=%s")
    if last:
        why = check_subject(last)
        print(f"\nLAST COMMIT SUBJECT\n   {last}")
        note = subject_note(last)
        if why:
            print(f"   -> {why}")
            head_bad.append(("HEAD", why))
        elif note:
            print(f"   -> ok ({note})")
        else:
            print("   -> ok")

    print(f"\n{'=' * 60}")
    if tracked_bad:
        print(f"{len(tracked_bad)} already-tracked violation(s) — REPORTED, not "
              f"gated. `git rm --cached <path>`\ngoing forward is reversible and "
              f"does not touch history or other agents'\nprovenance hashes. They "
              f"do not affect the exit code, so it stays informative.")
    if violations:
        print(f"\n{len(violations)} ACTIONABLE violation(s) in what you are "
              f"about to commit. Fix before committing.")
        return 1
    print("\nclean — nothing you are about to commit violates §13")
    return 0


def selfcheck():
    """H14: the runnable check §12.3 requires, which this module shipped without.

    It was `the one harness module with no test`, and it then died at IMPORT
    time with `NameError: name 're' is not defined` -- committed to HEAD, in
    every lane's §13 pre-commit path, for at least twenty minutes. The checker
    whose job is catching bad commits could not run to catch its own.

    Every case below is a defect this module actually had or a property §13
    actually needs, driven against throwaway repos. The live repo is never
    touched: a checker that can only be tested by breaking the real tree is
    exactly the thing this file warns other lanes about.
    """
    import shutil
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    fails = []

    def ck(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else '  ' + detail}")
        if not cond:
            fails.append(name)

    # 0 · THE DEFECT THAT MOTIVATED THIS ONE. No behavioural test would have
    #     caught it -- the module never got far enough to behave. Only importing
    #     it does, so that is the first check.
    # BY PATH, NOT BY NAME. The first version ran `import githygiene` with cwd
    # set to this directory, which imports whatever `githygiene.py` is installed
    # THERE -- so a copy of this module with `import re` deleted still passed,
    # because the probe imported the healthy original. Family C: the artifact is
    # not what you think. Found by falsifying this very check (falsify.py G1),
    # which is the only way it could have been found: it passed both before and
    # after the defect, so no amount of running it green proved anything.
    me = os.path.abspath(__file__)
    r = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys; runpy.run_path(sys.argv[1], run_name='probe')", me],
        capture_output=True, text=True)
    ck("module imports in a fresh interpreter", r.returncode == 0,
       r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "")

    def run_in(setup):
        d = tempfile.mkdtemp(prefix="ghsc_")
        try:
            for c in (["git", "init", "-q"],
                      ["git", "config", "user.email", "t@t"],
                      ["git", "config", "user.name", "t"]):
                subprocess.run(c, cwd=d, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            setup(d)
            p = subprocess.run([sys.executable, os.path.join(here, "githygiene.py")],
                               cwd=d, capture_output=True, text=True)
            return p.returncode, p.stdout + p.stderr
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def git(d, *a):
        subprocess.run(["git", *a], cwd=d, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stage(d, name, data=b"x"):
        p = os.path.join(d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(name) else None
        open(p, "wb").write(data)
        git(d, "add", name)

    # 1 · POSITIVE CONTROL FIRST. A checker that refuses everything passes every
    #     negative case below while being useless, and that is the shape this
    #     module was in an hour ago -- exit 1 unconditionally.
    rc, out = run_in(lambda d: stage(d, "RESULT.md", b"a finding\n"))
    ck("clean staged text passes", rc == 0, f"rc={rc}")

    # 2 · The three things §13 says must never be committed.
    rc, out = run_in(lambda d: stage(d, "model.gguf"))
    ck("staged model weights fail", rc == 1 and "binary/model" in out, f"rc={rc}")

    rc, out = run_in(lambda d: stage(d, "big.txt", b"0" * (2 * 1024 * 1024)))
    ck("staged oversized file fails", rc == 1 and "exceeds" in out, f"rc={rc}")

    # H35, ATTACKER-1. The case the check above cannot construct, because it
    # leaves the tree copy equal to the staged copy: STAGE the 2 MB, then shrink
    # the TREE copy. The commit still carries 2 MB. Verified RED with the
    # `staged_sizes` block deleted from an isolated copy.
    def _stage_then_shrink(d):
        stage(d, "big.txt", b"0" * (2 * 1024 * 1024))
        open(os.path.join(d, "big.txt"), "wb").write(b"small\n")
    rc, out = run_in(_stage_then_shrink)
    ck("oversized STAGED blob fails even when the tree copy has shrunk",
       rc == 1 and "exceeds" in out, f"rc={rc}")

    # NOTE the assertion, which was wrong first: it demanded the words "build
    # tree", but `.pyc` is caught by the EXTENSION rule before the path rule ever
    # runs. The behaviour was right and the check was too specific about HOW.
    # A check that pins the mechanism instead of the outcome fails on a correct
    # refactor, which is how a suite trains people to delete checks.
    rc, out = run_in(lambda d: stage(d, "__pycache__/x.pyc"))
    ck("staged build tree fails", rc == 1 and "__pycache__/x.pyc" in out, f"rc={rc}")

    # 3 · H14's headline: an already-tracked violation must be REPORTED and must
    #     NOT set the exit code. It was permanent exit 1 on 16 committed
    #     binaries that §13 forbids removing, so the verdict was the same before
    #     and after anything you did -- family A, the instrument cannot produce
    #     the answer.
    def tracked_only(d):
        stage(d, "old.gguf")
        git(d, "commit", "-q", "-m", "a finding was recorded here")
    rc, out = run_in(tracked_only)
    ck("already-tracked violation does NOT gate", rc == 0, f"rc={rc}")
    ck("  ... but is still reported", "already-tracked" in out)

    # 4 · The wrinkle this module documents about itself: `git rm --cached` is
    #     the remedy it prescribes, and it must not be reported as a violation.
    def removal(d):
        stage(d, "old.gguf")
        git(d, "commit", "-q", "-m", "a finding was recorded here")
        git(d, "rm", "-q", "--cached", "old.gguf")
    rc, out = run_in(removal)
    ck("the remedy it prescribes is not a violation", rc == 0, f"rc={rc}")

    # 4b · H71 · §13'S ONLY STATED COMMIT FORM CANNOT EXPRESS THE OPERATION
    #      EVERY CYCLE PERFORMS, AND THESE TWO CASES ARE THE PROOF PLUS THE
    #      RECIPE. §13 says `git commit --only <paths>`, not `git add` then
    #      `git commit`, and gives no other form. `--only` REFUSES an untracked
    #      path, and every cycle here creates a new spike directory. So the
    #      first case asserts the REFUSAL -- if a future git makes `--only`
    #      accept untracked paths, this check goes red and §13's workaround
    #      paragraph can be deleted rather than left as folklore.
    #
    #      These test git's behaviour, not this module's, which is deliberate:
    #      the guardrail H71 adds is a RECIPE in a document, and §12.10 says a
    #      guardrail that is written but not mechanised gets violated again by
    #      its own author. What can go stale here is the recipe, so the recipe
    #      is what is executed.
    def _only_refuses_untracked(d):
        stage(d, "seed.md", b"a finding\n")
        git(d, "commit", "-q", "-m", "a finding was recorded here")
        open(os.path.join(d, "new.md"), "wb").write(b"a new finding\n")
        return subprocess.run(
            ["git", "commit", "--only", "new.md", "-m", "S1: a finding"],
            cwd=d, capture_output=True, text=True)

    d = tempfile.mkdtemp(prefix="ghsc_h71_")
    try:
        for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
                  ["git", "config", "user.name", "t"]):
            subprocess.run(c, cwd=d, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p = _only_refuses_untracked(d)
        ck("H71 · `git commit --only` REFUSES an untracked path",
           p.returncode != 0 and "did not match any file" in (p.stdout + p.stderr),
           f"rc={p.returncode} {(p.stdout + p.stderr).strip()[:80]}")

        # ... and the recipe §13 now carries: intent-to-add YOUR paths, then
        # --only the SAME paths. The co-lane's fully staged file must stay OUT
        # of the commit -- that is the whole reason `--only` is the rule, and a
        # recipe that reintroduced the shared-index bug would be worse than the
        # refusal it works around.
        open(os.path.join(d, "co_lane.md"), "wb").write(b"another lane's work\n")
        subprocess.run(["git", "add", "co_lane.md"], cwd=d, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["git", "add", "-N", "new.md"], cwd=d, check=True,
                       stdout=subprocess.DEVNULL)
        p2 = subprocess.run(["git", "commit", "--only", "new.md",
                             "-m", "S1: a finding was recorded here"],
                            cwd=d, capture_output=True, text=True)
        files = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"],
                               cwd=d, capture_output=True, text=True).stdout.split()
        ck("H71 · `git add -N` then `--only` commits the new file",
           p2.returncode == 0 and "new.md" in files,
           f"rc={p2.returncode} files={files}")
        ck("H71 · ... and leaves a co-lane's STAGED file out of it",
           "co_lane.md" not in files, f"files={files}")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # 5 · Subject quality, checked as a function since it is pure.
    ck("weak subject rejected", bool(check_subject("wip")))
    ck("finding subject accepted",
       not check_subject("A18 audit: the 29x advantage is 1.09x at real sizes"))

    # 6 · Trailer value validation (the sibling lane's finding): a callsign must
    #     look like a callsign, and "self" is not a reviewer.
    ck("topic label rejected as a callsign", check_callsign("mutation-detection") is None)
    ck("callsign accepted and case-folded", check_callsign("agent-1") == "AGENT-1")
    ck("'self' is not a reviewer", "SELF" in NOT_A_REVIEWER)

    print()
    if fails:
        print(f"githygiene selfcheck: {len(fails)} FAILED — {', '.join(fails)}")
        return 1
    print("githygiene selfcheck: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else main())
