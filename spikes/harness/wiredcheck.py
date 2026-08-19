#!/usr/bin/env python3
# wiredcheck.py v2 — H256 (v1), H256-attack (v2). ok-1, 2026-08-19.
# Version in a `#` comment as well as the docstring: versioncheck.py reads a
# comment and cannot see a version declared in a docstring (H193).
"""A checker that REFUSES, that nothing runs.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **shipped and wired are different claims, and this harness had no
way to tell them apart.** Three consecutive cycles produced the same shape:

  * H229 — `githygiene.py --only` gates the object a `--only` commit carries, and
    is not called by `commit_scoped.sh`. Said so in the row, on purpose.
  * H243 — `lanelive.sh` fixed five readers of the callsign lock while the module
    itself sat UNTRACKED under a row marked DONE.
  * this row — `trackcheck.py`'s whole subject is *"a DONE row cites evidence that
    exists only on the author's disk"*. It exits **1 on this tree**, and **nothing
    invokes it**, which is why H243 got past every gate in the commit path.

A checker with no caller is not a weak gate. It is a gate that is not there, while
its file, its version header and its queue row all read as though it is.

WHAT IT MEASURES
----------------
Both sides are DERIVED from `git ls-files`; neither is typed. A hand-typed
population is what made H243's census wrong about a file it never opened.

  refusing checker   a `spikes/harness/*.py|sh` whose text can REFUSE
  invocation         `python3 X`, `sh X`, `bash X`, `. X`, `import x`,
                     `from x import` -- in code, with comments stripped, because
                     A MENTION IS NOT A USE (this cost three separate corrections
                     in one session: `scratchcheck.py` refusing a grep whose
                     PATTERN named a write, `sites.py` scoring a helper whose
                     comment said "not for lock pids", and this module's own
                     first draft calling `scratchcheck.py` uninvoked)
  registration       the same command form inside a tracked `.json` / `.plist` /
                     `.yml` / `.toml`. `scratchcheck.py` runs on every Bash call
                     from `settings.json` and no `.sh` mentions it.

THE A22 ANSWER, BECAUSE THIS CHECK HAS A SELF-DECLARATION IN IT
---------------------------------------------------------------
Some of these are meant to have no caller: `bringup.sh` and `send.sh` are typed by
an operator. That is a real category and it cannot be derived, so a module may
declare `Invoked-By: operator` in its header.

**The declaration changes the CATEGORY and can never change whether the module is
listed.** Every declared module is printed, with its declaration quoted, on every
run. So the failure mode of a false declaration is a line a reader can see and
challenge, not a silence -- which is the difference between this and an
allowlist, and the reason H229 refused a path allowlist for its own size gate.

Check that fails when this breaks (§12.3):
  python3 spikes/harness/wiredcheck.py --selfcheck
"""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
# v2, AND IT IS AN ATTACK ON v1 BY ITS AUTHOR ONE CYCLE LATER (§2).
#
# DEFECT 1 REMOVED: **THE PREDICATE THAT DECIDES WHAT A "REFUSING CHECKER" IS WAS
# WRITTEN BY EYE.** v1 matched `REFUSE|sys.exit(1)|exit 1` and nothing else, so a
# module that refuses through `sys.exit(2)`, `raise SystemExit` or `exit 3` was
# not in the population at all -- and a census reports its findings, never its
# population, so the number came out SMALLER AND CLEANER than the truth. Measured
# over the 76 tracked harness modules: **7 can exit non-zero by a route v1 could
# not see**, five of them real checkers (`depcheck.py`, `reprocheck.py`,
# `versioncheck.py`, `prosecite.py`, `channelcount.sh`).
#
# That is `sites.py`'s hand-typed population (H243) one level down: I derived the
# population and then hand-typed the rule that filters it.
#
# DEFECT 2 REMOVED: **THE EXCLUSION LIST WAS SILENT.** `NOT_A_GATE` is still
# hand-typed -- "is this a library or a gate" is a judgement and this module
# cannot make it -- but v1 dropped those files without a word. `sites.py`'s own
# header states the rule v1 broke: *"Excluded hits are PRINTED rather than
# dropped -- a census that hides its exclusions is one whose number cannot be
# checked."* v2 prints every exclusion on every run.
#
# CEILING, named: a module whose `main()` ends `return 2` with no `sys.exit`
# wrapper (`whois.py`, `registry.py`) is still outside the population. Both are
# lookups whose non-zero is an error path rather than a verdict, so the omission
# is defensible -- but it is an omission, not an absence, and it is stated here
# instead of being invisible.
NOT_A_GATE = re.compile(r'/(test_|[a-z_]*mutants|install_hooks|lanelive|kfcheck'
                        r'|edits|power|instrument|units|provenance)')
REFUSES = re.compile(r'REFUSE|sys\.exit\((?!0\))|raise SystemExit'
                     r'|(?<![\w.])exit\s+[1-9]')
DECLARED = re.compile(r'^[#\s]*Invoked-By:\s*(\S+)(.*)$', re.M)


def uncomment(text):
    """Drop `#` comments. Approximate on purpose: a `#` inside a string can only
    SHRINK a match, which is the safe direction for a rule that decides a module
    IS invoked."""
    return "\n".join(l.split("#", 1)[0] for l in text.split("\n"))


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def tracked(root):
    out = subprocess.run(["git", "ls-files"], cwd=root,
                         capture_output=True, text=True).stdout
    return [p for p in out.split("\n") if p]


def invocation_re(basename):
    stem = basename.rsplit(".", 1)[0]
    return re.compile(
        r'(?:python3?|sh|bash)\s+\S*' + re.escape(basename)
        + r'|^\s*\.\s+\S*' + re.escape(basename)
        + r'|(?:^|\n)\s*(?:import\s+' + re.escape(stem) + r'\b'
        + r'|from\s+' + re.escape(stem) + r'\s+import)', re.M)


def survey(root):
    """(gates, findings) — every refusing harness checker and how it is reached."""
    files = tracked(root)
    harness = [f for f in files
               if re.match(r'spikes/harness/[a-z_0-9]+\.(py|sh)$', f)
               and REFUSES.search(read(os.path.join(root, f)))]
    gates = [f for f in harness if not NOT_A_GATE.search(f)]
    excluded = [f for f in harness if NOT_A_GATE.search(f)]
    code = {f: read(os.path.join(root, f)) for f in files
            if f.endswith((".py", ".sh", ".hook")) and not f.startswith("elders/")}
    conf = {f: read(os.path.join(root, f)) for f in files
            if f.endswith((".json", ".plist", ".yml", ".yaml", ".toml"))}
    findings = []
    for g in gates:
        base = os.path.basename(g)
        pat = invocation_re(base)
        callers = sorted({os.path.basename(f) for f, t in code.items()
                          if f != g and not f.startswith("spikes/H")
                          and "test_" not in os.path.basename(f)
                          and pat.search(uncomment(t))})
        regs = sorted({os.path.basename(f) for f, t in conf.items()
                       if pat.search(t)})
        text = read(os.path.join(root, g))
        m = DECLARED.search(text)
        # F2 FIRED AND THIS IS WHAT IT BOUGHT. `selfcheckall.py` does not name
        # its modules -- it DISCOVERS every `spikes/harness/*.py` carrying a
        # `'--selfcheck'` literal and runs it with that flag. So a static search
        # for `python3 <name>` reports "reached by nothing" for a module that is
        # executed every 600 s (H78). The rule below is READ OFF selfcheckall's
        # own discovery predicate, not guessed at.
        #
        # And the distinction it exposes is sharper than the claim it corrects:
        # THE SELFCHECK IS EXERCISED, THE VERDICT IS ASKED FOR BY NOBODY. A green
        # selfcheck reads as "this checker is fine", which is true and beside the
        # point -- nothing ever asks it the question it exists to answer.
        selfcheck_only = (g.endswith(".py")
                          and re.search(r"['\"]--selfcheck['\"]", text) is not None)
        findings.append({
            "path": g,
            "callers": callers,
            "registrations": regs,
            "selfcheck_only": selfcheck_only,
            "declared": (m.group(1) + m.group(2)).strip() if m else None,
        })
    return gates, findings, excluded


def main(root=ROOT):
    gates, findings, excluded = survey(root)
    if not gates:
        print("wiredcheck REFUSES: no refusing checker was found at all. A survey "
              "with an empty population prints a clean zero and tells you nothing.")
        return 2
    asked = [f for f in findings if f["callers"] or f["registrations"]]
    rest = [f for f in findings if f not in asked]
    declared = [f for f in rest if f["declared"]]
    sc_only = [f for f in rest if not f["declared"] and f["selfcheck_only"]]
    orphans = [f for f in rest if not f["declared"] and not f["selfcheck_only"]]

    print(f"wiredcheck: {len(gates)} refusing checker(s) in spikes/harness/ — "
          f"{len(asked)} whose VERDICT something asks for, {len(sc_only)} whose "
          f"SELFCHECK runs and whose verdict nobody asks for, {len(declared)} "
          f"declared, {len(orphans)} reached by nothing at all")
    for f in declared:
        # PRINTED ON EVERY RUN, never summarised away: a self-declaration that is
        # not visible is an allowlist wearing a different word (A22).
        print(f"  DECLARED  {f['path']}  ->  Invoked-By: {f['declared']}")
    for f in sc_only:
        print(f"  VERDICT UNASKED {f['path']}: `selfcheckall.py` discovers it and "
              f"runs `--selfcheck`; nothing ever runs it for its verdict")
    for e in excluded:
        # v2 · PRINTED, never dropped. `NOT_A_GATE` is a judgement this module
        # cannot make, so the reader gets to disagree with it.
        print(f"  EXCLUDED  {e}: matched as a library or fixture, not a gate — "
              f"if that is wrong, this line is where you see it")
    for f in orphans:
        print(f"  NO CALLER {f['path']}: refuses, and no tracked code invokes it, "
              f"no tracked config registers it, and `selfcheckall.py` does not "
              f"discover it")
    if sc_only or orphans:
        print("\nREFUSE: a checker whose verdict nothing asks for is a gate that "
              "is not there,\n        while its file, its version header and its "
              "queue row read as though it is.\n        A GREEN SELFCHECK IS NOT "
              "COVERAGE: it proves the instrument works, not that\n        anyone "
              "ever points it at the tree. Wire the verdict, or declare\n        "
              "`Invoked-By: operator` in the header and be seen doing so.")
    return 1 if (sc_only or orphans) else 0


def selfcheck():
    bad = []
    here = os.path.dirname(os.path.abspath(__file__))

    def ck(name, cond, detail=""):
        if not cond:
            bad.append(f"{name} — {detail}")

    # 1 · A MENTION IS NOT A USE, and this is the check that would have caught
    #     all three of this session's corrections.
    pat = invocation_re("trackcheck.py")
    ck("a bare mention is not an invocation",
       not pat.search(uncomment("# see trackcheck.py for the floor mechanism")),
       "a comment naming the module counted as a caller")
    ck("a mention in live prose is not an invocation",
       not pat.search(uncomment("the row cites trackcheck.py as its evidence")),
       "prose naming the module counted as a caller")
    # ...and the positive control, because a pattern that matches nothing passes
    # every negative case above while being useless.
    ck("`python3 <path>` IS an invocation",
       bool(pat.search("python3 spikes/harness/trackcheck.py || exit 1")))
    ck("`. <path>` IS an invocation",
       bool(invocation_re("lanelive.sh").search(". spikes/harness/lanelive.sh")))
    ck("`from x import y` IS an invocation",
       bool(invocation_re("lanelive.py").search("from lanelive import launcher_alive")))

    # 2 · THE DECLARATION MUST NOT SILENCE THE LISTING. A22: the whole design
    #     rests on a declared module still being surveyed and still being seen.
    #     DRIVEN, not asserted about the source text -- v1 checked this by
    #     grepping its own file inside a 400-character window, which went red the
    #     first time a comment was added between the two lines. A text check
    #     cannot see behaviour; that is this lane's own standing defect and it
    #     shipped here inside the check written to prevent a different one.
    import shutil
    d = os.path.join(ROOT, ".scratch", "wiredcheck_selfcheck")   # §10, H89
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "spikes", "harness"))
    try:
        subprocess.run(["git", "init", "-q", "."], cwd=d,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        gate = os.path.join(d, "spikes", "harness", "declared_gate.py")
        with open(gate, "w", encoding="utf-8") as f:
            f.write("# Invoked-By: operator — typed by a human, by design\n"
                    "import sys\nsys.exit(1)\n")
        plain = os.path.join(d, "spikes", "harness", "plain_gate.py")
        with open(plain, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(1)\n")
        subprocess.run(["git", "add", "-A"], cwd=d,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        gates, findings, _ = survey(d)
        by = {os.path.basename(f["path"]): f for f in findings}
        ck("a declared module is STILL SURVEYED",
           "declared_gate.py" in by, f"got {sorted(by)}")
        ck("its declaration is read off the header",
           by.get("declared_gate.py", {}).get("declared", "").startswith("operator"),
           f"got {by.get('declared_gate.py', {}).get('declared')!r}")
        ck("an undeclared sibling is surveyed too, so the survey is not empty "
           "for the wrong reason",
           "plain_gate.py" in by, f"got {sorted(by)}")
        # ...and the declaration must not make it WIRED: category, never status.
        ck("a declaration does not fabricate a caller",
           by.get("declared_gate.py", {}).get("callers") == []
           and by.get("declared_gate.py", {}).get("registrations") == [],
           "declaring a module gave it a caller")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # 3 · An empty population refuses rather than reporting a clean zero — this
    #     lane's own defect in four consecutive cycles.
    d = os.path.join(ROOT, ".scratch", "wiredcheck_empty")       # §10, H89
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    try:
        subprocess.run(["git", "init", "-q", "."], cwd=d,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ck("an empty population REFUSES", main(d) == 2,
           "a tree with no checkers printed a clean result")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # 4 · v2 · THE PREDICATE THAT DECIDES WHAT A GATE *IS*. v1 matched
    #     `sys.exit(1)` and `exit 1` only, so `sys.exit(2)`, `raise SystemExit`
    #     and `exit 3` were outside the population -- and a census reports its
    #     findings, never its population, so the number came out cleaner than the
    #     truth. Both directions: a zero exit must NOT count, or everything does.
    for src, want, why in [
            ("import sys\nsys.exit(2)\n", True, "sys.exit(2)"),
            ("raise SystemExit('no')\n", True, "raise SystemExit"),
            ("echo bad\nexit 3\n", True, "exit 3"),
            ("print('REFUSE: nope')\n", True, "the word REFUSE"),
            ("import sys\nsys.exit(0)\n", False, "sys.exit(0) is SUCCESS"),
            ("print('all good')\n", False, "a module with no refusal"),
    ]:
        ck(f"REFUSES matches {why}" if want else f"REFUSES does not match {why}",
           bool(REFUSES.search(src)) == want)

    # 5 · v2 · AN EXCLUSION MUST BE VISIBLE. `NOT_A_GATE` is a judgement this
    #     module cannot make, so dropping a file silently makes the count
    #     uncheckable -- `sites.py`'s own rule, which v1 broke.
    d2 = os.path.join(ROOT, ".scratch", "wiredcheck_excl")       # §10, H89
    shutil.rmtree(d2, ignore_errors=True)
    os.makedirs(os.path.join(d2, "spikes", "harness"))
    try:
        subprocess.run(["git", "init", "-q", "."], cwd=d2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for name in ("test_thing.py", "real_gate.py"):
            with open(os.path.join(d2, "spikes", "harness", name), "w",
                      encoding="utf-8") as f:
                f.write("import sys\nsys.exit(2)\n")
        subprocess.run(["git", "add", "-A"], cwd=d2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        g, fnd, exc = survey(d2)
        ck("a fixture is EXCLUDED, not silently dropped",
           any("test_thing.py" in e for e in exc), f"excluded={exc}")
        ck("...and it is not counted as a gate",
           not any("test_thing.py" in x["path"] for x in fnd), f"findings={fnd}")
        ck("...while a real gate beside it IS counted",
           any("real_gate.py" in x["path"] for x in fnd), f"findings={fnd}")
    finally:
        shutil.rmtree(d2, ignore_errors=True)

    for b in bad:
        print("  FAIL  " + b)
    if not bad:
        print("wiredcheck selfcheck: mention != invocation (3 negatives, 3 positive "
              "controls), a declaration is printed and cannot un-list, an empty "
              "population refuses, REFUSES matches 4 exit routes and not a zero "
              "exit, an excluded fixture is named rather than dropped")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else main())
