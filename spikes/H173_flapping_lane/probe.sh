#!/usr/bin/env bash
# H173 -- ok-1, 2026-08-19.
#
# CLAIM UNDER TEST: bringup.sh's only crash-loop state is STALLED, which is
# `[ -n "$pid" ] && [ "$nfail" -ge 2 ]`. A lane that DIES every generation has no
# pid and never counts past 1, so the branch is skipped before `nfail` is read,
# DOWN falls through to MISSING, and the fleet is relaunched into the wall every
# 600s. Measured over the 27h outage: 163 STARTING blocks, 0 STALLED lines.
#
# FALSIFIERS, stated in CHANNEL.md before this file existed:
#   F1 any existing branch already refuses to relaunch a repeatedly-launched
#      lane -> withdraw.  (Answered by ARM D: the pre-fix file says DOWN.)
#   F3 a planted flap fixture that does not produce FLAPPING -> the branch is inert.
#   F4 stamps older than the window must still relaunch -> not an always-red gate.
#   F5 a DOWN lane with no history must still be launched -> the fix must not
#      break bring-up itself.
#
# WHY A SANDBOX (H88's harness, reused rather than rewritten): writing
# `.loop_launches.<lane>` for a real lane is A23 -- the instrument perturbing
# what it observes -- and another lane's per-lane state, which H19/H66 make not
# mine to write. Synthetic one-lane roster, everything inside the workspace (§10).
#
# usage: bash spikes/H173_flapping_lane/probe.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }

setup() {   # setup <target-file>
  rm -rf "$SB"; mkdir -p "$SB/prompts"
  cp "$1" "$SB/bringup.sh"
  printf 'PROBE-1\n' > "$SB/roster.txt"
  printf 'synthetic lane, H173 probe. Not a real brief.\n' > "$SB/prompts/PROBE-1.md"
  printf 'NOTE PROBE-1 synthetic\n' > "$SB/CHANNEL.md"
}
stamps() {  # stamps <count> <age-seconds>
  local n=$1 age=$2 now; now=$(date +%s)
  rm -f "$SB/.loop_launches.PROBE-1"
  while [ "$n" -gt 0 ]; do echo $(( now - age )) >> "$SB/.loop_launches.PROBE-1"; n=$(( n - 1 )); done
}
arm() { ( cd "$SB" && FLAP_WINDOW=3600 FLAP_MAX=3 bash ./bringup.sh --check 2>&1; echo "EXIT=$?" ); }
lane_line() { grep -E '^ +PROBE-1' || true; }

echo "=== TARGET: the live bringup.sh ==="
setup "$ROOT/bringup.sh"
h_live=$(shasum -a 256 "$ROOT/bringup.sh" | awk '{print $1}')
h_copy=$(shasum -a 256 "$SB/bringup.sh"   | awk '{print $1}')
[ "$h_live" = "$h_copy" ] && ctl C1 PASS "sandbox copy == live bringup.sh (${h_live:0:16})" \
                          || ctl C1 FAIL "sandbox copy DIFFERS -- the probe measures the wrong file"
# CAN FAIL BECAUSE: edit the copy after cp and it goes red.

# C2 (A29) -- a probe that cannot show it reached its branch has produced no
# evidence. PROBE-1 has no process, so the census must not call it UP; if it
# does, every arm below is measuring the UP path.
stamps 0 0
L=$(arm | lane_line)
case "$L" in
  *" UP "*) ctl C2 FAIL "census calls PROBE-1 UP: '$L' -- the DOWN branch is never reached" ;;
  *PROBE-1*) ctl C2 PASS "census reaches the DOWN branch for PROBE-1" ;;
  *) ctl C2 FAIL "census printed no PROBE-1 line at all: roster not read" ;;
esac

# F5 -- a lane DOWN with no launch history is still launched.
case "$L" in
  *DOWN*) ctl F5 PASS "no history -> DOWN (still launched)" ;;
  *)      ctl F5 FAIL "no history -> '$L' -- the fix broke first launch" ;;
esac

# F3 -- 3 launches inside the window, dead at census -> FLAPPING, not DOWN.
stamps 3 60
L=$(arm | lane_line)
case "$L" in
  *FLAPPING*) ctl F3 PASS "3 launches in 3600s -> FLAPPING, not added to MISSING" ;;
  *)          ctl F3 FAIL "3 launches in 3600s -> '$L' -- the branch is inert" ;;
esac
E=$(arm | tail -1)
[ "$E" = "EXIT=1" ] && ctl F3b PASS "FLAPPING refuses quorum (--check exit 1)" \
                    || ctl F3b FAIL "FLAPPING exits $E -- a lane bringup keeps restarting reads as a healthy fleet"

# F4 -- the same 3 launches, older than the window: self-clearing, launch again.
stamps 3 7200
L=$(arm | lane_line)
case "$L" in
  *DOWN*)     ctl F4 PASS "3 launches 7200s ago -> DOWN (window rolled, self-clearing)" ;;
  *FLAPPING*) ctl F4 FAIL "stale stamps still FLAPPING -- an always-red gate (H14/H52)" ;;
  *)          ctl F4 FAIL "unexpected: '$L'" ;;
esac

# F1 / two-sided -- the SAME fixture against the pre-fix file. If it also says
# FLAPPING there is no defect and the row is withdrawn; a one-sided green proves
# only that today is green (A29 applied to a repair).
# PINNED, NOT `HEAD`. A `HEAD:bringup.sh` arm stops being two-sided the moment
# this fix is committed, and a check that cannot run after its own commit is not
# a check. 85d393b is the last commit carrying the pre-FLAPPING census.
PREREV="${KF_H173_PREREV:-85d393b}"
echo "=== TARGET: ${PREREV}:bringup.sh (pre-fix, pinned) ==="
git -C "$ROOT" show "${PREREV}:bringup.sh" > "$SPIKE/bringup.pre.sh" || exit 2
grep -q 'FLAPPING' "$SPIKE/bringup.pre.sh" \
  && { echo "  REFUSING: ${PREREV} already carries FLAPPING -- wrong rev, the arm is not two-sided"; exit 2; }
grep -q 'MISSING+=' "$SPIKE/bringup.pre.sh" \
  || { echo "  REFUSING: ${PREREV}:bringup.sh has no MISSING branch -- not the file this row is about"; exit 2; }
setup "$SPIKE/bringup.pre.sh"
stamps 3 60
L=$(arm | lane_line)
case "$L" in
  *DOWN*) ctl F1 PASS "pre-fix: the same fixture is DOWN -- relaunched, which is the defect" ;;
  *)      ctl F1 FAIL "pre-fix: '$L' -- the premise is wrong, withdraw H173" ;;
esac

rm -rf "$SB" "$SPIKE/bringup.pre.sh"
echo
[ "$fail" = 0 ] && echo "H173 probe: all arms as stated" || echo "H173 probe: FAILED"
exit "$fail"
