#!/usr/bin/env python3
"""H219 certification. Every observation is PARSED out of a committed run file
(`probe.out`, `probe_prefix.out`, `falsify.out`) and never retyped from prose --
the two numbers I published wrong at cycle 29 were both retyped summaries of a
sample I had not read."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify
from provenance import Control, Falsifier


def read(name):
    with open(os.path.join(HERE, name)) as fh:
        return fh.read()


post, pre, fal = read('probe.out'), read('probe_prefix.out'), read('falsify.out')


def arm(text, tag):
    """The PASS/FAIL verdict the probe printed for one arm, by its label."""
    m = re.search(r'^  (PASS|FAIL)  (%s\b.*)$' % re.escape(tag), text, re.M)
    return (m.group(1), m.group(2)) if m else (None, None)


def tally(text):
    m = re.search(r'^probe: (\d+) passed, (\d+) failed$', text, re.M)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


post_pass, post_fail = tally(post)
pre_pass, pre_fail = tally(pre)
fal_arms = re.findall(r'^  (\S+)\s+(PASS|FAIL) (.*)$', fal, re.M)
fal_fail = [a for a in fal_arms if a[1] == 'FAIL']
hook_v = re.search(r'hook version: (v\d+)', post).group(1)
pre_v = re.search(r'hook version: (v\d+)', pre).group(1)

# C1 · THE PROBE REACHED THE HOOK. Without this every other arm is unreadable:
# a probe pointed at something that is not the hook returns `exit` for
# everything and would report the repair working on any file at all.
c1 = Control('probe_reaches_the_hook',
             'a probe that cannot show it reached its target has produced no '
             'evidence either way (A29)',
             null_must_contain='the hook must be capable of BOTH verdicts in the '
                               'same run, and it gives them: A3 (no switch) is '
                               '`block` and A1 (fleet-wide STOP) is `exit`',
             can_fail_because='a gate copy that is not a hook, or a ROOT rewrite '
                              'that silently no-opped, returns one verdict for '
                              'every input and A3 or A1 goes red')
c1.observe(arm(post, 'A3')[0] == 'PASS' and arm(post, 'A1')[0] == 'PASS',
           [arm(post, 'A3'), arm(post, 'A1')],
           'both baseline arms green in the same run, against %s' % hook_v)

# C2 · THE DEFECT WAS REAL AND IS THE HOOK'S, not the probe's. Same file, same
# arms, two gates through the seam.
c2 = Control('defect_present_at_head_absent_after',
             'the row claims a defect in a shipped file; one red run proves '
             'nothing unless the SAME instrument is green on the repair',
             null_must_contain='the pre-fix run must be capable of passing -- it '
                               'passes 6 of its 9 arms, including both baselines, '
                               'so the 3 failures are specific and not a dead probe',
             can_fail_because='if the pre-fix hook had honoured STOP.<lane>, A2 '
                              'and B2 would be green at HEAD and the row dies')
c2.observe(pre_fail == 3 and post_fail == 0,
           [(pre_v, pre_pass, pre_fail), (hook_v, post_pass, post_fail)],
           '%s: %d pass %d fail; %s: %d pass %d fail -- the three are A2 (own '
           'STOP refused), A6 (no such line) and B2 (20 of 20 attempts refused)'
           % (pre_v, pre_pass, pre_fail, hook_v, post_pass, post_fail))

# C3 · THE REPAIR DID NOT WIDEN THE SWITCH. This is the direction that matters:
# `STOP.*` would satisfy the row and retire the whole fleet on one lane's file.
c3 = Control('repair_is_not_a_glob',
             "H31's own defect restored from the other end would pass the row's "
             'headline check and stop all five lanes',
             null_must_contain='the cross-lane arm must be capable of `exit` -- '
                               'the M2 glob mutant makes it exactly that, which '
                               'is falsifier arm A2',
             can_fail_because='a `STOP*` or `STOP.*` read makes A4 report `exit` '
                              'and the suite check reports (want block, got exit)')
c3.observe(arm(post, 'A4')[0] == 'PASS'
           and any(a[0] == 'R2' and a[1] == 'PASS' for a in fal_arms),
           [arm(post, 'A4'), [a for a in fal_arms if a[0] in ('R2', 'R2b')]],
           "A4 green on the shipped hook, and the glob mutant reddens the suite's "
           'cross-lane check while leaving the own-lane check green')

# C4 · THE NEW SUITE CHECKS CAN FAIL, each in its own direction. A check written
# green against a hook that already carries the repair has a regression record
# and no detection record; those are different claims.
c4 = Control('suite_checks_have_been_red_on_purpose',
             '§5: a control that cannot fail is not a control, and you state the '
             'input that makes it fail',
             null_must_contain='the suite must be capable of passing on the same '
                               'inputs -- falsifier arm R0 runs it on the shipped '
                               'hook and it reports its own check count',
             can_fail_because='if any of the three mutants left the suite green, '
                              'that arm reports FAIL and names which check is inert')
c4.observe(len(fal_fail) == 0,
           [[(a[0], a[1]) for a in fal_arms]],
           'M1 deleted / M2 globbed / M3 relocated: 3 mutants, 3 distinct checks '
           'reddened, %d of %d falsifier arms as stated' % (len(fal_arms) - len(fal_fail),
                                                            len(fal_arms)))

# C5 · THE CLASS SWEEP IS NOT INERT AND ITS ONE HIT IS NAMED. A sweep printing
# zeros is worth nothing until you know it can print something else -- v1 of it
# printed eight clean zeros produced by a regex `ugrep` had rejected outright.
sweep = re.search(r'-> (\d+) bare site\(s\) across 8 per-lane state names\.', post)
c5 = Control('class_sweep_prints_its_hits',
             'the sweep is the §12.2 half of this row: fix the CLASS, and say '
             'what else is in it',
             null_must_contain='the sweep must be capable of a NON-zero -- it '
                               'reports 1 and prints the line, which is how the '
                               'hit was identified as a message string',
             can_fail_because='a sweep whose pattern the local grep rejects '
                              'returns 0 for every name; v1 did exactly that and '
                              'the count is now computed in python')
c5.observe(bool(sweep) and int(sweep.group(1)) >= 1,
           [sweep.group(0) if sweep else None],
           'one hit, printed with its text: bringup.sh:618 is `.loop_launcher` '
           'inside a MESSAGE STRING, not a read -- so the live count is 0 and the '
           'raw count is 1, and both are on the page')

F = [
    Falsifier('F1', 'the hook already honours the per-lane form through a path I '
                    'had not read, and the row dies',
              'the pre-fix hook returns `exit` for STOP.<own lane>',
              null_must_contain='the pre-fix hook must be capable of `exit` -- it '
                                'gives exactly that for the fleet-wide file in the '
                                'same run (A1)'),
    Falsifier('F2', 'the asymmetry exists but costs nothing, because the turn ends '
                    'promptly anyway',
              'a turn under STOP.<own lane> ends within the 20-attempt bound',
              null_must_contain='the bound must be capable of being reached -- B1 '
                                'reaches it at attempt 0 under the fleet-wide file'),
    Falsifier('F3', 'there is no asymmetry to report: both spellings give the same '
                    'verdict',
              'A1 and A2 agree on the pre-fix hook',
              null_must_contain='both arms read the SAME hook in the SAME run, so '
                                'agreement is reachable and is what the repaired '
                                'hook produces'),
    Falsifier('F4', 'the case is already covered and the row dies',
              'test_loop_gate.sh drives a per-lane STOP through the hook before v7',
              null_must_contain='the suite has a STOP section (8) that is driven '
                                'and green, so a per-lane check there would have '
                                'been found by the same grep that found section 8'),
]
# F1 · pre-fix A2 was `block`, so it did not fire.
F[0].observe(arm(pre, 'A2')[0] == 'PASS', [arm(pre, 'A2')])
# F2 · pre-fix B2 hit the bound: 'no' rather than an attempt number.
F[1].observe(arm(pre, 'B2')[0] == 'PASS', [arm(pre, 'B2')])
# F3 · pre-fix A1 exit vs A2 block: they disagreed.
F[2].observe(arm(pre, 'A1')[0] == 'PASS' and arm(pre, 'A2')[0] == 'PASS',
             [arm(pre, 'A1'), arm(pre, 'A2')])
# F4 · resolved against the FILE at HEAD, not from memory: HEAD's suite mentions
# STOP.$CALLSIGN only inside a launcher span fixture, never as a hook input.
import subprocess
head_suite = subprocess.run(['git', 'show', 'HEAD:spikes/harness/test_loop_gate.sh'],
                            cwd=ROOT, capture_output=True, text=True).stdout
head_perlane_hook_drives = [
    l for l in head_suite.splitlines()
    if 'STOP.' in l and 'blocked' in l]
F[3].observe(len(head_perlane_hook_drives) > 0, [head_perlane_hook_drives])

ok, problems = certify(
    HERE,
    deps=['spikes/harness', '.claude/hooks'],
    artifacts=[os.path.join(HERE, a) for a in
               ('probe.sh', 'probe.out', 'probe_prefix.out', 'falsify.out')],
    controls=[c1, c2, c3, c4, c5],
    falsifiers=F,
    allow_dirty=True,   # five lanes write spikes/harness continuously (§13/H19);
                        # the dep this row actually turns on is .claude/hooks, and
                        # the two runs above pin both gates by their own banner
    captures=[('post_fix_run', post), ('pre_fix_run', pre), ('falsifier_run', fal),
              ('hook_version_under_test', hook_v),
              ('pre_fix_hook_version', pre_v)],
    falsifier='if the pre-fix hook had returned `exit` for STOP.<own lane> (F1), '
              'or if a turn under it had ended within the bound (F2), or if the '
              'two spellings had agreed (F3), or if the suite had already driven '
              'a per-lane STOP through the hook (F4), this row is withdrawn. '
              'Measured at HEAD: block, 20-of-20 refused, disagreed, and the only '
              'STOP.$CALLSIGN in the suite is a launcher span fixture.',
    note='H219 — the per-lane kill switch had one reader and the hook was not it. '
         'ok-1, ATTACK cycle 30, 2026-08-19.')
print('certify ok=%s' % ok)
for p in problems:
    print('  ', p)
sys.exit(0 if ok else 1)
