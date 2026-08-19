#!/usr/bin/env python3
"""versioncheck.py v1 — H180. A file's version HEADER must equal its newest block.

CLASS OF DEFECT REMOVED
-----------------------
*A version number maintained in TWO places on a file that five lanes edit
concurrently, where only one of the two is the answer anyone reads.*

MISSION_LOOP §12.7 requires a version bump with a rationale block naming the
defect removed. In practice the BLOCK gets added and the one-line HEADER does
not — so the single line written to answer "which version am I running?" is the
line that goes stale.

EARNED TWICE IN ONE COMMIT, AND THE SECOND TIME BY THE FIX FOR THE FIRST.
`5472cb9` (mine) removed exactly this defect from `commit_scoped.sh`, whose
header said v2 over v3/v4/v5 blocks -- and shipped a header saying **v6** over
ok-1's **v7** block, which had landed in the shared working tree between my edit
and my `git add`. So the rule cannot be held by hand: `git add <path>` stages the
WORKING TREE, and on a file five lanes edit there is no window in which a
co-lane's version block does not ride along.

MEASURED ON THIS TREE AT v1 -- FOUR FILES, ONLY ONE OF THEM MINE:
    check_live_launcher.sh   header v1   newest block v3
    commit_scoped.sh         header v6   newest block v7   (fixed by this row)
    test_autoloop_local.sh   header v1   newest block v2
    headcheck.sh             header v2   newest block v1   <- INVERSE drift

The inverse case is reported separately and is NOT the same fault: a header
AHEAD of the blocks means a bump was made without a rationale block, which §12.7
also forbids, but for the opposite reason. Reporting them as one number would be
the "grouped by symptom, not by family" error §12.11 names.

Exit 0 = every header agrees with its newest block, 1 = drift found,
3 = refused (no harness directory).
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# `# <name>.sh v3 — ...`  in the first few lines
HEADER = re.compile(r"^#\s*(\S+?)\s+v(\d+)\b")
# `# ==== v3, H108 ... ` or `# v7, H183 ...`
BLOCK = re.compile(r"^#\s*={0,6}\s*v(\d+)[,\s]")

EXTS = (".sh", ".py", ".hook")
# `cat > x <<'F'` ... `F` — a heredoc's CONTENT is data, not this file's comments.
HEREDOC_OPEN = re.compile(r"<<-?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?")
HEAD_LINES = 8          # a header lives at the top or it is not a header
SCAN_LINES = 600


def strip_heredocs(lines):
    """Blank out heredoc BODIES.

    Earned immediately: v1 flagged its own `test_versioncheck.sh` at "header v1,
    newest block v4" because the suite's FIXTURES contain lines like
    `# ==== v4, H997 ====` inside `cat > f <<'F'` blocks. A checker that reads
    another file's data as its own metadata is family B -- the instrument
    reporting fiction -- and excluding test files instead would have been
    weakening a gate to pass it.
    """
    out, term = [], None
    for ln in lines:
        if term is None:
            m = HEREDOC_OPEN.search(ln)
            # only treat as a heredoc opener on a line that is not itself a comment
            if m and not ln.lstrip().startswith("#"):
                term = m.group(1)
                out.append(ln)
                continue
            out.append(ln)
        else:
            if ln.strip() == term:
                term = None
            out.append("")          # heredoc body is data, not metadata
    return out


def scan(root: str = None):
    root = root or HERE
    if not os.path.isdir(root):
        sys.stderr.write(f"versioncheck: REFUSING — no such directory {root}\n")
        sys.exit(3)
    stale, ahead, checked = [], [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".venv", "__pycache__")]
        for fn in sorted(filenames):
            if not fn.endswith(EXTS):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()[:SCAN_LINES]
            except OSError:
                continue
            lines = strip_heredocs(lines)
            stem = fn.split(".")[0]
            hdr = None
            for ln in lines[:HEAD_LINES]:
                m = HEADER.match(ln)
                if m and stem in m.group(1):
                    hdr = int(m.group(2))
                    break
            if hdr is None:
                continue          # no version header is not a defect; many files have none
            checked += 1
            blocks = [int(m.group(1)) for ln in lines if (m := BLOCK.match(ln))]
            if not blocks:
                continue
            top = max(blocks)
            if top > hdr:
                stale.append((path, hdr, top))
            elif top < hdr:
                ahead.append((path, hdr, top))
    return stale, ahead, checked


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else None
    stale, ahead, checked = scan(root)
    print(f"versioncheck v1 — {checked} versioned file(s) checked")
    if not stale and not ahead:
        print("OK — every version header equals its newest rationale block")
        return 0
    if stale:
        print(f"\nSTALE HEADER — the body carries a NEWER version than the header announces "
              f"({len(stale)}):")
        for p, h, t in stale:
            print(f"  {p}\n      header says v{h}, newest block is v{t}")
        print("\n  A lane resolving \"which version am I running?\" from the one line written")
        print("  to answer that gets an answer N revisions stale (MISSION_LOOP §12.7).")
    if ahead:
        print(f"\nHEADER AHEAD OF ITS BLOCKS — a bump with no rationale block ({len(ahead)}):")
        for p, h, t in ahead:
            print(f"  {p}\n      header says v{h}, newest block is v{t}")
        print("\n  Reported separately on purpose: §12.7 forbids this too, but for the")
        print("  OPPOSITE reason, and §12.11 says group by family rather than symptom.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
