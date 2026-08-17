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

  # The prompt MUST keep the literal "You are ${CALLSIGN}." prefix — the watchdog
  # below targets the turn with pkill -f on exactly that string, so that it can
  # never match the other lane or a human's interactive session.
  ( claude -p "You are ${CALLSIGN}. Read CLAUDE.md, then MISSION_LOOP.md, then HANDOFF.md if present, then run cycles per the loop contract.

The harness evolves with the codebase (MISSION_LOOP §12, CLAUDE.md §6). It is the instrument that runs every other instrument, and it had never been attacked before 2026-08-17 — it was carrying an inert Stop hook, a launcher that had never been run, and re-entry that depended on remembering one call per turn. So: a harness defect is a class-H WORK_QUEUE row, not a fix you make in passing. Fix the CLASS and not the site — name the defect class in one line, grep the whole harness for it, and post the class to livechat.log so the other lane greps its own tree. Resolve every reference to a section, spec or file mechanically rather than by eye. Any harness component you touch keeps a runnable check that fails when it breaks, and gains a version bump with a rationale block naming the defect removed. At least every fourth ATTACK cycle targets the loop itself rather than a spike.

A wrong number gets retracted by the next cycle. A dead lane has no next cycle." \
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
