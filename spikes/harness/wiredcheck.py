#!/usr/bin/env python3
# wiredcheck.py v1 — H256. ok-1, 2026-08-19.
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
# Libraries and fixtures: they exit non-zero as MODULES, not as gates.
NOT_A_GATE = re.compile(r'/(test_|[a-z_]*mutants|install_hooks|lanelive|kfcheck'
                        r'|edits|power|instrument|units|provenance)')
REFUSES = re.compile(r'REFUSE|sys\.exit\(1\)|exit 1')
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
    gates = [f for f in files
             if re.match(r'spikes/harness/[a-z_0-9]+\.(py|sh)$', f)
             and not NOT_A_GATE.search(f)
             and REFUSES.search(read(os.path.join(root, f)))]
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
    return gates, findings


def main(root=ROOT):
    gates, findings = survey(root)
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
        gates, findings = survey(d)
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

    for b in bad:
        print("  FAIL  " + b)
    if not bad:
        print("wiredcheck selfcheck: mention != invocation (3 negatives, 3 positive "
              "controls), a declaration is printed and cannot un-list, an empty "
              "population refuses")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else main())
