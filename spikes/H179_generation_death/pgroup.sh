#!/usr/bin/env bash
# H179 -- ok-1, 2026-08-19. THE MECHANISM: launchd kills the lane's process group.
#
#   Cites: man:launchd.plist "AbandonProcessGroup"
#     "When a job dies, launchd kills any remaining processes with the same
#      process group ID as the job. Setting this key to true disables that
#      behavior."
#
# com.kingfisher.bringup.plist does NOT set that key, so it defaults to false.
# bringup.sh launches `CALLSIGN=$lane ./run_loop.sh &`, and run_loop.sh's detach
# is `( nohup "$0" "$@" & ) &` -- a double fork, which REPARENTS the wrapper to
# init and does NOT change its process GROUP (its own header says "which is why
# this is not setsid"). So every lane launchd starts sits in the bringup job's
# process group, and dies when that job exits, ~10-30s later -- after its first
# turn, inside its first backoff. That is exactly the production shape: one turn
# per generation, at bringup's 600s cadence and not the lane's 30s backoff.
#
# probe.sh already established the other half: the launcher itself escalates
# fine (fail 1,2,3,4) when nothing kills it, so the death is external.
#
# ARMS (both states are a command, the pre-fix one PINNED to a rev):
#   A1 the lane inherits the launching process group          (the exposure)
#   A2 a group kill of that group KILLS the lane              (the mechanism)
#   A3 with the fix, the lane has its OWN group and SURVIVES  (the repair)
#   C1 the group kill actually reaches its target             (A29, else A2 is vacuous)
#   C2 SAFETY: refuse to signal a group that holds this shell or any live lane
#
# usage: bash spikes/H179_generation_death/pgroup.sh [rev]
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/pg_sandbox"; CS="PROBE-8"; REV="${1:-}"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }
pgid_of() { ps -o pgid= -p "$1" 2>/dev/null | tr -d ' '; }
alive()   { kill -0 "$1" 2>/dev/null && echo 1 || echo 0; }

cleanup() {
  pkill -f "You are ${CS}\." 2>/dev/null
  [ -f "$SB/.loop_lock.${CS}" ] && kill -9 "$(cat "$SB/.loop_lock.${CS}")" 2>/dev/null
  sleep 0.2
}
trap cleanup EXIT

rm -rf "$SB"; mkdir -p "$SB/prompts" "$SB/bin"
if [ -n "$REV" ]; then
  git -C "$ROOT" show "${REV}:run_loop.sh" > "$SB/run_loop.sh" || exit 2
  grep -q 'while \[ ! -f STOP \]' "$SB/run_loop.sh" \
    || { echo "REFUSING: ${REV}:run_loop.sh is not the launcher this row is about"; exit 2; }
  echo "=== TARGET: ${REV}:run_loop.sh ==="
else
  cp "$ROOT/run_loop.sh" "$SB/run_loop.sh"
  echo "=== TARGET: the live run_loop.sh ==="
fi
chmod +x "$SB/run_loop.sh"
printf '%s\n' "$CS" > "$SB/roster.txt"
printf 'synthetic lane, H179 probe. Not a real brief.\n' > "$SB/prompts/${CS}.md"
cat > "$SB/bin/claude" <<'STUB'
#!/usr/bin/env bash
echo "You've hit your weekly limit · resets 4pm (Europe/Lisbon)"
sleep 2
exit 1
STUB
chmod +x "$SB/bin/claude"

# `set -m` gives each background job its OWN process group, so the DRIVER below
# stands in for the launchd job: a group of its own that we may signal without
# touching this shell, this session, or the live fleet.
set -m
( cd "$SB" && PATH="$SB/bin:$PATH" CALLSIGN="$CS" BACKOFF_STEP=60 ./run_loop.sh >/dev/null 2>&1;
  sleep 300 ) &          # the trailing sleep IS the C1 control: a live group member
DRV=$!
sleep 8

DPG=$(pgid_of "$DRV")
MYPG=$(pgid_of $$)
LANE=$(cat "$SB/.loop_lock.${CS}" 2>/dev/null)
[ -n "$LANE" ] || { echo "  no lane lock written -- the launcher did not start"; exit 2; }
LPG=$(pgid_of "$LANE")

# ---- C2 SAFETY. Never signal a group holding this shell or a live fleet lane.
safe=1
[ "$DPG" = "$MYPG" ] && safe=0
[ -z "$DPG" ] && safe=0
[ "$DPG" = 1 ] && safe=0
for f in "$ROOT"/.loop_lock.*; do
  [ -f "$f" ] || continue
  p=$(cat "$f" 2>/dev/null); [ -n "$p" ] || continue
  [ "$(pgid_of "$p")" = "$DPG" ] && safe=0
done
[ "$safe" = 1 ] && ctl C2 PASS "target group $DPG holds no live fleet lane and is not this shell ($MYPG)" \
                || { ctl C2 FAIL "REFUSING to signal group $DPG"; kill -9 "$DRV" 2>/dev/null; exit 1; }

# ---- A1 the lane inherits the launching group
printf '    driver pid=%s pgid=%s   lane pid=%s pgid=%s\n' "$DRV" "$DPG" "$LANE" "$LPG"
if [ "$LPG" = "$DPG" ]; then
  ctl A1 PASS "the lane sits in the LAUNCHER'S process group -- exposed to the job kill"
else
  ctl A1 PASS "the lane has its OWN process group ($LPG != $DPG) -- not exposed"
fi

# ---- kill the group, as launchd does when the job dies
before=$(alive "$LANE")
kill -TERM -"$DPG" 2>/dev/null
sleep 2
after=$(alive "$LANE")
drv_after=$(alive "$DRV")

# ---- C1 the kill reached its target (A29): the driver's own sleep must be gone
[ "$drv_after" = 0 ] && ctl C1 PASS "the group kill reached the group (driver gone)" \
                     || ctl C1 FAIL "driver still alive -- the kill did not land, arms below are vacuous"

if [ "$LPG" = "$DPG" ]; then
  [ "$before" = 1 ] && [ "$after" = 0 ] \
    && ctl A2 PASS "MECHANISM REPRODUCED: the lane died with the group it inherited" \
    || ctl A2 FAIL "lane alive_before=$before alive_after=$after -- the group kill did not take it"
else
  [ "$before" = 1 ] && [ "$after" = 1 ] \
    && ctl A3 PASS "REPAIR: the lane survived the group kill (own process group)" \
    || ctl A3 FAIL "lane alive_before=$before alive_after=$after -- own group did not protect it"
fi

echo
[ "$fail" = 0 ] && echo "H179 pgroup: all arms as stated" || echo "H179 pgroup: FAILED"
exit "$fail"
