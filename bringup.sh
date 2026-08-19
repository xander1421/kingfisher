#!/usr/bin/env bash
# THERE ARE TWO `bringup.sh` IN THIS REPO AND THIS IS THE ONE THAT RUNS (H44).
#   ./bringup.sh                    <- this file. TRACKED. The LOADED LaunchAgent
#                                      `com.kingfisher.bringup` names this path;
#                                      verified with `launchctl list`. Reconciler:
#                                      census + start what is missing.
#   spikes/harness/bringup.sh       <- ALSO TRACKED. The PRE-FLIGHT one: installs
#                                      the untrackable .git/hooks, runs
#                                      test_loop_gate.sh, clears stale signals,
#                                      audits undeclared lanes. Named by
#                                      `CHANNEL.md:182`'s `DONE H6b` and by
#                                      spikes/harness/net.kingfisher.fleet.plist,
#                                      which is PROPOSED and NOT installed --
#                                      `ls ~/Library/LaunchAgents` confirms.
#
# CORRECTED 2026-08-17, ATOM-3, against this header's own first draft, which said
# `spikes/harness/bringup.sh` was "UNTRACKED, 228 lines" and this file "163
# lines". THREE FALSE FACTS IN THE HEADER OF THE ROW THAT IS ABOUT THESE TWO
# FILES. It had been tracked since 600d138 (13:56), 28 minutes before I wrote
# "UNTRACKED", and the two counts were 273 and 230 at HEAD. All three were
# measured once, early, and then RESTATED from memory in four documents -- the
# H44 queue row, `spikes/H6_liveness/RESULT.md:174`, `HANDOFF.ATOM-3.md:79` and
# here. That is CLAUDE.md's "claim decay across documents", which it names as one
# of the three things no tool catches, occurring inside the row whose subject is
# the two files. CLASS: A PROSE HEADER ASSERTING A CHECKABLE FACT ABOUT ANOTHER
# ARTIFACT, WITH NOTHING CHECKING IT. The line counts are GONE rather than
# updated: a line count of a file in the same repo is stale on the next edit and
# tells a reader nothing `wc -l` would not. What is left is the two facts that
# decide which file you want, and C10/C11 of
# `spikes/H6_liveness/test_h44_check_is_readonly.sh` now check both mechanically
# -- tracked status, and which path the LOADED LaunchAgent actually names.
# They no longer disagree about the fleet: both read `roster.txt` and both use the
# same `ps`-based `lane_pid` (H6). Consolidating them to one implementation is
# H58 -- this said H55, which was never a row and is now another lane's id;
# corrected under §12.4, see the block at the top of spikes/harness/bringup.sh.
# Changing which path launchd runs is a human action (§10, outside the
# workspace), which is why the entry point was settled by MEASURING launchd
# rather than by choosing.
#
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
# v2 (H6, ATOM-3, 2026-08-17). This was 2100 (35 min), "H6's threshold, same
# number run_loop.sh cites" -- and 35 min is the number from the POST-MORTEM of a
# dead fleet, not a threshold this file can act on. `.heartbeat.$CALLSIGN` is
# written ONCE per turn, at turn start (run_loop.sh:263), and a turn is legal
# until MAX_TURN=3600. So every threshold below 3600 fires on a healthy long
# turn, and no threshold above it beats the watchdog that already kills at 3600.
# The beat cannot be a lane-death detector at any setting.
#
# What it CAN detect, and now does: a beat older than MAX_TURN means the
# watchdog did not fire -- the turn outlived the only mechanism that bounds it.
# That is a real alarm with no healthy reading, and it is the one an external
# watcher cannot get from `ps`. Liveness moved to lane_pid/lane_lock_pid below,
# which need no threshold at all.
MAX_TURN_SECS=3600     # must track run_loop.sh's MAX_TURN default; asserted by test_h6_selfblind.sh
STALE_SECS=$(( MAX_TURN_SECS + 300 ))

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
#
# `ps`, NOT `pgrep` (H6, v2). CLASS: A CENSUS THAT CANNOT SEE ITS OWN OBSERVER.
# `man pgrep`, flag -a: "the current pgrep or pkill process and all of its
# ancestors are excluded". A lane running this census is ALWAYS its own census's
# ancestor -- claude -p -> bash -> bringup.sh -> pgrep -- so `pgrep` returned
# nothing for the one lane guaranteed to be alive.
#   MEASURED from inside ATOM-3, 2026-08-17: `./bringup.sh --check` printed
#   `ATOM-3 DOWN`, `quorum: 3/4`, exit 1, while `ps -eww` showed pid 44527
#   carrying `You are ATOM-3.` and `.loop_lock.ATOM-3` held its live wrapper.
#   The other three lanes, none of them ancestors, resolved correctly -- so the
#   failure is invisible unless the observer is inside the fleet it is counting.
#   Two-sided control in spikes/H6_liveness/: same pattern, same binary, marker
#   as ancestor -> pgrep [] / ps [3 pids]; marker as descendant -> both find it.
#   WORSE THAN A WRONG REPORT: without --check the DOWN branch LAUNCHES, so a
#   lane running its own bring-up relaunches its own callsign. That is H8, and
#   `.loop_lock` only covers lanes started by run_loop.sh v6 or later.
# The correct idiom was already 100 lines below in this same file -- the
# OFF-ROSTER block has always used `ps`, which has no ancestor rule.
# Snapshot BEFORE the search so the searcher cannot match itself (the first two
# runs of the control above failed exactly that way: `grep -v grep` deleted the
# target because the target's argv contained the word `grep`). `grep -F` keeps
# the trailing period literal.
lane_pid() {
  local snap
  snap=$(ps -eww -o pid=,command= 2>/dev/null)
  printf '%s\n' "$snap" | grep -F "You are ${1}." | awk 'NR==1{print $1}'
}

# THE RECORDED HOLDER (run_loop.sh v6 / H8): one file per callsign holding the
# loop pid. `You are X.` exists only while a turn is IN FLIGHT, so between turns
# -- and through a backoff that reaches 900s -- ps reads clear on a callsign that
# is held, and this census would call a healthy lane DOWN and relaunch it.
# ABSENCE IS UNKNOWN, NEVER CLEAR: the lanes launched before v6 carry no lock
# file at all, which is why this is a second opinion and not a replacement.
lane_lock_pid() {
  local f=".loop_lock.${1}" p
  [ -f "$f" ] || return 1
  p=$(tr -dc '0-9' < "$f")
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null && printf '%s\n' "$p"
}

beat_age() {
  local f=".heartbeat.${1}"
  [ -f "$f" ] || { echo -1; return; }
  echo $(( $(date +%s) - $(stat -f %m "$f") ))
}

# CONSECUTIVE FAILED TURNS (run_loop.sh v9 / H56). THE ONLY SIGNAL HERE THAT IS
# ABOUT THE WORK. Everything else this census reads is about the WRAPPER: the
# launcher pid, the lock it wrote, the beat it refreshes at turn start. All four
# read healthy from 14:29:20 to 15:56:02 today while every lane in the fleet ran
# `1..18` instant-exit turns on `You've hit your session limit` -- and this file
# sampled it EIGHT times inside that window and printed `quorum: 5/5`,
# `bringup: full quorum, nothing to start.`, every time. See
# spikes/H56_fleet_stall/. -1 means the file is absent, which is a launcher
# generation predating v9 (H21) and is NOT clear -- same rule as the beat.
#
# v2 (H88, AGENT-1, 2026-08-17). THE DEFECT REMOVED: THIS SENTINEL WAS COMPUTED,
# DOCUMENTED AS "NOT clear", AND READ BY A BRANCH THAT COULD NOT TELL IT FROM
# CLEAR. -1 was the whole vocabulary for "absent"; the only consumer was
# `[ "$nfail" -ge 2 ]` below, and -1 >= 2 and 0 >= 2 are both false, so ABSENT
# and HEALTHY printed a BYTE-IDENTICAL census line. MEASURED, not argued:
# spikes/H88_sentinel_branch/probe.sh drives this exact file against a synthetic
# one-lane roster and a stub process; arms A (absent) and B (nfail=0) are
# identical strings, arm C (nfail=2) is STALLED, so the census can distinguish a
# VALUE and could not distinguish NO VALUE.
#
# WHAT IT COST, and it is the same 5/5 twice: at 04:00 today ZERO
# `.loop_fails.*` existed while all 5 roster lanes held live locks, because 5 of
# 6 live launchers parsed the 14:09 body (cc1da90) and `echo 0 > "$FAILFILE"`
# first appears in 90decab (16:15, H56). So the crash-loop detector read -1 for
# the entire fleet and the census printed `quorum: 5/5` -- byte for byte the
# reading H56 recorded across its own 86-minute outage. The class survived
# inside the fix for it, in this file, for the second time.
#
# THE FIX IS A NAMED STATE AND DELIBERATELY NOT AN ALARM, pre-registered in
# CHANNEL.md before the probe existed:
#   * NEVER STALLED -- absent is the NORMAL reading for every launcher
#     generation predating v9, so alarming on it refuses quorum permanently, and
#     an always-red gate is bypassed as thoroughly as a flaky one (H14, H52).
#   * NEVER ADDED TO MISSING -- H6's "absent branch LAUNCHES" hazard: relaunching
#     a healthy lane because its counter is old is worse than a wrong number.
#   * SO: the beat's own idiom, ten lines below in this same file, where
#     `age < 0` prints NO BEAT FILE and names the four states one observation
#     covers. Two of the three sentinels here were already branched and named;
#     this was the outlier, and it was the only one aimed at a crash loop.
lane_fails() {
  local f=".loop_fails.${1}" n
  [ -f "$f" ] || { echo -1; return; }
  n=$(tr -dc '0-9' < "$f")
  [ -n "$n" ] && echo "$n" || echo -1
}

# v6 (H173, ok-1, 2026-08-19). THE DEFECT REMOVED: THE ONLY CRASH-LOOP STATE
# THIS CENSUS HAS IS "UP AND PRODUCING NOTHING", AND THE OUTAGE IT WAS WRITTEN
# FOR PRODUCED "DOWN AND BEING RESTARTED FOREVER".
#
# MEASURED over the 27h weekly-limit outage, from this fleet's own logs:
# `bringup.log` holds 163 `=== STARTING n MISSING LANE(S) ===` blocks and ZERO
# `STALLED` lines; `loop_ok-1.log` holds exactly one `exited after Ns (fail 1)`
# line per launcher generation, at the 10m17s cadence of this file's own
# `StartInterval 600`, and no `loop stopped` line anywhere. So each generation
# was dead before the next census, `pid` was empty, and the STALLED branch
# (`[ -n "$pid" ] && [ "$nfail" -ge 2 ]`) was skipped BEFORE `nfail` was read.
# Both conjuncts false, independently: a dead lane has no pid, and a lane that
# gets one turn per generation never counts past 1.
#
# SO PERSISTING `.loop_fails` ACROSS GENERATIONS DOES NOT FIX THIS, which is a
# correction to the reading this row was handed (kingfisher-60, 16:06). The
# counter is not consulted on the path a dying lane takes.
#
# THE OBSERVABLE THIS FILE ALREADY OWNS IS ITS OWN LAUNCHES. Everything else the
# census reads is written by the lane, and a lane that dies in 3 seconds writes
# nothing trustworthy; the one fact never in doubt is that THIS script started
# it, N times, and found it DOWN again every time. A healthy lane launched once
# stays up for hours -- H56's outage ran 86 minutes on ONE generation per lane.
#
# NOT AN ALARM AND NOT PERMANENT (H14/H52: an always-red gate is bypassed as
# thoroughly as a flaky one). The window rolls, and a refusal writes no new
# stamp, so FLAP_WINDOW after the last launch the lane is launched again with no
# human action. Both bounds are env-overridable so the probe drives the real
# branch instead of a reimplementation of it.
FLAP_WINDOW=${FLAP_WINDOW:-3600}   # seconds of launch history that counts
FLAP_MAX=${FLAP_MAX:-3}            # launches inside it before this file stops
lane_launches() {                  # launches of $1 within FLAP_WINDOW
  local f=".loop_launches.${1}" now n=0 t
  [ -f "$f" ] || { echo 0; return; }
  now=$(date +%s)
  while IFS= read -r t; do
    case "$t" in ''|*[!0-9]*) continue ;; esac
    [ $(( now - t )) -le "$FLAP_WINDOW" ] && n=$(( n + 1 ))
  done < "$f"
  echo "$n"
}
# v7 (H185, ok-1, 2026-08-19). WHICH LAUNCHER IS THIS LANE RUNNING? A generation
# runs the code it was STARTED with, so a fix to run_loop.sh reaches a live lane
# only at its next relaunch -- and nothing here could see that. Measured the hour
# run_loop.sh v11 landed: all five lanes were pre-v11 generations, carrying the
# process-group defect H179 had just fixed, and every one of them printed UP.
#
# THREE STATES AND EACH IS NAMED, which is H88's rule: ABSENT is not CURRENT.
# A lane started before the stamp existed reads `LAUNCHER UNRECORDED`, never
# silence -- H88's defect was exactly ABSENT and HEALTHY printing byte-identical
# lines, in this file, and it is not to be re-earned one function down.
#
# REPORTED, NEVER ACTED ON: no lane is added to MISSING and no quorum is refused
# for this. Relaunching a healthy lane because its launcher is old is H6's
# "absent branch LAUNCHES" hazard and worse than the number it reports.
# v8 (H185 ATTACK, ok-1, 2026-08-19, on my own v7 from one cycle earlier).
# DEFECT REMOVED: THREE CAUSES PRINTED ONE NAME, AND ONE OF THEM WAS NOT ABOUT
# THE LANE AT ALL. v7 returned `unrecorded` when the stamp file was missing (the
# intended meaning), when the stamp was empty or garbage, AND when
# `./run_loop.sh` could not be read from the census's cwd -- the last of which is
# a fact about THIS SCRIPT, would print for EVERY lane at once, and reads as
# "an old fleet" instead of "the instrument cannot answer".
#
# That is H88's class re-earned INSIDE the control written to prevent it: v7's
# probe asserts `unrecorded` is not silence, and the arm passes just as happily
# when the reason is that the census is standing in the wrong directory.
# spikes/H185_launcher_generation/attack.sh drives all three, two-sided.
lane_launcher() {   # current | stale <had> <now> | unrecorded | unreadable | uncomparable
  local f=".loop_launcher.${1}" had now
  now=$(shasum -a 256 ./run_loop.sh 2>/dev/null | cut -c1-16)
  [ -n "$now" ] || { echo uncomparable; return; }   # about the CENSUS, not the lane
  [ -f "$f" ] || { echo unrecorded; return; }
  had=$(awk 'NR==1{print $1}' "$f" 2>/dev/null)
  case "$had" in
    '' | *[!0-9a-f]* ) echo unreadable; return ;;
  esac
  [ "$had" = "$now" ] && echo current || echo "stale $had $now"
}
lane_launch_record() {             # called ONLY where this file actually launches
  local f=".loop_launches.${1}"
  date +%s >> "$f"
  tail -50 "$f" > "$f.tmp" && mv "$f.tmp" "$f"   # bounded: 50 stamps, not a log
}

# v3 (H43, ATOM-3, 2026-08-17). THE DEFECT: NOTHING IN THIS HARNESS OBSERVES
# WORK. Every signal it has observes the SUPERVISOR (launcher pid, .loop_lock,
# peers.sh), the TURN BOUNDARY (.heartbeat), or the TURN'S DURATION
# (.loop_fails) -- and H56's class is precisely "a health signal that observes
# the supervisor and not the work", so the class survived inside the fix for it.
#
# CONCRETELY, and it is decidable from the code without a run: `.loop_fails`
# only climbs when `run_loop.sh:422` sees `elapsed < 60`, and the STALLED branch
# below fires at `nfail >= 2`. Its own comment reads *"up and producing nothing:
# two or more consecutive turns exited under 60 s"* -- which SUBSTITUTES "exited
# under 60 s" for "producing nothing". So a lane whose turns last longer than a
# minute and produce nothing resets the counter every single turn, can never
# reach 2, and reports plain UP. **That is exactly the wedged lane H43 exists
# for**, and it is family A: the only trigger aimed at it cannot fire for it.
#
# THE OBSERVABLE IS ALREADY DEFINED BY THE MISSION and needed no invention:
# §14.2 says a big cycle is a row reaching DONE with its line in CHANNEL.md, and
# gives `grep -c '^DONE' CHANNEL.md` as the number the operator watches. This
# reads the same file per lane.
#
# NOT COMMITS. Measured before choosing, on the live fleet at 16:25: ok-1's last
# commit was 14:26 -- two hours -- while it was writing its journal that second
# and had posted `DONE H62` minutes earlier. A lane can work for hours without
# committing (that is H60's finding, not a stall), so commit recency would have
# reported a working lane as dead. The check must not repeat the error it names.
#
# AND IT DELIBERATELY HAS NO THRESHOLD. It prints the age and sets no verdict.
# H6's whole finding was that liveness needs no threshold, and H48's was that
# every threshold below MAX_TURN fires on a healthy long turn while none above
# it beats the watchdog. A work signal has the same shape -- a lane legitimately
# spends an hour on one row -- so this ADDS A COLUMN, not an alarm. The 86-minute
# outage H56 measured would have read `no DONE 86m` on all five lanes while
# every other signal read 5/5, which is the whole point: a human or a lane
# reading the census sees it, and nothing gets relaunched into a quota wall.
lane_lastwork() {
  local l=$1 n
  # The lane's own most recent CLAIM/DONE/NOTE line, by POSITION in an
  # append-only file -- CHANNEL.md carries no timestamps, so distance from the
  # end is the only ordering it actually has, and inventing a time would be
  # fiction. Reported as "lines back", which is honest about what was measured.
  [ -f CHANNEL.md ] || { echo -1; return; }
  n=$(grep -nE "^(CLAIM|DONE|NOTE|CORRECTION|ATTACK|EVIDENCE|STATUS|RENUMBERED|WITHDRAWN) [^ ]+ ${l}\b" CHANNEL.md \
        | tail -1 | cut -d: -f1)
  [ -n "$n" ] || { echo -1; return; }
  echo $(( $(wc -l < CHANNEL.md) - n ))
}

# v4 (H78, ATTACKER-1, 2026-08-17). THE DEFECT: §12.3 says every harness
# component ships a runnable check that fails when it breaks. Fifteen modules do.
# **NOTHING RAN THEM.** `pre-commit.hook:126` runs three of them in SCAN mode --
# the mode that judges the tree, never the mode that judges the checker -- and
# every other invocation in the repo is a line of `.md` prose. A mention in a
# document is not an invocation, and that distinction is the whole measurement.
# Measured cost on the day it was written: `demo8.py --selfcheck` was exiting 1,
# and had been since `ed1a68e` committed the live spike directory its positive
# control depends on. Nobody saw it because nothing looked.
#
# THIS FILE IS WHERE IT GOES BECAUSE THIS FILE IS THE ONLY AUTOMATIC PATH.
# `launchctl list` shows `com.kingfisher.bringup` LOADED and its plist names this
# script, RunAtLoad + StartInterval 600. Not the pre-commit gate: bolting
# tree-wide checks onto a gate three lanes share is `pre-commit.hook` v2's F2,
# i.e. H72.
#
# THREE PROPERTIES, EACH DELIBERATE:
#   * LAST IN THE FILE, AFTER the launch loop. Preregistered falsifier F3 was
#     "if the step can delay or block a lane launch it is worse than the gap it
#     fills". Placing it above the loop would have cost every lane ~2s per
#     reconcile; placing it here costs a launch nothing.
#   * NOT GATED. Bringup is a reconciler that STARTS lanes. Same reasoning the
#     RUNNING CODE block states for check_live_launcher.sh, and H52's: a red that
#     stops the fleet is a red everyone learns to remove.
#   * BOUNDED. `selfcheckall.py` caps each module and reports TIMEOUT as its own
#     state; `timeout(1)` does not exist on this host.
#
# v5 (H95, ATTACKER-1, 2026-08-18). DEFECT REMOVED: **THIS BLOCK HAD NEVER RUN.**
# v4 placed it last in the file and asserted that placement POSITIONALLY -- which
# was true, and is not the property that matters. `bringup.sh` has five `exit`
# statements above it; the two that carry the traffic are `:430` (`--check`, the
# census path) and `:467` (`full quorum, nothing to start.`, the steady state).
# Measured before the fix: `bringup.log` carried **26** terminal `full quorum`
# lines and **0** occurrences of the string `selfcheck`, and one of those runs
# names `pid 73799`, which started 2026-08-18 04:59:11 -- eleven hours AFTER v4
# committed (`64af5af`, 17:46). So it was unreachable, not merely not-yet-run.
#
# CLASS: A CONTROL-FLOW PROPERTY ASSERTED BY TEXT POSITION INSTEAD OF BY
# EXECUTION. v4's own rationale is the confession: *"placing it here costs a
# launch nothing"* -- it cost a launch nothing because it ran ONLY when there was
# a launch, i.e. only when the fleet was already degraded, which is the inverse
# of the property v4 was optimising for.
#
# WHY A TRAP AND NOT A MOVE. Moving the block above `:430` would fix the two
# exits that exist today and would be re-broken by the next `exit` added above
# it -- the same site-not-class repair §12.2 forbids. `trap ... EXIT` is reached
# from EVERY termination path by construction, including ones not yet written,
# and it still fires AFTER the launch loop, so v4's preregistered F3 ("the step
# must not delay a lane launch") is preserved rather than traded away. The guard
# makes it once-only; the handler runs no `exit`, so `$?` is passed through
# untouched and `--check`'s contract (`:45`, exit 1 when quorum fails) is intact.
_SELFCHECKS_RAN=0
harness_selfchecks() {
  [ "$_SELFCHECKS_RAN" = 0 ] || return 0
  _SELFCHECKS_RAN=1
echo
echo "=== HARNESS SELFCHECKS ==="
if [ -f spikes/harness/selfcheckall.py ]; then
  _sca=$(python3 spikes/harness/selfcheckall.py 2>&1); _scarc=$?
  printf '%s\n' "$_sca" | sed 's/^/  /'
  if [ "$_scarc" -ne 0 ]; then
    echo "  NOT GATED — a failing selfcheck must never stop a lane launching."
    echo "  It means the CHECKER is broken, so every verdict it has given since is"
    echo "  unattributable. Fix the module, or open a class-H row for it."
  fi
else
  echo "  selfcheckall.py ABSENT — the harness self-tests are running nowhere,"
  echo "  which is H78's original state and is not the same as passing (H40)."
fi

# H103. `idscope.py` reconciles WORK_QUEUE.md against CHANNEL.md and NOTHING RAN
# IT -- `pre-commit.hook`'s CHECKS list is refcheck/journalcheck/githygiene/
# recordloss, and `selfcheckall.py` runs `--selfcheck`, which judges the CHECKER
# and never the tree. So a module that refuses on five live divergences produced
# a verdict nobody read, which is H78's class one level up: a mention is not an
# invocation, and a SELFCHECK is not a SCAN.
#
# HERE AND NOT IN pre-commit, deliberately: idscope exits 1 on the shared
# documents today, and adding it to the gate would refuse every lane's next
# commit over rows nobody can clear alone (H14, H52). This block is ungated by
# construction, so a refusing checker is safe in it and loud in the log.
if [ -f spikes/harness/idscope.py ]; then
  echo
  echo "  --- record scope (idscope, REPORT ONLY, never gates a launch) ---"
  python3 spikes/harness/idscope.py 2>&1 | sed 's/^/  /'
fi
}

# H95. Every exit path runs the harness selfchecks exactly once.
trap harness_selfchecks EXIT

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

# 0 · THE FLEET KILL SWITCH OUTRANKS A BRING-UP (H44, ATOM-3, 2026-08-17).
# THIS FILE HAD NO `STOP` CHECK AT ALL, and it is the copy launchd actually runs
# (`com.kingfisher.bringup`, StartInterval 600). So a deliberately halted fleet
# was relaunched every ten minutes, forever: each attempt spawns a launcher that
# reads STOP at its own loop top, prints `loop stopped (X)` and exits, and
# `bringup.log` records "N lane(s) launched" for lanes that never ran a turn.
# `spikes/harness/bringup.sh` section 1 has always refused under STOP -- so the
# two copies disagreed on the single most consequential precondition there is,
# which is H44's whole point.
# MEASURED, on myself: STOP had been present since 14:11 and I ran `./bringup.sh`
# and it reported `STARTING 3 MISSING LANE(S)` and launched three. They refused
# correctly, so nothing was damaged and the launcher's own gate held -- but the
# bring-up should never have asked. The census is why: it reported the three
# lanes DOWN, and DOWN reads as "restore me" when the truth was "retired on
# purpose". Absent is not stale and halted is not dead.
if [ -f STOP ]; then
  echo "=== HALTED ==="
  printf '  fleet STOP present (%s) -- the operator halted the fleet.\n' \
    "$(stat -f '%Sm' -t '%H:%M' STOP 2>/dev/null)"
  echo "  bringup will not start anything. rm STOP to resume."
  [ "$CHECK_ONLY" = 1 ] || exit 1
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
UP=0; STALLED=0; ORPHAN=0; FLAPPING=0; MISSING=()
for lane in "${ROSTER[@]}"; do
  # TWO SOURCES, because neither alone can answer it (H6). A turn in flight is
  # visible to ps and vanishes between turns; the loop lock survives between
  # turns and does not exist for lanes started before run_loop.sh v6.
  # H120: UP is SUPERVISOR-BACKED. Prefer the lock. A turn with no live
  # supervisor is ORPHAN — one turn from gone — and must not count as quorum.
  # Not added to MISSING: launching a second supervisor over a live orphan is
  # H8 (two holders of one callsign). H121 is the watchdog that reaps it.
  # Pre-v6 launchers have no lock: a mid-turn pre-v6 lane now reads ORPHAN
  # rather than UP. That is the honest state; the lock is what H8 made the
  # holder of record.
  lock=$(lane_lock_pid "$lane")
  turn=$(lane_pid "$lane")
  if [ -n "$lock" ]; then
    pid=$lock; src="loop"
  elif [ -n "$turn" ]; then
    printf '  %-12s ORPHAN pid %-7s (turn) -- supervisor gone; not counted up\n' \
      "$lane" "$turn"
    ORPHAN=$((ORPHAN+1))
    continue
  else
    pid=""; src=""
  fi
  age=$(beat_age "$lane")
  nfail=$(lane_fails "$lane")
  # H88. -1 is "no counter on disk", which is NOT the same observation as "the
  # counter says 0" and until v2 printed the same line. Carried as a suffix
  # rather than a branch of its own because it is orthogonal to beat and work:
  # a lane can be missing its counter and stale and silent, and collapsing
  # those into one branch would hide two of them.
  fnote=''
  [ "$nfail" -lt 0 ] && fnote=' NO FAIL COUNTER -- pre-v9 launcher or never written; crash-loop detection is BLIND for this lane, not clear'
  if [ -n "$pid" ] && [ "$nfail" -ge 2 ]; then
    # STALLED IS NOT UP AND IT IS NOT DOWN. The wrapper is alive and is producing
    # nothing: two or more consecutive turns exited under 60 s. One failed turn is
    # a transient and reads as 1; there is no healthy reading of 2.
    # NOT ADDED TO MISSING, deliberately. The observed cause is an account-wide
    # quota wall with a stated reset time, and relaunching five lanes into it is
    # the "absent branch LAUNCHES" hazard H6 already recorded as worse than a
    # wrong number. Same shape as the HALTED branch below: report it, refuse
    # quorum, restore nothing.
    printf '  %-12s STALLED pid %-7s (%s) %s CONSECUTIVE FAILED TURNS -- up and producing nothing; see loop_%s.log\n' \
      "$lane" "$pid" "$src" "$nfail" "$lane"
    STALLED=$((STALLED+1))
    continue
  fi
  if [ -n "$pid" ]; then
    UP=$((UP+1))
    if [ "$age" -lt 0 ]; then
      # ABSENT IS NOT STALE, and only one of them has a timestamp. run_loop.sh
      # removes the beat on a clean exit, so absence also means retired, or
      # never started, or -- observed on ok-1, alive and mid-turn with no beat
      # file at all -- a wrapper still running a launcher generation that
      # predates the beat (H21). Four states, one observation: say so.
      printf '  %-12s UP   pid %-7s (%s) NO BEAT FILE -- retired, pre-v5 launcher, or never started%s\n' "$lane" "$pid" "$src" "$fnote"
    elif [ "$age" -gt "$STALE_SECS" ]; then
      # Not "the lane is dead" -- ps or the lock just said it is not. It means
      # the turn outlived MAX_TURN, i.e. the watchdog that exists to bound it
      # did not fire. There is no healthy reading of this.
      printf '  %-12s UP   pid %-7s (%s) WATCHDOG FAILED: turn age %ss > MAX_TURN+300 (%ss)%s\n' "$lane" "$pid" "$src" "$age" "$STALE_SECS" "$fnote"
    else
      # THE WORK COLUMN (H43). Reported beside the turn age, never instead of
      # it: turn age says the supervisor is alive, this says the lane has
      # produced something. Both, because either alone was the 5/5 lie.
      w=$(lane_lastwork "$lane")
      # H185: WHICH launcher, appended to the same line rather than a new column,
      # so a lane that is up-to-date costs no extra output and the two states
      # that are not `current` are impossible to skim past.
      case "$(lane_launcher "$lane")" in
        current)      lnote='' ;;
        unrecorded)   lnote=' LAUNCHER UNRECORDED -- generation predates the stamp (H185); not stale, UNKNOWN' ;;
        unreadable)   lnote=' LAUNCHER UNREADABLE -- .loop_launcher exists and carries no hash; the stamp is corrupt, not old' ;;
        uncomparable) lnote=' LAUNCHER UNCOMPARABLE -- ./run_loop.sh is not readable FROM THIS CENSUS CWD; this says nothing about the lane' ;;
        stale\ *)     set -- $(lane_launcher "$lane")
                      lnote=" LAUNCHER STALE -- started with ${2}, tree has ${3}; picks up the fix at its next relaunch" ;;
      esac
      if [ "$w" -lt 0 ]; then
        printf '  %-12s UP   pid %-7s (%s) turn age %ss, NO CHANNEL LINE EVER -- nothing observed of this lane%s%s\n' \
          "$lane" "$pid" "$src" "$age" "$fnote" "$lnote"
      else
        printf '  %-12s UP   pid %-7s (%s) turn age %ss, last CHANNEL line %s back%s%s\n' \
          "$lane" "$pid" "$src" "$age" "$w" "$fnote" "$lnote"
      fi
    fi
  elif [ -f STOP ] || [ -f "STOP.$lane" ]; then
    # HALTED IS NOT DOWN. A lane retired on purpose and a lane that died are the
    # same observation to `ps`, and reporting both as DOWN is what invited a
    # relaunch into a halted fleet. Not added to MISSING: nothing should restore it.
    printf '  %-12s HALTED  (%s present -- retired on purpose, not a fault)\n' \
      "$lane" "$([ -f "STOP.$lane" ] && echo "STOP.$lane" || echo STOP)"
  else
    nlaunch=$(lane_launches "$lane")
    if [ "$nlaunch" -ge "$FLAP_MAX" ]; then
      # FLAPPING IS NOT DOWN. DOWN means "start it"; this means "I already did,
      # ${nlaunch} times inside ${FLAP_WINDOW}s, and it was dead again by every
      # census". Reported and NOT added to MISSING -- the same idiom as STALLED
      # and HALTED above: report it, refuse quorum, restore nothing.
      printf '  %-12s FLAPPING -- launched %s time(s) in the last %ss and DOWN at every census; NOT relaunching\n' \
        "$lane" "$nlaunch" "$FLAP_WINDOW"
      printf '               a relaunch does not clear a quota wall or a broken launcher. Read the tail of loop_%s.log\n' "$lane"
      printf '               and detach_%s.log for the reason the generation ends. Clears itself %ss after the last launch.\n' "$lane" "$FLAP_WINDOW"
      FLAPPING=$((FLAPPING+1))
      continue
    fi
    printf '  %-12s DOWN\n' "$lane"
    MISSING+=("$lane")
  fi
done
echo "  quorum: ${UP}/${#ROSTER[@]}$([ "$STALLED" -gt 0 ] && printf ' (%s STALLED, NOT counted up)' "$STALLED")$([ "$ORPHAN" -gt 0 ] && printf ' (%s ORPHAN, NOT counted up)' "$ORPHAN")"

# FLEET OUTPUT AGE (H43), and this line exists because MY OWN FIRST FIX COULD NOT
# HAVE CAUGHT THE FAILURE IT WAS BUILT FOR. The per-lane column above reports a
# lane's last CHANNEL line as a DISTANCE FROM THE END of an append-only file. If
# nobody posts, that distance does not grow -- it FREEZES. Measured against the
# real outage: `git log -- CHANNEL.md` is EMPTY from 14:29 to 15:56 and there
# were ZERO commits of any kind in those 87 minutes, so every lane's column
# would have read the same small number at all EIGHT of bringup's samples, and
# a single census could not have told a silent fleet from a busy one. Family A,
# in the instrument I had just written to fix family A.
#
# The two answer different questions and both are kept: the per-lane distance
# says WHICH LANE IS BEHIND THE OTHERS; this says WHETHER ANYTHING IS HAPPENING
# AT ALL, and it is absolute, so one reading is enough.
#
# NO THRESHOLD, for the third time in this file: a fleet legitimately spends an
# hour on hard rows, and H48 measured what a threshold below MAX_TURN does to a
# healthy long turn. It prints the age. During the 14:29-15:56 outage this line
# would have read 0m, then 10m, then 20m ... while quorum read 5/5 at every one
# of those samples, which is the whole of H56's finding in one number.
if [ -f CHANNEL.md ]; then
  _cm=$(( $(date +%s) - $(stat -f %m CHANNEL.md) ))
  printf '  fleet output: CHANNEL.md last written %sm %ss ago (no threshold -- compare across samples)\n' \
    "$(( _cm / 60 ))" "$(( _cm % 60 ))"
fi

# IS THE CODE THEY ARE RUNNING THE CODE ON DISK? (H68, ATTACKER-1, 2026-08-17.)
#
# THE DEFECT REMOVED, and it is H56's class at a second site in the file H56
# fixed one hour earlier -- a signal about the SUPERVISOR and not the WORK. H56
# made this census refuse a lane that is up and PRODUCING NOTHING. It still said
# `quorum: 5/5` over a fleet that is up and running SUPERSEDED CODE, because
# `MISSING` is this file's only launch list and a live-but-stale lane is neither
# `MISSING` nor `HALTED`. So there was no delivery step at all: a launcher fix
# could not reach the fleet by any automatic route, and nothing said so.
#
# `check_live_launcher.sh` already answers this exactly, and MEASURED 2026-08-17:
# NO EXECUTABLE CALLED IT. `grep -rn` returned journals, HUMAN_NEEDED.md, queue
# rows and two briefs -- all prose. It fired only when a lane remembered to type
# it, which is §12.8's founding defect (re-entry depending on the agent
# remembering one call per turn) applied to a checker instead of a hook.
#
# IT DOES NOT GATE THE EXIT CODE, AND THAT IS THE DESIGN CALL, NOT AN OVERSIGHT.
# Only a human can relaunch a live lane, so this condition has a PERMANENT
# non-zero floor until they do, and H52 already recorded that a gate with a
# permanent floor is read as background noise. That is precisely what separates it
# from the STALLED branch above, which the lane itself clears when its quota
# lifts. Reported loudly, asked for in HUMAN_NEEDED.md, never gated.
echo
echo "=== RUNNING CODE ==="
# Captured in a VARIABLE and not a temp file: §10 says nothing is written outside
# the workspace, and `/tmp/...$$` was this block's first draft. Also means a
# read-only diagnostic stays read-only, which is H44's defect.
if [ -f spikes/harness/check_live_launcher.sh ]; then
  _clc=$(bash spikes/harness/check_live_launcher.sh 2>&1); _clcrc=$?
  if [ "$_clcrc" -eq 0 ]; then
    printf '%s\n' "$_clc" | grep -E '^(all |no live launcher|selection:|control:)' | sed 's/^/  /'
  else
    printf '%s\n' "$_clc" | grep -E '^(STALE|REFUSE:|selection:|control:|EDIT IN FLIGHT)' | sed 's/^/  /'
    echo "  NOT GATED (H52: a permanent non-zero floor reads as noise). Relaunch is a"
    echo "  human action -- see HUMAN_NEEDED.md. Until then every launcher fix newer"
    echo "  than those start times is committed and NOT running."
  fi
else
  echo "  check_live_launcher.sh ABSENT -- staleness unknown, which is not clear (H40)"
fi

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
  # H173: FLAPPING joins the non-zero set. A lane this file has launched three
  # times in an hour and found DOWN at every census is not a quorum, and --check
  # is what a human and `test_h44_check_is_readonly.sh` read.
  [ "${#MISSING[@]}" -eq 0 ] && [ "$ROLE_FAIL" = 0 ] && [ "$STALLED" -eq 0 ] \
    && [ "$FLAPPING" -eq 0 ] && exit 0 || exit 1
fi

# A LAUNCHER THAT DOES NOT PARSE TAKES THE WHOLE FLEET DOWN SILENTLY (H44).
# Observed today: a lane edited `run_loop.sh` in place at 14:08; three wrappers
# and every relaunch for the next ten minutes died with
# `run_loop.sh: line 173: syntax error near unexpected token '('`, straight into
# `detach_$CALLSIGN.log` where nothing reads it, while `bringup.log` recorded
# each attempt as "launched". `git commit --only` protects the shared INDEX from
# concurrent lanes; nothing protected the shared WORKING FILE from being read
# while half-written, and the launcher is the one file every lane must parse to
# exist. One `bash -n` is cheaper than an outage nobody can see.
if [ "${#MISSING[@]}" -gt 0 ] && ! bash -n ./run_loop.sh 2>/dev/null; then
  echo
  echo "bringup: REFUSING to launch -- ./run_loop.sh does not parse:"
  bash -n ./run_loop.sh 2>&1 | sed 's/^/    /'
  echo "  Every lane started from it would die at parse time, into detach_*.log."
  echo "  Someone is probably mid-edit; edit to a temp file and mv it into place."
  exit 1
fi

if [ "${#MISSING[@]}" -eq 0 ] && [ "$STALLED" -gt 0 ]; then
  # THE SENTENCE THIS REPLACES IS THE DEFECT (H56). `bringup: full quorum,
  # nothing to start.` is what this file printed eight times into bringup.log
  # while all five lanes were crash-looping on a quota wall. Nothing to START is
  # true and it is not the same claim as nothing WRONG.
  echo
  echo "bringup: ${STALLED} lane(s) STALLED -- up, and producing nothing."
  echo "  Nothing to start: a relaunch does not clear a quota wall, and five"
  echo "  lanes retrying one is how 86 minutes were lost on 2026-08-17."
  echo "  Read the tail of loop_<lane>.log for the reason the turns are exiting."
  exit 1
fi

if [ "${#MISSING[@]}" -eq 0 ] && [ "$FLAPPING" -gt 0 ]; then
  # H173. Same shape as the STALLED branch above, for the state that outage
  # actually produced: nothing to start is true, and it is not the same claim as
  # nothing wrong. 163 relaunches in 27h printed neither line.
  echo
  echo "bringup: ${FLAPPING} lane(s) FLAPPING -- launched repeatedly and dead again by every census."
  echo "  NOT relaunching them. The 27h weekly-limit outage was 163 relaunches"
  echo "  into a wall, and this file printed no STALLED line for any of them"
  echo "  because a lane that dies has no pid and never counts past fail 1."
  echo "  Read loop_<lane>.log and detach_<lane>.log for why the generation ends."
  exit 1
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
  # CLEAR STALE STATE FOR THIS LANE, GUARDED BY LIVENESS. A dead lane leaves
  # .loop_lock / .loop_blocks / .loop_exit behind, and every one of them makes
  # the NEXT launch exit silently: run_loop sees a held callsign or a blown fuse
  # and prints `loop stopped`. On 08-18 that cost an hour -- bringup reported
  # "3 launched" four times in a row while starting nothing, because the
  # launcher refused and the supervisor never contradicted itself. A human
  # cleared the files by hand each time, which is precisely the hand-holding
  # this loop is supposed to remove.
  #
  # ONLY for a lane with no live process. A lock whose pid is alive is a real
  # lock and removing it would authorise two lanes on one callsign, which is the
  # defect the lock exists to prevent. Absence of a process is checked here, not
  # assumed, and the lane is in MISSING precisely because that check already ran.
  for _f in ".loop_lock.$lane" ".loop_blocks.$lane" ".loop_exit.$lane"; do
    [ -e "$_f" ] && { rm -f "$_f"; echo "  $lane cleared stale $(basename "$_f")"; }
  done
  CALLSIGN="$lane" ./run_loop.sh &
  lane_launch_record "$lane"      # H173: the one fact this file never has to trust a dying lane for
  echo "  $lane launched"
  sleep 2      # stagger: four lanes racing the same git index is H19
done
echo
echo "re-check with: ./bringup.sh --check"
