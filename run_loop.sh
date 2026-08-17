#!/usr/bin/env bash
# usage: CALLSIGN=AGENT-2 ./run_loop.sh     (one terminal/tmux pane per agent)
#
# v3, 2026-08-17. Five defects fixed; each one had ended or could end a lane
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
# 5. A TERMINAL SIGNAL OUTLIVED THE SPAN THAT WROTE IT (v3, class H16). The turn
#    -start cleanup cleared .loop_blocks and .loop_exit and NOT
#    .loop_signal.$CALLSIGN, so a signal written by a previous span was live
#    ammunition for the next one. Observed, not theorised: AGENT-1 wrote
#    LOOP-HALT at 11:30 under STOP; loop_gate.sh's STOP branch (its section 1)
#    exits BEFORE it consumes a signal, so the file survived; the operator then
#    removed STOP; the relaunched lane would have had that signal consumed at its
#    FIRST turn end and exited having done no work, logging "terminal signal,
#    exiting" as though the span had finished. Cleared here rather than in the
#    hook's STOP branch because the launcher is the one choke point every span
#    passes through, so it also covers the arming paths the hook cannot see: a
#    crash or SIGKILL between the signal write and the turn end, the watchdog's
#    own pkill, and a hand-written signal. A signal that survives a completed
#    turn is stale by construction -- the hook consumes a live one at the turn
#    end that follows it -- so clearing at turn start cannot destroy an in-flight
#    exit. Checked by spikes/harness/test_loop_gate.sh, which drives this script
#    with a stub claude and fails if a seeded stale signal reaches the turn.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# FAIL CLOSED, same rule the hook enforces. This defaulted to BUILDER-1 -- a
# callsign holding 9 historical DONE rows -- which is the identical
# default-identity defect fixed in the hook one version earlier, left standing in
# the launcher by the author of "fix the class, not the site". Found by a reviewer.
: "${CALLSIGN:?run_loop.sh: set CALLSIGN explicitly, e.g. CALLSIGN=AGENT-1 ./run_loop.sh}"
export CALLSIGN
LOG="loop_${CALLSIGN}.log"
EXIT_MARK=".loop_exit.${CALLSIGN}"        # written by the hook, cleared only here
BEAT=".heartbeat.${CALLSIGN}"             # mtime = last turn start; watch this for staleness
MAX_TURN=${MAX_TURN:-3600}                # seconds before a turn is called wedged
command -v claude >/dev/null || { echo "claude CLI not found"; exit 1; }

# Per-lane spawn brief. A lane's role, its reading order and its first cycles
# belong in a tracked reviewable file, not in one operator's chat scrollback --
# AGENT-2's lane definition lived only inside HANDOFF.md, which is contested by
# two writers, and a lane was spawned onto an already-held callsign because
# nothing at launch said who was live. Read fresh every turn so an edit to the
# brief reaches the lane on its next cycle without a relaunch.
BRIEF_FILE="prompts/${CALLSIGN}.md"

fails=0
while [ ! -f STOP ]; do
  rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK" ".loop_signal.${CALLSIGN}"
  date +%s > "$BEAT"
  started=$(date +%s)

  # The prompt MUST keep the literal "You are ${CALLSIGN}." prefix — the watchdog
  # below targets the turn with pkill -f on exactly that string, so that it can
  # never match the other lane or a human's interactive session.
  ( claude -p "You are ${CALLSIGN}. Read CLAUDE.md, then MISSION_LOOP.md, then HANDOFF.md if present, then run cycles per the loop contract.

The harness evolves with the codebase (MISSION_LOOP §12). It is the instrument that runs every other instrument, and it had never been attacked before 2026-08-17 — it was carrying an inert Stop hook, a launcher whose supervision had never been exercised, and re-entry that depended on remembering one call per turn. So: a harness defect is a class-H WORK_QUEUE row, not a fix you make in passing. Fix the CLASS and not the site — name the defect class in one line, grep the whole harness for it, and post the class to livechat.log so the other lane greps its own tree. Resolve every reference to a section, spec or file mechanically rather than by eye. Any harness component you touch keeps a runnable check that fails when it breaks, and gains a version bump with a rationale block naming the defect removed. At least every fourth ATTACK cycle targets the loop itself rather than a spike.

A wrong number gets retracted by the next cycle. A dead lane has no next cycle.
$([ -f "$BRIEF_FILE" ] && printf '\n--- your spawn brief, %s ---\n' "$BRIEF_FILE" && cat "$BRIEF_FILE")" \
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
