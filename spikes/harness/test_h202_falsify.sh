#!/usr/bin/env bash
# test_h202_falsify.sh v1 — ok-1, H202, 2026-08-19.
#
# THE FALSIFIER FOR test_loop_gate.sh's COVERAGE GUARD. That guard says every
# marker the hook ACCEPTS is driven end to end by the suite. Its only red run so
# far was an accident during its own development, and §5 is explicit: a control
# that cannot fail is not a control, and you state the input that makes it fail.
#
# THE INPUT: a hook carrying a FOURTH terminal marker that no check drives. The
# suite must go RED and must NAME it. If it stays green, the guard is inert and
# the next marker added to the hook is unverified exactly as LOOP-DONE was.
#
# usage: bash spikes/harness/test_h202_falsify.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT="$PWD"; SB="$ROOT/.scratch/h202_falsify"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }
rm -rf "$SB"; mkdir -p "$SB"

sed 's/LOOP-DONE|LOOP-HALT|LOOP-IDLE)/LOOP-DONE|LOOP-HALT|LOOP-IDLE|LOOP-NEVER)/' \
    "$ROOT/.claude/hooks/loop_gate.sh" > "$SB/gate_with_4th.sh"
# THE MUTATION IS ASSERTED. A sed whose anchor is absent returns the input
# unchanged, and this whole file would then be testing the shipped hook and
# reporting a pass -- the no-op-edit defect CLAUDE.md's Editing section names.
ctl C1 "$([ "$(grep -c 'LOOP-NEVER)' "$SB/gate_with_4th.sh")" = 1 ] && echo PASS || echo FAIL)" \
    "the fourth marker reached the accept branch"

OUT=$(KF_TEST_GATE="$SB/gate_with_4th.sh" bash "$ROOT/spikes/harness/test_loop_gate.sh" 2>&1)
printf '%s\n' "$OUT" > "$SB/red_run.txt"

case "$OUT" in
  *"H202: every marker the hook ACCEPTS is driven end-to-end here (want '0', got '1')"*)
     ctl A1 PASS "an undriven marker turns the guard RED" ;;
  *) ctl A1 FAIL "the guard stayed green over an undriven marker -- it is inert: $(printf '%s' "$OUT" | grep -m1 'H202: every')" ;;
esac
case "$OUT" in
  *"the hook accepts LOOP-NEVER and this suite never drives it per-lane"*)
     ctl A2 PASS "and it NAMES the marker, so a reader sees WHICH" ;;
  *) ctl A2 FAIL "the guard went red without naming the marker" ;;
esac
# TWO-SIDED. Without this, A1 would also pass on a suite that is red for any
# reason at all -- including the seam pointing at a broken hook.
OUT2=$(KF_TEST_GATE="$ROOT/.claude/hooks/loop_gate.sh" bash "$ROOT/spikes/harness/test_loop_gate.sh" 2>&1)
case "$OUT2" in
  *"checks pass") ctl A3 PASS "the SAME suite is green on the unmutated hook: $(printf '%s' "$OUT2" | tail -1)" ;;
  *) ctl A3 FAIL "the suite is red on the shipped hook too, so A1 measured nothing: $(printf '%s' "$OUT2" | tail -1)" ;;
esac
# The seam must be OFF by default, or every real run is about a fixture.
grep -q 'KF_TEST_GATE:-\$ROOT' "$ROOT/spikes/harness/test_loop_gate.sh" \
  && ctl C2 PASS "the seam defaults to the shipped hook (unset in every real run)" \
  || ctl C2 FAIL "the seam is not defaulted"

[ "$fail" = 0 ] && echo "H202 falsifier: all arms as stated" || echo "H202 falsifier: FAILED"
exit "$fail"
