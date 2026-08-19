#!/usr/bin/env bash
# H121 probe. Falsifier: if killing the wrapper still reaps the turn after MAX_TURN,
# the row is withdrawn.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail=0
say() { printf '%s\n' "$*"; }
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-6s %-4s %s\n' "$1" "$2" "$3"; }

alive() { pgrep -f '^h121stubproc' >/dev/null 2>&1; }
cleanup() { pkill -f '^h121stubproc' 2>/dev/null || true; rm -f .loop_turn_gen.PROBE-H121; }
trap cleanup EXIT
cleanup

say "=== CURRENT pattern (child dog, parent exits) ==="
bash ./pattern_current.sh 2
sleep 0.4
if alive; then
  ctl C3 PASS "turn still live 0.4s after wrapper exit"
else
  ctl C3 FAIL "turn died immediately — not measuring an orphan"
fi
sleep 3
if alive; then
  say "  current: turn survived MAX_TURN=2 after wrapper death"
  CUR=DEFECT_PRESENT
  ctl C1 PASS "current pattern leaves orphan unbounded (the row)"
else
  say "  current: turn reaped (F2 would withdraw if this IS live run_loop)"
  CUR=DEFECT_ABSENT
  ctl C1 FAIL "current pattern already reaps — F2 fire if this is the shipped watchdog"
fi
cleanup

say ""
say "=== FIXED pattern (disowned dog + generation) ==="
bash ./pattern_fixed.sh 2 .loop_turn_gen.PROBE-H121
sleep 0.4
if alive; then
  ctl C4 PASS "turn live immediately after wrapper exit (dog has not yet fired)"
else
  ctl C4 FAIL "fixed pattern killed the turn before MAX_TURN"
fi
sleep 3
if alive; then
  ctl C5 FAIL "fixed pattern did not reap after MAX_TURN"
  FIX=DEFECT_PRESENT
else
  ctl C5 PASS "fixed pattern reaped the orphan after MAX_TURN"
  FIX=DEFECT_ABSENT
fi
cleanup

say ""
say "=== generation skip (new gen must not be killed by old dog) ==="
bash ./pattern_fixed.sh 2 .loop_turn_gen.PROBE-H121
sleep 0.2
printf '9999999999\n' > .loop_turn_gen.PROBE-H121
sleep 3
if alive; then
  ctl C6 PASS "old dog skipped after generation change"
else
  ctl C6 FAIL "old dog reaped a later generation"
fi
cleanup

say ""
say "=== VERDICT ==="
say "current=$CUR fixed_reap=$FIX"
if [ "$fail" = 0 ] && [ "$CUR" = DEFECT_PRESENT ] && [ "$FIX" = DEFECT_ABSENT ]; then
  say "H121 pattern CONFIRMED then FIXED (sandbox). Apply the same shape to run_loop.sh."
  exit 0
fi
say "H121 probe not closed. fail=$fail current=$CUR fix=$FIX"
exit 1
