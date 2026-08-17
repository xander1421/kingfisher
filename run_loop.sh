#!/usr/bin/env bash
# usage: CALLSIGN=AGENT-2 ./run_loop.sh     (one terminal/tmux pane per agent)
#
# v2, 2026-08-17. Four defects fixed; each one had ended or could end a lane
# silently. Numbered so a stall can be diagnosed against this list.
#
# 1. THE LAUNCHER DECIDED THE LOOP WAS OVER BY GREPPING ITS OWN LOG for
#    LOOP-DONE / LOOP-HALT. That is the identical defect loop_gate.sh was
#    hardened against in ITS v2 -- and the hook's refusal message quotes all
#    three marker words, so any turn that printed the refusal killed the lane.
#    Terminal signals are FILES. The hook now hands the launcher an exit marker
#    that only the launcher clears, so there is no race over who consumes it and
#    no way for prose to end a loop.
# 2. STATE FILES WERE GLOBAL WHILE THERE ARE TWO LANES. One .loop_signal meant
#    lane B's hook could consume lane A's exit and die in A's place; one
#    .loop_blocks meant a shared fuse and each lane's rm resetting the other's.
#    Both are now per-callsign.
# 3. NO BACKOFF. A claude that exits instantly (auth, rate limit, usage cap)
#    respawned every 5s forever -- a hot spin that looks alive and does nothing.
# 4. NO TIMEOUT. The loop handled a crash and not a hang; a wedged turn waited
#    forever. macOS ships no timeout(1), so the watchdog is inline.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CALLSIGN=${CALLSIGN:-BUILDER-1}
LOG="loop_${CALLSIGN}.log"
EXIT_MARK=".loop_exit.${CALLSIGN}"        # written by the hook, cleared only here
BEAT=".heartbeat.${CALLSIGN}"             # mtime = last turn start; watch this for staleness
MAX_TURN=${MAX_TURN:-3600}                # seconds before a turn is called wedged
command -v claude >/dev/null || { echo "claude CLI not found"; exit 1; }

fails=0
while [ ! -f STOP ]; do
  rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK"
  date +%s > "$BEAT"
  started=$(date +%s)

  ( claude -p "You are ${CALLSIGN}. Read MISSION_LOOP.md, then HANDOFF.md if present, then run cycles per the loop contract." \
      --dangerously-skip-permissions 2>&1 | tee -a "$LOG" ) &
  turn=$!
  # Watchdog: convert a hang into a crash, which the loop below already handles.
  # pkill is matched on the callsign in the prompt so it cannot touch the other
  # lane or a human's interactive session.
  ( sleep "$MAX_TURN"
    if kill -0 "$turn" 2>/dev/null; then
      echo "[run_loop] ${CALLSIGN} turn exceeded ${MAX_TURN}s, terminating" | tee -a "$LOG"
      pkill -f "You are ${CALLSIGN}\." 2>/dev/null
      kill -TERM "$turn" 2>/dev/null
    fi ) &
  dog=$!
  wait "$turn" 2>/dev/null
  kill -TERM "$dog" 2>/dev/null          # turn finished first: cancel the watchdog
  elapsed=$(( $(date +%s) - started ))

  # Terminal signal: a file the hook moved here, never a word in the transcript.
  if [ -f "$EXIT_MARK" ]; then
    case "$(tr -d '[:space:]' < "$EXIT_MARK")" in
      LOOP-DONE|LOOP-HALT)
        echo "[run_loop] ${CALLSIGN} terminal signal, exiting" | tee -a "$LOG"; break ;;
      LOOP-IDLE)
        echo "[run_loop] ${CALLSIGN} idle, all work blocked on human; 600s" | tee -a "$LOG"
        fails=0; sleep 600; continue ;;
      LOOP-FUSE)
        echo "[run_loop] ${CALLSIGN} fuse: session span ended, resuming" | tee -a "$LOG"
        fails=0; sleep 5; continue ;;
    esac
  fi

  # A turn that did real work resets the failure count. A turn that died in
  # under a minute did not, so back off instead of hammering the API.
  if [ "$elapsed" -ge 60 ]; then
    fails=0
    sleep 5
  else
    fails=$(( fails + 1 ))
    back=$(( fails * 30 )); [ "$back" -gt 900 ] && back=900
    echo "[run_loop] ${CALLSIGN} exited after ${elapsed}s (fail ${fails}), backing off ${back}s" | tee -a "$LOG"
    sleep "$back"
  fi
done
echo "loop stopped (${CALLSIGN})"
