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


def main():
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
