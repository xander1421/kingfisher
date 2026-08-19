#!/usr/bin/env bash
# H179 -- ok-1, 2026-08-19. WHY DOES A LAUNCHER GENERATION DIE AFTER ONE TURN?
#
# H173 measured the consequence and refused to guess the cause. Two candidates
# are already dead: not STOP (the loop's only clean exit prints `loop stopped`;
# 0 such lines in 27h of logs) and not a launchd process-group kill (falsified
# on the live fleet: every lane's group leader is dead and the lanes run on).
#
# THIS DRIVES THE REAL run_loop.sh with a stub CLI that exits instantly, which
# is the quota wall's shape: `You've hit your weekly limit`, rc!=0, 2-3s.
#
# F1 reaches turn 2 -> the death is EXTERNAL to run_loop.sh
# F2 dies after turn 1 -> reproduced locally, bisect from here
# F3 .loop_fails reaches 2 while the log shows one line -> the LOG is the
#    unreliable instrument, not the loop
#
# H80: the stub lives in a PER-BLOCK bin dir and the lane is killed at the end.
# A detached lane outliving this probe would run the NEXT block's stub.
#
# usage: bash spikes/H179_generation_death/probe.sh [seconds]
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"; CS="PROBE-9"; WATCH="${1:-95}"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }

cleanup() {
  pkill -f "You are ${CS}\." 2>/dev/null
  [ -f "$SB/.loop_lock.${CS}" ] && kill "$(cat "$SB/.loop_lock.${CS}")" 2>/dev/null
  pkill -f "$SB/run_loop.sh" 2>/dev/null
  sleep 0.3
}
trap cleanup EXIT

rm -rf "$SB"; mkdir -p "$SB/prompts" "$SB/bin"
cp "$ROOT/run_loop.sh" "$SB/run_loop.sh"; chmod +x "$SB/run_loop.sh"
h_live=$(shasum -a 256 "$ROOT/run_loop.sh" | awk '{print $1}')
h_copy=$(shasum -a 256 "$SB/run_loop.sh"   | awk '{print $1}')
[ "$h_live" = "$h_copy" ] && ctl C2 PASS "sandbox drives the live run_loop.sh (${h_live:0:16})" \
                          || ctl C2 FAIL "copy DIFFERS -- the probe measures the wrong launcher"

printf '%s\n' "$CS" > "$SB/roster.txt"
printf 'synthetic lane, H179 probe. Not a real brief.\n' > "$SB/prompts/${CS}.md"

# The stub: the quota wall's exact shape -- a line on stdout, a fast non-zero exit.
cat > "$SB/bin/claude" <<'STUB'
#!/usr/bin/env bash
echo "You've hit your weekly limit · resets 4pm (Europe/Lisbon)"
sleep 2
exit 1
STUB
chmod +x "$SB/bin/claude"

( cd "$SB" && PATH="$SB/bin:$PATH" CALLSIGN="$CS" BACKOFF_STEP=10 ./run_loop.sh >/dev/null 2>&1 )
sleep "$WATCH"

LOG="$SB/loop_${CS}.log"
turns=$(grep -c 'exited after' "$LOG" 2>/dev/null || echo 0); turns=$(( turns ))
maxfail=$(grep -oE '\(fail [0-9]+\)' "$LOG" 2>/dev/null | grep -oE '[0-9]+' | sort -n | tail -1)
[ -n "$maxfail" ] || maxfail=0
ff=$(cat "$SB/.loop_fails.${CS}" 2>/dev/null || echo MISSING)
stopped=$(grep -c 'loop stopped' "$SB"/*.log 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
alive=0; p=$(cat "$SB/.loop_lock.${CS}" 2>/dev/null); [ -n "$p" ] && kill -0 "$p" 2>/dev/null && alive=1

echo "  --- after ${WATCH}s with a 10s backoff step ---"
printf '    turns logged=%s  max fail=%s  .loop_fails=%s  clean exits=%s  launcher alive=%s\n' \
  "$turns" "$maxfail" "$ff" "$stopped" "$alive"

[ "$turns" -ge 1 ] && ctl C1 PASS "the stub was reached: $turns turn(s) ran and exited under 60s" \
                   || ctl C1 FAIL "no turn ran at all -- nothing below is evidence"

if [ "$turns" -ge 2 ]; then
  ctl F1 PASS "reached turn $turns (max fail $maxfail) -- run_loop.sh DOES escalate; the production death is EXTERNAL"
else
  ctl F2 PASS "died after turn 1 -- REPRODUCED locally, bisect from here"
fi
[ "$ff" = "$maxfail" ] && ctl F3 PASS ".loop_fails ($ff) agrees with the log ($maxfail)" \
                       || ctl F3 FAIL ".loop_fails=$ff but the log's max is $maxfail -- one of them is fiction"

echo
[ "$fail" = 0 ] && echo "H179 probe: all controls as stated" || echo "H179 probe: FAILED"
sed -n '1,12p' "$LOG" 2>/dev/null | sed 's/^/    | /'
exit "$fail"
