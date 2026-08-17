#!/usr/bin/env bash
# test_h6_selfblind.sh — H6, ATOM-3, 2026-08-17.
#
# CLASS UNDER TEST: A CENSUS THAT CANNOT SEE ITS OWN OBSERVER.
# `man pgrep`, flag -a: "the current pgrep or pkill process and all of its
# ancestors are excluded". Every fleet census in this repo was a `pgrep -f`, and
# a lane running a census is ALWAYS that census's ancestor
# (claude -p -> bash -> bringup.sh -> pgrep). So the one lane guaranteed to be
# alive was the one lane the census could not see.
#
# FALSIFIER, STATED BEFORE THE RUN: if `pgrep -f` returns an ancestor pid on
# this machine, the whole finding is wrong and C1 goes red. If `ps` also fails
# to return it, the probe never planted a target and C2 goes red — which is the
# case that matters, because the first two attempts at this control BOTH failed
# that way and both looked like a clean result:
#   attempt 1: the marker sat late in a long argv, past macOS `ps` line
#              truncation, so both arms read empty (A29).
#   attempt 2: the search was `grep -v grep` and the target's own argv contained
#              the string "grep", so the filter deleted the target.
# Neither was visible without a positive control. C2 is that control.
#
# run: sh spikes/H6_liveness/test_h6_selfblind.sh    (exit 0 = all pass)
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)

pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
chk()  { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 -- expected [$3] got [$2]"; fi; }

MARK=KFH6MARK
echo "H6 · a census that cannot see its own observer"
echo

# ---------------------------------------------------------------- mechanism --
# Two arms, one pattern, one binary, one machine. The ONLY difference is whether
# the marker process is an ancestor or a descendant of the searcher. The search
# pattern is written KFH6MAR[K] so that no searcher's own argv ever contains the
# literal marker — attempt 2's defect.
echo "MECHANISM"

anc=$(bash -c "${MARK}=1; sleep 0
  ps_hits=\$(ps -eww -o pid=,command= 2>/dev/null | grep -c 'KFH6MAR[K]')
  pg_hits=\$(pgrep -f 'KFH6MAR[K]' 2>/dev/null | wc -l | tr -d ' ')
  echo \"\$ps_hits \$pg_hits\"")
anc_ps=${anc% *}; anc_pg=${anc#* }

bash -c "${MARK}=1; sleep 5" &
desc_target=$!
sleep 1
desc_ps=$(ps -eww -o pid=,command= 2>/dev/null | grep -c 'KFH6MAR[K]')
desc_pg=$(pgrep -f 'KFH6MAR[K]' 2>/dev/null | wc -l | tr -d ' ')
kill "$desc_target" 2>/dev/null; wait "$desc_target" 2>/dev/null

# C2 FIRST, because it is the one that decides whether C1 means anything.
# Fails if: the marker never reached any process argv, or ps cannot report it.
if [ "$anc_ps" -ge 1 ]; then ok "C2 positive control — ps DOES see the ancestor ($anc_ps hit(s))"
else bad "C2 positive control — ps saw no ancestor marker; the probe planted nothing, C1 below is vacuous"; fi
if [ "$desc_ps" -ge 1 ] && [ "$desc_pg" -ge 1 ]; then
  ok "C2b positive control — descendant arm found by BOTH ps ($desc_ps) and pgrep ($desc_pg)"
else
  bad "C2b positive control — descendant arm: ps=$desc_ps pgrep=$desc_pg; the pattern does not match a live target"
fi

# C1. Fails if pgrep starts returning ancestors (a macOS change would break every
# claim in bringup.sh's rationale block, and this is where it surfaces).
chk "C1 mechanism — pgrep returns NOTHING for its own ancestor" "$anc_pg" "0"

# -------------------------------------------------------------------- site --
# The real lane_pid, read out of bringup.sh and executed inside a process whose
# argv carries a lane marker — i.e. the census's own ancestor is the lane it is
# looking for. Reverting bringup.sh to `pgrep` turns this red; that is C4's job.
echo
echo "SITE"
for f in bringup.sh spikes/harness/bringup.sh; do
  impl=$(sed -n '/^lane_pid() {/,/^}/p' "$ROOT/$f")
  if [ -z "$impl" ]; then bad "C3 $f — no lane_pid() found to test"; continue; fi
  got=$(bash -c ": claude -p You are KFTEST-9.
$impl
lane_pid KFTEST-9" 2>/dev/null | tr -d ' \n')
  if [ -n "$got" ]; then ok "C3 $f lane_pid() sees a lane that is its own ancestor (pid $got)"
  else bad "C3 $f lane_pid() is BLIND to its own ancestor -- the H6 defect is back"; fi
done

# ------------------------------------------------------------------- class --
# §12.2: fix the class, never the site. Any NEW census written with pgrep -f
# anywhere in the harness turns this red, including in files that do not exist
# yet. Scoped to process-census patterns; the watchdog's `pkill -f` is NOT a
# census and is deliberately out of scope (its target is a sibling, never an
# ancestor, and `kill -TERM $turn` backs it up).
echo
echo "CLASS"
hits=$(grep -rn "pgrep -f" --include='*.sh' --include='*.py' --include='*.hook' . 2>/dev/null \
       | grep -vE '^\./(\.verify_head|elders)/' \
       | grep -vE '^[^:]*:[0-9]+: *#' \
       | grep -vE 'spikes/H6_liveness/' || true)
if [ -z "$hits" ]; then
  ok "C4 no shell census in the harness uses pgrep -f"
else
  bad "C4 pgrep -f census site(s) reintroduced:"
  printf '%s\n' "$hits" | sed 's/^/         /'
fi

# C4b. The shell sweep above cannot see a Python census: whois.py calls
# sh("pgrep", "-f", "claude"), which the literal pattern misses. NAMED rather
# than quietly out of scope -- a check whose blind spot is undocumented reads as
# full coverage. whois.py is AGENT-2's (H37) and it DECLARES the limit itself;
# the assertion is that the declaration is still there, so deleting the caveat
# without fixing the call turns this red.
pysites=$(grep -rn '"pgrep"' --include='*.py' . 2>/dev/null | grep -vE '^\./(\.verify_head|elders)/' || true)
if [ -z "$pysites" ]; then
  ok "C4b no Python census uses pgrep"
elif [ "$(printf '%s\n' "$pysites" | wc -l | tr -d ' ')" = 1 ] \
     && printf '%s\n' "$pysites" | grep -q 'whois.py' \
     && grep -qi 'does not return this session\|cannot see itself\|own pid' spikes/harness/whois.py; then
  ok "C4b one Python census (whois.py) uses pgrep and DECLARES that it cannot see itself"
else
  bad "C4b Python census site(s) using pgrep with no declared self-blindness:"
  printf '%s\n' "$pysites" | sed 's/^/         /'
fi

# --------------------------------------------------------------- threshold --
# The beat is written ONCE per turn (run_loop.sh: date +%s > "$BEAT"), so any
# staleness threshold at or below MAX_TURN fires on a healthy long turn. This
# asserts the two files still agree; it goes red if either number moves.
echo
echo "THRESHOLD"
mt=$(sed -n 's/^MAX_TURN=\${MAX_TURN:-\([0-9]*\)}.*/\1/p' "$ROOT/run_loop.sh" | head -1)
ss=$(sed -n 's/^MAX_TURN_SECS=\([0-9]*\).*/\1/p' "$ROOT/bringup.sh" | head -1)
if [ -z "$mt" ] || [ -z "$ss" ]; then
  bad "C5 could not read MAX_TURN from run_loop.sh [$mt] or MAX_TURN_SECS from bringup.sh [$ss]"
elif [ "$ss" = "$mt" ]; then
  ok "C5 bringup.sh's MAX_TURN_SECS ($ss) tracks run_loop.sh's MAX_TURN ($mt)"
else
  bad "C5 MAX_TURN drift: run_loop.sh=$mt bringup.sh=$ss -- the stale threshold is computed from the wrong number"
fi

# -------------------------------------------------------------- falsifier ---
# §12.10: a check that has never been seen red is not known to be a check. Revert
# lane_pid to the defective pgrep form on an ISOLATED COPY and confirm C3 goes
# red there. If this passes, C3 above is passing for some other reason.
echo
echo "FALSIFIER (C3 must go red when the defect is restored)"
# No mktemp: H17 (does §10's "nothing outside the workspace is written" have an
# exception for /tmp scratch?) is an OPEN, undecided row, and a suite that takes
# a side on it by running is deciding it by default. The defective form is one
# line; it does not need a directory.
got=$(bash -c ': claude -p You are KFTEST-9.
lane_pid() { pgrep -f "You are ${1}\." 2>/dev/null | head -1; }
lane_pid KFTEST-9' 2>/dev/null | tr -d ' \n')
if [ -z "$got" ]; then ok "C6 restored pgrep form IS blind to its ancestor -- C3 can fail"
else bad "C6 restored pgrep form still found pid $got; C3 is not testing what it claims"; fi

echo
echo "-------------------------------------------------------------"
printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
