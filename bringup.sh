#!/usr/bin/env bash
# Mission bring-up. Idempotent: safe to run any number of times, including from
# a LaunchAgent at login. Starts what is missing, touches what is already up
# exactly not at all, and NEVER kills anything.
#
#   ./bringup.sh            # report + start missing lanes
#   ./bringup.sh --check    # report only, start nothing (exit 1 if no quorum)
#
# Written 2026-08-17 after a laptop restart took out every lane and the cron
# loop with them. The cron job did not come back; nothing re-established the
# mission, and the gap was invisible because the surviving processes looked
# healthy in isolation. Three defects it closes:
#
#  1. NO ROSTER. run_loop.sh validated the callsign CHARSET and that a brief
#     file existed -- and briefs are written by the lane itself, so a lane could
#     authorise its own launch. `ok-1` came up exactly that way.
#  2. NO QUORUM CHECK. "Is AGENT-1 alive" was answerable; "is the mission up"
#     was not. A lane can be missing for hours with every other lane healthy.
#  3. RESTART DOES NOT SURVIVE. Use `./bringup.sh --install-agent` for the
#     LaunchAgent, because cron died with the reboot and does not self-restore.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ROSTER_FILE="roster.txt"
STALE_SECS=2100        # 35 min: H6's threshold, same number run_loop.sh cites

[ -f "$ROSTER_FILE" ] || { echo "bringup: $ROSTER_FILE missing -- refusing to guess the roster"; exit 1; }
# Strip comments (inline and whole-line) and blanks.
# NOT `mapfile`: macOS ships bash 3.2 and /usr/bin/env bash finds it, so
# mapfile is "command not found" and `set -u` then reports the roster as an
# unbound variable -- a launcher that fails on the machine it ships for.
ROSTER=()
while read -r _lane; do
  [ -n "$_lane" ] && ROSTER+=("$_lane")
done < <(sed 's/#.*//' "$ROSTER_FILE" | awk 'NF{print $1}')
[ "${#ROSTER[@]}" -gt 0 ] || { echo "bringup: roster is empty"; exit 1; }

# Match the launch prompt exactly. `You are AGENT-1.` with the trailing period,
# so AGENT-1 never matches a future AGENT-10.
lane_pid() { pgrep -f "You are ${1}\." 2>/dev/null | head -1; }

beat_age() {
  local f=".heartbeat.${1}"
  [ -f "$f" ] || { echo -1; return; }
  echo $(( $(date +%s) - $(stat -f %m "$f") ))
}

CHECK_ONLY=0; INSTALL=0
for a in "$@"; do
  case "$a" in
    --check) CHECK_ONLY=1 ;;
    --install-agent) INSTALL=1 ;;
    *) echo "bringup: unknown flag $a"; exit 1 ;;
  esac
done

if [ "$INSTALL" = 1 ]; then
  PL="$HOME/Library/LaunchAgents/net.kingfisher.bringup.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PL" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>net.kingfisher.bringup</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$(pwd)/bringup.sh</string></array>
  <key>WorkingDirectory</key><string>$(pwd)</string>
  <!-- RunAtLoad covers the reboot that started all this. StartInterval
       re-checks every 10 min, so a lane that dies mid-day is also recovered:
       bringup is idempotent, so a no-op run costs one pgrep per lane. -->
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>600</integer>
  <key>StandardOutPath</key><string>$(pwd)/bringup.log</string>
  <key>StandardErrorPath</key><string>$(pwd)/bringup.log</string>
</dict></plist>
PLIST
  launchctl unload "$PL" 2>/dev/null
  launchctl load "$PL" && echo "bringup: LaunchAgent installed and loaded -> $PL"
  echo "  survives reboot (RunAtLoad) and re-checks every 600s."
  echo "  remove with: launchctl unload $PL && rm $PL"
  exit 0
fi

echo "=== ROLES ==="
ROLE_FAIL=0
for lane in "${ROSTER[@]}"; do
  brief="prompts/${lane}.md"
  if [ ! -f "$brief" ]; then
    printf '  %-12s BRIEF MISSING  %s -- run_loop.sh will refuse to launch\n' "$lane" "$brief"
    ROLE_FAIL=1
  elif ! git ls-files --error-unmatch "$brief" >/dev/null 2>&1; then
    # Untracked means no other lane has reviewed it, and a brief is a lane's
    # own instructions. Not fatal; it is the A22 smell worth printing.
    printf '  %-12s brief ok (%s lines) UNTRACKED -- self-authored, uncommitted\n' \
      "$lane" "$(wc -l < "$brief" | tr -d ' ')"
  else
    printf '  %-12s brief ok (%s lines)\n' "$lane" "$(wc -l < "$brief" | tr -d ' ')"
  fi
done

echo
echo "=== QUORUM ==="
UP=0; MISSING=()
for lane in "${ROSTER[@]}"; do
  pid=$(lane_pid "$lane")
  age=$(beat_age "$lane")
  if [ -n "$pid" ]; then
    UP=$((UP+1))
    if [ "$age" -lt 0 ]; then
      printf '  %-12s UP   pid %-7s no heartbeat file yet\n' "$lane" "$pid"
    elif [ "$age" -gt "$STALE_SECS" ]; then
      printf '  %-12s UP   pid %-7s HEARTBEAT STALE %ss (>%ss)\n' "$lane" "$pid" "$age" "$STALE_SECS"
    else
      printf '  %-12s UP   pid %-7s beat %ss ago\n' "$lane" "$pid" "$age"
    fi
  else
    printf '  %-12s DOWN\n' "$lane"
    MISSING+=("$lane")
  fi
done
echo "  quorum: ${UP}/${#ROSTER[@]}"

# A lane running that the roster does not name. This is how ok-1 went unnoticed:
# every named lane was healthy, so nothing looked wrong.
echo
echo "=== OFF-ROSTER ==="
OFF=0
while read -r name; do
  for lane in "${ROSTER[@]}"; do [ "$name" = "$lane" ] && continue 2; done
  printf '  %-12s running but NOT in %s -- add the line or stop it deliberately\n' "$name" "$ROSTER_FILE"
  OFF=1
# `.` must be OUTSIDE the class and REQUIRED. With `.` inside it the capture was
# "AGENT-1." including the period, so no roster entry ever matched and all four
# healthy lanes were reported off-roster; without requiring it, prose in the
# launch prompt ("You are the ...") matched as a lane named `the`. Both wrong in
# opposite directions, and both look like a working check.
done < <(ps -eo command | grep -oE 'You are [A-Za-z0-9_-]+\.' \
         | sed -e 's/You are //' -e 's/\.$//' | sort -u)
[ "$OFF" = 0 ] && echo "  none"

if [ "$CHECK_ONLY" = 1 ]; then
  [ "${#MISSING[@]}" -eq 0 ] && [ "$ROLE_FAIL" = 0 ] && exit 0 || exit 1
fi

if [ "${#MISSING[@]}" -eq 0 ]; then
  echo
  echo "bringup: full quorum, nothing to start."
  exit 0
fi

echo
echo "=== STARTING ${#MISSING[@]} MISSING LANE(S) ==="
for lane in "${MISSING[@]}"; do
  if [ ! -f "prompts/${lane}.md" ]; then
    echo "  $lane SKIPPED -- no brief; write prompts/${lane}.md first (run_loop.sh refuses without one)"
    continue
  fi
  CALLSIGN="$lane" ./run_loop.sh &
  echo "  $lane launched"
  sleep 2      # stagger: four lanes racing the same git index is H19
done
echo
echo "re-check with: ./bringup.sh --check"
