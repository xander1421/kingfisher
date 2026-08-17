#!/bin/sh
# H73 <-> H72 reconciliation, and it is a check rather than a note.
#
# ATTACKER-1 shipped `spikes/harness/commit_scoped.sh` v2 (H72) EIGHT MINUTES
# after AGENT-1's H71 landed -- mtime 17:22:31 against commit 09c8717 at
# 17:14:43 -- and it cites the `git add -N` sentence H71 put into §13. So the two
# lanes converged on one defect an hour apart from opposite sides: H72 built a
# wrapper that restores the checks `--no-verify` drops and SCOPES the tree-wide
# verdict; H73 measured that the tree-wide scope is what freezes the fleet and
# proposed scoping the hook itself (H75).
#
# THE QUESTION THIS SCRIPT ANSWERS MECHANICALLY, because "their tool would have
# helped me" is exactly the kind of thing that is obvious and wrong:
# would H72's predicate have cleared the ACTUAL 20-minute block H73 records?
#
# Both arms are driven through H72's own DRY_RUN seam with its real refusal text.
# The second arm is the one that makes the first mean anything -- a wrapper that
# proceeds on everything would pass arm 1 and is useless (H68's "never refuses
# anything satisfies C1").
#
#   sh spikes/H73_gate_scope/reconcile_h72.sh
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
W=spikes/harness/commit_scoped.sh
D=spikes/H73_gate_scope
fails=0

[ -f "$W" ] || { echo "SKIP — $W is not on disk (it was untracked when this was written)"; exit 0; }

printf 'S1: a finding was recorded here\n\nAtom: AGENT-1\nClaude-Session: unassigned\nReviewed-By: unreviewed\n' > "$D/_msg.txt"

# ARM 1 — H73's real block: the refusal names ok-1's file, the commit carries mine.
printf 'UNRESOLVED spikes/harness/test_loop_gate.sh: `spikes/H61_lock_handoff/RESULT.md` does not exist\nREFUSE: 1 citation(s) in the harness do not resolve.\n' > "$D/_inject.txt"
rc=0
DRY_RUN=1 CHECKERS_OUT_FILE=$D/_inject.txt CHECKERS_RC=1 \
  sh "$W" "$D/_msg.txt" spikes/S36_witnessed_job/RESULT.md >"$D/_out1.txt" 2>&1 || rc=$?
if [ "$rc" -eq 0 ] && grep -q 'would commit, all gates passed' "$D/_out1.txt"; then
  echo "PASS  arm 1 — H72's wrapper CLEARS H73's actual block (rc=0)"
else
  echo "FAIL  arm 1 — expected rc=0 and a proceed, got rc=$rc"; fails=$((fails+1))
fi

# ARM 2 — the null. Same wrapper, refusal now names a path the commit DOES carry.
printf 'UNRESOLVED spikes/S36_witnessed_job/RESULT.md: `spikes/nope/RESULT.md` does not exist\nREFUSE: 1 citation(s) in the harness do not resolve.\n' > "$D/_inject2.txt"
rc=0
DRY_RUN=1 CHECKERS_OUT_FILE=$D/_inject2.txt CHECKERS_RC=1 \
  sh "$W" "$D/_msg.txt" spikes/S36_witnessed_job/RESULT.md >"$D/_out2.txt" 2>&1 || rc=$?
# The pattern is COPIED FROM THE EMITTING LINE, not recalled. The first draft
# grepped `names a path your commit carries`; the script prints "the tree-wide
# checkers NAME a path your commit carries". Arm 2 went red on a working wrapper.
# That is defect 1 of `commit_scoped.sh` v2's own header -- vocabulary invented by
# eye instead of resolved against the code that emits it -- reproduced by the lane
# checking that file, one screen below where it is written down.
if [ "$rc" -ne 0 ] && grep -q 'name a path your commit carries' "$D/_out2.txt"; then
  echo "PASS  arm 2 — and REFUSES when the refusal names the commit's own path (rc=$rc)"
else
  echo "FAIL  arm 2 — expected a refusal, got rc=$rc"; fails=$((fails+1))
fi

rm -f "$D"/_msg.txt "$D"/_inject.txt "$D"/_inject2.txt "$D"/_out1.txt "$D"/_out2.txt
echo
if [ "$fails" -ne 0 ]; then
  echo "reconcile_h72: $fails FAILED"
  exit 1
fi
cat <<'NOTE'
reconcile_h72: both arms pass.

WHAT THIS SETTLES, AND WHAT IT DOES NOT
  SETTLED: H73's 20-minute block was avoidable with a tool that already existed
  in the tree, and H75 as originally written -- "change the hook" -- is no longer
  the only route. The wrapper's predicate is the same predicate H75 proposes,
  applied at the caller instead of in the hook.
  NOT SETTLED, and it is the reason H75 stays open rather than closing: the
  wrapper is OPT-IN. A lane that does not know it exists is blocked exactly as
  H73 measured, and H15 already recorded that "a check that reports but does not
  gate is prose with extra steps" -- the same argument applies to a remedy nobody
  is routed to. H73's own case is the evidence: the wrapper was on disk while
  AGENT-1 held two green cycles for twenty minutes.
NOTE
