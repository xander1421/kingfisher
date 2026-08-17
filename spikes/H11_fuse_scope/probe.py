#!/usr/bin/env python3
"""H11 — what does the runaway fuse actually count, and can it fire for the
runaway this repo has actually had?

The row says `run_loop.sh` clears `.loop_blocks.$CALLSIGN` at every span start,
so `MAX_BLOCKS`=400 can only be reached inside ONE `claude -p`, and the hook's own
comment (`loop_gate.sh:91-97`) concludes it "cannot fire for the runaway it exists
to stop". Both halves are prose about the code. This measures them.

FIRST OBSERVATION, before any code, and it is what made the row worth taking:
`ls .loop_blocks.*` at the repo root returns NOTHING for any of the five live
lanes. A lane that had ended one turn in its current span would have a file.

FALSIFIERS, STATED BEFORE THE FIRST RUN (posted to CHANNEL.md at claim time):

  FA  a scratch span drives the hook and the counter does NOT climb -> the
      counter is broken outright, not mis-scoped, and the row understates it
  FB  a simulated CROSS-SPAN crash loop -- the shape that actually happened here
      (H56: 18 consecutive instant-exit turns on "You've hit your session limit")
      -- increments the counter at all -> the row's premise is wrong, withdraw it
  FC  the counter PERSISTS across spans in the scratch launcher -> the clear at
      `run_loop.sh:387` is not what the row says it is, withdraw it
  FD  no arm makes the fuse fire -> the probe never reached its target and has
      produced no evidence in either direction (A29), no verdict is taken

ISOLATION: the gate copy's pinned ROOT is rewritten to the scratch tree and the
rewrite is ASSERTED, because a no-op there points the copy at the live workspace
and eats a running lane's terminal signal. Same guard, same reason, as
`test_loop_gate.sh`'s.

usage:  python3 spikes/H11_fuse_scope/probe.py
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
import falsify                                                     # noqa: E402

CS = 'FUSE-1'
SPANS = 3


def scratch():
    """A scratch harness with the gate's ROOT repointed at it."""
    t = tempfile.mkdtemp(prefix='h11_')
    falsify.build(t)
    gate = os.path.join(t, '.claude', 'hooks', 'loop_gate.sh')
    src = open(gate).read()
    out = re.sub(r'^ROOT=.*$', f'ROOT="{t}"', src, count=1, flags=re.M)
    assert f'\nROOT="{t}"\n' in out, 'ROOT anchor did not match; refusing to run'
    open(gate, 'w').write(out)
    os.chmod(gate, 0o755)
    os.makedirs(os.path.join(t, 'prompts'), exist_ok=True)
    open(os.path.join(t, 'prompts', f'{CS}.md'), 'w').write('# scratch\n')
    open(os.path.join(t, 'roster.txt'), 'w').write(f'# scratch\n{CS}\n')
    return t


def counter(t, name=None):
    p = os.path.join(t, name or f'.loop_blocks.{CS}')
    if not os.path.exists(p):
        return 'ABSENT'
    return open(p).read().strip() or 'EMPTY'


def a1_within_span():
    """Drive the gate the way a turn end does, with a small cap. If this does not
    climb and fire, nothing below is evidence (FA/FD)."""
    t = scratch()
    try:
        gate = os.path.join(t, '.claude', 'hooks', 'loop_gate.sh')
        env = dict(os.environ, CALLSIGN=CS, MAX_BLOCKS='3')
        seen = []
        for _ in range(5):
            subprocess.run(['bash', gate], cwd=t, env=env, capture_output=True,
                           stdin=subprocess.DEVNULL)
            seen.append(counter(t))
        mark = counter(t, f'.loop_exit.{CS}')
        print(f'  A1 within one span, MAX_BLOCKS=3   counter after each stop: '
              f'{",".join(seen)}   exit marker: {mark}')
        return seen, mark
    finally:
        shutil.rmtree(t, ignore_errors=True)


STUB_RUNS = r'''#!/usr/bin/env bash
# An agent that RUNS and ends its turn twice, which is what makes the Stop hook
# fire. `claude` is what invokes the hook in production; the stub does it here.
n=$(( $(cat spans 2>/dev/null || echo 0) + 1 )); echo "$n" > spans
bash .claude/hooks/loop_gate.sh </dev/null >/dev/null 2>&1
bash .claude/hooks/loop_gate.sh </dev/null >/dev/null 2>&1
echo "span ${n}: $(cat ".loop_blocks.${CALLSIGN}" 2>/dev/null || echo ABSENT)" >> seen.log
[ "$n" -ge %(spans)d ] && touch "STOP.${CALLSIGN}"
exit 0
'''

STUB_DIES = r'''#!/usr/bin/env bash
# THE RUNAWAY THAT ACTUALLY HAPPENED (H56): claude exits instantly and the agent
# never runs, so no turn ever ends and the Stop hook is never invoked.
n=$(( $(cat spans 2>/dev/null || echo 0) + 1 )); echo "$n" > spans
echo "span ${n}: $(cat ".loop_blocks.${CALLSIGN}" 2>/dev/null || echo ABSENT)" >> seen.log
[ "$n" -ge %(spans)d ] && touch "STOP.${CALLSIGN}"
echo "You've hit your session limit"
exit 1
'''


def spans_arm(name, stub):
    """Run the REAL launcher for SPANS spans against a stub claude."""
    t = scratch()
    try:
        os.makedirs(os.path.join(t, 'bin'), exist_ok=True)
        p = os.path.join(t, 'bin', 'claude')
        open(p, 'w').write(stub % {'spans': SPANS})
        os.chmod(p, 0o755)
        env = dict(os.environ,
                   PATH=os.path.join(t, 'bin') + os.pathsep + os.environ['PATH'],
                   CALLSIGN=CS, KF_DETACHED='1', MAX_TURN='30',
                   BACKOFF_STEP='1')
        env.pop('KF_LOCK_OWNER', None)
        subprocess.run(['bash', './run_loop.sh'], cwd=t, env=env,
                       capture_output=True, text=True, timeout=180)
        log = os.path.join(t, 'seen.log')
        seen = open(log).read().split('\n') if os.path.exists(log) else []
        seen = [x for x in seen if x.strip()]
        fails = counter(t, f'.loop_fails.{CS}')
        print(f'  {name}')
        for line in seen:
            print(f'      {line}')
        print(f'      after the loop: .loop_blocks={counter(t)}  '
              f'.loop_fails={fails}')
        return seen, counter(t), fails
    finally:
        shutil.rmtree(t, ignore_errors=True)


print(f'H11 — what the fuse counts. {SPANS} spans per launcher arm.\n')
seen1, mark1 = a1_within_span()
print()
seen2, blocks2, fails2 = spans_arm(
    'A2 across spans, the agent RUNS and ends two turns per span:', STUB_RUNS)
print()
seen3, blocks3, fails3 = spans_arm(
    'A3 across spans, CRASH LOOP — claude exits instantly, no turn ever ends:',
    STUB_DIES)
print()

# FD first: an arm that never reached its target is not a negative result.
if seen1[-1] != '5' or mark1 != 'LOOP-FUSE':
    print(f'  PROBLEM  FD/FA FIRED: driving the gate 5 times under MAX_BLOCKS=3 '
          f'gave counter={seen1} marker={mark1}, not 1..5 / LOOP-FUSE. The fuse '
          'was not reached, so nothing below is evidence either way (A29).')
    sys.exit(2)
print(f'FA/FD ok: inside one span the counter climbs {",".join(seen1)} and the '
      'hook writes LOOP-FUSE past MAX_BLOCKS. The mechanism works where it is '
      'driven, so the arms below measure SCOPE and not breakage.')

per_span = [ln.split(': ', 1)[1] for ln in seen2]
if per_span and per_span[-1] not in ('ABSENT', '0'):
    counts = [c for c in per_span if c.isdigit()]
    if counts and any(int(c) > 2 for c in counts):
        print('FC FIRED: the counter PERSISTS across spans — '
              f'{per_span} — so the clear at run_loop.sh:387 is not what the row '
              'says it is. H11 is withdrawn.')
        sys.exit(1)
print(f'FC did not fire: every span ENDS at the same value ({per_span}) after the '
      f'same two turn ends, and the final on-disk count is {blocks2} rather than '
      f'{2 * SPANS} — the count does not accumulate across spans.')

if blocks3 != 'ABSENT' or any(x.split(': ', 1)[1] != 'ABSENT' for x in seen3):
    print('FB FIRED: the crash loop DID increment the fuse counter — '
          f'{[x.split(": ", 1)[1] for x in seen3]}. The row\'s premise is wrong '
          'and H11 is withdrawn.')
    sys.exit(1)
print(f'FB did not fire, and this is the row: across {SPANS} crash-loop spans the '
      f'fuse counter is {blocks3} at every observation while .loop_fails reaches '
      f'{fails3}. The fuse counts BLOCKED STOPS, and a blocked stop exists only '
      'when the agent RAN and tried to end a turn. In the runaway this fleet '
      'actually had — 18 consecutive instant-exit spans on "You\'ve hit your '
      'session limit" (H56) — claude never ran, so the counter never moved.')
print()
print('VERDICT: H11 STANDS, and it is narrower and sharper than filed. The fuse '
      'is not broken and its per-span scope is not wrong: it bounds ONE span, '
      'which is exactly what MISSION_LOOP §7 says LOOP-FUSE means ("a session '
      'span ended"). What is wrong is `loop_gate.sh`\'s name for it — "runaway '
      'fuse" — and the reading that follows from it. It cannot see a runaway in '
      'which the agent never runs, which is the only kind this repo has '
      'recorded. The counter for that already exists and is a different '
      'mechanism: `.loop_fails.$CALLSIGN` (H56, run_loop.sh v9 defect 12).')
