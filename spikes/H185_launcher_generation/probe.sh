#!/usr/bin/env bash
# H185 -- ok-1, 2026-08-19. WHICH LAUNCHER IS THIS LANE RUNNING?
#
# A generation runs the code it was STARTED with, so a fix to run_loop.sh reaches
# a live lane only at its next relaunch. Measured the hour v11 (H179's
# process-group fix) landed: all five lanes were pre-v11 generations and every one
# printed UP, because the census had no column for it.
#
# TWO SIDES, and they fail differently:
#   PRODUCER  run_loop.sh v12 writes .loop_launcher.<lane> = <sha16> <epoch>
#   CONSUMER  bringup.sh v7 names THREE states -- current / stale / unrecorded
#
# C1 is H88's defect restated as a control: ABSENT must not print what CURRENT
# prints. That defect was in THIS file's lane_fails and is not to be re-earned one
# function down.
# F3 is the rail: a stale launcher must never add a lane to MISSING or refuse
# quorum -- relaunching a healthy lane because its launcher is old is H6's
# "absent branch LAUNCHES" hazard.
#
# usage: bash spikes/H185_launcher_generation/probe.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"; CS="PROBE-7"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }
STUB=""; LANE=""
cleanup() {
  [ -n "$STUB" ] && kill "$STUB" 2>/dev/null
  pkill -f "You are ${CS}\." 2>/dev/null
  [ -f "$SB/.loop_lock.${CS}" ] && kill "$(cat "$SB/.loop_lock.${CS}")" 2>/dev/null
  sleep 0.2
}
trap cleanup EXIT

rm -rf "$SB"; mkdir -p "$SB/prompts" "$SB/bin"
cp "$ROOT/bringup.sh" "$SB/bringup.sh"
cp "$ROOT/run_loop.sh" "$SB/run_loop.sh"; chmod +x "$SB/run_loop.sh"
for f in bringup run_loop; do
  a=$(shasum -a 256 "$ROOT/$f.sh" | awk '{print $1}')
  b=$(shasum -a 256 "$SB/$f.sh"   | awk '{print $1}')
  [ "$a" = "$b" ] || { ctl C2 FAIL "$f.sh copy differs -- probe measures the wrong file"; }
done
[ "$fail" = 0 ] && ctl C2 PASS "sandbox drives the live bringup.sh AND run_loop.sh"
printf '%s\n' "$CS" > "$SB/roster.txt"
printf 'synthetic lane, H185 probe. Not a real brief.\n' > "$SB/prompts/${CS}.md"
printf 'NOTE PROBE-7 synthetic\n' > "$SB/CHANNEL.md"
cat > "$SB/bin/claude" <<'STUB2'
#!/usr/bin/env bash
sleep 120
STUB2
chmod +x "$SB/bin/claude"

# ---------------------------------------------------------------- PRODUCER
( cd "$SB" && PATH="$SB/bin:$PATH" CALLSIGN="$CS" ./run_loop.sh >/dev/null 2>&1 )
sleep 4
GEN="$SB/.loop_launcher.${CS}"
if [ -f "$GEN" ]; then
  had=$(awk '{print $1}' "$GEN"); ts=$(awk '{print $2}' "$GEN")
  want=$(shasum -a 256 "$SB/run_loop.sh" | cut -c1-16)
  [ "$had" = "$want" ] && ctl P1 PASS "the launcher stamped its OWN content ($had)" \
                       || ctl P1 FAIL "stamped '$had', launcher is '$want' -- the stamp names another file"
  case "$ts" in ''|*[!0-9]*) ctl P2 FAIL "second field '$ts' is not an epoch" ;;
                *) ctl P2 PASS "and when it started ($ts)" ;; esac
else
  ctl P1 FAIL "no .loop_launcher written -- the producer half never ran"
fi

# ---------------------------------------------------------------- CONSUMER
arm() { ( cd "$SB" && bash ./bringup.sh --check 2>&1; echo "EXIT=$?" ); }
lane_line() { grep -E "^ +${CS}" || true; }

L=$(arm | lane_line)
case "$L" in
  *" UP "*) ctl C3 PASS "census sees ${CS} UP, so the launcher note is reached" ;;
  *) ctl C3 FAIL "census does not see ${CS} UP: '$L' -- consumer arms are vacuous" ;;
esac
case "$L" in
  *LAUNCHER*) ctl A1 FAIL "a CURRENT launcher printed a note: '$L'" ;;
  *)          ctl A1 PASS "current launcher prints no note (quiet when there is nothing to say)" ;;
esac

# STALE: rewrite the stamp to a hash that is not the tree's
printf 'deadbeefdeadbeef %s\n' "$(date +%s)" > "$GEN"
L=$(arm | lane_line)
case "$L" in
  *"LAUNCHER STALE"*deadbeefdeadbeef*) ctl A2 PASS "stale is NAMED and quotes both hashes" ;;
  *) ctl A2 FAIL "stale not named: '$L'" ;;
esac

# UNRECORDED: no stamp at all -- H88's defect as a control
rm -f "$GEN"
L=$(arm | lane_line)
case "$L" in
  *"LAUNCHER UNRECORDED"*) ctl C1 PASS "ABSENT is NAMED, not silent -- H88's defect not re-earned" ;;
  *) ctl C1 FAIL "absent stamp printed what CURRENT prints: '$L'" ;;
esac

# F3: none of this may move quorum or MISSING
printf 'deadbeefdeadbeef %s\n' "$(date +%s)" > "$GEN"
OUT=$(arm)
E=$(printf '%s' "$OUT" | tail -1)
printf '%s\n' "$OUT" | grep -qE "DOWN|STARTING|FLAPPING" \
  && ctl F3 FAIL "a stale launcher moved the lane out of UP -- H6's absent-branch-LAUNCHES hazard" \
  || ctl F3 PASS "stale launcher: still UP, not MISSING, quorum untouched ($E)"

echo
[ "$fail" = 0 ] && echo "H185 probe: all arms as stated" || echo "H185 probe: FAILED"
exit "$fail"
