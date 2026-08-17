#!/usr/bin/env bash
# bringup.sh — establish the fleet: verify roles, clear stale state, launch what
# is missing, then report quorum. IDEMPOTENT: safe to run when everything is
# already up, which is the property that makes it usable from launchd at boot.
#
# WHY THIS EXISTS. Every lane in this project has been launched by hand, one
# `CALLSIGN=X ./run_loop.sh` at a time, and every failure mode came from that:
#   * a lane spawned onto a callsign another agent already held (H8), because
#     nothing checked before launching;
#   * a probe lane spawned by accident during a test and still running hours
#     later with no role definition (`ok-1`, H32);
#   * three lanes dead with .heartbeat.* 35 minutes stale and nothing reporting
#     it (H6), because the supervisor was a child of the session that started it;
#   * a stale terminal signal killing a relaunched lane at its FIRST turn end
#     while logging "terminal signal, exiting" as though the span had finished
#     (H16).
# A bring-up that checks preconditions and refuses is the mechanical form of all
# four. §12.3: a rule without a runnable check is a promise.
#
# usage:
#   sh spikes/harness/bringup.sh              # verify + launch what is missing
#   sh spikes/harness/bringup.sh --check      # verify only, launch nothing
#   sh spikes/harness/bringup.sh --lanes "AGENT-1 ATTACKER-1"
#
# exit 0 = every declared lane is up. non-zero = at least one is not, and why.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

# FOUR declared lanes. `ok-1` was UNDECLARED for hours -- spawned by an ATOM-3
# probe of this very launcher, killed at the child and respawned by its detached
# wrapper (H31) -- and is declared now because it had already closed H13, the
# runaway-fuse race, while nobody had given it a role. It owns class H: that class
# was held by an interactive session that cannot run cycles, so its rows
# accumulated to 29. A queue class whose owner cannot work it is not owned.
# H38 (reported by ok-1, verified by AGENT-1 2026-08-17). This list was
# HARDCODED while ../../roster.txt is the sanction file, so the repo had TWO
# supervisors that could disagree -- and did: this one carried `ok-1`, which
# run_loop.sh:117 refuses against the roster, so it would report starting a lane
# its own launcher cannot start. run_loop.sh asserts "roster.txt is the sanction,
# and it is the same file bringup.sh starts from, so the two ends cannot drift."
# That sentence was TRUE of ./bringup.sh and FALSE of this copy, and AGENT-1
# wrote it without checking there was only one. A claim about "the" file, in a
# repo holding two, is the H18 ambiguous-namespace class again.
# Now read from the roster; the hardcoded list survives only as the fallback for
# a tree with no roster.txt, and $LANES still overrides for tests.
_ROSTER="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/roster.txt"
if [ -z "${LANES:-}" ] && [ -f "$_ROSTER" ]; then
  LANES="$(sed 's/#.*//' "$_ROSTER" | awk 'NF{print $1}' | tr '\n' ' ')"
fi
LANES=${LANES:-"AGENT-1 AGENT-2 ATTACKER-1 ATOM-3 ok-1"}
CHECK_ONLY=no
while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK_ONLY=yes ;;
    --lanes) shift; LANES="$1" ;;
    *) echo "bringup: unknown arg $1"; exit 2 ;;
  esac
  shift
done

problems=0
note() { printf '  %-9s %s\n' "$1" "$2"; }
fail() { problems=$((problems+1)); note FAIL "$1"; }

# v2 (H6, ATOM-3, 2026-08-17). CLASS: A CENSUS THAT CANNOT SEE ITS OWN OBSERVER.
# Every lane lookup here was `pgrep -f "You are $l\."`, and `man pgrep` (-a)
# says: "the current pgrep or pkill process and all of its ancestors are
# excluded". A lane running this script is its own lookup's ancestor
# (claude -p -> bash -> bringup.sh -> pgrep), so the ONE lane guaranteed alive
# read as absent. Measured in ./bringup.sh, which had the identical line:
# `ATOM-3 DOWN, quorum 3/4` reported from inside ATOM-3, pid 44527 live.
# HERE IT IS WORSE THAN A WRONG COUNT: section 8's absent branch runs
# `CALLSIGN="$l" ./run_loop.sh`, so a lane running its own bring-up launches a
# SECOND launcher on its own held callsign -- H8, the defect section 8's own
# header says it exists to prevent. `.loop_lock` only covers lanes started by
# run_loop.sh v6+; the four lanes live right now predate it and hold no lock.
# `ps` has no ancestor rule. Snapshot taken before the search so the searcher
# cannot match itself; `grep -F` keeps the trailing period literal so AGENT-1
# never matches a future AGENT-10.
lane_pid() {
  _snap=$(ps -eww -o pid=,command= 2>/dev/null)
  printf '%s\n' "$_snap" | grep -F "You are ${1}." | awk 'NR==1{print $1}'
}

# lane_pid takes NR==1, so it answers "is at least one alive" and is blind to
# TWO processes holding one callsign -- which is H8, the thing section 8 exists to
# prevent, invisible to the lookup that guards it. Observed: a launcher probe left
# two `ok-1` running and bring-up reported the fleet healthy at 5/5.
# Same snapshot, so the count cannot disagree with the pid it reports.
lane_count() {
  _snap=$(ps -eww -o pid=,command= 2>/dev/null)
  printf '%s\n' "$_snap" | grep -cF "You are ${1}."
}

echo "PRECONDITIONS"

# 1 · The fleet-wide kill switch outranks a bring-up. Launching into STOP would
#     start lanes that exit at their first turn end, which looks like a crash.
if [ -f STOP ]; then
  fail "STOP is present — the operator halted the fleet. rm STOP to resume."
  echo; echo "bringup: refusing to launch into a halted fleet"; exit 1
fi
note ok "no fleet STOP"

# 2 · ROLES. run_loop.sh refuses a lane with no brief (H30), so a missing brief
#     is a launch failure and not a warning. Checked here so the report names the
#     lane rather than leaving the operator to read a launcher refusal.
for l in $LANES; do
  if [ -f "prompts/$l.md" ]; then
    note ok "role $l — prompts/$l.md ($(wc -l < "prompts/$l.md" | tr -d ' ') lines)"
  else
    fail "role $l — prompts/$l.md MISSING; run_loop.sh will refuse to launch it"
  fi
done

# 3 · THE UNTRACKABLE HALF OF THE HARNESS. `.git/hooks/` cannot be tracked in
#     git, so the installed pre-commit/commit-msg gates do NOT arrive by pull or
#     clone -- and `test_loop_gate.sh` fails when the installed copy has drifted
#     from its tracked source. Observed on this very bring-up: the tracked source
#     had moved to v5 (H27) and the installed copy was stale, so the suite failed
#     and bring-up correctly refused. Installed here rather than reported, because
#     this is the one part of the harness a fresh machine cannot get any other way
#     and it is precisely what breaks across a restart or a re-clone.
if [ -f spikes/harness/install_hooks.sh ]; then
  if sh spikes/harness/install_hooks.sh >/dev/null 2>&1; then
    note ok "git hooks installed/refreshed from tracked source"
  else
    fail "install_hooks.sh failed — the commit gates are not installed"
  fi
fi

# 4 · The harness must be enforceable before anything runs under it. A fleet
#     brought up on a broken gate is a fleet with no loop contract.
if sh spikes/harness/test_loop_gate.sh >/dev/null 2>&1; then
  note ok "loop contract enforceable (test_loop_gate.sh passes)"
else
  fail "test_loop_gate.sh FAILS — the loop contract is not enforceable as written"
fi

# 5 · The hook must be installed where a lane's session will actually find it.
#     It was inert for an entire session because it was registered in a directory
#     no session used, and that is the defect §14.4 records as earned.
for sj in .claude/settings.json; do
  if grep -q 'loop_gate.sh' "$sj" 2>/dev/null; then
    note ok "hook registered in $sj"
  else
    fail "hook NOT registered in $sj — turns would end freely, no loop at all"
  fi
done

# 6 · STALE TERMINAL SIGNALS (H16). A signal that outlived its span is live
#     ammunition for the next one: the hook consumes it at the first turn end and
#     the lane exits having done no work, logging a clean-looking exit. run_loop.sh
#     clears these at turn start, but a signal for a lane we are ABOUT to start
#     should be gone before the launch so the state the operator sees is true.
for f in .loop_signal.* .loop_exit.*; do
  case "$f" in *'*'*) continue ;; esac
  case "$f" in *.last) continue ;; esac
  note cleared "stale $f ($(tr -d '\n' < "$f" 2>/dev/null | head -c 20))"
  rm -f "$f"
done

# 7 · LOAD. Not a launch blocker — §3 says gates are respected, never waited on,
#     and load-insensitive work is always available. But a fleet brought up on a
#     loaded machine produces invalid timings, and S9 is the canonical case: every
#     timing taken on a loaded machine, 5.3x off. So it is reported loudly.
if [ -x spikes/quiet.sh ] || [ -f spikes/quiet.sh ]; then
  if sh spikes/quiet.sh >/dev/null 2>&1; then
    note ok "quiet.sh passes — load-bound measurement is valid"
  else
    note WARN "quiet.sh REFUSES — no load-bound measurement is valid; lanes must"
    note ""   "         prefer load-insensitive work (§3). Not a launch blocker."
  fi
fi

echo
echo "LANES"

# 8 · CALLSIGN ALLOCATION (H8). Never launch onto a held callsign. A CLAIM whose
#     signature is ambiguous destroys the only mechanism preventing two lanes
#     doing the same work -- and it has happened twice, once producing two spikes
#     numbered G25.
started=0
for l in $LANES; do
  live=$(lane_pid "$l")
  if [ "$(lane_count "$l")" -gt 1 ]; then
    # Count AND list from ONE observation. The count used the snapshot helper
    # while the list re-ran `ps`, so the list saw its own grep and disagreed with
    # the count beside it -- 2 vs 3 in the same sentence. Two numbers from two
    # observations of a moving system is how an instrument contradicts itself.
    _dup=$(ps -eww -o pid=,command= 2>/dev/null)
    fail "$l -- $(lane_count "$l") processes hold this callsign: $(printf '%s\n' "$_dup" | grep -F "You are ${l}." | grep 'claude -p' | awk '{print $1}' | tr '\n' ' ')"
    note "" "  H8. Retire the newer at its WRAPPER CHAIN, not its child -- killing"
    note "" "  the child respawns it (H31). \`ps -o etimes=\` is not a macOS keyword."
    continue
  fi
  if [ -n "$live" ]; then
    beat="n/a"
    [ -f ".heartbeat.$l" ] && beat="$(( $(date +%s) - $(cat ".heartbeat.$l") ))s"
    note up "$l — pid $live, turn age $beat  (already held; not relaunching)"
    continue
  fi
  if [ ! -f "prompts/$l.md" ]; then
    fail "$l — down, and cannot be started without a brief"
    continue
  fi
  if [ -f "STOP.$l" ]; then
    note halted "$l — STOP.$l present; retired on purpose. rm STOP.$l to resume."
    continue
  fi
  if [ "$CHECK_ONLY" = yes ]; then
    note DOWN "$l — would launch (not launching, --check)"
    problems=$((problems+1))
    continue
  fi
  CALLSIGN="$l" ./run_loop.sh >/dev/null 2>&1
  started=$((started+1))
  note launched "$l — detached"
done

# 9 · VERIFY the launch rather than trusting it. A launcher that printed
#     "detached" and exited 0 without starting anything is exactly the shape this
#     repo keeps finding: a passing check and an inert check are the same
#     observation.
if [ "$started" -gt 0 ]; then
  sleep 6
  echo
  echo "VERIFY"
  for l in $LANES; do
    [ -f "STOP.$l" ] && continue
    p=$(lane_pid "$l")
    if [ -n "$p" ]; then
      pp=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
      note ok "$l — pid $p, heartbeat $([ -f .heartbeat.$l ] && echo present || echo MISSING)"
    else
      fail "$l — launched but no process; see detach_$l.log"
    fi
  done
fi

# 10 · UNDECLARED LANES. The launcher gates entry on a brief; nothing audited what
#     was already inside, which is how `ok-1` ran for hours with no role (H32).
echo
echo "AUDIT"
# `ps`, not `pgrep`: the AUDIT FOR UNDECLARED LANES could not see the lane
# running it, because pgrep excludes its own ancestors (H6). So a lane that
# was itself off-roster -- exactly ok-1's case, which is why this block was
# written -- audited the fleet and reported itself absent.
ps -eww -o pid=,command= 2>/dev/null | grep -F 'claude -p' | awk '{print $1}' | while read -r p; do
  cs=$(ps -ww -o command= -p "$p" 2>/dev/null | sed -n 's/.*You are \([A-Za-z0-9._-]*\)\..*/\1/p')
  [ -z "$cs" ] && continue
  case " $LANES " in *" $cs "*) continue ;; esac
  printf '  %-9s %s\n' UNDECLARED "$cs (pid $p) is running and is not in LANES."
  # CHECK, do not assert. This branch printed "no prompts/$cs.md" as a fixed
  # string and was caught claiming that about ok-1, whose brief is 199 lines. A
  # message that states a fact it never checked is the same defect as a control
  # that reports a verdict it never measured -- and it was in the audit whose
  # entire job is telling the operator what is true.
  if [ -f "prompts/$cs.md" ]; then
    printf '  %-9s %s\n' "" "  HAS a brief (prompts/$cs.md); add it to LANES or it stays unaudited."
  else
    printf '  %-9s %s\n' "" "  no prompts/$cs.md, so nothing defines its role."
  fi
  printf '  %-9s %s\n' "" "  stop it with: touch STOP.$cs   (killing the child will NOT work — H31)"
done

echo
if [ "$problems" -eq 0 ]; then
  echo "bringup: fleet established — $(echo $LANES | wc -w | tr -d ' ') lane(s) up"
  exit 0
fi
echo "bringup: $problems problem(s) — fleet NOT fully established"
exit 1
