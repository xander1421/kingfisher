#!/usr/bin/env bash
# test_h43_work_signal.sh — H43, ATOM-3, 2026-08-17.
#
# THE DEFECT UNDER TEST. Nothing in this harness observed WORK. Every signal it
# had observed the SUPERVISOR (launcher pid, `.loop_lock`, `peers.sh`), the TURN
# BOUNDARY (`.heartbeat`), or the TURN'S DURATION (`.loop_fails`). H56's own
# class is "a health signal that observes the supervisor and not the work", so
# the class survived inside the fix for it.
#
# DECIDABLE FROM THE CODE, BEFORE ANY RUN, which is why this is family A:
# `.loop_fails` climbs only where `run_loop.sh` sees `elapsed < 60`, and
# bringup's STALLED branch fires at `nfail >= 2`. Its comment reads "up and
# producing nothing: two or more consecutive turns exited under 60 s" — which
# SUBSTITUTES "exited under 60 s" for "producing nothing". A lane whose turns
# last over a minute and produce nothing resets the counter every turn, can
# never reach 2, and reports plain UP. That is exactly the wedged lane H43
# exists for: the only trigger aimed at it cannot fire for it.
#
# FALSIFIERS, STATED BEFORE THE RUN:
#   F1  if any pre-existing signal observes work, the row is wrong. Decided by
#       grep over the harness for a reader of DONE lines / commits / output,
#       not by my reading of the design. (Ran: none.)
#   F2  THE KILLING ONE, and it fired against my FIRST fix. Would the new signal
#       have caught the 87-minute outage H56 measured? The per-lane column
#       reports distance from the END of an append-only file, so when nobody
#       posts it FREEZES rather than growing, and all eight of bringup's samples
#       in that window would have read the same small number. Measured, not
#       argued: `git log -- CHANNEL.md` is EMPTY 14:29–15:56 and there were ZERO
#       commits of any kind. C4 is that case, and it is why the fleet-output
#       line exists at all.
#
# run: bash spikes/H6_liveness/test_h43_work_signal.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)
SUT="$ROOT/bringup.sh"

pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }

SCRATCH="$ROOT/spikes/H6_liveness/.h43.$$"      # inside the workspace (§10)
trap 'rm -rf "$SCRATCH"' EXIT
mkdir -p "$SCRATCH"

# The function READ OUT OF THE FILE UNDER TEST, so deleting or narrowing it
# turns these red. Retyping it here would test a private copy — the trap
# H44's C1 and H48's probe both had to be built around.
LW=$(sed -n '/^lane_lastwork() {/,/^}/p' "$SUT")
[ -n "$LW" ] || { echo "  FAIL could not extract lane_lastwork from $SUT"; exit 1; }

run_lw() {  # run_lw <lane> ; CHANNEL.md must already exist in $SCRATCH
  ( cd "$SCRATCH" && eval "$LW" && lane_lastwork "$1" )
}

echo "H43 · the census must observe WORK, not only the supervisor"
echo

# ---- C1 . a lane that has posted is found, and the distance is right --------
{ echo "CLAIM H1 AGENT-1 something"; echo "DONE H1 AGENT-1 something"; echo "NOTE x ok-1 hello"; } > "$SCRATCH/CHANNEL.md"
r=$(run_lw AGENT-1)
[ "$r" = 1 ] && ok "C1 a lane's last line is located (AGENT-1, 1 line back)" \
             || bad "C1 expected 1 line back for AGENT-1, got '$r'"

# ---- C2 . a lane that has NEVER posted is -1, not 0 -------------------------
# The two must differ. `0` means "posted on the last line" and is the healthiest
# reading there is; collapsing "never posted" into it would report the most
# invisible lane as the most active. A29: the free answer must not be the pass.
r=$(run_lw NEVER-SEEN)
[ "$r" = "-1" ] && ok "C2 a lane with no line ever reads -1, distinct from 0" \
                || bad "C2 expected -1 for a lane that never posted, got '$r'"

# ---- C3 . the FALSIFIER: the old signal cannot fire for this case -----------
# Reproduce run_loop.sh's reset and bringup's trigger from the real files, and
# show a wedged-but-slow lane can never reach the threshold. Both numbers are
# read out of the sources, so a change to either turns this red instead of
# leaving a stale constant in a test.
reset_at=$(grep -oE 'elapsed" -ge [0-9]+' "$ROOT/run_loop.sh" | grep -oE '[0-9]+$' | head -1)
trigger_at=$(grep -oE 'nfail" -ge [0-9]+' "$SUT" | grep -oE '[0-9]+$' | head -1)
if [ -z "$reset_at" ] || [ -z "$trigger_at" ]; then
  bad "C3 could not read the reset/trigger constants out of the sources"
else
  # A lane doing turns of reset_at+1 seconds that produce nothing: fails is set
  # to 0 on every turn, so the counter's ceiling is 0 and the trigger is >= 2.
  fails=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    elapsed=$(( reset_at + 1 ))
    if [ "$elapsed" -ge "$reset_at" ]; then fails=0; else fails=$(( fails + 1 )); fi
  done
  if [ "$fails" -lt "$trigger_at" ]; then
    ok "C3 falsifier fires: 10 unproductive ${reset_at}s+ turns leave fails=$fails, trigger is >=$trigger_at"
  else
    bad "C3 the old signal DOES fire for a slow unproductive lane; H43's premise is wrong"
  fi
  # Two-sided: the same arithmetic MUST reach the trigger for fast failures, or
  # C3 is an assertion about a counter that never moves under any input.
  fails=0
  for _ in 1 2 3; do
    elapsed=$(( reset_at - 1 ))
    if [ "$elapsed" -ge "$reset_at" ]; then fails=0; else fails=$(( fails + 1 )); fi
  done
  [ "$fails" -ge "$trigger_at" ] && ok "C3b and it DOES fire for fast failures (fails=$fails) -- so C3 is not a dead counter" \
                                 || bad "C3b the counter never reaches the trigger under any input; C3 proves nothing"
fi

# ---- C4 . THE ONE THAT KILLED MY FIRST FIX ---------------------------------
# A silent fleet must be distinguishable from a busy one IN A SINGLE READING.
# The per-lane distance cannot do it: with nobody posting, the file does not
# grow and every lane's number is unchanged across samples.
cp "$SCRATCH/CHANNEL.md" "$SCRATCH/CHANNEL.before"
s1=$(run_lw AGENT-1)
sleep 1                                     # time passes; nobody posts
s2=$(run_lw AGENT-1)
if [ "$s1" = "$s2" ]; then
  ok "C4 confirmed: the per-lane distance FREEZES on a silent fleet ($s1 = $s2)"
else
  bad "C4 the per-lane distance changed with no new lines; the measurement is not what I think"
fi
# ...so the census must also carry an ABSOLUTE age. Read out of the file under
# test: delete that line and this goes red.
if grep -q 'fleet output: CHANNEL.md last written' "$SUT"; then
  ok "C4b the census carries an absolute fleet-output age, which one reading CAN decide"
else
  bad "C4b no absolute fleet-output age -- a single census cannot tell silence from work"
fi

# ---- C5 . the work column is REPORTED, never a verdict ---------------------
# H6 found liveness needs no threshold; H48 found every threshold below MAX_TURN
# fires on a healthy long turn. A work signal has the same shape -- a lane may
# legitimately spend an hour on one row -- so this must not gate quorum. If it
# ever does, a slow lane gets relaunched into whatever is actually wrong, which
# is H6's own "absent branch LAUNCHES" hazard.
if grep -nE 'lane_lastwork|fleet output' "$SUT" | grep -qE 'MISSING\+=|STALLED=|exit 1'; then
  bad "C5 the work signal now gates something -- it must report, not judge"
else
  ok "C5 the work signal reports and sets no verdict (no threshold, per H6/H48)"
fi

echo
echo "-------------------------------------------------------------"
printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
