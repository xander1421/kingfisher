#!/usr/bin/env bash
# usage: CALLSIGN=BUILDER-2 ./run_loop.sh     (one terminal/tmux pane per agent)
export CALLSIGN=${CALLSIGN:-BUILDER-1}
LOG="loop_${CALLSIGN}.log"
command -v claude >/dev/null || { echo "claude CLI not found"; exit 1; }
while [ ! -f STOP ]; do
  rm -f .loop_blocks                       # reset the hook's runaway counter
  claude -p "You are ${CALLSIGN}. Read MISSION_LOOP.md, then HANDOFF.md if present, then run cycles per the loop contract." \
    --dangerously-skip-permissions 2>&1 | tee -a "$LOG"
  T=$(tail -c 3000 "$LOG")
  case "$T" in
    *LOOP-DONE*|*LOOP-HALT*) break ;;
    *LOOP-IDLE*)             sleep 600 ;;   # all agent-doable work blocked on human
    *)                       sleep 5   ;;   # handoff or crash: resurrect fast
  esac
done
echo "loop stopped ($CALLSIGN)"
