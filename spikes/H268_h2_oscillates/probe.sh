#!/usr/bin/env bash
# H268 — H2's closing condition is a MONITOR's state, not a row's verdict.
# ok-1, 2026-08-19, ATTACK cycle 40.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1";
       else fail=$((fail+1)); printf '  FAIL  %s (want %s, got %s)\n' "$1" "$3" "$2"; fi; }

echo "H268 — the three code halves of H2, and the state of its closing condition"

# F1 · THE CODE HALVES. H2 names three defects. Each is checked against the file
# as it stands, not against the row's prose about it.
echo "F1 · the three defects H2 names, in the launcher as it stands"
prose=$(grep -cE "grep -q .?(LOOP-DONE|LOOP-HALT|LOOP-IDLE)" run_loop.sh || true)
ck "  the launcher does not decide the loop is over by grepping its own log" "$prose" "0"
ck "  backoff exists"        "$([ "$(grep -c 'BACKOFF_STEP' run_loop.sh)" -ge 1 ] && echo yes || echo no)" "yes"
ck "  hang watchdog exists"  "$([ "$(grep -c 'MAX_TURN' run_loop.sh)" -ge 1 ] && echo yes || echo no)" "yes"

# F2 · THE CUTOVER. Was the all-current state ever RECORDED? The row's own
# arbiter is check_live_launcher.sh; the observation is quoted in a committed
# RESULT, which is a record a later reader can check rather than a memory.
echo "F2 · the recorded observation of the cutover"
q=$(grep -c 'all 6 live launcher processes at or newer than' spikes/H219_stop_asymmetry/RESULT.md || true)
ck "  a committed RESULT records the checker reporting ALL launchers current" "$q" "1"

# ... and the state NOW, which is the whole point: it flips.
echo "F2b · the same checker, now"
out=$(bash spikes/harness/check_live_launcher.sh 2>&1 || true)
now=$(printf '%s' "$out" | sed -nE 's/^REFUSE: ([0-9]+) of ([0-9]+) live launcher.*/\1 of \2/p')
[ -n "$now" ] || now="none refused"
echo "     $now stale against the newest commit touching run_loop.sh"
ck "  the condition is NOT satisfied now" "$([ "$now" = "none refused" ] && echo satisfied || echo unsatisfied)" "unsatisfied"

# F3 · IS THE PROPAGATION HAZARD REPRESENTED OUTSIDE THE ROW? Closing H2 must not
# delete the fleet's only record of it.
echo "F3 · where else the propagation hazard is recorded"
for f in spikes/harness/check_live_launcher.sh MISSION_LOOP.md prompts/AGENT-1.md; do
  n=$(grep -c 'relaunch\|predate' "$f" 2>/dev/null || echo 0)
  printf '     %-42s %s mention(s)\n' "$f" "$n"
done
ck "  the standing checker exists and is executable" \
   "$([ -x spikes/harness/check_live_launcher.sh ] && echo yes || echo no)" "yes"

echo
echo "probe: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
