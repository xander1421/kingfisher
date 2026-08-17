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
"""

import os
import subprocess
import sys

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
    if staged:
        violations += check_paths(staged, "STAGED")
    else:
        print("nothing staged")

    tracked = sh("git", "ls-files").splitlines()
    violations += check_paths(tracked, "TRACKED (already committed)")

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

    last = sh("git", "log", "-1", "--pretty=%s")
    if last:
        why = check_subject(last)
        print(f"\nLAST COMMIT SUBJECT\n   {last}")
        note = subject_note(last)
        if why:
            print(f"   -> {why}")
            violations.append(("HEAD", why))
        elif note:
            print(f"   -> ok ({note})")
        else:
            print("   -> ok")

    print(f"\n{'=' * 60}")
    if violations:
        print(f"{len(violations)} violation(s). New ones: fix before "
              f"committing.\nAlready-tracked ones: `git rm --cached <path>` "
              f"going forward — reversible,\nand it does not touch history or "
              f"other agents' provenance hashes.")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
