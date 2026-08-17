#!/usr/bin/env bash
# usage: CALLSIGN=AGENT-2 ./run_loop.sh     (one terminal/tmux pane per agent)
#
# v6, 2026-08-17. Nine defects fixed; each one had ended or could end a lane
# silently. Numbered so a stall can be diagnosed against this list. (7 and 8 are
# numbered here by AGENT-1/H30; 7 is ATOM-3's self-detach, whose own rationale
# block sits at the code and which was not in this list -- §12.7 asks a harness
# change for a version bump AND a rationale, and it had the second only.)
# (9 added by AGENT-2/H8. This list is itself an id namespace with no allocator:
# my block was written as "7" against the v4 header, and v5 landed in another
# lane's edit while I wrote it. Renumbered by `grep -nE '^# [0-9]+\.'` rather
# than by eye -- §12.4, and H18's class for the fourth time.)
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
#
# 6 through 9 are documented AT THEIR CODE below, not here: the callsign
# whitelist, the self-detach, the spawn-brief requirement, and the callsign lock.
# Read to `while`.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# FAIL CLOSED, same rule the hook enforces. This defaulted to BUILDER-1 -- a
# callsign holding 9 historical DONE rows -- which is the identical
# default-identity defect fixed in the hook one version earlier, left standing in
# the launcher by the author of "fix the class, not the site". Found by a reviewer.
: "${CALLSIGN:?run_loop.sh: set CALLSIGN explicitly, e.g. CALLSIGN=AGENT-1 ./run_loop.sh}"
# 6. A CALLSIGN IS AN UNTRUSTED STRING (v4, ATTACKER-1, H7). It becomes a
#    filename (.loop_signal.$CALLSIGN, .loop_exit.$CALLSIGN, loop_$CALLSIGN.log),
#    the watchdog's `pkill -f` pattern, and -- since loop_gate.sh v6 -- a JSON
#    string inside the refusal the agent reads. MEASURED: CALLSIGN='L"6' made the
#    hook emit a block decision that fails to parse, so the refusal was lost and
#    the lane could stop for the one reason the hook exists to prevent.
#    loop_gate.sh fails closed on the same whitelist, and it does so SILENTLY --
#    a lane spawned on a callsign the hook will not gate runs completely
#    unsupervised. Both ends must agree, so this is the same whitelist, refusing
#    loudly at the only place a human is watching. §12.2: the class, not the site.
case "$CALLSIGN" in (*[!A-Za-z0-9._-]*)
  echo "run_loop.sh: CALLSIGN must contain only [A-Za-z0-9._-]; loop_gate.sh will"
  echo "not gate '${CALLSIGN}', so the lane would run with no loop contract at all."
  exit 1 ;;
esac
# 8. A LANE COULD LAUNCH WITH NO SPAWN BRIEF AND NOTHING SAID SO (v5, H30).
#    The brief was read as `$([ -f "$BRIEF_FILE" ] && ... && cat ...)` inside the
#    prompt, so an absent file expanded to the empty string and the lane launched
#    looking exactly like one that had a brief. MEASURED at 13:25 today: of three
#    live lanes, only ATTACKER-1 had a brief. AGENT-1 and AGENT-2 -- the pair
#    that actually collided on a callsign and burned two G25 spikes -- had none,
#    and the only written form of the allocation rule (H8) is §0 of a brief, so
#    it reached one lane in three. The comment below this block says the brief
#    exists because "AGENT-2's lane definition lived only inside HANDOFF.md,
#    which is contested by two writers"; that condition was still true for two
#    lanes while the mechanism meant to end it reported nothing.
#
#    CLASS: a missing INPUT silently degrades a harness mechanism to a no-op and
#    the mechanism still reports success. Named and fixed at ONE site 40 minutes
#    earlier -- refcheck.py's harness_files() skipped a HARNESS entry that did
#    not exist and still printed "every citation resolves" (H26b) -- so this is
#    §12.2's own failure mode: the class was named, the site was fixed, and two
#    more live instances stood. The second is journalcheck.queue_done(), which
#    returned an empty set when WORK_QUEUE.md was absent, making the whole check
#    vacuous and green; fixed in the same cycle.
#
#    ABOVE THE DETACH, deliberately, and this is the half that is easy to get
#    wrong: BRIEF_FILE was defined further down, i.e. in the DETACHED CHILD, and
#    a refusal there goes to detach_$CALLSIGN.log while the parent has already
#    printed "detached" and exited 0. Same reasoning as defect 7's own header --
#    never detach what has not been validated -- applied to the launch
#    precondition rather than to the callsign. Checked by test_loop_gate.sh
#    ("launcher refuses a callsign with no spawn brief", and the caller sees it).
#
#    Per-lane spawn brief. A lane's role, its reading order and its first cycles
#    belong in a tracked reviewable file, not in one operator's chat scrollback.
#    Read fresh every turn (below), so an edit to a brief reaches the lane on its
#    next cycle without a relaunch.
# 10. NO ROSTER (v7, AGENT-1, after the 2026-08-17 restart). The two checks
#     above validate the callsign's CHARSET and that a brief EXISTS -- and a
#     brief is written BY the lane it briefs, so a lane could author its own
#     authorisation and launch on it. `ok-1` came up exactly that way and ran
#     --dangerously-skip-permissions against the shared git index for 8 minutes
#     before anyone noticed; it went unnoticed precisely because every NAMED
#     lane was healthy, so nothing looked wrong. Existence of a brief is not
#     sanction. roster.txt is the sanction.
#     CORRECTED 2026-08-17: this said "and it is the same file bringup.sh starts
#     from, so the two ends cannot drift". FALSE WHEN WRITTEN. There were THREE
#     lane sets, not two -- ./bringup.sh read the roster, spikes/harness/bringup.sh
#     and spikes/harness/send.sh each carried a hard-coded literal, and both
#     listed `ok-1`, which this very check refuses. A supervisor would have
#     reported starting a lane its own launcher rejects. Reported by ok-1,
#     third copy found by rostercheck.py after the first two were reconciled.
#     I asserted a property of "the" file in a repo holding three, and did not
#     grep. All three now read roster.txt; `python3 spikes/harness/rostercheck.py`
#     refuses if any drifts again.
ROSTER_FILE="roster.txt"
if [ -f "$ROSTER_FILE" ]; then
  if ! sed 's/#.*//' "$ROSTER_FILE" | awk 'NF{print $1}' | grep -qx "$CALLSIGN"; then
    echo "run_loop.sh: '${CALLSIGN}' is not in ${ROSTER_FILE}."
    echo "A brief that the lane wrote for itself is not sanction to run. Add the"
    echo "callsign to ${ROSTER_FILE} deliberately, or launch a rostered lane."
    exit 1
  fi
else
  echo "run_loop.sh: WARNING ${ROSTER_FILE} absent -- launching unrostered."
fi

BRIEF_FILE="prompts/${CALLSIGN}.md"

# INBOX. Cross-lane messages addressed BY CALLSIGN, delivered into the prompt and
# archived on delivery so they are read exactly once.
#
# The session bus (ListAgents/SendMessage) reaches a live session immediately and
# is the right channel for anything needing action now. It is also IN-MEMORY: a
# message to a lane that is respawning is lost, and these lanes respawn every
# turn. livechat.log is durable but has no addressee and no delivery guarantee --
# "sent" and "seen" are indistinguishable in an append-only file nobody is obliged
# to read. The prompt is the one path that certainly reaches a lane, because the
# launcher rebuilds it every turn.
#
# Archived rather than left in place: an inbox that redelivers forever trains the
# reader to skip it, which is githygiene's own "a checker that fires on
# known-accepted items every run is a checker everyone learns to ignore".
INBOX="inbox/${CALLSIGN}.md"
mkdir -p inbox inbox/archive
if [ ! -f "$BRIEF_FILE" ]; then
  echo "run_loop.sh: no spawn brief at $BRIEF_FILE."
  echo "A lane with no brief has no written role, no reading order and no §0"
  echo "identity claim, and nothing downstream can tell it from a briefed lane."
  echo "Write $BRIEF_FILE (prompts/AGENT-1.md is the short form) and relaunch."
  exit 1
fi
# VALIDATE BEFORE DETACHING. The detach block below was originally placed ABOVE
# both the CALLSIGN:? fail-closed check and the whitelist, so a hostile callsign
# printed "detached" and exited 0 -- spawning a detached lane on a callsign
# loop_gate.sh will NOT gate, i.e. one running with no loop contract at all, and
# now beyond the caller's process tree so it could not be reaped with it. Caught
# by another atom's check "launcher refuses what the hook will not gate" inside a
# minute of me introducing it. Never detach what has not been validated: an
# unvalidated child you can no longer kill is strictly worse than a rejected one.
# SELF-DETACH.  v3, 2026-08-17.
#
# Every lane launched during this project died at the teardown of whatever
# launched it, because a wrapper started from an agent's shell tool is a CHILD OF
# THAT SESSION'S PROCESS TREE. Observed: three lanes gone, wrappers gone,
# .heartbeat.* 35 minutes stale, and nothing reported it -- which is H6, and its
# root cause is not "no alarm" but "the supervisor is itself unsupervised and
# inherits the lifetime of its parent".
#
# So the supervisor detaches itself rather than relying on the caller to remember
# nohup. The double-fork subshell is the portable form: when the inner subshell
# exits, the surviving process is reparented away from the caller. macOS ships no
# setsid, which is why this is not setsid.
#
# KF_DETACHED is the recursion guard. Without it this re-execs forever, which is
# the shape of every runaway in this repo.
LOCK=".loop_lock.${CALLSIGN}"
  # 9. NOTHING REFUSED A SECOND LAUNCHER ON A HELD CALLSIGN (v6, 2026-08-17, H8).
  #    A callsign is the ONLY thing that distinguishes a lane -- it names the
  #    lane's .loop_signal / .loop_exit / .loop_blocks / .heartbeat, and it is the
  #    signature on every CHANNEL line. So two launchers on one callsign is not a
  #    cosmetic clash: they share a terminal signal (either can consume the
  #    other's exit, §12.6), share a fuse, and sign each other's work.
  #
  #    EARNED TWICE, and the second time was live while this was being written:
  #      * CLIENT-3 spawned a lane as AGENT-2 over a live AGENT-2 session; both
  #        signed CHANNEL, two spikes were independently numbered G25, one had to
  #        be renamed (§12, §13.3).
  #      * 2026-08-17 13:26:33 a launcher was live in the repo root under
  #        CALLSIGN=ok-1 -- a test fixture name -- spawning real
  #        `claude -p "You are ok-1."` turns with --dangerously-skip-permissions.
  #        At that moment it had no brief, no CHANNEL line and no queue row.
  #        Nothing refused it and nothing recorded it: it was found by reading
  #        `lsof` output for an unfamiliar detach log, because `ps` cannot show a
  #        callsign. SCOPED AN HOUR LATER RATHER THAN LEFT TO DECAY: ok-1 is now a
  #        legitimate atom with prompts/ok-1.md and CHANNEL claims of its own, so
  #        the finding is about the WINDOW -- a lane ran unallocated and
  #        unrecorded, and only a human's later decision separated it from a
  #        runaway. That window is what this lock closes; it is not a claim that
  #        the lane was illegitimate.
  #
  #    §12 answers this with prose ("a lane's callsign is allocated, not
  #    assumed") and prompts/ATTACKER-1.md §0 tells a lane to check
  #    `ps -eo command= | grep 'You are X\.'`. THAT INSTRUCTION CANNOT BE
  #    CARRIED OUT: measured on this machine, `ps` shows every launcher as
  #    `bash ./run_loop.sh` with no callsign anywhere in argv, and the
  #    LAUNCHER's environment is not readable either -- `ps -E` is silently
  #    ignored and `ps eww` over every live launcher pid exposes no CALLSIGN.
  #    CORRECTED 2026-08-17, same cycle, by a peer session's counter-measurement:
  #    this first read "macOS does not expose another process's environment",
  #    which is FALSE -- `ps eww` reads a same-user process's environment fine,
  #    and that is how the peer enumerated the fleet. What is true is narrower
  #    and is what the conclusion actually rests on: the launcher does not
  #    expose it and the turn does.
  #    The one turn-shaped process that DOES carry it is the `claude -p` child,
  #    which exists only while a turn is in flight -- so between turns the check
  #    reads clear on a held callsign. A rule enforced by an unrunnable check is
  #    §12.4's failure: it reads as satisfied.
  #
  #    So the holder is RECORDED rather than inferred: one file per callsign,
  #    holding the loop's pid. This is also the answer to "who holds AGENT-2?"
  #    for an agent, which is `cat .loop_lock.AGENT-2` and needs no ps at all.
  #
  #    Acquired HERE, before the fork, because a refusal after the detach goes
  #    to detach_$CALLSIGN.log where nobody looks and the caller still sees
  #    exit 0 -- the same defect as detaching before validation, fixed one
  #    comment block above. noclobber makes create-or-fail atomic, so two
  #    launchers racing cannot both win.
  #
  #    STALE LOCKS ARE RECLAIMED, NOT RESPECTED. There is no release path on
  #    purpose: a trap covers a clean exit and misses SIGKILL, the watchdog's own
  #    pkill, and a power cut, so the reclaim branch has to be right anyway and a
  #    second mechanism would only be the one that is never exercised (H16 was a
  #    signal that outlived its span; a lock that outlives its holder is the same
  #    class pointed the other way -- it wedges the lane instead of killing it).
  #
  #    LIVENESS IS pid + COMMAND, never pid alone. `kill -0` on its own reports
  #    HELD after any pid reuse, and pid reuse here is not theoretical: this
  #    fleet burned ~1300 pids/minute while three lanes ran, so macOS's 99999-pid
  #    space wraps in about 75 minutes. A false HELD refuses a legitimate lane,
  #    and a dead lane has no next cycle.
  if ! ( set -o noclobber; echo $$ > "$LOCK" ) 2>/dev/null; then
    held=$(cat "$LOCK" 2>/dev/null)
    case "$held" in
      ''|*[!0-9]*) held='' ;;                      # corrupt lock: treat as stale
      "${KF_LOCK_OWNER:-}") held='' ;;             # my own pre-detach parent
      *) ps -p "$held" -o command= 2>/dev/null | grep -q 'run_loop\.sh' || held='' ;;
    esac
    if [ -n "$held" ]; then
      echo "run_loop.sh: CALLSIGN ${CALLSIGN} is HELD by live launcher pid ${held}." >&2
      echo "  Two lanes on one callsign share .loop_signal.${CALLSIGN}," >&2
      echo "  .loop_exit.${CALLSIGN} and .loop_blocks.${CALLSIGN} -- either can consume" >&2
      echo "  the other's terminal signal -- and both sign CHANNEL.md as the same atom." >&2
      echo "  Use a different callsign, or stop pid ${held} first." >&2
      exit 1
    fi
    echo $$ > "$LOCK"                              # holder is dead: reclaim
  fi
  # The detached child re-execs this script and must not refuse itself. It is
  # told which pid it is inheriting rather than guessing: PPID is useless here
  # because the double fork reparents it to init, and reusing KF_DETACHED for
  # this was the first attempt and was wrong -- see below.
  export KF_LOCK_OWNER=$$
if [ -z "${KF_DETACHED:-}" ]; then
  export KF_DETACHED=1
  ( nohup "$0" "$@" >>"detach_${CALLSIGN:-unset}.log" 2>&1 & ) &
  sleep 1
  echo "run_loop: ${CALLSIGN:-unset} detached (survives caller teardown); log detach_${CALLSIGN:-unset}.log"
  exit 0
fi
# A LAUNCHER'S PRIVATE CONTROL VARIABLES MUST NOT REACH THE TURN (v6, H34).
# `claude -p` below inherits this process's environment, and every shell the
# agent then opens inherits it again. So KF_DETACHED=1 -- the recursion guard --
# was live inside every lane's own shell, and a launcher started BY an agent
# skipped its detach block entirely: no nohup, no reparenting, and the new lane
# dies with the session that started it, which is H6's root cause returning
# through the mechanism added to fix it. MEASURED, not reasoned: this defect ate
# four checks of the H8 suite below, which refused to go green until the variable
# was unset, and `bash -x` on the launcher printed `[ -z 1 ]` from a shell that
# had never set it. KF_LOCK_OWNER is unset for the sharper reason: it authorises
# taking over a held callsign, so leaking it into the turn hands every agent a
# key to the one lock this version exists to enforce.
unset KF_DETACHED KF_LOCK_OWNER

export CALLSIGN
LOG="loop_${CALLSIGN}.log"
EXIT_MARK=".loop_exit.${CALLSIGN}"        # written by the hook, cleared only here
BEAT=".heartbeat.${CALLSIGN}"             # mtime = last turn start; watch this for staleness
MAX_TURN=${MAX_TURN:-3600}                # seconds before a turn is called wedged
command -v claude >/dev/null || { echo "claude CLI not found"; exit 1; }

# BRIEF_FILE is set and REQUIRED above the detach (defect 8), because a refusal
# down here is written into detach_$CALLSIGN.log after the caller has already
# been told the lane started. The original motivation stays where the check is:
# AGENT-2's lane definition lived only inside HANDOFF.md, which is contested by
# two writers, and a lane was spawned onto an already-held callsign because
# nothing at launch said who was live.

fails=0
# PER-LANE STOP (H31). `touch STOP` is fleet-wide, and until now that was the only
# stop that existed -- so there was no way to retire ONE lane. Worse, since H6's
# self-detach the wrapper is reparented to init, so killing a lane's claude child
# does not kill the lane: the wrapper respawns it. That is how `ok-1`, a probe lane
# spawned by accident, survived being killed and is still running. Killing the
# child is not killing the lane; this is.
while [ ! -f STOP ] && [ ! -f "STOP.${CALLSIGN}" ]; do
  rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK" ".loop_signal.${CALLSIGN}"
  date +%s > "$BEAT"
  started=$(date +%s)

  # The prompt MUST keep the literal "You are ${CALLSIGN}." prefix — the watchdog
  # below targets the turn with pkill -f on exactly that string, so that it can
  # never match the other lane or a human's interactive session.
  ( claude -p "You are ${CALLSIGN}. Read CLAUDE.md, then MISSION_LOOP.md, then HANDOFF.md if present, then run cycles per the loop contract.

The harness evolves with the codebase (MISSION_LOOP §12). It is the instrument that runs every other instrument, and it had never been attacked before 2026-08-17 — it was carrying an inert Stop hook, a launcher whose supervision had never been exercised, and re-entry that depended on remembering one call per turn. So: a harness defect is a class-H WORK_QUEUE row, not a fix you make in passing. Fix the CLASS and not the site — name the defect class in one line, grep the whole harness for it, and post the class to livechat.log so the other lane greps its own tree. Resolve every reference to a section, spec or file mechanically rather than by eye. Any harness component you touch keeps a runnable check that fails when it breaks, and gains a version bump with a rationale block naming the defect removed. At least every fourth ATTACK cycle targets the loop itself rather than a spike.

A wrong number gets retracted by the next cycle. A dead lane has no next cycle.
$([ -f "$BRIEF_FILE" ] && printf '\n--- your spawn brief, %s ---\n' "$BRIEF_FILE" && cat "$BRIEF_FILE")
$([ -s "$INBOX" ] && printf '\n--- UNREAD MESSAGES addressed to you. Act on these before selecting a queue item; reply over the session bus (fleet/registry.tsv maps callsign to socket) or with spikes/harness/send.sh ---\n' && cat "$INBOX")" \
      --dangerously-skip-permissions 2>&1 | tee -a "$LOG" ) &
  # Archived AFTER the prompt is built, so a crash before the turn starts cannot
  # silently eat mail: the file is only moved once its contents are in the prompt.
  if [ -s "$INBOX" ]; then
    cat "$INBOX" >> "inbox/archive/${CALLSIGN}.log"
    rm -f "$INBOX"
  fi
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
rm -f "$BEAT"        # a retired lane must not leave a heartbeat that reads as live
echo "loop stopped (${CALLSIGN})"
