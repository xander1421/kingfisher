#!/usr/bin/env python3
"""ATTACK on rostercheck.py — my own instrument, shipped one hour ago (§2:
instruments before conclusions, self-authored data first).

THREE FALSIFIERS, STATED BEFORE RUNNING. Each one, if it fires, means the
checker reports "one roster" over a tree that has two.

  F1  A lane list written as a BASH ARRAY -- `LANES=(A B C)` -- is invisible to
      the regex, which requires a double-quoted scalar. bringup.sh already uses
      the array form for its own roster loop, so this is not hypothetical syntax.
  F2  A lane list in PYTHON -- `LANES = ["A", "B"]` -- same. rostercheck.py scans
      .py files in spikes/harness/ and would not see a lane set in one.
  F3  A SINGLE-QUOTED scalar -- LANES='A B' -- differs from the matched form by
      one character.

A checker that misses all three is not "scoped"; it is a checker whose green run
means only that nobody used a different quote. That is family A -- the instrument
cannot produce the answer -- and it is the H26 class I cited in my own v4 header.
"""
import os, shutil, sys, tempfile, io, contextlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import rostercheck                                                # noqa: E402

CASES = [
    ('F1 bash array',   'LANES=(' + 'AGENT-1 ok-9)'),
    ('F2 python list',  'LANES = [' + '"AGENT-1", "ok-9"]'),
    ('F3 single quote', "LANES='" + "AGENT-1 ok-9'"),
    ('CONTROL dquote',  'LANES=' + '"AGENT-1 ok-9"'),
]
missed = []
for name, decl in CASES:
    t = tempfile.mkdtemp(prefix='h38a_')
    try:
        os.makedirs(os.path.join(t, 'spikes', 'harness'))
        open(os.path.join(t, 'roster.txt'), 'w').write('AGENT-1\nAGENT-2\n')
        ext = '.py' if 'python' in name else '.sh'
        open(os.path.join(t, 'spikes', 'harness', 'sup' + ext), 'w').write(decl + '\n')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = rostercheck.scan(t)
        caught = rc == 1 and 'ok-9' in buf.getvalue()
        print(f"  {'SEES  ' if caught else 'BLIND '} {name}")
        if not caught and not name.startswith('CONTROL'):
            missed.append(name)
        if not caught and name.startswith('CONTROL'):
            missed.append(name + ' (the control itself failed -- this attack proves nothing)')
    finally:
        shutil.rmtree(t, ignore_errors=True)

print()
if missed:
    print('ATTACK SUCCEEDS: rostercheck.py is blind to', missed)
    print('A green run means only that nobody wrote the list in another form.')
    sys.exit(1)
print('ATTACK FAILS: every divergent form is caught')
