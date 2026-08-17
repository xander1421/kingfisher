#!/usr/bin/env python3
"""rostercheck.py v1 — H38. One roster, or the fleet has two answers about itself.

THE DEFECT REMOVED
------------------
The harness held TWO lane rosters and they disagreed, so "is X a sanctioned
lane" resolved to two opposite answers depending on which file you opened.
That is §12.4's *"a reference that resolves to TWO things fails the same way"*
applied to a FACT rather than to a pointer, and it is the same no-allocator
class already paid for at callsigns (H8), spike numbers (§13.3) and queue row
ids (H18) -- the first three were answered with prose, H18 with a check.

Measured on this tree at 14:0x, 2026-08-17, three sites:

  * `roster.txt` names AGENT-1, AGENT-2, ATTACKER-1, ATOM-3 and EXCLUDES
    `ok-1`, with a correction block explaining why.
  * `spikes/harness/bringup.sh` defaults `LANES` to
    "AGENT-1 AGENT-2 ATTACKER-1 ok-1" -- ATOM-3 absent, ok-1 present, i.e.
    wrong in BOTH directions -- and launches each through
    `CALLSIGN="$l" ./run_loop.sh`.
  * `run_loop.sh` then REFUSES ok-1 against roster.txt.

So that supervisor starts a lane its own launcher cannot start, reports it as a
start, and never starts the elder. And `run_loop.sh`'s own rationale asserts the
property this breaks: *"roster.txt is the sanction, and it is the same file
bringup.sh starts from, so the two ends cannot drift."* True of the root
`bringup.sh`, which reads roster.txt; false of the second copy, which does not
mention it.

WHAT THIS CHECKS, AND WHAT IT DELIBERATELY DOES NOT
---------------------------------------------------
It checks that no harness file hard-codes a lane set differing from
`roster.txt`. It does **not** decide who belongs on the roster. Sanction is a
fleet-level act; `roster.txt` itself records that a lane talked its way onto it
once, so a checker that resolved the disagreement by picking a side would be the
same defect with a script in front of it. The divergence is reported, loudly,
and the answer is left to whoever owns the roster.

NOT IN THE PRE-COMMIT SET, and that is a decision, not an oversight (H14): it is
RED on this tree right now, and a gate that fires on a known-accepted state every
run is one everyone learns to bypass. It joins the gate when it is green.

  python3 rostercheck.py [--selfcheck]    exit 0 = one roster, no divergence.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# A lane set written into code. The pattern is deliberately narrow: a shell
# assignment whose VALUE is a whitespace-separated run of callsign-shaped words.
# Broader ("any string containing a callsign") would match every rationale block
# in the harness, and this repo is full of prose naming lanes -- a checker that
# fires on prose is one nobody runs (H14).
HARDCODED = re.compile(
    r'^\s*(?:LANES|ROSTER|AGENTS|CALLSIGNS)=(?:\$\{[A-Za-z_]+:-)?"([^"]+)"',
    re.M)

# The callsign shape, from commit-msg.hook's `is_callsign`, PLUS the lower-case
# form -- because the divergence this module exists for is about `ok-1`, and a
# pattern that could not see it would be A21, a test that cannot express its
# verdict. That the two shapes disagree at all is its own open row (H8).
CALLSIGN = re.compile(r'^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+$')


def roster(path=None):
    """The sanctioned set. Comments stripped, first field per line."""
    p = path or os.path.join(ROOT, 'roster.txt')
    if not os.path.exists(p):
        return None
    out = []
    for line in open(p):
        line = line.split('#')[0].strip()
        if line:
            out.append(line.split()[0])
    return out


def harness_files(root=None):
    r = root or ROOT
    out = []
    for rel in ('run_loop.sh', 'bringup.sh', '.claude/hooks/loop_gate.sh'):
        if os.path.exists(os.path.join(r, rel)):
            out.append(rel)
    for d in ('spikes/harness',):
        dp = os.path.join(r, d)
        if os.path.isdir(dp):
            for fn in sorted(os.listdir(dp)):
                if fn.endswith(('.sh', '.py', '.hook')):
                    out.append(os.path.join(d, fn))
    return out


def scan(root=None):
    r = root or ROOT
    rp = os.path.join(r, 'roster.txt')
    sanctioned = roster(rp)
    problems = []
    if sanctioned is None:
        # ABSENT IS A REFUSAL, not a skip. `refcheck.py` v3(b) shipped the other
        # way -- a missing harness file silently narrowed the scan and it still
        # printed a green verdict (family B). The same mistake here would report
        # "one roster" over a tree that has none.
        print('  MISSING roster.txt -- there is no sanctioned set to compare against')
        print('\nREFUSE: the roster is the sanction. Absent, every lane list in the '
              'harness is\n        self-authorised, which is the condition roster.txt '
              'was written to end.')
        return 1
    if not sanctioned:
        problems.append('roster.txt names no lanes')

    for rel in harness_files(r):
        text = open(os.path.join(r, rel), errors='replace').read()
        for m in HARDCODED.finditer(text):
            words = m.group(1).split()
            if not words or not all(CALLSIGN.match(w) for w in words):
                continue          # not a lane set; some other quoted value
            extra = [w for w in words if w not in sanctioned]
            missing = [w for w in sanctioned if w not in words]
            if extra or missing:
                problems.append(
                    f'{rel}: hard-coded lane set {words} diverges from roster.txt '
                    f'{sanctioned}'
                    + (f' -- NOT SANCTIONED: {extra}' if extra else '')
                    + (f' -- MISSING: {missing}' if missing else ''))
            else:
                print(f'  AGREES  {rel} lane set matches roster.txt')

    for p in sorted(set(problems)):
        print('  DIVERGES ' + p)
    if problems:
        print('\nREFUSE: %d lane set(s) disagree with roster.txt. "Is X a sanctioned '
              'lane" now\n        has more than one answer, and the launcher and the '
              'supervisor read\n        different ones -- a supervisor can start a lane '
              'its own launcher refuses.\n        This does NOT say who belongs on the '
              'roster; sanction is not a checker\'s\n        call. Fix the hard-coded '
              'list, or change roster.txt deliberately.' % len(problems))
        return 1
    print('rostercheck: every hard-coded lane set in the harness matches roster.txt')
    return 0


def selfcheck():
    """§12.3. Both directions: planted divergence must fire, agreement must not."""
    import tempfile, shutil, io, contextlib
    bad = []
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, 'spikes', 'harness'))
        open(os.path.join(tmp, 'roster.txt'), 'w').write(
            '# comment\nAGENT-1   # trailing comment\nAGENT-2\n\nATOM-3\n')
        # Assembled from parts for refcheck.py's stated reason: written as a
        # literal, this source would carry a lane list of its own for its own
        # scan to trip over.
        agree = 'LANES=' + '"AGENT-1 AGENT-2 ATOM-3"'
        diverge = 'LANES=${LANES:-' + '"AGENT-1 ok-9"}'
        other = 'MODE=' + '"fast slow"'          # not a lane set: must be ignored
        open(os.path.join(tmp, 'bringup.sh'), 'w').write(f'#!/bin/sh\n{agree}\n{other}\n')
        open(os.path.join(tmp, 'spikes', 'harness', 'sup.sh'), 'w').write(
            f'#!/bin/sh\n{diverge}\n')

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = scan(tmp)
        out = buf.getvalue()

        cases = [
            (rc == 1, 'REFUSES on a divergent lane set'),
            ('ok-9' in out, 'names the unsanctioned lane'),
            ('MISSING' in out and 'ATOM-3' in out, 'names the lane the list omits'),
            ('AGREES  bringup.sh' in out, 'QUIET on a matching lane set'),
            ('MODE' not in out, 'ignores a quoted value that is not a lane set'),
        ]
        for good, desc in cases:
            print(f"  {'OK  ' if good else 'BAD '} {desc}")
            if not good:
                bad.append(desc)

        # The absent-roster branch, driven separately: a check for what the
        # scanner DOES NOT HAVE cannot share a pass with the thing it contradicts.
        os.remove(os.path.join(tmp, 'roster.txt'))
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = scan(tmp)
        ok2 = rc2 == 1 and 'MISSING roster.txt' in buf2.getvalue()
        print(f"  {'OK  ' if ok2 else 'BAD '} REFUSES rather than skips when roster.txt is absent")
        if not ok2:
            bad.append('absent roster')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if bad:
        print('SELFCHECK FAILED:', bad)
        return 1
    print('selfcheck: divergence fires, agreement stays quiet, an absent roster refuses')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else scan())
