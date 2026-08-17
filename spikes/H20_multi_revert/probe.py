#!/usr/bin/env python3
"""H20's stated falsifier, run BEFORE building anything, on the REAL instrument.

v2, 2026-08-17 (ok-1). THE DEFECT REMOVED: arm B restored the wrong defect.
H20's two checks are both about a callsign-less session, and the second one asks
whether it can consume LANE `L1`'s signal -- so the partner defect has to be the
one that makes the hook read OTHER lanes' signal files, which is F14's glob
(`for SIGFILE in .loop_signal.*`). v1 used F5's bare-signal form
(`".loop_signal.${LANE}" ".loop_signal"`), and `.loop_signal.L1` matches neither
of those, so the A+B arm could not have reddened the check under ANY hook and
the probe would have reported "row does not stand" over a defect of its own.
Found by reading the section the check lives in rather than the check's name.

Arms, and each one exists to answer a stated falsifier:
  FA  either check red under a SINGLE revert  -> H20 misdiagnosed it, withdraw
  FB  "writes no 'unknown' marker" red under A+B -> the A15 reading below is
      wrong, withdraw it
  FC  that check NOT red under A once its section is given a signal to consume
      -> the proposed one-line suite fix is wrong, withdraw it
  FD  control+SUITEFIX not all-green -> the suite fix reddens a clean tree and
      is not shippable, whatever it proves

The A15 reading being tested: section 9 opens `rm -f .loop_signal*`, so when its
`nolane` call runs there is NO signal file anywhere. The hook writes
`.loop_exit.<LANE>` only after consuming a signal. So `writes no 'unknown'
marker` cannot go red under any combination of hook defects -- it is not a check
that needs two reverts, it is a check whose precondition its own section deletes.
"""
import os, shutil, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'H7_harness_attack'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import falsify                                                     # noqa: E402
from edits import anchored_replace                                 # noqa: E402

GATE = '.claude/hooks/loop_gate.sh'
SUITE = 'spikes/harness/test_loop_gate.sh'

A = (GATE,
     'if [ -z "${CALLSIGN:-}" ]; then\n  exit 0\nfi\nLANE="$CALLSIGN"',
     'LANE="${CALLSIGN:-unknown}"')
B = (GATE,
     'for SIGFILE in ".loop_signal.${LANE}"; do',
     'for SIGFILE in .loop_signal.*; do')
SUITEFIX = (SUITE,
            'check "no callsign is not gated"      "$(nolane)" "exit"',
            'echo LOOP-HALT > .loop_signal.unknown\n'
            'check "no callsign is not gated"      "$(nolane)" "exit"')

MARKER = "writes no 'unknown' marker"
SIGNAL = 'lane signal untouched'
WANT = [MARKER, SIGNAL]


def arm(name, edits):
    t = tempfile.mkdtemp(prefix='h20_')
    try:
        falsify.build(t)
        for rel, old, new in edits:
            p = os.path.join(t, rel)
            src = open(p).read()               # READ BEFORE OPENING 'w' (H14)
            open(p, 'w').write(anchored_replace(src, old, new))
        passed, failed, out = falsify.run_suite(t)
        red = [w for w in WANT if any(w in f for f in failed)]
        print(f'  {name:<16} {len(passed)} pass / {len(failed)} fail; '
              f'target red: {red if red else "neither"}', flush=True)
        if not passed:
            print('           SUITE PRODUCED NO PASSES -- the probe did not reach '
                  'the checks; treat this arm as no evidence (A29)', flush=True)
        return red, passed, failed
    finally:
        shutil.rmtree(t, ignore_errors=True)


print('H20 falsifiers — one revert, two reverts, and the section-9 precondition',
      flush=True)
c,  cp, _ = arm('control', [])
a,  _,  _ = arm('A (unknown)', [A])
b,  _,  _ = arm('B (glob sig)', [B])
ab, _,  _ = arm('A+B', [A, B])
cs, _, csf = arm('control+FIX', [SUITEFIX])
af, _,  _ = arm('A+FIX', [A, SUITEFIX])

reached = bool(cp)
FA = reached and not c and not a and not b
FB = MARKER not in ab
FC = MARKER in af
FD = not csf
print()
print(f'  FA  no target check reds on a single revert ............ {"PASS" if FA else "FAIL"}')
print(f'  FB  "{MARKER}" stays green under A+B ... {"PASS" if FB else "FAIL"}')
print(f'  FC  it reds under A once its section has a signal ...... {"PASS" if FC else "FAIL"}')
print(f'  FD  the suite fix leaves a clean tree all-green ........ {"PASS" if FD else "FAIL"}')
print(f'  ..  "{SIGNAL}" reds under A+B ................... '
      f'{"PASS" if SIGNAL in ab else "FAIL"}')
print()
ok = FA and FB and FC and FD and SIGNAL in ab
print('VERDICT:', 'H20 is HALF RIGHT — one check needs list support, the other '
      'needs its precondition' if ok else
      'at least one falsifier fired; read the arms before writing anything')
sys.exit(0 if ok else 1)
