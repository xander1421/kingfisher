#!/bin/sh
# H257 runnable check (§12.3). Each assertion names the input that would fail it.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 3
fail=0; ok() { echo "  ok   $1"; }; bad() { echo "  BAD  $1"; fail=1; }

echo "--- 1 · the two hits are real, verified against the PARENT BLOB not the diff ---"
# FAILS IF: a hit's block already existed in the parent, i.e. a false accusation (H105's 8%).
for pair in "bb2c229:PREDATES THE CURRENT FILE" "d066c4b:v2 (H88, AGENT-1"; do
  c=${pair%%:*}; s=${pair#*:}
  p=$(git show "$c^:bringup.sh" 2>/dev/null | grep -cF "$s")
  n=$(git show "$c:bringup.sh"  2>/dev/null | grep -cF "$s")
  if [ "$p" = 0 ] && [ "$n" -ge 1 ]; then ok "$c introduced it (parent $p -> commit $n)"
  else bad "$c: parent=$p commit=$n -- the block predates the commit, this is a false accusation"; fi
done

echo "--- 2 · neither hit declared the lane it names ---"
# FAILS IF: someone amends history, which §13 forbids -- so this going red is itself a finding.
for c in bb2c229 d066c4b; do
  car=$(git log -1 --format='%(trailers:key=Carries,valueonly,separator=%x20)' $c | tr -d ' \n')
  if [ -z "$car" ]; then ok "$c still carries no Carries: trailer"
  else bad "$c now declares Carries:[$car] -- history was rewritten, which §13 forbids"; fi
done

echo "--- 3 · the detector still finds them, and finds nothing else ---"
# FAILS IF: the pattern is loosened back toward v0 (33% false) or tightened to blindness.
n=$(sh spikes/harness/codecarry.sh 400 | grep -c 'names:')
if [ "$n" = 2 ]; then ok "2 hits over the same 400-commit window"
else bad "detector returned $n hits, not 2 -- pattern drifted, re-measure the precision"; fi

echo "--- 4 · the scan cannot report clean because it did not run ---"
out=$(sh spikes/harness/codecarry.sh 0 2>&1); rc=$?
if [ "$rc" = 3 ]; then ok "a 0-commit scan REFUSES rather than printing 0 hits"
else bad "0-commit scan rc=$rc out='$out'"; fi

echo "--- 5 · the module's own suite ---"
if sh spikes/harness/codecarry.sh --selfcheck >/dev/null 2>&1; then ok "codecarry --selfcheck PASS (6 arms + fixture self-assertion)"
else bad "codecarry --selfcheck FAILED"; sh spikes/harness/codecarry.sh --selfcheck; fi

echo "--- 6 · the severity limit is still stated in the artifact ---"
# FAILS IF: someone edits sweep.json to drop the 1-of-2-functional downgrade.
if grep -q '"functional_captures": 1' spikes/H257_shared_code_capture/sweep.json \
  && grep -q '"attributional_only_captures": 1' spikes/H257_shared_code_capture/sweep.json; then
  ok "sweep.json still records 1 functional / 1 attributional, not 2 captures unqualified"
else bad "sweep.json no longer carries the F3 downgrade"; fi

[ "$fail" = 0 ] && echo "check.sh: PASS" || echo "check.sh: FAIL"
exit "$fail"
