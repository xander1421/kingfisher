#!/bin/sh
# H210 check. Fails if depcheck breaks OR if the finding silently evaporates.
# Deliberately does NOT re-run the full sweep: the tree is live and the counts
# move. It asserts the instrument's own arms and the named instance.
set -e
cd "$(dirname "$0")/../.."

echo "--- depcheck selfcheck (four-sided + declared-ignore) ---"
python3 spikes/harness/depcheck.py --selfcheck

echo "--- the instance: H188/H200 -> S91, resolved by AST, still untracked ---"
python3 - <<'PY'
import sys
sys.path.insert(0, 'spikes/harness')
import depcheck
hits, _ = depcheck.scan('.')
pairs = {(h['file'], h['dep']) for h in hits
         if 'AST' in h['modes'] and h['dep_status'] == 'UNTRACKED'}
want = ('spikes/H188_seats_are_one_computation/attack.py',
        'spikes/S91_multi_agent_quorum/run.py')
tracked, _d = depcheck.tracked_set('.')
if want[1] in tracked:
    print('  S91/run.py is now TRACKED -- the instance is CLOSED, not broken.')
    sys.exit(0)
assert want in pairs, f'AST mode lost its motivating pair: {want}'
assert len(pairs) > 1, 'sweep degenerated to a single pair (F2 would now fire)'
print(f'  ok  {want[0]} -> {want[1]}   ({len(pairs)} untracked executable pairs)')
PY
