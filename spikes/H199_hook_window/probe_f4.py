#!/usr/bin/env python3
"""H199 F4 - PRECISION OF THE POSITIONAL DETECTOR, the measurement that decides
whether a `commit-msg` injection may WRITE the `Carries:` trailer or may only
REPORT it.

F4 as preregistered (CHANNEL.md, ok-1 cycle 29): *fires when the anchored
positional detector names a lane on a constructed line that lane did not author
-- quoted line, indented continuation, alias pair, callsign mid-sentence - then
injection can false-accuse and ships REPORT-ONLY, honouring H180's F1 rather
than rewriting it.*

ASSERTIONS RECORD THE MEASURED BEHAVIOUR, NOT THE DESIRED ONE, so this file is
GREEN today and goes RED when the detector changes. `should_be` states what a
correct detector would return and the divergence count is the finding. A probe
whose normal state is red is a probe nobody can wire into a runner.

TWO PARTS, because a constructed counterexample shows a thing is POSSIBLE and
says nothing about how often it is REAL, and this repo has published the first
as if it were the second:

  PART 1  constructed shapes, run through the SHIPPED `authors_of`
  PART 2  how often that shape occurs in the REAL `CHANNEL.md`

PART 2's FIRST DRAFT WAS THE ERROR IT WAS WRITTEN TO AVOID. It counted any line
whose field 2 was not id-shaped as prose, got 73/576 = 12.7%, and every one of
the eight sampled - `CLAIM architect-lane CLIENT-3`, `DONE G25-no_death AGENT-2`,
`ATTACK cycle4 AGENT-1` - was a CORRECT attribution with a hyphenated label in
field 2. That number measured labels, not false accusations, and as a headline it
would have been Family E. Both crisp shapes are counted separately below and the
loose one is reported as the UPPER BOUND it is.

Run: python3 spikes/H199_hook_window/probe_f4.py
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
import carriescheck as cc          # THE SHIPPED MODULE, not a copy

fail = 0


def ck(name, got, want):
    global fail
    if got == want:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} (want {want!r}, got {got!r})")
        fail += 1


# ---------------------------------------------------------------- PART 1
# line, the lane that WROTE it, what the detector RETURNS today, what a correct
# detector would return.
CASES = [
    ("plain author line -- the arm that can fail, so a blanket-empty detector "
     "cannot pass this suite",
     "DONE H199 ok-1 the row is closed", "ok-1", {"ok-1"}, {"ok-1"}),
    ("quoted with '> ' prefix: the ^ anchor holds",
     "> DONE H199 ok-1 the row is closed", "ATTACKER-1", set(), set()),
    ("indented continuation: the ^ anchor holds",
     "  DONE H199 ok-1 the row is closed", "ATTACKER-1", set(), set()),
    ("REJECT, whose grammatical object is the OTHER lane",
     "REJECT H199 ok-1 -- the window is 50ms, not zero", "ATTACKER-1",
     {"ok-1"}, set()),
    ("ATTACK, same shape",
     "ATTACK H23 ok-1 vocabulary check reads both sets from one file",
     "ATTACKER-1", {"ok-1"}, set()),
    ("CORRECTED, same shape",
     "CORRECTED H180 AGENT-1 trailer was omitted, not over-declared", "ATOM-3",
     {"AGENT-1"}, set()),
    ("callsign MID-SENTENCE in field 3 -- ordinary English after a verb word",
     "NOTE the ok-1 lane found this first", "AGENT-2", {"ok-1"}, set()),
    ("possessive mid-sentence: (?![\\w-]) does not exclude an apostrophe",
     "FINDING in ok-1's probe the guard was vacuous", "ATTACKER-1",
     {"ok-1"}, set()),
    ("alias pair collapses to the canonical lane, correctly",
     "DONE H201 CLIENT-3 elder read", "ATOM-3", {"ATOM-3"}, {"ATOM-3"}),
]

print("--- PART 1: constructed shapes, against the shipped authors_of ---")
diverge = []
for label, line, writer, observed, should_be in CASES:
    got = cc.authors_of("CHANNEL.md", [line])
    ck(f"P1 {label}", got, observed)
    if observed != should_be:
        diverge.append((label, line, writer, observed))

# ---------------------------------------------------------------- PART 2
print("\n--- PART 2: how often the offending shapes occur in the real CHANNEL.md ---")
chan = (ROOT / "CHANNEL.md").read_text(errors="replace").splitlines()
p1, p2 = cc.CHANNEL_PATTERNS

# SHAPE A -- ordinary English in field 2. A tiny closed stoplist, because it is
# checkable by eye; a broad "not id-shaped" test measured labels instead (above).
ENGLISH = {"the", "a", "an", "in", "on", "of", "that", "this", "from", "for",
           "and", "but", "to", "by", "is", "was", "it", "my", "your", "their",
           "his", "her", "its", "with", "at", "as", "not"}
# SHAPE B -- a verb whose grammatical object is a lane. `CLAIM`/`DONE`/`FILED`
# name the lane DOING the work; these name the lane the work is ABOUT.
OBJECT_VERBS = {"REJECT", "ATTACK", "CORRECTED", "CORRECTION", "FINDING", "NOTE"}
ID = re.compile(r"^(?:[A-Z]+[-\w]*\d[\w-]*|[a-z][\w/]*-[\w/]*|\d+)$")

matched = shape_a = shape_b = loose = 0
sa, sb = [], []
for ln in chan:
    m = p1.match(ln) or p2.match(ln)
    if not m:
        continue
    matched += 1
    parts = ln.split()
    verb, field2 = parts[0], (parts[1] if len(parts) > 1 else "")
    if field2.lower() in ENGLISH:
        shape_a += 1
        if len(sa) < 5:
            sa.append((m.group(1), ln[:110]))
    if verb in OBJECT_VERBS:
        shape_b += 1
        if len(sb) < 5:
            sb.append((m.group(1), ln[:110]))
    if not ID.match(field2) and field2.lower() not in ENGLISH:
        loose += 1

print(f"lines the detector attributes at all                    : {matched}")
print(f"  SHAPE A  field 2 is an English function word          : {shape_a}")
print(f"  SHAPE B  verb's object is a lane (REJECT/ATTACK/...)   : {shape_b}")
print(f"  loose upper bound (field 2 neither id-shaped nor English): {loose}")
for named, ln in sa:
    print(f"    A -> names {named}: {ln}")
for named, ln in sb:
    print(f"    B -> names {named}: {ln}")

# Family B: an arm whose healthy answer is a zero cannot tell you it ran. This
# probe's sibling A4 in probe.sh failed exactly this way an hour before.
ck("P2-guard the corpus arm actually matched lines", matched > 0, True)

print(f"\nF4 VERDICT: {'FIRES' if diverge else 'does not fire'} on construction "
      f"-- {len(diverge)} shape(s) name a lane that did not write the line")
for label, line, writer, got in diverge:
    print(f"    {writer} wrote: {line!r}  -> detector says {sorted(got)}")

print(f"\nchecks failed: {fail}")
sys.exit(1 if fail else 0)
