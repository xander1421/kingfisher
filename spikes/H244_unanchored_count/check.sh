#!/bin/sh
# H244 runnable check (§12.3) — fails when the anchor breaks.
# Every assertion names the input that would make it fail.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 3
CC=spikes/harness/channelcount.sh
fail=0
ok()  { echo "  ok   $1"; }
bad() { echo "  BAD  $1"; fail=1; }

echo "--- 1 · the anchor holds across the rotation this row is about ---"
# FAILS IF: channelcount stops reading history and reads the file.
a=$(KF_REV=b9a1b33 sh $CC total); b=$(KF_REV=228fc46 sh $CC total); c=$(sh $CC total)
if [ "$a" -le "$b" ] && [ "$b" -le "$c" ]; then
  ok "monotonic across the rotation: $a -> $b -> $c"
else
  bad "NOT monotonic: b9a1b33=$a 228fc46=$b HEAD=$c -- the anchor is not an anchor"
fi

echo "--- 2 · the defect is still reproducible from the file alone ---"
# FAILS IF: someone un-rotates CHANNEL.md, which would make this row historical.
f=$(git show 228fc46:CHANNEL.md | grep -c '^DONE')
if [ "$f" -lt "$a" ]; then
  ok "the unanchored form still collapses at 228fc46: $a -> $f"
else
  bad "the unanchored form reads $f at 228fc46, not below $a -- the fixture is gone"
fi

echo "--- 3 · the four lanes the rotation erased are visible again ---"
# FAILS IF: the per-lane anchor regresses to reading the working file.
for l in GROK-LOCAL GEMINI GROK-2 BUILDER-1; do
  n=$(sh $CC lane "$l"); w=$(grep -cE "^DONE [^ ]+ $l( |\$)" CHANNEL.md)
  if [ "$n" -gt 0 ] && [ "$w" = 0 ]; then
    ok "$l: anchored $n, current file $w"
  else
    bad "$l: anchored=$n file=$w -- expected a positive anchored count over an empty file"
  fi
done

echo "--- 4 · bringup's third state exists and is distinct ---"
# FAILS IF: the -2 branch is removed and a rotated-out lane reads as never-seen.
if grep -q 'PREDATES THE CURRENT FILE' bringup.sh && grep -q 'echo -2; return' bringup.sh; then
  ok "lane_lastwork distinguishes 'predates the file' from 'never observed'"
else
  bad "bringup.sh lost the -2 state -- a rotated-out lane reads as NO CHANNEL LINE EVER again"
fi

echo "--- 5 · the contract cites the anchored command ---"
# FAILS IF: §14.2 reverts to the unanchored grep.
if grep -q 'channelcount.sh total' MISSION_LOOP.md; then
  ok "MISSION_LOOP §14.2 cites the anchored command"
else
  bad "MISSION_LOOP no longer cites channelcount.sh -- §14.2 is back on the file"
fi

echo "--- 6 · the module's own suite ---"
if sh $CC --selfcheck >/dev/null 2>&1; then ok "channelcount --selfcheck PASS (7 arms)"
else bad "channelcount --selfcheck FAILED"; sh $CC --selfcheck; fi

echo "--- 7 · a silent instrument has no verdict (errors 42/44) ---"
# FAILS IF: a dead git call is allowed to report 0 rather than refuse.
out=$(KF_REV=deadbeefdeadbeef sh $CC total 2>&1); rc=$?
if [ "$rc" = 3 ]; then ok "an unresolvable rev REFUSES rather than counting 0"
else bad "bad rev -> rc=$rc out='$out'"; fi

[ "$fail" = 0 ] && echo "check.sh: PASS" || echo "check.sh: FAIL"
exit "$fail"
