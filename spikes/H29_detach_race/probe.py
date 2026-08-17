#!/usr/bin/env python3
"""H29's stated falsifier, run BEFORE any repair, on the real suite.

THE CLAIM UNDER TEST is mine, from the H29 row: *"the launcher checks run
`bash ./run_loop.sh` with `KF_DETACHED` unset, so each one self-detaches and the
assertion races the detached child, in the direction where the not-yet-run child
yields the PASSING answer."*

Four of the suite's launcher assertions are ABSENCE assertions -- `it never
reached the turn`, `and never detached an unbriefed lane`, `launcher never
reached claude` (twice). Absence of an asynchronous event is not observable at
the instant the parent returns: the launcher forks, the parent exits, and the
child reaches `claude` some time later. So the question is not whether these
checks are green (they are, 63/63) but whether they COULD go red on the defect
their block exists for, and what that depends on.

ARMS, each answering a falsifier stated before the run:

  FA  D1 / D2 -- the gate the block tests is neutered. If the absence assertion
      is still GREEN, it cannot fail on the defect its own block exists for
      (A15) and my claim stands unconditionally on this machine.
  FB  D1+NS / D2+NS -- the same defect, with `sleep 1` deleted from
      run_loop.sh's detach block. That line's purpose is unrelated to any test;
      it gives the forked child a head start before the parent exits. If the
      absence assertions stay RED without it, the suite does NOT depend on it
      and the sleep-dependency half of this reading is WRONG -- withdraw it.
  FC  NS alone -- a clean tree with that sleep removed must stay ALL-GREEN. If
      it reddens anything, the NS arms are confounded and prove nothing about
      the absence assertions.
  FD  any arm producing ZERO passes never reached the checks: A29, no evidence
      rather than a negative result.

WHY IT MATTERS BEYOND THE SUITE: H29 is the row asking whether this suite can
gate every commit. A check that is green because of a one-line sleep inside the
component it tests is not a gate; it is a coin that has been landing heads.

usage:  python3 spikes/H29_detach_race/probe.py
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'H7_harness_attack'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import falsify                                                     # noqa: E402
from edits import anchored_replace                                 # noqa: E402

LAUNCHER = 'run_loop.sh'

# The gate each launcher block exists to test, neutered. D1 is F8's own revert
# (the charset whitelist); D2 is the pre-H30 state (a lane with no brief
# launched and looked exactly like a briefed one).
D1 = (LAUNCHER,
      'case "$CALLSIGN" in (*[!A-Za-z0-9._-]*)',
      'case "$CALLSIGN" in (thiswillnevermatch)')
D2 = (LAUNCHER,
      'if [ ! -f "$BRIEF_FILE" ]; then',
      'if false; then   # brief gate neutered')
# The line the suite's absence assertions turn out to rest on. Removed, not
# shortened: `sleep 0` would still be a scheduling point.
NS = (LAUNCHER,
      '( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &\n  sleep 1\n',
      '( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &\n')

# The four absence assertions, by their stable check-name prefixes.
ABSENCE = ['it never reached the turn',
           'and never detached an unbriefed lane',
           'launcher never reached claude']
# v2, AFTER the repair: the two assertions added because the four above cannot be
# trusted to fail. Both read the PARENT's own stdout, which it writes before
# exiting, so no child scheduling can decide their verdict. Listed separately
# because the point of the arms is that these must be red in EVERY arm where the
# defect is present -- with the launcher's post-fork sleep and without it.
# `probe.out` is v1's output, measured on the suite BEFORE these existed;
# `verify.out` is this version's. To reproduce v1's numbers, run this file against
# the parent commit's `spikes/harness/test_loop_gate.sh`.
SYNC = ['and refuses for THAT reason',
        'announced no detach (synchronous',
        'announced no detach (the PARENT prints it']
# The rc assertions in the same two blocks. They are what currently catches D1
# and D2, and the arms below are only interesting if these DO fire -- otherwise
# the injection did not take.
RC = ['launcher refuses what the hook will not gate',
      'launcher refuses a callsign with no spawn brief']
WANT = ABSENCE + SYNC + RC


def arm(name, edits):
    t = tempfile.mkdtemp(prefix='h29_')
    try:
        falsify.build(t)
        for rel, old, new in edits:
            p = os.path.join(t, rel)
            src = open(p).read()              # READ BEFORE OPENING 'w' (H14)
            open(p, 'w').write(anchored_replace(src, old, new))
        passed, failed, out = falsify.run_suite(t)
        red = [w for w in WANT if any(w in f for f in failed)]
        print(f'  {name:<14} {len(passed):>3} pass / {len(failed):>2} fail', flush=True)
        for w in WANT:
            mark = 'RED  ' if w in red else 'green'
            print(f'      {mark}  {w}', flush=True)
        if not passed:
            print('      ZERO PASSES -- this arm never reached the checks; no '
                  'evidence (A29)', flush=True)
        return red, passed, failed
    finally:
        shutil.rmtree(t, ignore_errors=True)


print('H29 — can the launcher blocks\' ABSENCE assertions fail on their own '
      'defect?\n')
_,  cpass, cfail = arm('control', [])
ns, npass, nfail = arm('NS only', [NS])
d1, _, _ = arm('D1 charset', [D1])
d1n, _, _ = arm('D1+NS', [D1, NS])
d2, _, _ = arm('D2 brief', [D2])
d2n, _, _ = arm('D2+NS', [D2, NS])

print()
problems = []
if cfail:
    problems.append(f'FD: control tree is not all-green ({cfail}) — no arm here '
                    f'is evidence')
ns_other = [f for f in nfail if not any(w in f for w in WANT)]
if [f for f in nfail if any(w in f for w in WANT)]:
    problems.append(f'FC: removing the launcher\'s sleep reddens an assertion '
                    f'this probe reasons about, on a CLEAN tree ({nfail}) — the '
                    f'NS arms are confounded')
elif ns_other:
    # v2: FC as first written treated ANY red under NS as a confound and exited
    # before printing the rest. It fired -- on three checks in a DIFFERENT block,
    # about the callsign lock, so the arms remain evidence about the gate blocks
    # they were built for. Reported here rather than swallowed, because it is a
    # finding about run_loop.sh and a bigger one than the row it turned up in:
    # the parent->child lock handoff is synchronised by that sleep.
    print('  LAUNCHER FINDING (not a confound — different block): removing '
          'run_loop.sh\'s post-fork `sleep 1` reddens')
    for f in ns_other:
        print(f'      {f}')
    print('    i.e. the callsign lock\'s parent->child handoff depends on that '
          'timing constant, whose\n    own comment gives it an unrelated purpose. '
          'Filed as its own row; NOT fixed here.')
    print()
for label, red in (('D1', d1), ('D2', d2)):
    if not any(w in red for w in RC):
        problems.append(f'FD: {label} reddened no rc assertion — the injection '
                        f'did not take, treat the arm as no evidence')

absent_with_sleep = sorted({w for w in ABSENCE if w in d1 or w in d2})
absent_without = sorted({w for w in ABSENCE if w in d1n or w in d2n})
print(f'absence assertions RED with the launcher\'s sleep:    {absent_with_sleep}')
print(f'absence assertions RED with it removed:              {absent_without}')
lost = [w for w in absent_with_sleep if w not in absent_without]
print(f'assertions that go GREEN over a live defect if that one line goes: {lost}')
print()
sync_d1 = [w for w in SYNC if w in d1 and w in d1n]
sync_d2 = [w for w in SYNC if w in d2 and w in d2n]
print(f'synchronous assertions RED under D1 with AND without the sleep: {sync_d1}')
print(f'synchronous assertions RED under D2 with AND without the sleep: {sync_d2}')
if not (sync_d1 and sync_d2):
    problems.append('the repair does not hold: a defect arm has no assertion '
                    'that reddens both with and without the launcher\'s sleep, '
                    'so the block\'s verdict still depends on child scheduling')
print()
if problems:
    for p in problems:
        print(f'  PROBLEM  {p}')
    sys.exit(2)

if not absent_with_sleep:
    print('FA STANDS: the absence assertions cannot fail on the defect their own '
          'block exists for, sleep or no sleep.')
elif lost:
    print('FB DID NOT FIRE: the absence assertions are green only because '
          'run_loop.sh sleeps 1s after forking. Delete that line — a line with '
          'no test-facing purpose — and they pass over a live defect.')
else:
    print('FB FIRED: the absence assertions fail on their defect with or without '
          'the sleep. The sleep-dependency reading is WITHDRAWN.')
