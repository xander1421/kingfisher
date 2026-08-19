#!/usr/bin/env python3
"""H199 arm C - THE ROW'S OWN FALSIFIER, which no cycle had run.

ATOM-3 wrote it into the H199 row and it is the reason the row exists:

  *"FALSIFIER: if trailer and post-commit recomputation agree across the last
  ~50 `Carries:`-bearing commits, this is a one-off race and the row closes as a
  HABIT note, not a script defect. Measure before writing code."*

I wrote code first (arms A and B) and am running this second, which is the wrong
order and is recorded rather than hidden.

METHOD: for every commit in the window carrying a `Carries:` trailer, recompute
`carriescheck.py <Atom> <sha> --trailer` - the SHIPPED module against the LANDED
object, which is the only reading with no window in it - and compare to the
trailer the message declares. Three outcomes, counted separately because they
are three different defects and H180/H199 are two of them:

  AGREE          the hand-typed trailer was right
  OVER-DECLARED  message names a lane the commit does not carry   (H199)
  UNDER-DECLARED message misses a lane the commit does carry      (H180)

CORRECTED BEFORE ITS FIRST NUMBER WAS PUBLISHED, AND THE WITHDRAWN NUMBER IS
KEPT BECAUSE IT IS THE POINT. v1 read the declaration by grepping the whole
commit body for `^Carries:` and splitting the rest of the line on whitespace. It
reported **37 trailers, 26 over-declared** - and the over-declared list contained
`declared=['.', '35', '42', 'Run', 'before', 'commit:', ...]`, which is not a
lane list, it is a SENTENCE. Three commits in that count (`8ec3427f`,
`9ae3da9f`, `b8e27b14`) merely DISCUSS the trailer in prose; `git
interpret-trailers --parse` reports no `Carries:` trailer on any of them. A
number computed by a parser that cannot tell a trailer from a sentence about
trailers is Family B, and 26/37 would have been this cycle's headline.

SO THE DECLARATION IS READ TWO WAYS AND BOTH ARE REPORTED, because the
disagreement between them is itself a finding: `git interpret-trailers --parse`
(git's own definition: the final trailer block) versus `^Carries:` anywhere in
the body, which is what `commit-msg.hook:236` uses to grant the cross-lane
AUTHORISATION. Lane names are then taken as the known-callsign tokens, so a
trailer with a prose tail contributes its lanes and not its adjectives.

THE WINDOW IS PINNED AND PRINTED. `git log -N` moves as five lanes commit;
citing a moving count as a fixed number is a defect this repo has recorded
(DECISIONS.log, AGENT-2). The base sha is printed so the number is re-derivable.

Run: python3 spikes/H199_hook_window/probe_c.py
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CC = ROOT / "spikes" / "harness" / "carriescheck.py"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, cwd=ROOT).stdout


head = sh("git", "rev-parse", "HEAD").strip()
shas = sh("git", "log", "-400", "--format=%H").split()
print(f"window pinned at HEAD={head[:8]}, scanning {len(shas)} commits\n")

sys.path.insert(0, str(ROOT / "spikes" / "harness"))
import carriescheck as cc          # the shipped callsign vocabulary, not a copy
KNOWN = re.compile(cc._CS + r"(?![\w-])")


def lanes_in(text):
    return sorted({cc.canon(m.group(0)) for m in KNOWN.finditer(text)})


rows = []
grep_only = []
for s in shas:
    body = sh("git", "show", "-s", "--format=%B", s)
    parsed = subprocess.run(["git", "interpret-trailers", "--parse"],
                            input=body, capture_output=True, text=True,
                            cwd=ROOT).stdout
    trailer = [l for l in parsed.splitlines() if l.startswith("Carries:")]
    grepped = [l for l in body.splitlines() if l.startswith("Carries:")]
    atom = next((l[len("Atom:"):].strip() for l in parsed.splitlines()
                 if l.startswith("Atom:")), None)
    if not atom:
        continue
    if grepped and not trailer:
        grep_only.append((s, atom, grepped[0][:90]))
    if not trailer:
        continue
    declared = lanes_in(" ".join(t[len("Carries:"):] for t in trailer))
    out = subprocess.run([sys.executable, str(CC), atom, s, "--trailer"],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    actual = lanes_in(out[len("Carries:"):]) if out.startswith("Carries:") else []
    rows.append((s, atom, declared, actual))

agree = [r for r in rows if r[2] == r[3]]
over = [r for r in rows if set(r[2]) - set(r[3])]
under = [r for r in rows if set(r[3]) - set(r[2])]

print(f"commits carrying a `Carries:` trailer in the window : {len(rows)}")
print(f"  AGREE                                            : {len(agree)}")
print(f"  OVER-DECLARED  (H199's direction)                : {len(over)}")
print(f"  UNDER-DECLARED (H180's direction)                : {len(under)}")

for label, rs in (("OVER", over), ("UNDER", under)):
    for s, atom, d, a in rs[:12]:
        print(f"    {label} {s[:8]} Atom={atom:11s} declared={d} actual={a}")

# A run that scanned nothing prints three clean zeros and reads as "no defect
# found". Family B, and this spike's arm A shipped that bug an hour ago.
if not rows:
    print("\nREFUSING: no `Carries:`-bearing commit in the window - "
          "this run measured NOTHING and its zeros are not evidence.")
    sys.exit(2)

verdict = ("AGREE ACROSS THE WINDOW - the row closes as a HABIT note"
           if not over and not under else
           "DISAGREEMENT PRESENT - not a one-off race; the row is a script defect")
print(f"\nROW FALSIFIER: {verdict}")

# The two readers, and the gap between them. `commit-msg.hook:236` grants the
# cross-lane authorisation on `grep -qi "^Carries:.*$owner"`; git grants trailer
# status only inside the final block. Every commit below satisfies the hook's
# reader and carries no trailer at all by git's.
print(f"\nREADER DISAGREEMENT: {len(grep_only)} commit(s) have a `^Carries:` line "
      f"the hook's grep accepts and `git interpret-trailers --parse` does not")
for s, atom, ln in grep_only[:10]:
    print(f"    {s[:8]} Atom={atom:11s} {ln}")
