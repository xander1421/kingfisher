#!/usr/bin/env python3
"""H61 — is the callsign lock's parent->child handoff window reachable by LOAD?

v3, AND v2's PRINTED VERDICT WAS WRONG TOO — the second wrong verdict in this one
file, both from reasoning past a number the probe itself had flagged.

v2 counted a refusal by grepping `race.log`, which holds only what the PARENT
printed: the child is `nohup`ed to `detach_$CALLSIGN.log`. So the one arm that
answers the row (`sleep 1` + slow child, staggered) came back
`survivors=1 HELD=0 UNACCOUNTED: 1+0 != 2`, the probe printed the UNACCOUNTED
warning **and the verdict logic then used `survivors=1` anyway** to print
"H61 IS WITHDRAWN AS FILED". An arm the instrument has declared no-evidence is
not a negative result (A29), and this file's own docstring says so.

v3 counts refusals in BOTH logs and reports WHERE the refusal happened, because
that is the discriminator the row actually turns on, and it refuses a verdict on
any unaccounted arm instead of printing one.

WHAT THE v2 RUN ALREADY SHOWS, once its own logs are counted (`probe_v2.out`):
the second launcher is refused in every arm; what changes is WHO refuses it.
Under `sleep 1` + a slow child the refusal moves into the CHILD, 3 s after the
parent has already printed `detached` and exited 0 — which is the exact defect
`run_loop.sh:232-234` says the pre-fork acquisition exists to prevent: *"a
refusal after the detach goes to detach_$CALLSIGN.log where nobody looks and the
caller still sees exit 0"*. So H61 is NOT the double admission I filed; it is a
LAUNCH FAILURE REPORTED AS A SUCCESS. The fix is the same fix.

v1's PRINTED VERDICT WAS WRONG. v1 ran the whole suite and counted how
many of the three 20-launcher lock checks went red, then concluded from `2/3 red`
that a slow child breaks the lock. **Reading the numbers it printed says
otherwise**: `leave ONE survivor (want '1', got '0')` and `every launcher is
accounted for (want '20', got '19')`. Zero survivors and 19 correct HELD refusals
is not two lanes on one callsign -- it is the ONE admitted lane still sleeping when
the suite's 2 s settle expired. A red check counted as evidence of the wrong
mechanism: correct numbers, wrong attribution, which `CLAUDE.md` lists as one of
the three things no tool catches. `probe.out` is v1's run and is kept for that.

So v2 measures the thing directly and can tell the two apart:
  * >1 unique pid in `reached_claude`  -> TWO LANES GOT ONE CALLSIGN (the window)
  * 0 survivors                       -> the admitted child was merely late
  * survivors + HELD refusals != 20   -> unaccounted, no verdict either way
and it waits out the injected delay before counting, so lateness cannot masquerade
as either answer.

FALSIFIERS, STATED BEFORE v2's FIRST RUN:

  FA  slow child (3 s, CHILD ONLY) under the current `sleep 1` yields ONE survivor:
      the window is not reachable by load at this delay and **H61 is withdrawn as
      filed** -- only an edit to that line opens it
  FB  the POSITIVE CONTROL (`sleep 1` deleted, H29's arm) does not yield >1
      survivor: then this probe cannot see a double admission at all and NOTHING
      here is evidence, in either direction (A29)
  FC  the condition wait yields anything but exactly one survivor and 19 HELD, with
      or without the slow child: the fix does not hold and must not ship

TWO MORE, STATED BEFORE v3's FIRST RUN, on the question v2 could not see:

  FD  under `sleep 1` + a slow child, staggered, the second launcher is refused by
      the PARENT (its refusal is in `race.log`): then the pre-fork acquisition
      holds under load, nothing moves into the detach log, and **H61 is withdrawn
      outright** rather than restated
  FE  under the condition wait the refusal is in the CHILD: the fix does not
      restore parent-side refusal and must not ship, whatever the survivor count
  FF  any arm's survivors + parent refusals + child refusals != the launchers
      started: that arm is NO EVIDENCE and no verdict may be computed from it.
      v2 printed exactly this condition and then computed one anyway

The delay is gated on `KF_DETACHED`, so it lands in the child only and the arms
differ in exactly one thing: how long the child takes to reach the reclaim it
already performs.

usage:  python3 spikes/H61_lock_handoff/probe.py
"""
import os
import re
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
N = 20                      # matches H13's and the suite's concurrency figure
CHILD_DELAY = 3             # seconds of "load" inside the child, before its reclaim
SETTLE = CHILD_DELAY + 5    # counted only after this, so late != absent

SLOW = (LAUNCHER,
        'LOCK=".loop_lock.${CALLSIGN}"',
        '[ -n "${KF_DETACHED:-}" ] && sleep %d   # H61 probe: a slow child\n'
        'LOCK=".loop_lock.${CALLSIGN}"' % CHILD_DELAY)

SLEEP_ANCHOR = ('( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &\n'
                '  sleep 1\n')
# The positive control: the sleep removed entirely, which is H29's NS arm. If this
# does not produce more than one survivor, this probe cannot see the failure it is
# looking for and every "1 survivor" below is unattributable.
NOSLEEP = (LAUNCHER, SLEEP_ANCHOR,
           '( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &\n')
# The fix: wait for the handoff instead of sleeping through it.
WAIT = (LAUNCHER, SLEEP_ANCHOR,
        '( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &\n'
        '  _h61=0\n'
        '  while [ "$_h61" -lt 100 ]; do\n'
        '    [ "$(cat "$LOCK" 2>/dev/null)" = "$$" ] || break\n'
        '    sleep 0.1; _h61=$((_h61 + 1))\n'
        '  done\n')

RUNNER = r'''#!/usr/bin/env bash
# 20 launchers on ONE callsign, at once. Same shape as the suite's simultaneity
# block, but the counting happens here so the verdict is a survivor COUNT and not
# a pass/fail of somebody else's check.
set -u
unset KF_DETACHED KF_LOCK_OWNER
mkdir -p bin prompts
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster\nRACE-1\n' > roster.txt
printf '# scratch\n' > prompts/RACE-1.md
: > reached_claude; : > race.log
for _i in $(seq 1 %(n)d); do
  ( PATH="$PWD/bin:$PATH" CALLSIGN=RACE-1 MAX_TURN=5 bash ./run_loop.sh >>race.log 2>&1 ) &
done
wait
sleep %(settle)d
echo "SURVIVORS=$(sort -u reached_claude | grep -c .)"
echo "HELD=$(grep -c 'is HELD by live launcher' race.log)"
for lkpid in $(cat .loop_lock.RACE-1 2>/dev/null); do kill "$lkpid" 2>/dev/null; done
'''


# STAGGERED ARRIVAL, and it is the only arm that can answer the row. v2's 20-at-
# once arms all came back with one survivor and 19 HELD, and the reason is not that
# the window is closed: all 20 competitors reach the lock check within the first
# instant, while the FIRST launcher's parent is still inside its 1 s sleep and
# therefore still LIVE. The window opens later -- from the parent's exit until the
# child's reclaim -- and closing it matters only for a launcher ARRIVING in it. So
# this arm arrives there on purpose: one launcher, then a second after the parent
# has exited and before a slow child has reclaimed.
#
# THE FALSIFIER FOR THIS ARM, stated before it ran: if the second launcher is
# refused as HELD under `sleep 1` + slow child, then no arrival time opens the
# window and H61 is withdrawn outright.
# THE FIRST LANE MUST STILL BE RUNNING WHEN THE SECOND ARRIVES, and the control is
# what caught that: with a stub that finishes instantly, the staggered arm reported
# 2 survivors on an UNMODIFIED tree — and that is correct behaviour, not a defect.
# Lane A had finished, its lock was stale (there is no release path, by design), so
# B reclaimed it legitimately. Two sequential lanes and two concurrent lanes were
# byte-identical in the count. So the stub holds its turn for 8 s and MAX_TURN is
# raised past it: now a second `reached_claude` pid means two lanes ALIVE on one
# callsign, which is the thing H8's lock exists to prevent.
STAGGER = r'''#!/usr/bin/env bash
set -u
unset KF_DETACHED KF_LOCK_OWNER
mkdir -p bin prompts
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
sleep 8                                   # hold the turn: A is ALIVE when B arrives
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster\nRACE-1\n' > roster.txt
printf '# scratch\n' > prompts/RACE-1.md
: > reached_claude; : > race.log
( PATH="$PWD/bin:$PATH" CALLSIGN=RACE-1 MAX_TURN=60 bash ./run_loop.sh >>race.log 2>&1 ) &
sleep %(gap)s        # after the parent's 1s sleep, before a slow child's reclaim
( PATH="$PWD/bin:$PATH" CALLSIGN=RACE-1 MAX_TURN=60 bash ./run_loop.sh >>race.log 2>&1 ) &
wait
sleep %(settle)d
echo "SURVIVORS=$(sort -u reached_claude | grep -c .)"
echo "HELD=$(grep -c 'is HELD by live launcher' race.log)"
for lkpid in $(cat .loop_lock.RACE-1 2>/dev/null); do kill "$lkpid" 2>/dev/null; done
'''


def refusals(path):
    """How many launchers this log refused as HELD. Absent log = 0, and the
    accounting check below is what turns a wrong 0 into a refused verdict."""
    if not os.path.exists(path):
        return 0
    return sum(1 for line in open(path) if 'is HELD by live launcher' in line)


def arm(name, edits, script=None, expect=None):
    t = tempfile.mkdtemp(prefix='h61_')
    try:
        falsify.build(t)
        for rel, old, new in edits:
            p = os.path.join(t, rel)
            src = open(p).read()               # READ BEFORE OPENING 'w' (H14)
            open(p, 'w').write(anchored_replace(src, old, new))
        runner = os.path.join(t, 'race.sh')
        with open(runner, 'w') as f:
            f.write(script if script else RUNNER % {'n': N, 'settle': SETTLE})
        p = subprocess.run(['bash', 'race.sh'], cwd=t, capture_output=True,
                           text=True, timeout=300)
        out = p.stdout + p.stderr
        surv = int(re.search(r'SURVIVORS=(\d+)', out).group(1))
        # WHERE the refusal is printed IS the finding (v3). `race.log` is what the
        # caller sees; the child is nohup'ed to the detach log, so a refusal there
        # is one the caller never sees and the launcher exited 0 in front of.
        held_p = refusals(os.path.join(t, 'race.log'))
        held_c = refusals(os.path.join(t, 'detach_RACE-1.log'))
        tag = ('TWO LANES ON ONE CALLSIGN' if surv > 1 else
               'none admitted' if surv == 0 else 'one lane')
        want = expect if expect is not None else N
        acct = ('' if surv + held_p + held_c == want else
                f'  UNACCOUNTED: {surv}+{held_p}+{held_c} != {want}')
        print(f'  {name:<26} survivors={surv:<3} refused_by_parent={held_p:<3} '
              f'refused_by_child={held_c:<3} {tag}{acct}', flush=True)
        # AN UNACCOUNTED LAUNCHER IS NO EVIDENCE, NOT A NEGATIVE RESULT (A29), and
        # v2 took a verdict off an arm reporting 1+0 of 2. Dump what the launchers
        # actually said rather than inferring it.
        if acct:
            for log in ('race.log', 'detach_RACE-1.log'):
                path = os.path.join(t, log)
                txt = open(path).read() if os.path.exists(path) else f'(no {log})'
                for line in [x for x in txt.splitlines() if x.strip()][-6:]:
                    print(f'        {log[:5]}| {line[:140]}', flush=True)
        return surv, held_p, held_c
    finally:
        shutil.rmtree(t, ignore_errors=True)


print(f'H61 v3 — {N} launchers on one callsign, counted after a {SETTLE}s settle\n')
c   = arm('control (as in tree)', [])
p   = arm('POSITIVE CTL: no sleep', [NOSLEEP])
s   = arm('slow child, `sleep 1`', [SLOW])
w   = arm('wait fix', [WAIT])
ws  = arm('wait fix + slow child', [WAIT, SLOW])

print()
print('STAGGERED ARRIVAL — a second launcher arriving INSIDE the handoff window')
stag = {'gap': '1.5', 'settle': SETTLE}
g     = arm('sleep 1 + slow child', [SLOW], STAGGER % stag, expect=2)
gw    = arm('wait fix + slow child', [WAIT, SLOW], STAGGER % stag, expect=2)
g_ctl = arm('control, no slow child', [], STAGGER % stag, expect=2)

STAG = {'sleep 1 + slow child': (g, 2), 'wait fix + slow child': (gw, 2),
        'control, no slow child': (g_ctl, 2)}
SIMUL = {'control': (c, N), 'positive control': (p, N), 'slow child': (s, N),
         'wait fix': (w, N), 'wait fix + slow child': (ws, N)}

print()
# FF FIRST, and before any arithmetic on these numbers. v2 printed the UNACCOUNTED
# warning and then computed a verdict from the same arm anyway; the guard has to
# be a refusal or it is a comment.
bad = [n for n, ((sv, hp, hc), want) in {**SIMUL, **STAG}.items()
       if sv + hp + hc != want]
if bad:
    print(f'  PROBLEM  FF FIRED on: {", ".join(bad)}. Launchers are unaccounted '
          'for, so those arms are NO EVIDENCE and no verdict is computed from '
          'them (A29). Read the dumped log lines above.')
    sys.exit(2)
if p[0] <= 1:
    print('  PROBLEM  FB FIRED: the positive control did not produce a double '
          f'admission (survivors={p[0]}). This probe cannot see the failure it is '
          'looking for, so nothing above is evidence in either direction (A29).')
    sys.exit(2)
print(f'FB ok: the positive control admits {p[0]} lanes on one callsign, so a '
      'double admission IS visible to this probe.')
print(f'FA: slow child under `sleep 1`, 20 at once -> survivors={s[0]}, '
      f'parent-refused={s[1]}, child-refused={s[2]}')
print(f'FC: the wait fix -> {w[0]}/{w[1]}/{w[2]} clean, {ws[0]}/{ws[1]}/{ws[2]} '
      'with the slow child (survivors/parent/child)')
for n, ((sv, hp, hc), _) in STAG.items():
    print(f'FD/FE  stagger {n:<24} survivors={sv} parent-refused={hp} '
          f'child-refused={hc}')
print()

# THE ROW TURNS ON WHO REFUSES, NOT ON THE SURVIVOR COUNT. Both are printed above;
# the branch below reads the discriminator v2 could not see.
if g[0] > 1:
    print('H61 STANDS AS FILED: the staggered arrival puts TWO LANES ON ONE '
          f'CALLSIGN under `sleep 1` ({g[0]} survivors).')
elif g[1] == 0 and g[2] >= 1 and gw[1] >= 1:
    print('H61 IS RESTATED, AGAINST THE ROW AS I FILED IT, AND IT IS NOT A DOUBLE '
          'ADMISSION. Under `sleep 1` + a slow child the second launcher IS '
          'refused — but by the CHILD, into `detach_$CALLSIGN.log`, seconds after '
          'its parent printed `detached` and exited 0. The caller is told the lane '
          'launched and it did not. That is verbatim the failure '
          '`run_loop.sh:232-234` says the pre-fork acquisition exists to prevent. '
          f'Under the condition wait the refusal is back in the PARENT '
          f'({gw[1]} parent-refused, {gw[2]} child-refused), in front of the '
          'caller, with a non-zero exit.')
elif g[1] >= 1:
    print('FD FIRED: the parent refuses even under a slow child, so the pre-fork '
          'acquisition holds under load and H61 IS WITHDRAWN OUTRIGHT. The fix is '
          'unnecessary; do not ship it.')
    sys.exit(1)
else:
    print(f'NO VERDICT: staggered arm reads survivors={g[0]} parent={g[1]} '
          f'child={g[2]}, which none of the stated falsifiers describes.')
    sys.exit(2)
if gw[2] >= 1:
    print('FE FIRED: under the condition wait the refusal is still in the child. '
          'Do not ship it.')
    sys.exit(1)
if w[0] == 1 and w[1] == N - 1 and ws[0] == 1 and ws[1] == N - 1:
    print('THE FIX HOLDS AND DOES NOT REGRESS SIMULTANEITY: exactly one survivor '
          'and 19 parent-side refusals with and without the slow child.')
else:
    print('FC FIRED: the wait fix does not give one survivor and 19 parent-side '
          'refusals in both arms. Do not ship it.')
    sys.exit(1)
