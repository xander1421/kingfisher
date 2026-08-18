#!/usr/bin/env python3
"""H88 certification -- runs both drivers, PERSISTS what they printed, records it.

Every control persists the actual verdict strings rather than a boolean: a null
reported only in prose cannot be rechecked afterwards, and this row's entire
finding is about a value that was computed and never made visible.

ARTIFACTS ARE THE OUTPUTS, NOT THE SCRIPTS. First pass declared probe.sh/run.sh
as artifacts and `certify` REFUSED all five with STALE ARTIFACT -- correctly:
the staleness rule asks whether an artifact could have been BUILT from the tree
recorded beside it, and a source file is not built from itself, so every script
in a spike is "stale" the moment any later file lands. The scripts are pinned by
sha256 capture instead, which is the A24 question actually being asked of them
(WHICH file was measured), and the .out files carry the staleness check for real
because they genuinely are produced by this run.
"""
import hashlib
import os
import subprocess
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'harness')))
from kfcheck import certify, Control
from provenance import Falsifier

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
ROOT = os.path.abspath('../..')


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def save(name, text):
    with open(os.path.join(HERE, name), 'w') as fh:
        fh.write(text)
    return name


def probe(target, out_name):
    env = dict(os.environ, KF_H88_TARGET=target)
    r = subprocess.run(['bash', './probe.sh'], capture_output=True, text=True, env=env)
    save(out_name, r.stdout + r.stderr)
    grab = lambda k: [l.split(k)[1].split()[0] for l in r.stdout.splitlines() if k in l]
    v, c = grab('verdict='), grab('controls_ok=')
    return (v[-1] if v else 'NONE'), (c[-1] if c else 'NONE')


PRE = os.path.join(HERE, 'bringup.before_h88.sh')
LIVE = os.path.join(ROOT, 'bringup.sh')
pre_v, pre_c = probe(PRE, 'probe.prefix.out')
live_v, live_c = probe(LIVE, 'probe.live.out')
fal = subprocess.run(['bash', './falsify.sh'], capture_output=True, text=True)
save('falsify.out', fal.stdout + fal.stderr)
chk = subprocess.run(['bash', './run.sh'], capture_output=True, text=True)
save('run.out', chk.stdout + chk.stderr)
lines = lambda r: [l.strip() for l in r.stdout.splitlines() if 'PASS' in l or 'FAIL' in l]

c_neg = Control(
    'negative_control_prefix',
    'the probe must be able to SEE the defect, or the live arm reading clean means nothing',
    null_must_contain='the pre-fix census line pair, which differ only if the fix is present',
    can_fail_because='point the pre-fix arm at the repaired file and it reads DEFECT_ABSENT')
c_neg.observe(pre_v == 'DEFECT_PRESENT',
              [f'pre_fix_verdict={pre_v}', f'pre_fix_controls_ok={pre_c}'],
              'bringup.before_h88.sh: absent and nfail=0 print byte-identical census lines')

c_live = Control(
    'live_file_repaired',
    'the claim recorded is that the LIVE bringup.sh no longer collapses absent into 0',
    null_must_contain='an absent-counter census line, which the pre-v2 file emits identically to nfail=0',
    can_fail_because='remove the fnote assignment or any of its four print sites and it reads DEFECT_PRESENT')
c_live.observe(live_v == 'DEFECT_ABSENT',
               [f'live_verdict={live_v}', f'live_controls_ok={live_c}'],
               'bringup.sh v2: absent emits the NO FAIL COUNTER suffix, nfail=0 does not')

c_chk = Control(
    'runnable_check_green',
    'section 12.3 -- the component keeps a check that fails when it breaks; this is that check RUN',
    null_must_contain='either arm disagreeing with its expected verdict',
    can_fail_because='either arm returning the other verdict, or controls_ok=false, exits 1')
c_chk.observe(chk.returncode == 0, [f'run_sh_rc={chk.returncode}'] + lines(chk))

# A CONTROL, NOT A Falsifier. Detecting a planted mutation is an instrument check
# that MUST come out positive; `Falsifier` is for a test whose FIRING refutes the
# claim, and filing "the mutation was caught" as a refutation would be A21 in the
# direction that class was built to prevent.
c_mut = Control(
    'fix_removal_detected',
    'a check nobody has broken on purpose is a check nobody has tested (M1_10: 2 of 4 probes scored clean against the bug fully present)',
    null_must_contain='an untouched copy, which must stay DEFECT_ABSENT',
    can_fail_because='a check watching the ASSIGNMENT instead of the OUTPUT would miss F2 and this reads FAIL')
c_mut.observe(fal.returncode == 0, lines(fal),
              'both mutations detected, control green; mutations asserted non-no-op by cmp')

# THE PREREGISTERED FALSIFIER, RECORDED WITH ITS OUTCOME. Stated in CHANNEL.md
# before probe.sh existed. It did NOT fire, and this records that rather than
# leaving it silent.
f_pre = Falsifier(
    'H88 was never a defect',
    "the row's claim that ABSENT and nfail=0 were indistinguishable",
    'the PRE-FIX bringup.before_h88.sh already prints something for absent that it does not print for 0',
    null_must_contain='the pre-fix census line pair')
f_pre.observe(pre_v != 'DEFECT_PRESENT',
              [f'pre_fix_verdict={pre_v}', 'expected_if_fired=DEFECT_ABSENT'],
              'did not fire: the pre-fix file collapses absent into 0')

ok, problems = certify(
    HERE,
    deps=[ROOT],
    artifacts=['probe.prefix.out', 'probe.live.out', 'falsify.out', 'run.out'],
    controls=[c_neg, c_live, c_chk, c_mut],
    falsifiers=[f_pre],
    captures=[('probe.sh', sha('probe.sh')), ('run.sh', sha('run.sh')),
              ('falsify.sh', sha('falsify.sh')),
              ('bringup.before_h88.sh', sha(PRE)), ('bringup.sh', sha(LIVE))],
    allow_dirty=True,
    note='H88: a sentinel computed, documented as "not clear", and read by the one '
         'branch that could not tell it from clear. Two-sided against the pre-fix copy.',
    falsifier='if an absent .loop_fails already produced output distinguishable from '
              'nfail=0 in the PRE-FIX file, the defect was never there and H88 is withdrawn')
print('ok=%s' % ok)
for p in problems:
    print('  PROBLEM:', p)
sys.exit(0 if ok else 1)
