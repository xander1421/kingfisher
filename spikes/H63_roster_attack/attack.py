#!/usr/bin/env python3
"""H63 — ATTACK on the loop's ADMISSION gate (§2 cycle 8, §12.8's target).

`run_loop.sh:124-134` is the fleet's admission mechanism: a callsign not listed in
`roster.txt` is refused, and `run_loop.sh`'s own comment says why -- *"a brief that
the lane wrote for itself is not sanction to run. roster.txt is the sanction."*
It is the answer to H32 (nothing audits what is already running) and the thing
H38's two-roster divergence was about.

`grep -n roster spikes/harness/test_loop_gate.sh` returns three lines, all three a
scratch roster written FOR the 20-launcher block. **Not one check asserts that the
gate refuses anything.** So the suite that exists to make the loop enforceable has
no coverage of the mechanism that decides which lanes may run at all.

FALSIFIERS, STATED BEFORE THE FIRST RUN:

  FA  delete the roster block from `run_loop.sh` and the suite stays all-green
      -> the admission gate is unfalsified by the harness's own suite (A15 applied
      to a whole gate rather than to one check)
  FB  roster PRESENT, callsign absent from it: the launcher must refuse, name the
      roster file, and never reach `claude`. If it launches, this is a live defect
      and the attack stops being about coverage
  FC  roster ABSENT: measured, not assumed. `run_loop.sh` prints a WARNING and
      launches unrostered. If that is what happens, the admission gate FAILS OPEN
      on a missing input and the only signal is a line in a log
  FD  `grep -qx` is load-bearing: a callsign that is a SUBSTRING of a rostered one
      (`ok` against `ok-1`) must be refused. If `grep -q` would admit it and no
      check notices, the exactness of the match is unprotected

  A29 GUARD: every arm records whether it reached the launcher at all. An arm with
  no output is no evidence, not a negative result.

usage:  python3 spikes/H63_roster_attack/attack.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'H7_harness_attack'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import falsify                                                     # noqa: E402
from edits import anchored_replace                                 # noqa: E402

LAUNCHER = 'run_loop.sh'

# The whole roster block, removed. Not weakened -- an attack on coverage has to
# remove the mechanism, because a weakened one may still refuse by accident.
GATE_GONE = (LAUNCHER,
             '''if [ -f "$ROSTER_FILE" ]; then
  if ! sed 's/#.*//' "$ROSTER_FILE" | awk 'NF{print $1}' | grep -qx "$CALLSIGN"; then''',
             '''if false; then
  if false; then''')
# Exact match -> substring match. `ok` then satisfies a roster listing `ok-1`.
GATE_LOOSE = (LAUNCHER,
              'grep -qx "$CALLSIGN"',
              'grep -q "$CALLSIGN"')

# Check names this attack expects to exist AFTER the repair. Before it, the point
# is that none of them do.
WANT = ['unrostered callsign is refused',
        'refusal names the roster',
        'never reached claude',
        'a callsign that is a SUBSTRING of a rostered one is refused']


def suite_arm(name, edits):
    """Run the whole suite in a scratch tree with `edits` applied."""
    t = tempfile.mkdtemp(prefix='h63_')
    try:
        falsify.build(t)
        for rel, old, new in edits:
            p = os.path.join(t, rel)
            src = open(p).read()               # READ BEFORE OPENING 'w' (H14)
            open(p, 'w').write(anchored_replace(src, old, new))
        passed, failed, out = falsify.run_suite(t)
        red = sorted({w for w in WANT if any(w in f for f in failed)})
        print(f'  {name:<22} {len(passed):>3} pass / {len(failed):>2} fail   '
              f'roster-related red: {red if red else "NONE"}', flush=True)
        if not passed:
            print('      ZERO PASSES -- arm never reached the checks; no evidence '
                  '(A29)', flush=True)
        return red, passed, failed
    finally:
        shutil.rmtree(t, ignore_errors=True)


def launch_arm(name, callsign, roster, edits=()):
    """Drive the real launcher once. Returns (rc, stdout, reached_claude).

    KF_DETACHED=1 keeps the loop body in the FOREGROUND so `reached` is a fact
    rather than a race -- H62's finding, applied to the instrument measuring the
    next gate along. The ordering property (a refusal must beat the detach) is
    covered in the suite by the detach-announcement checks and is not what these
    arms are about.
    """
    t = tempfile.mkdtemp(prefix='h63_launch_')
    try:
        falsify.build(t)
        for rel, old, new in edits:
            p = os.path.join(t, rel)
            src = open(p).read()
            open(p, 'w').write(anchored_replace(src, old, new))
        os.makedirs(os.path.join(t, 'bin'), exist_ok=True)
        os.makedirs(os.path.join(t, 'prompts'), exist_ok=True)
        stub = os.path.join(t, 'bin', 'claude')
        with open(stub, 'w') as f:
            f.write('#!/usr/bin/env bash\necho reached > reached_claude\n'
                    'echo LOOP-HALT > ".loop_exit.${CALLSIGN}"\n')
        os.chmod(stub, 0o755)
        # A brief EXISTS for every arm: the brief gate sits below the roster gate,
        # and H62 is the cycle that learned what a later gate refusing first does
        # to a check. If the brief were missing, every arm here would "refuse"
        # and none of it would be about the roster.
        with open(os.path.join(t, 'prompts', f'{callsign}.md'), 'w') as f:
            f.write(f'# scratch brief for {callsign}\n')
        if roster is not None:
            with open(os.path.join(t, 'roster.txt'), 'w') as f:
                f.write(roster)
        env = dict(os.environ, PATH=os.path.join(t, 'bin') + os.pathsep
                   + os.environ['PATH'], CALLSIGN=callsign, MAX_TURN='5',
                   KF_DETACHED='1')
        p = subprocess.run(['bash', './run_loop.sh'], cwd=t, env=env,
                           capture_output=True, text=True, timeout=120)
        out = p.stdout + p.stderr
        reached = os.path.exists(os.path.join(t, 'reached_claude'))
        print(f'  {name:<22} rc={p.returncode}  reached_claude={reached}  '
              f'said_roster={"roster.txt" in out}', flush=True)
        if not out.strip() and not reached:
            print('      NO OUTPUT AND NO TURN -- arm produced no evidence (A29)',
                  flush=True)
        return p.returncode, out, reached
    finally:
        shutil.rmtree(t, ignore_errors=True)


print('H63 — the admission gate: does anything fail when it is removed?\n')
print('SUITE ARMS')
control_red, cpass, cfail = suite_arm('control', [])
gone_red, gpass, gfail = suite_arm('roster gate DELETED', [GATE_GONE])
loose_red, lpass, lfail = suite_arm('exact match -> substr', [GATE_LOOSE])

print('\nLAUNCHER ARMS (the gate itself, driven)')
rc_unrostered, out_unrostered, reached_unrostered = launch_arm(
    'unrostered + roster', 'X1', '# scratch roster\nOTHER-1\n')
rc_rostered, out_rostered, reached_rostered = launch_arm(
    'rostered (control)', 'X1', '# scratch roster\nX1\n')
rc_noroster, out_noroster, reached_noroster = launch_arm(
    'roster ABSENT', 'X1', None)
rc_substr, out_substr, reached_substr = launch_arm(
    'substring of rostered', 'ok', '# scratch roster\nok-1\n')
rc_substr_loose, out_substr_loose, reached_substr_loose = launch_arm(
    'substring, grep -q', 'ok', '# scratch roster\nok-1\n', [GATE_LOOSE])

print()
problems = []
if cfail:
    problems.append(f'control suite is not all-green ({cfail}) — no suite arm here '
                    f'is evidence')
if not reached_rostered:
    problems.append('the ROSTERED control never reached claude — the launcher '
                    'refuses everything in this tree, so every refusal below is '
                    'unattributable (A29)')

print('FA  suite reds with the roster gate DELETED:      '
      f'{gone_red if gone_red else "NONE — the gate is unfalsified by the suite"}')
print('FA\' suite reds with exact match loosened:         '
      f'{loose_red if loose_red else "NONE — the exactness is unprotected"}')
print(f'FB  unrostered, roster present: rc={rc_unrostered}, '
      f'reached_claude={reached_unrostered}, names the roster='
      f'{"roster.txt" in out_unrostered}')
print(f'FC  roster ABSENT:              rc={rc_noroster}, '
      f'reached_claude={reached_noroster}, warned='
      f'{"WARNING" in out_noroster}')
print(f'FD  `ok` against roster `ok-1`: rc={rc_substr}, '
      f'reached_claude={reached_substr}   '
      f'(with grep -q: rc={rc_substr_loose}, reached={reached_substr_loose})')
print()

if problems:
    for p in problems:
        print(f'  PROBLEM  {p}')
    sys.exit(2)

verdicts = []
if not gone_red:
    verdicts.append('FA FIRED: the whole admission gate can be deleted and the '
                    'suite stays green.')
if reached_unrostered or rc_unrostered == 0:
    verdicts.append('FB FIRED AND THIS IS A LIVE DEFECT: an unrostered callsign '
                    'launched.')
else:
    verdicts.append('FB did not fire: the gate refuses an unrostered callsign and '
                    'names the roster.')
if reached_noroster:
    verdicts.append('FC MEASURED: with roster.txt absent the launcher launches '
                    'ANY callsign — the admission gate fails OPEN on a missing '
                    'input, and the only signal is a warning line.')
if reached_substr:
    verdicts.append('FD FIRED AND THIS IS A LIVE DEFECT: a substring of a '
                    'rostered callsign was admitted.')
elif reached_substr_loose:
    verdicts.append('FD did not fire, and `grep -qx` is what stops it: with '
                    '`grep -q` the same callsign is admitted, so the exactness is '
                    'load-bearing and needs a check that fails when it goes.')
for v in verdicts:
    print(f'  {v}')
