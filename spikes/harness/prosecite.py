#!/usr/bin/env python3
"""prosecite.py v1 — H168. A number in a write-up must exist in an artifact.

CLASS OF DEFECT REMOVED
-----------------------
*A per-item diagnostic printed to STDOUT keyed by an internal index, never
persisted to any artifact, and then attributed to names BY EYE in the write-up.*

Earned, 2026-08-19, by G92 (`spikes/G92_wn18rr_hybrid`). Its routing table is
printed at `run.py:323` as `Rel {p:2d}` — index only, while `r2i` is in scope on
the same line's function. `result.json` records the ROUTING (keyed by name, and
correct) but not the per-relation validation MRRs the routing was chosen from.
So the console scrollback was the only record those numbers ever had, and the
RESULT.md reconstructed them from it: it attributes a RotatE validation MRR of
0.9246 to `_hypernym`, which H164 independently measured at 0.0122 on test,
while `_derivationally_related_form` measured 0.9412. Every figure is real and
each points at the wrong relation — `CLAUDE.md`'s non-mechanisable failure #2,
"correct numbers, wrong attribution".

WHY THIS CHECK AND NOT A NAME CHECK
-----------------------------------
The obvious check — "print names, not indices" — is a style rule at one site and
`MISSION_LOOP` 12.2 says fix the class. The class is not the printing; it is that
**a load-bearing number lived only in a terminal.** A number that reached no
artifact cannot be re-read, diffed, or attacked by another lane, and its
attribution cannot be checked by anyone including its author. So the check is:

    every metric-shaped number asserted in a RESULT.md must appear in SOME
    committed text artifact in this repo.

It is deliberately conservative and under-reports:
  * a number found in ANY spike's artifact passes, because cross-spike baseline
    citation is legitimate and normal (G91 quoting G89's 0.0355);
  * only >=3 decimal places count, so counts, dates, versions and section
    numbers are not metric-shaped and are ignored;
  * trailing-zero variants are matched both ways (0.3550 vs 0.355).

Under-reporting is the right direction: a checker that cries wolf gets bypassed,
and MISSION_LOOP 9's rail says never weaken a gate to pass it.

MEASURED ON THIS TREE AT v1
---------------------------
`python3 spikes/harness/prosecite.py`, 2026-08-19: **63 ghost numbers in 27
spikes**, over 254 RESULT.md and 985 text artifacts. G92 is rank 2 with four of
the five per-relation validation MRRs its write-up quotes (0.9246, 0.8453,
0.4565, 0.3594) — none of which reached any file. The count moves as the tree
does; it is dated and the command reproduces it, rather than being asserted.

**NOT WIRED INTO `selfcheckall.py`, DELIBERATELY.** 63 findings means it would
be RED on the first run and stay red, and H14/H52 already recorded what this
repo does with an always-red gate: it gets bypassed, and then it guards nothing.
This is a SURVEY you run and read, not a gate. It earns promotion to a gate when
the backlog is worked down, and not before.

KNOWN FALSE-POSITIVE MODE, stated because a checker that hides its own is worse
than no checker: a prose figure DERIVED at write-up time — a ratio, a delta, a
percentage computed from two recorded numbers but never itself stored — is
reported as a ghost. That is arguably correct (a derived number is still a
number no run produced) but it is not fraud, and G45's rounded table is the
example. Read the list; do not treat it as an accusation.

**CORRECTION, IN THE SAME CYCLE THAT WROTE THIS FILE, AGAINST ITS OWN FIRST
NUMBER.** v1's header claimed "15 numbers in 6 spikes". That was measured with
`glob("spikes/*/result.json")`, which saw **19 of 252** spikes and treated
`.json` as the only artifact format — while this tree writes 171 `.txt`, 67
`.out` and 827 extensionless artifacts, and spikes such as `S9_timing_rigor` and
`G36_repro_g34` record their numbers in `RUN.txt` and `.out` files. So the first
run reported ghosts that were sitting in a committed artifact all along, and it
is the same failure family as the defect this file exists to catch: **an
instrument that could not see most of the population, reporting a confident
number over the part it could see.** The corrected scan reads every
`.json/.txt/.out/.tsv/.csv/.log/.md` under `spikes/`. Widening the artifact set
cut the count from 140 to 73 and REMOVED 14 spikes from the list; G92's five
survived it unchanged, which is what makes them worth reporting.

Exit 0 = clean, 1 = ghost numbers found, 3 = refused (no inputs).
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))   # spikes/harness -> spikes -> repo


def default_root() -> str:
    """The tree to scan: cwd if it looks like one, else this file's repo.

    v1 derived the root from `__file__` ALONE. `test_prosecite.sh` then built a
    sandbox, `cd`-ed into it, and scanned THE REAL REPO EVERY TIME -- 7 of its 9
    checks were false green, and the one asserting a ghost was found passed only
    because the real G92 happens to contain the same number the sandbox used.
    A suite that cannot address its own fixture is the happy-path-only defect
    the ATTACKER-1 brief names, and it shipped here inside the fix for it.
    """
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "spikes")):
        return cwd
    return REPO


ROOT = default_root()

# metric-shaped: >=3 decimals, not part of a longer token (so 1.2.3 and v1.234x
# and 2026-08-19 do not match)
NUM = re.compile(r'(?<![\w.])(\d+\.\d{3,})(?![\w])')

# Artifact formats this tree actually writes. `.json` alone saw 19 of 252 spikes
# and produced a wrong count -- see the CORRECTION block above.
ARTIFACT_EXT = {".json", ".txt", ".out", ".tsv", ".csv", ".log", ".md"}
SKIP_DIRS = {".venv", "__pycache__", "node_modules", "target"}


def normalise(n: str) -> str:
    """0.3550 and 0.355 are the same number written two ways; 0.3551 is not."""
    t = n.rstrip("0").rstrip(".")
    return t if t else n


# A write-up quotes a ROUNDED figure -- "0.0879" -- while the run records
# 0.08794043... . Requiring an exact match flags every rounded table cell in the
# repo (238 of them, measured), which is noise, not findings. So an artifact
# value backs a prose number if it ROUNDS to it at the precision the prose
# chose. Rounding both ways is the only honest relation between a table cell and
# a recorded value; anything stricter reports formatting as fraud.
ROUND_DP = range(3, 9)


def keys_for_artifact_value(tok: str) -> set:
    """Every prose spelling this recorded value could legitimately appear as."""
    out = {normalise(tok)}
    try:
        v = float(tok)
    except ValueError:
        return out
    for k in ROUND_DP:
        out.add(normalise(f"{v:.{k}f}"))
    return out


def collect_artifact_numbers(root: str) -> tuple[set, int]:
    """Every metric-shaped number in every text artifact under spikes/.

    Returns a SET of normalised numbers, not a blob. v1 substring-searched a
    concatenated blob, which is both O(numbers x bytes) -- the sandbox run timed
    out at 2 minutes -- and WRONG IN THE PERMISSIVE DIRECTION: `0.355 in blob`
    is satisfied by an artifact containing 0.3551, so a prose number that no run
    produced passes because a longer, different number contains its digits.
    A checker whose error mode is a false clean bill of health is worth nothing.

    RESULT.md itself is excluded -- otherwise every prose number trivially
    matches itself and the check can never fire (a control that cannot fail,
    which is the family A defect this harness has shipped four times).
    """
    nums, n = set(), 0
    spikes = os.path.join(root, "spikes")
    for dirpath, dirnames, filenames in os.walk(spikes):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn == "RESULT.md":
                continue
            if os.path.splitext(fn)[1] not in ARTIFACT_EXT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for m in NUM.findall(f.read()):
                        nums |= keys_for_artifact_value(m)
                n += 1
            except OSError:
                continue
    return nums, n


def scan(root: str = None):
    root = root or default_root()
    known, n_json = collect_artifact_numbers(root)
    if n_json == 0:
        sys.stderr.write("prosecite: REFUSING — no text artifacts found under spikes/\n")
        sys.exit(3)

    findings = []
    n_md = 0
    spikes = os.path.join(root, "spikes")
    if not os.path.isdir(spikes):
        sys.stderr.write(f"prosecite: REFUSING — no spikes/ under {root}\n")
        sys.exit(3)
    for name in sorted(os.listdir(spikes)):
        d = os.path.join(spikes, name)
        rm = os.path.join(d, "RESULT.md")
        if not os.path.isdir(d) or not os.path.exists(rm):
            continue
        n_md += 1
        with open(rm, "r", encoding="utf-8", errors="replace") as f:
            md = f.read()
        ghosts = sorted({m for m in NUM.findall(md)
                         if normalise(m) not in known})
        if ghosts:
            findings.append((name, ghosts))
    return findings, n_md, n_json


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else None
    findings, n_md, n_json = scan(root)
    print(f"prosecite v1 — {n_md} RESULT.md scanned against {n_json} text artifacts")
    if not findings:
        print("OK — every metric-shaped number in a RESULT.md exists in some artifact")
        return 0
    total = sum(len(g) for g in (f[1] for f in findings))
    print(f"\nGHOST NUMBERS — asserted in prose, present in no artifact ({total} in {len(findings)} spikes):\n")
    for name, ghosts in sorted(findings, key=lambda f: -len(f[1])):
        print(f"  {name}")
        print(f"      {', '.join(ghosts)}")
    print("\nA number that reached no artifact cannot be re-read, diffed or attacked,")
    print("and its attribution cannot be checked by anyone including its author.")
    print("Remedy: write the table to an artifact keyed by NAME, not to stdout keyed by index.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
