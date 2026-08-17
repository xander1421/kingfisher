#!/usr/bin/env python3
"""Citations in commits: verify they resolve, then emit them as graph triples.

A commit message says WHAT changed. It does not say what AUTHORITY says the old
code was wrong, and "I believed X about the tool" is how most of this repo's
defects happened:

  * `git diff --cached --name-only` was assumed not to list deletions. `man
    git-diff` says --diff-filter selects "Deleted (D)" among the status letters,
    so deletions ARE listed by default. One man page would have prevented it.
  * `score(..., cap=MAX_PAIRS)` was assumed to follow a monkeypatched global.
    Python binds default arguments at DEFINITION time. One language reference
    line would have prevented it.
  * a Cargo FEATURE was assumed not to change `fuel_used`. It does, 107 vs 580.

So a fix commit carries `Cites:` lines, and THIS SCRIPT CHECKS THEY RESOLVE. An
unverifiable citation is worse than none: it looks like evidence.

  Cites: man:git-diff "Deleted (D)"
  Cites: file:analysis/GUARDRAILS.md "A15"
  Cites: url:https://example/spec corpus/refs/spec.txt

VERIFICATION, and each kind can fail:
  man   the page must exist AND contain the quoted anchor. A page that exists
        but does not say the thing is a FAIL, not a pass -- that is the whole
        point, since the failure mode is misremembering what a tool does.
  file  the path must exist and contain the anchor.
  url   a LOCAL COPY must exist at the given path. The URL is recorded for
        provenance; the copy is what is checked, because a remote that changes
        under you is not a citation.

LICENCE (§7): we store an EXCERPT and a hash, never a wholesale copy of a
third-party document. Man pages and vendor docs are not ours to redistribute,
and `elders/` is gitignored for exactly that reason.

The triples go to corpus/graph.tsv so the G-series miner can run on this repo's
own history: which atom made a change, who reviewed it, what authority it cited,
and which defect class it corrected. That is a real knowledge graph built out of
our own corrections rather than a downloaded benchmark.

v2 (AGENT-2, G35, 2026-08-17) — THE DEFECT REMOVED
--------------------------------------------------
v1 verifies `Cites:` lines. **It only ever reads COMMIT TRAILERS, so an
attribution carrying NO `Cites:` line at all is invisible to it** — and that is
the shape the defect actually took. G30's RESULT.md published a nine-row table
of external benchmark figures to three decimals under a column headed
"Notes / Attribution", attributed in-text to five surnames, with no `Cites:`
line anywhere and no excerpt under `corpus/`. v1 reports such a commit as having
zero citations, which it prints as *"NO CITATIONS FOUND. Not a pass — nothing
was checked."* That sentence is right and nobody was reading it.

MEASURED, and it is why this is worth a mechanism rather than a rule: the
withdrawal of those figures took twenty minutes to be overtaken. G30 §3 was
withdrawn at 16:05; by 16:10 `spikes/G34_length1_and_constants/` had
`f3_fires = (mrr_full < 0.1980)` — one of the withdrawn figures, pre-registered
as a pass/fail threshold in another spike's falsifier.

`attributions` scans prose and source for author-year attributions and reports
each one that resolves to nothing stored. §13.2: an unverifiable citation is
worse than none, because it looks like evidence.

IT REPORTS, IT DOES NOT GATE, and that is deliberate. This file is in no hook,
it is not this lane's, and wiring a newly-authored check into every lane's
commit path is the hazard filed as H33/H54 — a gate that a non-author trips and
only the author may fix. The count goes to the fleet first; gating is a decision
for whoever owns the harness, not a side effect of this edit.

WHAT WAS TRIED AND REFUSED, recorded so it is not re-attempted: the general form
— *a number in a RESULT.md with nothing behind it* — is NOT decidable this way.
Measured over 48 tracked spikes: 1070 cited decimals, 433 with no match in any
artifact. That figure is dominated by legitimately DERIVED quantities (ratios,
percentages, means) which no artifact would store, and it is not published
anywhere. Family A, decidable from the design.
"""

import os
import re
import subprocess
import sys

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True).stdout.strip()
CORPUS = os.path.join(ROOT, "corpus")
CITE_RE = re.compile(r"^\s*Cites:\s*(\S+?):(.+)$", re.M)
TRAILER_RE = re.compile(r"^\s*(Atom|Reviewed-By|Claude-Session):\s*(.+)$", re.M)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def anchor_of(rest):
    """`git-diff "Deleted (D)"` -> ("git-diff", 'Deleted (D)')"""
    m = re.match(r'^\s*(\S+)\s*(?:"([^"]*)")?\s*(\S+)?\s*$', rest.strip())
    if not m:
        return rest.strip(), None, None
    return m.group(1), m.group(2), m.group(3)


def verify(kind, rest):
    target, anchor, extra = anchor_of(rest)
    if kind == "man":
        env = dict(os.environ, MANWIDTH="80")
        page = subprocess.run(["man", target], capture_output=True, text=True,
                              env=env).stdout
        if not page.strip():
            return False, f"no man page '{target}'"
        if anchor and anchor not in re.sub(r"\x08.", "", page):
            return False, f"man {target} does not contain {anchor!r}"
        return True, f"man {target}" + (f" contains {anchor!r}" if anchor else "")
    if kind == "file":
        p = os.path.join(ROOT, target)
        if not os.path.exists(p):
            return False, f"missing file {target}"
        if anchor and anchor not in open(p, errors="ignore").read():
            return False, f"{target} does not contain {anchor!r}"
        return True, f"{target}" + (f" contains {anchor!r}" if anchor else "")
    if kind == "url":
        if not extra:
            return False, "url citation needs a local copy path"
        p = os.path.join(ROOT, extra)
        if not os.path.exists(p):
            return False, (f"no local copy at {extra} — a remote that can "
                           f"change under you is not a citation")
        return True, f"local copy {extra}"
    return False, f"unknown citation kind {kind!r}"



# --------------------------------------------------------------- v2, G35
# An author-year attribution in prose or source. Deliberately NOT a general
# "citation" regex: this matches the shape that carries a NUMBER in this repo —
# `[Meilicke 2019]`, `(Bordes et al., 2013)`, `Sun et al., 2019` — because the
# defect being caught is an external FIGURE presented as sourced.
ATTRIB_RE = re.compile(
    r"\[([A-Z][A-Za-zÀ-ÿ\-]+)\s+(?:et\s+al\.?,?\s*)?((?:19|20)\d{2})\]"
    r"|\(([A-Z][A-Za-zÀ-ÿ\-]+)\s+et\s+al\.,?\s*((?:19|20)\d{2})\)"
    r"|(?<![\w\[(])([A-Z][A-Za-zÀ-ÿ\-]+)\s+et\s+al\.,?\s+((?:19|20)\d{2})")

SCAN_EXT = (".md", ".py", ".txt")


def _corpus_index(root):
    """Every surname this workspace can actually vouch for.

    An attribution resolves only if the workspace HOLDS something: an excerpt
    file under corpus/ whose name or body carries the surname, or a line in
    corpus/CITATIONS.md. A name appearing only in the spike that cites it is
    not evidence -- that is the whole failure being caught.
    """
    text, names = "", []
    for base, dirs, files in os.walk(os.path.join(root, "corpus")):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for n in files:
            if not n.endswith((".md", ".txt")):
                continue
            names.append(n)
            fp = os.path.join(base, n)
            try:
                if os.path.getsize(fp) < 2_000_000:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        text += f.read()
            except OSError:
                pass
    return text, names


def attributions(root=".", paths=None):
    """(unresolved, total). Reports; the caller decides what to do about it."""
    corpus_text, corpus_names = _corpus_index(root)
    targets = []
    if paths:
        targets = list(paths)
    else:
        for base, dirs, files in os.walk(os.path.join(root, "spikes")):
            dirs[:] = [d for d in dirs
                       if d not in {"run", "__pycache__", "target", "node_modules"}]
            targets += [os.path.join(base, n) for n in files if n.endswith(SCAN_EXT)]

    found = {}
    for fp in targets:
        try:
            if os.path.getsize(fp) > 2_000_000:
                continue
            with open(fp, encoding="utf-8", errors="ignore") as f:
                body = f.read()
        except OSError:
            continue
        for m in ATTRIB_RE.finditer(body):
            g = [x for x in m.groups() if x]
            if len(g) != 2:
                continue
            surname, year = g
            found.setdefault((surname, year), set()).add(os.path.relpath(fp, root))

    unresolved = []
    for (surname, year), where in sorted(found.items()):
        hit = surname in corpus_text or any(surname.lower() in n.lower()
                                            for n in corpus_names)
        if not hit:
            unresolved.append((surname, year, sorted(where)))

    for surname, year, where in unresolved:
        print(f"  UNSOURCED   {surname} {year}")
        for w in where[:4]:
            print(f"              -> {w}")
    print(f"\n{len(found)} attribution(s), {len(unresolved)} resolving to "
          f"nothing stored under corpus/")
    if not found:
        print("NO ATTRIBUTIONS FOUND. Not a pass -- nothing was checked.")
    print("REPORT ONLY -- this does not gate. §13.2 is the rule; storing an "
          "excerpt with provenance is the fix.")
    return len(unresolved), len(found)


def selfcheck():
    """Red when the scanner stops distinguishing sourced from unsourced.

    The fixture holds BOTH cases, because a scanner that reports everything
    unsourced would pass a one-case test and be useless. Paths are built from
    parts, never written as literals, so an absent path named here cannot read
    to refcheck as a broken citation of it (ok-1's livechat CLASS 1).
    """
    import shutil as _sh
    import tempfile
    t = tempfile.mkdtemp()
    try:
        cdir = os.path.join(t, "corpus", "refs")
        sdir = os.path.join(t, "spikes", "Z1_fixture")
        os.makedirs(cdir)
        os.makedirs(sdir)
        # STORED: one excerpt the workspace can vouch for
        # EVERY fixture name is built from parts. Written as literals, this
        # file's own source matches ATTRIB_RE and the scanner flags ITSELF --
        # measured, 2 self-hits on the first real run. Same trap, and the same
        # remedy, as refcheck.selfcheck().
        kept, miss, par = "Kn" + "uth", "Nosuch" + "name", "Also" + "missing"
        y1, y2, y3 = "19" + "74", "20" + "19", "20" + "13"
        with open(os.path.join(cdir, "stored" + "-ref.txt"), "w") as f:
            f.write(f"excerpt from {kept} et al. {y1}, stored with provenance\n")
        with open(os.path.join(sdir, "RESULT" + ".md"), "w") as f:
            f.write(f"backed by [{kept} {y1}] and unbacked by [{miss} {y2}]\n"
                    f"also ({par} et al., {y3}) in parentheses\n")
        n_unres, n_tot = attributions(root=t)
        fails = []
        if n_tot != 3:
            fails.append(f"expected 3 attributions parsed, got {n_tot}")
        if n_unres != 2:
            fails.append(f"expected 2 unsourced, got {n_unres}")
        # NEGATIVE CONTROL: with the corpus emptied, the STORED one must flip
        _sh.rmtree(os.path.join(t, "corpus"))
        os.makedirs(os.path.join(t, "corpus"))
        n2, _ = attributions(root=t)
        if n2 != 3:
            fails.append(f"expected all 3 unsourced once corpus is empty, got {n2}")
        for f_ in fails:
            print(f"  BAD  {f_}")
        if not fails:
            print("selfcheck: resolved and unresolved attributions are "
                  "distinguished, and the distinction depends on corpus/")
        return 1 if fails else 0
    finally:
        _sh.rmtree(t, ignore_errors=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        return selfcheck()
    if len(sys.argv) > 1 and sys.argv[1] == "attributions":
        root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        root = root if os.path.isdir(os.path.join(root, "spikes")) else "."
        unresolved, _ = attributions(root=root)
        return 0                      # REPORTS, does not gate. See the v2 block.
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40
    log = sh("git", "log", f"-{n}", "--format=%H%x01%s%x01%b%x02")
    triples, bad, seen = [], 0, 0
    for entry in log.split("\x02"):
        if not entry.strip():
            continue
        sha, subj, body = (entry.strip().split("\x01") + ["", ""])[:3]
        short = sha[:12]
        for key, val in TRAILER_RE.findall(body):
            triples.append((short, key.lower().replace("-", "_"), val.strip()))
        if re.match(r"^(CORRECTED|RETRACTED)", subj):
            triples.append((short, "corrects", subj.split(":")[0]))
        for kind, rest in CITE_RE.findall(body):
            seen += 1
            ok, detail = verify(kind, rest)
            cid = f"{kind}:{anchor_of(rest)[0]}"
            triples.append((short, "cites", cid))
            triples.append((cid, "kind", kind))
            if not ok:
                bad += 1
                print(f"  UNRESOLVED  {short}  {kind}:{rest.strip()}\n"
                      f"              -> {detail}")
            else:
                print(f"  ok          {short}  {detail}")

    os.makedirs(CORPUS, exist_ok=True)
    out = os.path.join(CORPUS, "graph.tsv")
    with open(out, "w") as f:
        for s, p, o in triples:
            f.write(f"{s}\t{p}\t{o}\n")

    preds = {}
    for _, p, _ in triples:
        preds[p] = preds.get(p, 0) + 1
    print(f"\n{seen} citation(s) over {n} commits, {bad} unresolved")
    print(f"{len(triples)} triples -> corpus/graph.tsv")
    for p, c in sorted(preds.items(), key=lambda x: -x[1]):
        print(f"   {p:<16}{c}")
    if seen == 0:
        print("\nNO CITATIONS FOUND. Not a pass — nothing was checked. A commit "
              "that\nfixes a defect should say what authority says the old code "
              "was wrong.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
