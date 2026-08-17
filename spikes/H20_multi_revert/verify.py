#!/usr/bin/env python3
"""H20 — the two checks are reachable now, and the repair disarmed nothing.

Falsifiers, stated before the run:
  V1  control still all-green .................. else the repair reddens a clean tree
  V2  "writes no 'unknown' marker" reds under the LANE-default defect ALONE
  V3  "lane signal untouched" reds under the PAIR
  V4  neither reds under either single revert other than V2's
  V5  the LANE-default defect still reddens AT LEAST as many checks as before
      the repair (6) -- the disarming test, which is the one the obvious fix
      would have failed
"""
import os, shutil, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'H7_harness_attack'))
import falsify                                                     # noqa: E402

GATE = '.claude/hooks/loop_gate.sh'
A = (GATE, 'if [ -z "${CALLSIGN:-}" ]; then\n  exit 0\nfi\nLANE="$CALLSIGN"',
     'LANE="${CALLSIGN:-unknown}"')
B = (GATE, 'for SIGFILE in ".loop_signal.${LANE}"; do',
     'for SIGFILE in .loop_signal.*; do')
MARKER, SIGNAL = "writes no 'unknown' marker", 'lane signal untouched'


def arm(name, edits):
    t = tempfile.mkdtemp(prefix='h20v_')
    try:
        falsify.build(t)
        falsify.apply_edits(t, edits)
        passed, failed, _ = falsify.run_suite(t)
        red = [w for w in (MARKER, SIGNAL) if any(w in f for f in failed)]
        print(f'  {name:<14} {len(passed)} pass / {len(failed)} fail; '
              f'target red: {red if red else "neither"}', flush=True)
        return red, passed, failed
    finally:
        shutil.rmtree(t, ignore_errors=True)


c, cp, cf = arm('control', [])
a, _, af = arm('A (unknown)', [A])
b, _, _ = arm('B (glob sig)', [B])
ab, _, _ = arm('A+B', [A, B])
V = [('V1 control all-green', not cf and bool(cp)),
     ('V2 marker reds under A alone', MARKER in a),
     ('V3 signal reds under the pair', SIGNAL in ab),
     ('V4 signal quiet under either alone', SIGNAL not in a and SIGNAL not in b),
     ('V5 A still reddens >= 6 checks', len(af) >= 6)]
print()
for n, ok in V:
    print(f'  {"PASS" if ok else "FAIL"}  {n}')
print(f'\n  (A reddens {len(af)} checks; it reddened 6 before this repair)')
sys.exit(0 if all(ok for _, ok in V) else 1)
